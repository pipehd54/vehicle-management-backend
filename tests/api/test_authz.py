"""Pruebas de autorización: los endpoints protegidos exigen un token válido."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modelos import UsuarioDB


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("metodo", "url", "payload"),
    [
        ("post", "/vehiculos/", {"placa": "SIN-123", "marca": "Kia", "modelo": "Rio"}),
        ("get", "/vehiculos/", None),
        ("get", "/vehiculos/1", None),
        ("get", "/vehiculos/1/proximo-mantenimiento", None),
        ("put", "/vehiculos/1", {"placa": "SIN-123", "marca": "Kia", "modelo": "Rio"}),
        ("delete", "/vehiculos/1", None),
        (
            "post",
            "/mantenimientos/",
            {"vehiculo_id": 1, "descripcion": "Cambio de aceite"},
        ),
        (
            "put",
            "/mantenimientos/1",
            {"descripcion": "Cambio de aceite", "estado": "pendiente"},
        ),
        ("delete", "/mantenimientos/1", None),
        ("get", "/mantenimientos/", None),
        ("get", "/mantenimientos/1", None),
        ("get", "/usuarios/pendientes", None),
        ("patch", "/usuarios/1/activar", None),
    ],
)
async def test_endpoints_protegidos_requieren_token(cliente, metodo, url, payload):
    """Sin cabecera Authorization todos los endpoints protegidos devuelven 401."""
    kwargs = {}
    if payload is not None:
        kwargs["json"] = payload
    respuesta = await getattr(cliente, metodo)(url, **kwargs)

    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_token_invalido_es_rechazado(cliente):
    """Un token con firma inválida no da acceso a la API."""
    respuesta = await cliente.get(
        "/vehiculos/", headers={"Authorization": "Bearer token.inventado"}
    )

    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_usuario_desactivado_pierde_el_acceso(
    cliente, base_de_datos, usuario_prueba
):
    """Desactivar la cuenta invalida el token en la siguiente petición."""
    token = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "password123"},
    )
    cabeceras = {"Authorization": f"Bearer {token.json()['access_token']}"}

    assert (await cliente.get("/vehiculos/", headers=cabeceras)).status_code == 200

    fabrica = async_sessionmaker(
        base_de_datos, class_=AsyncSession, expire_on_commit=False
    )
    async with fabrica() as sesion:
        resultado = await sesion.execute(
            select(UsuarioDB).where(UsuarioDB.email == usuario_prueba["email"])
        )
        usuario = resultado.scalar_one()
        usuario.is_active = False
        await sesion.commit()

    assert (await cliente.get("/vehiculos/", headers=cabeceras)).status_code == 401
