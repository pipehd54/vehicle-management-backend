"""Pruebas del ciclo de vida de las cuentas de usuario."""

import pytest

from app.modelos import UsuarioDB


@pytest.mark.asyncio
async def test_mi_usuario_devuelve_la_cuenta_autenticada(cliente, headers_autorizacion):
    """/usuarios/me devuelve los datos del usuario del token."""
    respuesta = await cliente.get("/usuarios/me", headers=headers_autorizacion)

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["email"] == "mecanico@example.com"
    assert datos["rol"] == "mecanico"
    assert "hashed_password" not in datos


@pytest.mark.asyncio
async def test_mi_usuario_requiere_token(cliente):
    """/usuarios/me no es público."""
    respuesta = await cliente.get("/usuarios/me")

    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_cambiar_password_permite_entrar_con_la_nueva(
    cliente, headers_autorizacion
):
    """Tras cambiar la contraseña, la nueva sirve para iniciar sesión."""
    respuesta = await cliente.post(
        "/usuarios/me/cambiar-password",
        json={"password_actual": "password123", "password_nuevo": "nuevaClave456"},
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 200
    login = await cliente.post(
        "/usuarios/login",
        data={"username": "mecanico@example.com", "password": "nuevaClave456"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_cambiar_password_exige_la_actual(cliente, headers_autorizacion):
    """Sin la contraseña actual correcta, el cambio se rechaza."""
    respuesta = await cliente.post(
        "/usuarios/me/cambiar-password",
        json={"password_actual": "incorrecta", "password_nuevo": "nuevaClave456"},
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_desactivar_cuenta_corta_el_acceso(
    cliente, headers_admin, usuario_prueba
):
    """Un administrador desactiva una cuenta y su token deja de servir."""
    respuesta = await cliente.patch(
        f"/usuarios/{usuario_prueba['id']}/desactivar", headers=headers_admin
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["is_active"] is False

    token = await cliente.post(
        "/usuarios/login",
        data={"username": usuario_prueba["email"], "password": "password123"},
    )
    assert token.status_code == 401


@pytest.mark.asyncio
async def test_desactivar_cuenta_requiere_admin(
    cliente, headers_autorizacion, usuario_prueba
):
    """Un mecánico no puede desactivar cuentas."""
    respuesta = await cliente.patch(
        f"/usuarios/{usuario_prueba['id']}/desactivar", headers=headers_autorizacion
    )

    assert respuesta.status_code == 403


@pytest.mark.asyncio
async def test_no_se_puede_desactivar_la_propia_cuenta(
    cliente, headers_admin, admin_prueba
):
    """Un administrador no puede dejar la instalación sin ningún acceso."""
    respuesta = await cliente.patch(
        f"/usuarios/{admin_prueba['id']}/desactivar", headers=headers_admin
    )

    assert respuesta.status_code == 400
    assert "propia cuenta" in respuesta.json()["detail"]


@pytest.mark.asyncio
async def test_una_cuenta_desactivada_puede_reactivarse(
    cliente, headers_admin, usuario_prueba
):
    """El ciclo completo es desactivar y volver a activar."""
    await cliente.patch(
        f"/usuarios/{usuario_prueba['id']}/desactivar", headers=headers_admin
    )
    respuesta = await cliente.patch(
        f"/usuarios/{usuario_prueba['id']}/activar", headers=headers_admin
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["is_active"] is True


@pytest.mark.asyncio
async def test_desactivar_cuenta_inexistente(cliente, headers_admin):
    """Desactivar un identificador que no existe devuelve 404."""
    respuesta = await cliente.patch("/usuarios/9999/desactivar", headers=headers_admin)

    assert respuesta.status_code == 404


@pytest.mark.asyncio
async def test_el_correo_se_guarda_en_minusculas(base_de_datos, cliente):
    """El correo se normaliza al registrarse, también al crear el admin."""
    from sqlalchemy import select

    await cliente.post(
        "/usuarios/",
        json={"email": "Taller@Example.COM", "password": "password123"},
    )

    async with base_de_datos.connect() as conexion:
        resultado = await conexion.execute(
            select(UsuarioDB.email).where(UsuarioDB.email == "taller@example.com")
        )
        assert resultado.scalar_one() == "taller@example.com"
