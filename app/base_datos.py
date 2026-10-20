"""Motor y sesiones de base de datos."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.configuracion import settings


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos ORM."""


# El motor de conexión asíncrono a la base de datos.
# pool_pre_ping=True verifica la salud de las conexiones inactivas en
# producción (por ejemplo, en Railway).
# pool_recycle=300 evita que el servidor cierre conexiones viejas.
_opciones_motor: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# SQLite (usado en las pruebas locales) no admite los parámetros de pool
# asíncronos, así que solo se ajustan para motores reales como PostgreSQL.
if not settings.DATABASE_URL.startswith("sqlite"):
    _opciones_motor.update(
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
    )

engine = create_async_engine(settings.DATABASE_URL, **_opciones_motor)

# Fábrica de sesiones asíncronas.
# expire_on_commit=False evita el lazy-loading problemático
# después de hacer commit en contexto async.
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependencia de FastAPI que provee una sesión de DB por petición.

    El bloque 'async with' garantiza que la sesión se cierra
    correctamente al terminar, incluso si ocurre una excepción.
    """
    async with async_session() as sesion:
        yield sesion


async def cerrar_engine() -> None:
    """Cierra el pool de conexiones al apagar la aplicación."""
    await engine.dispose()
