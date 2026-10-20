"""Autenticación: hash de contraseñas, emisión y validación de tokens JWT."""

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_datos import get_db
from app.configuracion import settings
from app.errores import credenciales_invalidas
from app.modelos import UsuarioDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="usuarios/login")

#: Límite de bytes que procesa bcrypt (los passphrase más largos se truncan).
MAX_BCRYPT_BYTES = 72

#: Hash señuelo. Cuando el correo no existe se compara igualmente contra este
#: hash, de modo que el tiempo de respuesta del login sea el mismo exista o no
#: la cuenta y no se pueda enumerar por medición de tiempos.
HASH_SENUELO = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode("utf-8")


def obtener_hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_BYTES:
        raise ValueError("La contraseña excede el límite de 72 bytes de bcrypt.")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba una contraseña en texto plano contra su hash bcrypt."""
    plain_bytes = plain_password.encode("utf-8")
    if len(plain_bytes) > MAX_BCRYPT_BYTES:
        return False
    hashed_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except ValueError:
        # Hash corrupto o de otro algoritmo: se trata como contraseña inválida.
        return False


def crear_token_acceso(data: dict[str, str]) -> str:
    """Emite un token JWT firmado con la clave de la aplicación.

    El claim `rol` es únicamente informativo: la autorización real siempre se
    resuelve leyendo el usuario de la base de datos, de modo que un cambio de
    rol surte efecto de inmediato y sin depender del token.
    """
    payload = data.copy()
    ahora = datetime.now(UTC)
    payload.update(
        {
            "iat": ahora,
            "exp": ahora + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }
    )
    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )


async def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UsuarioDB:
    """Valida el token JWT y devuelve el usuario completo de la base de datos.

    Devolver el objeto `UsuarioDB` (en lugar de solo el email) permite que
    otras dependencias, como `requiere_admin`, accedan al rol y a otros campos
    sin hacer una consulta adicional a la base de datos.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
    except InvalidTokenError as error:
        raise credenciales_invalidas() from error

    email = payload.get("sub")
    if not isinstance(email, str) or not email:
        raise credenciales_invalidas()

    resultado = await db.execute(select(UsuarioDB).where(UsuarioDB.email == email))
    usuario = resultado.scalar_one_or_none()

    # Un usuario desactivado pierde el acceso aunque su token siga vigente.
    if usuario is None or not usuario.is_active:
        raise credenciales_invalidas()

    return usuario
