import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

load_dotenv()


# 1. La clase base para mapear tus tablas futuras
class Base(DeclarativeBase):
    pass


# 2. El cable de red hacia la base de datos
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("La variable de entorno DATABASE_URL no está configurada. Revisa tu archivo .env")
engine = create_async_engine(DATABASE_URL)

# 3. El cajero que fabrica las sesiones
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

# 4. El metadata que Alembic usará para autogenerar migraciones
target_metadata = Base.metadata

# 4. La dependencia con yield que limpia el canal al terminar
async def get_db():
    async with async_session() as session:
        yield session