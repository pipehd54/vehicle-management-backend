"""Pruebas de la herramienta de línea de comandos."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import cli
from app.enums import RolUsuario
from app.modelos import UsuarioDB
from app.seguridad import verificar_password


@pytest.fixture
def sesion_de_pruebas(base_de_datos, monkeypatch):
    """Conecta la CLI con la base de datos de las pruebas."""
    fabrica = async_sessionmaker(
        base_de_datos, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(cli, "async_session", fabrica)
    return fabrica


@pytest.mark.asyncio
async def test_crear_admin_crea_una_cuenta_activa(sesion_de_pruebas, base_de_datos):
    """La herramienta crea el administrador que la API no permite crear."""
    codigo = await cli._crear_administrador("admin@taller.com", "password123")

    assert codigo == 0
    async with sesion_de_pruebas() as sesion:
        resultado = await sesion.execute(
            select(UsuarioDB).where(UsuarioDB.email == "admin@taller.com")
        )
        admin = resultado.scalar_one()
        assert admin.rol == RolUsuario.ADMINISTRADOR
        assert admin.is_active is True
        assert verificar_password("password123", admin.hashed_password)


@pytest.mark.asyncio
async def test_crear_admin_no_duplica_cuentas(sesion_de_pruebas):
    """Si el correo ya existe, la herramienta no toca la base de datos."""
    await cli._crear_administrador("admin@taller.com", "password123")
    codigo = await cli._crear_administrador("admin@taller.com", "otraClave456")

    assert codigo == 1


@pytest.mark.asyncio
async def test_la_contrasena_se_guarda_cifrada(sesion_de_pruebas):
    """La contraseña nunca se guarda en texto plano."""
    await cli._crear_administrador("admin@taller.com", "password123")

    async with sesion_de_pruebas() as sesion:
        resultado = await sesion.execute(
            select(UsuarioDB).where(UsuarioDB.email == "admin@taller.com")
        )
        admin = resultado.scalar_one()
        assert "password123" not in admin.hashed_password
