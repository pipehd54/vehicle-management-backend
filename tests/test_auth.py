import pytest
from app.rate_limit import LIMITE_LOGIN_POR_IP


@pytest.mark.asyncio
async def test_registro_exitoso_crea_cuenta_inactiva(cliente):
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": "nuevo@example.com", "password": "password123"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "mensaje": "Solicitud recibida. Si los datos son válidos, será procesada."
    }


@pytest.mark.asyncio
async def test_registro_impide_escalacion_a_administrador(cliente):
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": "intento_admin@example.com", "password": "password123", "rol": "administrador"},
    )

    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_registro_duplicado_responde_igual_que_nuevo(cliente, usuario_prueba):
    """Anti-enumeración: un correo existente devuelve el mismo 201 con la misma forma."""
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": usuario_prueba["email"], "password": "password123"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "mensaje": "Solicitud recibida. Si los datos son válidos, será procesada."
    }


@pytest.mark.asyncio
async def test_login_falla_antes_de_activacion(cliente):
    await cliente.post(
        "/usuarios/",
        json={"email": "pendiente@example.com", "password": "password123"},
    )
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": "pendiente@example.com", "password": "password123"},
    )

    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_admin_activa_cuenta_y_permite_login(cliente, headers_admin):
    registro = await cliente.post(
        "/usuarios/",
        json={"email": "por_activar@example.com", "password": "password123"},
    )
    assert registro.status_code == 201
    assert registro.json() == {
        "mensaje": "Solicitud recibida. Si los datos son válidos, será procesada."
    }

    pendientes = await cliente.get("/usuarios/pendientes", headers=headers_admin)
    assert pendientes.status_code == 200
    usuario_pendiente = next(
        u for u in pendientes.json() if u["email"] == "por_activar@example.com"
    )
    usuario_id = usuario_pendiente["id"]

    activacion = await cliente.patch(
        f"/usuarios/{usuario_id}/activar", headers=headers_admin
    )
    assert activacion.status_code == 200
    assert activacion.json()["is_active"] is True

    login = await cliente.post(
        "/usuarios/login",
        data={"username": "por_activar@example.com", "password": "password123"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_activacion_requiere_admin(cliente, headers_autorizacion):
    respuesta = await cliente.patch("/usuarios/1/activar", headers=headers_autorizacion)

    assert respuesta.status_code == 403


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


@pytest.mark.asyncio
async def test_login_bloquea_fuerza_bruta(cliente, usuario_prueba):
    # El límite ya no se aplica por cuenta: se rechaza el siguiente intento por IP.
    for _ in range(LIMITE_LOGIN_POR_IP[0]):
        respuesta = await cliente.post(
            "/usuarios/login",
            data={"username": usuario_prueba["email"], "password": "incorrecta"},
        )
        assert respuesta.status_code == 401

    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "incorrecta"},
    )
    assert respuesta.status_code == 429


@pytest.mark.asyncio
async def test_registro_bloquea_creacion_masiva(cliente):
    # Sin fixture de usuario aquí: los 10 intentos de la ventana son del test.
    for indice in range(10):
        respuesta = await cliente.post(
            "/usuarios/",
            json={"email": f"masivo{indice}@example.com", "password": "password123"},
        )
        assert respuesta.status_code == 201

    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": "masivo10@example.com", "password": "password123"},
    )
    assert respuesta.status_code == 429
