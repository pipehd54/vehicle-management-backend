"""Limitador de intentos en memoria (ventana deslizante) para login y registro.

Mitiga fuerza bruta y creación masiva de cuentas sin añadir dependencias.
Es por proceso: con varios workers o réplicas, cada uno aplica su propio
conteo. Para un despliegue multirréplica real, migrar a un contador
compartido (p. ej. Redis) manteniendo esta misma interfaz.
"""

import time
from collections import OrderedDict, deque

from fastapi import HTTPException, Request, status

# Límites: (máximo de intentos, ventana en segundos).
LIMITE_LOGIN_POR_IP = (20, 300)
LIMITE_REGISTRO_POR_IP = (10, 3600)
MAX_CLAVES_LIMITADOR = 4096
INTERVALO_LIMPIEZA_SEG = 30

_ventanas: OrderedDict[str, deque[float]] = OrderedDict()
_proxima_limpieza = 0.0


def reiniciar_limitador() -> None:
    """Vacía el registro de intentos. Solo para pruebas automatizadas."""
    global _proxima_limpieza
    _ventanas.clear()
    _proxima_limpieza = 0.0


def _duracion_clave(clave: str) -> int:
    if clave.startswith("registro:"):
        return LIMITE_REGISTRO_POR_IP[1]
    return LIMITE_LOGIN_POR_IP[1]


def _limpiar_ventanas_vencidas(ahora: float) -> None:
    """Retira colas expiradas incluso si el cliente no vuelve a usar la clave."""
    global _proxima_limpieza
    if ahora < _proxima_limpieza:
        return

    for clave, intentos in list(_ventanas.items()):
        duracion = _duracion_clave(clave)
        while intentos and ahora - intentos[0] > duracion:
            intentos.popleft()
        if not intentos:
            del _ventanas[clave]

    _proxima_limpieza = ahora + INTERVALO_LIMPIEZA_SEG


def _verificar(clave: str, max_intentos: int, ventana_seg: int) -> None:
    ahora = time.monotonic()
    _limpiar_ventanas_vencidas(ahora)
    intentos = _ventanas.get(clave)
    if intentos is None:
        # El límite total evita que claves controladas por clientes consuman
        # memoria sin cota. La estructura es una protección local best-effort;
        # despliegues con varias réplicas deben limitar en un gateway/Redis.
        while len(_ventanas) >= MAX_CLAVES_LIMITADOR:
            _ventanas.popitem(last=False)
        intentos = deque()
        _ventanas[clave] = intentos

    while intentos and ahora - intentos[0] > ventana_seg:
        intentos.popleft()
    if not intentos:
        _ventanas.pop(clave, None)
        intentos = deque()
        _ventanas[clave] = intentos

    if len(intentos) >= max_intentos:
        _ventanas.move_to_end(clave)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
        )
    intentos.append(ahora)
    _ventanas.move_to_end(clave)


def _ip_origen(request: Request) -> str:
    if request.client is not None:
        return request.client.host
    return "desconocida"


def registrar_intento_login(request: Request) -> None:
    """Limita intentos por IP sin permitir bloquear una cuenta ajena."""
    _verificar(f"login:ip:{_ip_origen(request)}", *LIMITE_LOGIN_POR_IP)


def registrar_intento_registro(request: Request) -> None:
    """Cuenta un intento de registro por IP."""
    _verificar(f"registro:ip:{_ip_origen(request)}", *LIMITE_REGISTRO_POR_IP)
