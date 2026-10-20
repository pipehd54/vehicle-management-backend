"""Configuración compartida de las pruebas.

Por defecto las pruebas usan SQLite asíncrono en memoria. Si se define
`TEST_DATABASE_URL` (por ejemplo, el PostgreSQL de CI) se ejecutan contra esa
base de datos.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("SECRET_KEY", "clave_de_pruebas_segura_de_mas_de_32_bytes")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.base_datos import Base, get_db
from app.enums import RolUsuario
from app.limitador import reiniciar_limitador
from app.main import app
from app.modelos import UsuarioDB
from app.seguridad import obtener_hash_password

CONTRASENA_PRUEBA = "password123"


@pytest_asyncio.fixture
async def base_de_datos():
    """Crea una base aislada por prueba; CI puede usar PostgreSQL real."""
    test_database_url = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite://")
    engine_options = {}
    if test_database_url.startswith("sqlite"):
        engine_options.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    engine = create_async_engine(test_database_url, **engine_options)

    if test_database_url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def activar_foreign_keys(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async with engine.begin() as conexion:
        await conexion.run_sync(Base.metadata.create_all)

    yield engine
    async with engine.begin() as conexion:
        await conexion.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def cliente(base_de_datos):
    """Cliente HTTP contra la aplicación, con la base de datos de pruebas."""
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


@pytest.fixture(autouse=True)
def limites_reiniciados():
    """Aísla el limitador de intentos entre pruebas."""
    reiniciar_limitador()
    yield
    reiniciar_limitador()


async def _activar_usuario(base_de_datos, email: str) -> dict:
    """Activa directamente en la base de datos una cuenta registrada."""
    fabrica = async_sessionmaker(
        base_de_datos, class_=AsyncSession, expire_on_commit=False
    )
    async with fabrica() as sesion:
        resultado = await sesion.execute(
            select(UsuarioDB).where(UsuarioDB.email == email)
        )
        usuario = resultado.scalar_one()
        usuario.is_active = True
        await sesion.commit()
        return {
            "id": usuario.id,
            "email": usuario.email,
            "rol": usuario.rol.value,
            "is_active": usuario.is_active,
        }


@pytest_asyncio.fixture
async def usuario_prueba(cliente, base_de_datos):
    """Cuenta de mecánico registrada y activada."""
    email = "mecanico@example.com"
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": email, "password": CONTRASENA_PRUEBA},
    )
    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "mensaje": "Solicitud recibida. Si los datos son válidos, será procesada."
    }
    return await _activar_usuario(base_de_datos, email)


@pytest_asyncio.fixture
async def token_valido(cliente, usuario_prueba):
    """Token JWT de un mecánico activo."""
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": CONTRASENA_PRUEBA},
    )
    assert respuesta.status_code == 200
    return respuesta.json()["access_token"]


@pytest_asyncio.fixture
async def headers_autorizacion(token_valido):
    """Cabecera Authorization del mecánico."""
    return {"Authorization": f"Bearer {token_valido}"}


@pytest_asyncio.fixture
async def admin_prueba(base_de_datos):
    """Cuenta de administrador activa."""
    fabrica = async_sessionmaker(
        base_de_datos, class_=AsyncSession, expire_on_commit=False
    )
    async with fabrica() as sesion:
        admin = UsuarioDB(
            email="admin@example.com",
            hashed_password=obtener_hash_password(CONTRASENA_PRUEBA),
            rol=RolUsuario.ADMINISTRADOR,
        )
        sesion.add(admin)
        await sesion.commit()
        await sesion.refresh(admin)
        return {
            "id": admin.id,
            "email": admin.email,
            "rol": admin.rol.value,
            "is_active": admin.is_active,
        }


@pytest_asyncio.fixture
async def headers_admin(cliente, admin_prueba):
    """Cabecera Authorization del administrador."""
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": admin_prueba["email"], "password": CONTRASENA_PRUEBA},
    )
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
