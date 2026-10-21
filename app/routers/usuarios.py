"""Endpoints de usuarios: registro, login y activación de cuentas."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_datos import get_db
from app.dependencias import requiere_admin
from app.enums import RolUsuario
from app.esquemas import (
    CambiarPassword,
    RegistroRespuesta,
    UsuarioCreate,
    UsuarioResponse,
)
from app.limitador import (
    comprobar_limite_login,
    registrar_fallo_login,
    registrar_intento_registro,
)
from app.modelos import UsuarioDB
from app.repositorio import obtener_usuario_o_404
from app.seguridad import (
    HASH_SENUELO,
    crear_token_acceso,
    obtener_hash_password,
    obtener_usuario_actual,
    verificar_password,
)

router = APIRouter()

# Respuesta única del registro: no revela si el correo ya estaba en uso.
MENSAJE_REGISTRO = "Solicitud recibida. Si los datos son válidos, será procesada."


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=RegistroRespuesta)
async def registrar_usuario(
    usuario: UsuarioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Registra una solicitud de cuenta.

    La cuenta nace inactiva y con rol de mecánico: un administrador debe
    activarla desde `PATCH /usuarios/{id}/activar`. El rol nunca se toma del
    cuerpo de la petición, de modo que no se puede escalar privilegios.
    """
    # Frena la creación masiva de cuentas desde una misma IP.
    registrar_intento_registro(request)

    nuevo_usuario = UsuarioDB(
        email=usuario.email,
        hashed_password=obtener_hash_password(usuario.password),
        rol=RolUsuario.MECANICO,
        is_active=False,
    )

    db.add(nuevo_usuario)
    try:
        await db.commit()
        await db.refresh(nuevo_usuario)
    except IntegrityError:
        await db.rollback()
        # El mismo código y cuerpo se devuelve para registros nuevos y duplicados.
        return RegistroRespuesta(mensaje=MENSAJE_REGISTRO)

    return RegistroRespuesta(mensaje=MENSAJE_REGISTRO)


@router.post("/login")
async def login(
    request: Request,
    credenciales: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Autentica a un usuario activo y devuelve un token JWT.

    Solo se cuentan los intentos fallidos contra el limitador, de modo que un
    usuario legítimo no agota la cuota por escribir mal su contraseña.
    """
    correo = credenciales.username.strip().lower()

    # Se comprueba la cuota antes de tocar la base de datos.
    comprobar_limite_login(request, correo)

    resultado = await db.execute(select(UsuarioDB).where(UsuarioDB.email == correo))
    usuario_db = resultado.scalar_one_or_none()

    # Se verifican tres condiciones en orden:
    # 1. El usuario existe en la DB.
    # 2. Su cuenta está activa (is_active=True, tras activación admin).
    # 3. La contraseña enviada coincide con el hash almacenado.
    # Si cualquiera falla, se devuelve el mismo error genérico (401) para no
    # revelar si el email existe o no en el sistema. Cuando el correo no
    # existe se compara contra un hash señuelo, de modo que el tiempo de
    # respuesta tampoco permita deducirlo.
    hash_a_comprobar = usuario_db.hashed_password if usuario_db else HASH_SENUELO
    contraseña_correcta = verificar_password(credenciales.password, hash_a_comprobar)

    if usuario_db is None or not usuario_db.is_active or not contraseña_correcta:
        registrar_fallo_login(request, correo)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Acceso denegado al taller.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = crear_token_acceso(
        data={"sub": usuario_db.email, "rol": usuario_db.rol.value}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UsuarioResponse)
async def mi_usuario(usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)):
    """Devuelve los datos del usuario autenticado.

    Es la fuente fiable de "quién soy": el rol se lee de la base de datos,
    no del token, que puede estar desfasado.
    """
    return usuario_actual


@router.post("/me/cambiar-password")
async def cambiar_password(
    datos: CambiarPassword,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Cambia la contraseña del usuario autenticado.

    Exige la contraseña actual: sin ella, un token robado permitiría
    dejar la cuenta inutilizable para su dueño.
    """
    if not verificar_password(datos.password_actual, usuario_actual.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual no es correcta.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario_actual.hashed_password = obtener_hash_password(datos.password_nuevo)
    await db.commit()
    return {"mensaje": "La contraseña se actualizó correctamente."}


@router.get("/pendientes", response_model=list[UsuarioResponse])
async def listar_cuentas_pendientes(
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Lista las cuentas registradas que aún no fueron activadas. Solo admin."""
    consulta = (
        select(UsuarioDB).where(UsuarioDB.is_active.is_(False)).order_by(UsuarioDB.id)
    )
    resultado = await db.execute(consulta)
    return list(resultado.scalars().all())


@router.patch("/{usuario_id}/desactivar", response_model=UsuarioResponse)
async def desactivar_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Desactiva una cuenta y le corta el acceso de inmediato.

    El token sigue siendo válido hasta su expiración, pero cada petición
    vuelve a leer `is_active` de la base de datos, así que la cuenta queda
    inutilizable en el acto. Solo admin.
    """
    if usuario_id == admin_actual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta.",
        )

    usuario = await obtener_usuario_o_404(usuario_id, db)
    usuario.is_active = False
    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/activar", response_model=UsuarioResponse)
async def activar_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Activa una cuenta registrada para que pueda iniciar sesión. Solo admin."""
    usuario = await obtener_usuario_o_404(usuario_id, db)
    usuario.is_active = True
    await db.commit()
    await db.refresh(usuario)
    return usuario
