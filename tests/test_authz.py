import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("metodo", "url", "payload"),
    [
        ("post", "/vehiculos/", {"placa": "SIN-123", "marca": "Kia", "modelo": "Rio"}),
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
    ],
)
async def test_endpoints_protegidos_requieren_token(cliente, metodo, url, payload):
    kwargs = {}
    if payload is not None:
        kwargs["json"] = payload
    respuesta = await getattr(cliente, metodo)(url, **kwargs)

    assert respuesta.status_code == 401
