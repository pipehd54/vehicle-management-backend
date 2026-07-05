from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# La clase base de la que heredan todos los modelos ORM
class Base(DeclarativeBase):
    pass


# Motor de conexión asíncrono a la base de datos.
# La URL viene de settings, que la validó y cargó desde .env al arrancar.
engine = create_async_engine(settings.DATABASE_URL)

# Fábrica de sesiones asíncronas.
# expire_on_commit=False evita el lazy-loading problemático
# después de hacer commit en contexto async.
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


# Dependencia de FastAPI que provee una sesión de DB por petición.
# El bloque 'async with' garantiza que la sesión se cierra
# correctamente al terminar, incluso si ocurre una excepción.
async def get_db():
    async with async_session() as session:
        yield session