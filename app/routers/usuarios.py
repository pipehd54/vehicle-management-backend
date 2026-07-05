from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import UsuarioDB
from app.schemas import UsuarioCreate, UsuarioResponse
from app.security import crear_token_acceso, obtener_hash_password, verificar_password

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UsuarioResponse)
async def registrar_usuario(usuario: UsuarioCreate, db: AsyncSession = Depends(get_db)):

    contrasena_encriptada = obtener_hash_password(usuario.password)

    nuevo_usuario = UsuarioDB(
        email=usuario.email, hashed_password=contrasena_encriptada, rol="mecanico"
    )

    db.add(nuevo_usuario)
    try:
        await db.commit()
        await db.refresh(nuevo_usuario)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo completar el registro. Verifica los datos e inténtalo de nuevo.",
        )

    return nuevo_usuario


@router.post("/login")
async def login(
    credenciales: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    consulta = select(UsuarioDB).where(UsuarioDB.email == credenciales.username)
    resultado = await db.execute(consulta)
    usuario_db = resultado.scalar_one_or_none()

    # Verificamos tres condiciones en orden:
    # 1. El usuario existe en la DB.
    # 2. Su cuenta está activa (is_active=True).
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

    token = crear_token_acceso(data={"sub": usuario_db.email})

    return {"access_token": token, "token_type": "bearer"}
