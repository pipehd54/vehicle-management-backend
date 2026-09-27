from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.depends import requiere_admin
from app.models import UsuarioDB
from app.rate_limit import registrar_intento_login, registrar_intento_registro
from app.schemas import RegistroRespuesta, UsuarioCreate, UsuarioResponse
from app.security import crear_token_acceso, obtener_hash_password, verificar_password

router = APIRouter()
MENSAJE_REGISTRO = "Solicitud recibida. Si los datos son válidos, será procesada."


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=RegistroRespuesta)
async def registrar_usuario(
    usuario: UsuarioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Frena la creación masiva de cuentas desde una misma IP.
    registrar_intento_registro(request)

    contrasena_encriptada = obtener_hash_password(usuario.password)

    # La respuesta uniforme evita revelar si el correo ya existía.
    # Las cuentas nuevas nacen inactivas y requieren activación administrativa.
    nuevo_usuario = UsuarioDB(
        email=usuario.email,
        hashed_password=contrasena_encriptada,
        rol="mecanico",
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
    # Se cuenta antes de consultar: los intentos contra cuentas
    # inexistentes también consumen cuota del atacante.
    registrar_intento_login(request)

    consulta = select(UsuarioDB).where(UsuarioDB.email == credenciales.username)
    resultado = await db.execute(consulta)
    usuario_db = resultado.scalar_one_or_none()

    # Verificamos tres condiciones en orden:
    # 1. El usuario existe en la DB.
    # 2. Su cuenta está activa (is_active=True, tras activación admin).
    # 3. La contraseña enviada coincide con el hash almacenado.
    # Si cualquiera falla, retornamos el mismo error genérico (401)
    # para no revelar si el email existe o no en el sistema.
    if (
        not usuario_db
        or not usuario_db.is_active
        or not verificar_password(credenciales.password, usuario_db.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Acceso denegado al taller.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = crear_token_acceso(data={"sub": usuario_db.email, "rol": usuario_db.rol})

    return {"access_token": token, "token_type": "bearer"}


@router.get("/pendientes", response_model=list[UsuarioResponse])
async def listar_cuentas_pendientes(
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Lista las cuentas registradas que aún no fueron activadas. Solo admin."""
    consulta = (
        select(UsuarioDB)
        .where(UsuarioDB.is_active == False)  # noqa: E712
        .order_by(UsuarioDB.id)
    )
    resultado = await db.execute(consulta)
    return resultado.scalars().all()


@router.patch("/{usuario_id}/activar", response_model=UsuarioResponse)
async def activar_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Activa una cuenta registrada para que pueda iniciar sesión. Solo admin."""
    consulta = select(UsuarioDB).where(UsuarioDB.id == usuario_id)
    resultado = await db.execute(consulta)
    usuario = resultado.scalar_one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    usuario.is_active = True
    await db.commit()
    await db.refresh(usuario)
    return usuario
