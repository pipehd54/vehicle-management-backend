from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import UsuarioDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="usuarios/login")


def obtener_hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verificar_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def crear_token_acceso(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    # get_secret_value() es la única forma de acceder al valor real de SecretStr.
    # Esto hace que el acceso a la clave sea explícito e intencional en el código.
    token_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )
    return token_jwt


async def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UsuarioDB:
    """
    Dependencia que valida el token JWT y retorna el objeto completo del usuario.

    Retornar el objeto UsuarioDB (en lugar de solo el email) permite que otras
    dependencias, como requiere_admin, accedan al rol y otros campos sin
    hacer una consulta adicional a la base de datos.
    """
    credenciales_excepcion = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        email: str | None = payload.get("sub")

        if email is None:
            raise credenciales_excepcion

        consulta = select(UsuarioDB).where(UsuarioDB.email == email)
        resultado = await db.execute(consulta)
        usuario = resultado.scalar_one_or_none()

        if not usuario or not usuario.is_active:
            raise credenciales_excepcion

        return usuario  # Retornamos el objeto completo, no solo el email

    except InvalidTokenError:
        raise credenciales_excepcion

