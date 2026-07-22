import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("SECRET_KEY", "clave_de_pruebas_segura_de_mas_de_32_bytes")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def base_de_datos():
    """Crea una base SQLite en memoria independiente para cada prueba."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def activar_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def cliente(base_de_datos):
    fabrica_sesiones = async_sessionmaker(
        base_de_datos, class_=AsyncSession, expire_on_commit=False
    )

    async def obtener_db_pruebas():
        async with fabrica_sesiones() as sesion:
            yield sesion

    app.dependency_overrides[get_db] = obtener_db_pruebas
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as cliente_http:
        yield cliente_http
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def usuario_prueba(cliente):
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": "mecanico@example.com", "password": "password123", "rol": "mecanico"},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


@pytest_asyncio.fixture
async def token_valido(cliente, usuario_prueba):
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "password123"},
    )
    assert respuesta.status_code == 200
    return respuesta.json()["access_token"]


@pytest_asyncio.fixture
async def headers_autorizacion(token_valido):
    return {"Authorization": f"Bearer {token_valido}"}


@pytest_asyncio.fixture
async def admin_prueba(cliente):
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": "admin@example.com", "password": "password123", "rol": "administrador"},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


@pytest_asyncio.fixture
async def headers_admin(cliente, admin_prueba):
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": admin_prueba["email"], "password": "password123"},
    )
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
