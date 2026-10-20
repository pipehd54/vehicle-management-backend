"""Limitador de intentos en memoria (ventana deslizante).

Protege el login contra fuerza bruta y el registro contra creación masiva de
cuentas. No requiere dependencias externas, pero es **por proceso**: con
varios workers o réplicas cada uno aplica su propio conteo. Para un despliegue
multirréplica real, migrar a un contador compartido (p. ej. Redis) manteniendo
esta misma interfaz.

Criterio de conteo:

* Solo se cuentan los **intentos fallidos** de login. Un usuario que escribe
  mal su contraseña tres veces y luego entra bien no consume cuota, y el
  tráfico legítimo no agota el límite por IP detrás de un proxy.
* El registro sí cuenta todos los intentos, porque todos crean una cuenta.
"""

import time
from collections import OrderedDict, deque

from fastapi import HTTPException, Request, status

from app.configuracion import settings

# Límites: (máximo de intentos, ventana en segundos).
LIMITE_LOGIN_POR_IP = (30, 300)
LIMITE_LOGIN_POR_CUENTA = (10, 900)
LIMITE_REGISTRO_POR_IP = (10, 3600)

# Tope de claves vivas: evita que un atacante que rote direcciones IP agote
# la memoria del proceso.
MAX_CLAVES_LIMITADOR = 4096

# Cada cuánto tiempo se revisan las ventanas caducadas.
INTERVALO_LIMPIEZA_SEG = 30

# Clave -> (intentos, duración de la ventana en segundos).
_ventanas: OrderedDict[str, tuple[deque[float], int]] = OrderedDict()
_proxima_limpieza = 0.0


def reiniciar_limitador() -> None:
    """Vacía el registro de intentos. Solo para pruebas automatizadas."""
    global _proxima_limpieza
    _ventanas.clear()
    _proxima_limpieza = 0.0


def _limpiar_ventanas_vencidas(ahora: float) -> None:
    """Retira colas expiradas incluso si el cliente no vuelve a usar la clave."""
    global _proxima_limpieza
    if ahora < _proxima_limpieza:
        return

    for clave, (intentos, duracion) in list(_ventanas.items()):
        while intentos and ahora - intentos[0] > duracion:
            intentos.popleft()
        if not intentos:
            del _ventanas[clave]

    _proxima_limpieza = ahora + INTERVALO_LIMPIEZA_SEG


def _obtener_ventana(clave: str, duracion: int) -> deque[float]:
    """Devuelve la cola de intentos de una clave, creándola si hace falta."""
    _limpiar_ventanas_vencidas(time.monotonic())

    entrada = _ventanas.get(clave)
    if entrada is None:
        while len(_ventanas) >= MAX_CLAVES_LIMITADOR:
            _ventanas.popitem(last=False)
        intentos: deque[float] = deque()
        _ventanas[clave] = (intentos, duracion)
        return intentos

    _ventanas.move_to_end(clave)
    return entrada[0]


def _supera_el_limite(clave: str, max_intentos: int, duracion: int) -> bool:
    """Indica si la clave ya alcanzó su cuota, sin contar un intento nuevo."""
    intentos = _obtener_ventana(clave, duracion)
    ahora = time.monotonic()
    while intentos and ahora - intentos[0] > duracion:
        intentos.popleft()
    return len(intentos) >= max_intentos


def _contar_intento(clave: str, max_intentos: int, duracion: int) -> None:
    """Suma un intento a la clave."""
    intentos = _obtener_ventana(clave, duracion)
    intentos.append(time.monotonic())


def _demasiados() -> HTTPException:
    """Error 429 con el mensaje estándar del limitador."""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
    )


def ip_cliente(request: Request) -> str:
    """Devuelve la IP real del cliente.

    Detrás de un proxy inverso (Railway, Nginx, un balanceador) todas las
    peticiones llegan desde la IP del proxy. Solo si esa IP está declarada en
    `TRUSTED_PROXY_IPS` se lee la cabecera `X-Forwarded-For`, y se toma
    siempre la dirección más a la derecha que no sea de otro proxy de
    confianza: así un cliente no puede falsear su propia IP.
    """
    host = request.client.host if request.client is not None else "desconocida"
    proxies = settings.trusted_proxy_ips
    if not proxies or host not in proxies:
        return host

    cabecera = request.headers.get("x-forwarded-for", "")
    direcciones = [parte.strip() for parte in cabecera.split(",") if parte.strip()]
    for direccion in reversed(direcciones):
        if direccion not in proxies:
            return direccion
    return direcciones[0] if direcciones else host


def registrar_intento_registro(request: Request) -> None:
    """Cuenta un intento de registro por IP y bloquea si se supera la cuota."""
    max_intentos, duracion = LIMITE_REGISTRO_POR_IP
    clave = f"registro:ip:{ip_cliente(request)}"
    if _supera_el_limite(clave, max_intentos, duracion):
        raise _demasiados()
    _contar_intento(clave, max_intentos, duracion)


def comprobar_limite_login(request: Request, correo: str) -> None:
    """Comprueba las cuotas de login sin contar un intento nuevo.

    Se llama antes de validar las credenciales: si la cuota ya está agotada
    ni siquiera se consulta la base de datos.
    """
    max_ip, ventana_ip = LIMITE_LOGIN_POR_IP
    max_cuenta, ventana_cuenta = LIMITE_LOGIN_POR_CUENTA
    ip = ip_cliente(request)
    clave_cuenta = f"login:cuenta:{correo.lower()}:{ip}"

    if _supera_el_limite(f"login:ip:{ip}", max_ip, ventana_ip):
        raise _demasiados()
    if _supera_el_limite(clave_cuenta, max_cuenta, ventana_cuenta):
        raise _demasiados()


def registrar_fallo_login(request: Request, correo: str) -> None:
    """Cuenta un intento de login fallido contra las cuotas de IP y de cuenta."""
    max_ip, ventana_ip = LIMITE_LOGIN_POR_IP
    max_cuenta, ventana_cuenta = LIMITE_LOGIN_POR_CUENTA
    ip = ip_cliente(request)

    _contar_intento(f"login:ip:{ip}", max_ip, ventana_ip)
    _contar_intento(f"login:cuenta:{correo.lower()}:{ip}", max_cuenta, ventana_cuenta)
