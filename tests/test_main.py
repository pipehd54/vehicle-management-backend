import pytest


@pytest.mark.asyncio
async def test_inicio_responde_mensaje_de_la_api(cliente):
    response = await cliente.get("/")

    assert response.status_code == 200
    assert response.json() == {"mensaje": "API de gestión de taller mecánico"}
