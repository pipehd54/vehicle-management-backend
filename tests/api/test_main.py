"""Pruebas de los endpoints raíz y de salud de la API."""

import pytest


@pytest.mark.asyncio
async def test_inicio_responde_mensaje_de_la_api(cliente):
    """La raíz de la API saluda con un mensaje."""
    response = await cliente.get("/")

    assert response.status_code == 200
    assert response.json() == {"mensaje": "API de gestión de taller mecánico"}


@pytest.mark.asyncio
async def test_health_check_confirma_conexion(cliente):
    """El health check verifica que la base de datos responde."""
    response = await cliente.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


@pytest.mark.asyncio
async def test_las_respuestas_incluyen_cabeceras_de_seguridad(cliente):
    """Todas las respuestas llevan las cabeceras de endurecimiento."""
    response = await cliente.get("/")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
