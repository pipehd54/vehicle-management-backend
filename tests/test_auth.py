import pytest


@pytest.mark.asyncio
async def test_registro_exitoso(cliente):
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": "nuevo@example.com", "password": "password123"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] == "nuevo@example.com"
    assert "hashed_password" not in respuesta.json()


@pytest.mark.asyncio
async def test_registro_duplicado(cliente, usuario_prueba):
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": usuario_prueba["email"], "password": "password123"},
    )

    assert respuesta.status_code == 400


@pytest.mark.asyncio
async def test_login_exitoso(cliente, usuario_prueba):
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "password123"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["token_type"] == "bearer"
    assert respuesta.json()["access_token"]


@pytest.mark.asyncio
async def test_login_fallido(cliente, usuario_prueba):
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "incorrecta"},
    )

    assert respuesta.status_code == 401
