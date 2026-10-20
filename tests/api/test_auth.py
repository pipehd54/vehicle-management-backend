"""Pruebas de registro, login y activación de cuentas."""

import pytest
from sqlalchemy import select

from app.limitador import LIMITE_LOGIN_POR_CUENTA, LIMITE_LOGIN_POR_IP
from app.modelos import UsuarioDB


@pytest.mark.asyncio
async def test_registro_exitoso_crea_cuenta_inactiva(cliente):
    """El registro crea la cuenta pero la deja pendiente de activación."""
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
    """No se puede pedir un rol superior en el registro."""
    respuesta = await cliente.post(
        "/usuarios/",
        json={
            "email": "intento_admin@example.com",
            "password": "password123",
            "rol": "administrador",
        },
    )

    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_registro_duplicado_responde_igual_que_nuevo(cliente, usuario_prueba):
    """Anti-enumeración: un correo existente devuelve el mismo 201."""
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": usuario_prueba["email"], "password": "password123"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "mensaje": "Solicitud recibida. Si los datos son válidos, será procesada."
    }


@pytest.mark.asyncio
async def test_registro_normaliza_el_correo(cliente, base_de_datos):
    """El correo se guarda en minúsculas para no duplicar cuentas."""
    respuesta = await cliente.post(
        "/usuarios/",
        json={"email": "Taller@Example.COM", "password": "password123"},
    )
    assert respuesta.status_code == 201

    async with base_de_datos.connect() as conexion:
        resultado = await conexion.execute(
            select(UsuarioDB.email).where(UsuarioDB.email == "taller@example.com")
        )
        assert resultado.scalar_one() == "taller@example.com"


@pytest.mark.asyncio
async def test_login_falla_antes_de_activacion(cliente):
    """Una cuenta sin activar no puede iniciar sesión."""
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
    """El administrador activa las cuentas pendientes."""
    registro = await cliente.post(
        "/usuarios/",
        json={"email": "por_activar@example.com", "password": "password123"},
    )
    assert registro.status_code == 201

    pendientes = await cliente.get("/usuarios/pendientes", headers=headers_admin)
    assert pendientes.status_code == 200
    usuario_pendiente = next(
        u for u in pendientes.json() if u["email"] == "por_activar@example.com"
    )

    activacion = await cliente.patch(
        f"/usuarios/{usuario_pendiente['id']}/activar", headers=headers_admin
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
    """Un mecánico no puede activar cuentas."""
    respuesta = await cliente.patch("/usuarios/1/activar", headers=headers_autorizacion)

    assert respuesta.status_code == 403


@pytest.mark.asyncio
async def test_login_exitoso(cliente, usuario_prueba):
    """El login de una cuenta activa devuelve un token."""
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "password123"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["token_type"] == "bearer"  # noqa: S105
    assert respuesta.json()["access_token"]


@pytest.mark.asyncio
async def test_login_fallido(cliente, usuario_prueba):
    """Una contraseña incorrecta devuelve 401."""
    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "incorrecta"},
    )

    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_login_bloquea_fuerza_bruta_sobre_una_cuenta(cliente, usuario_prueba):
    """Tras varios fallos seguidos la cuenta queda bloqueada un tiempo."""
    for _ in range(LIMITE_LOGIN_POR_CUENTA[0]):
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
async def test_los_logins_correctos_no_consumen_cuota(cliente, usuario_prueba):
    """El tráfico legítimo no agota el límite por IP ni por cuenta."""
    for _ in range(LIMITE_LOGIN_POR_CUENTA[0] + 2):
        respuesta = await cliente.post(
            "/usuarios/login",
            data={"username": usuario_prueba["email"], "password": "password123"},
        )
        assert respuesta.status_code == 200


@pytest.mark.asyncio
async def test_el_limite_por_ip_agrega_distintas_cuentas(cliente, usuario_prueba):
    """Muchos intentos fallidos contra cuentas distintas agotan la cuota de IP."""
    for indice in range(LIMITE_LOGIN_POR_IP[0]):
        respuesta = await cliente.post(
            "/usuarios/login",
            data={
                "username": f"fantasma{indice}@example.com",
                "password": "incorrecta",
            },
        )
        assert respuesta.status_code == 401

    respuesta = await cliente.post(
        "/usuarios/login",
        data={"username": "otro@example.com", "password": "incorrecta"},
    )
    assert respuesta.status_code == 429


@pytest.mark.asyncio
async def test_registro_bloquea_creacion_masiva(cliente):
    """El registro se limita por IP."""
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
