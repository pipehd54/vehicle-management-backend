"""Pruebas de los endpoints de mantenimientos."""

import pytest


async def crear_vehiculo(cliente, headers, **extra):
    """Crea un vehículo de apoyo."""
    cuerpo = {
        "placa": "MNT-123",
        "marca": "Renault",
        "modelo": "Logan",
    }
    cuerpo.update(extra)
    respuesta = await cliente.post("/vehiculos/", json=cuerpo, headers=headers)
    return respuesta.json()


async def crear_mantenimiento(cliente, headers, vehiculo_id, **extra):
    """Crea un mantenimiento de apoyo."""
    cuerpo = {
        "vehiculo_id": vehiculo_id,
        "descripcion": "Cambio de aceite y filtros",
        "estado": "pendiente",
        "costo_estimado": 120000,
    }
    cuerpo.update(extra)
    return await cliente.post("/mantenimientos/", json=cuerpo, headers=headers)


@pytest.mark.asyncio
async def test_crear_mantenimiento_para_vehiculo_existente(
    cliente, headers_autorizacion
):
    """Se puede registrar un mantenimiento para un vehículo existente."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    respuesta = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    assert respuesta.status_code == 201
    assert respuesta.json()["vehiculo_id"] == vehiculo["id"]


@pytest.mark.asyncio
async def test_crear_mantenimiento_para_vehiculo_inexistente(
    cliente, headers_autorizacion
):
    """Un vehículo que no existe devuelve 404."""
    respuesta = await crear_mantenimiento(cliente, headers_autorizacion, 9999)

    assert respuesta.status_code == 404


@pytest.mark.asyncio
async def test_crear_mantenimiento_rechaza_estado_invalido(
    cliente, headers_autorizacion
):
    """El estado debe pertenecer a la lista admitida por el taller."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    respuesta = await crear_mantenimiento(
        cliente, headers_autorizacion, vehiculo["id"], estado="en proceso"
    )

    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_listar_mantenimientos_filtrados_por_vehiculo(
    cliente, headers_autorizacion
):
    """El listado se puede filtrar por vehículo."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.get(
        f"/mantenimientos/?vehiculo_id={vehiculo['id']}&skip=0&limit=20",
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["vehiculo_id"] == vehiculo["id"]


@pytest.mark.asyncio
async def test_obtener_mantenimiento_por_id(cliente, headers_autorizacion):
    """Se puede consultar un mantenimiento por su identificador."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.get(
        f"/mantenimientos/{creado.json()['id']}", headers=headers_autorizacion
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creado.json()["id"]


@pytest.mark.asyncio
async def test_actualizar_mantenimiento(cliente, headers_autorizacion):
    """La actualización cambia el estado del mantenimiento."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.put(
        f"/mantenimientos/{creado.json()['id']}",
        json={
            "descripcion": "Frenos revisados",
            "estado": "completado",
            "costo_estimado": 90000,
        },
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "completado"
    assert respuesta.json()["fecha_completado"] is not None


@pytest.mark.asyncio
async def test_completar_mantenimiento_conserva_la_fecha_de_cierre(
    cliente, headers_autorizacion
):
    """Reabrir un mantenimiento no borra la fecha de cierre ya registrada."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(
        cliente, headers_autorizacion, vehiculo["id"], estado="completado"
    )
    fecha_cierre = creado.json()["fecha_completado"]
    assert fecha_cierre is not None

    respuesta = await cliente.put(
        f"/mantenimientos/{creado.json()['id']}",
        json={"descripcion": "Frenos revisados", "estado": "en_progreso"},
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "en_progreso"
    assert respuesta.json()["fecha_completado"] == fecha_cierre


@pytest.mark.asyncio
async def test_completar_mantenimiento_actualiza_el_kilometraje_del_vehiculo(
    cliente, headers_autorizacion
):
    """El odómetro del vehículo se actualiza al cerrar un servicio."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    await crear_mantenimiento(
        cliente,
        headers_autorizacion,
        vehiculo["id"],
        estado="completado",
        kilometraje=42000,
    )

    respuesta = await cliente.get(
        f"/vehiculos/{vehiculo['id']}", headers=headers_autorizacion
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["kilometraje_actual"] == 42000


@pytest.mark.asyncio
async def test_el_kilometraje_del_vehiculo_nunca_retrocede(
    cliente, headers_autorizacion
):
    """Un kilometraje menor no reduce el odómetro ya conocido."""
    vehiculo = await crear_vehiculo(
        cliente, headers_autorizacion, kilometraje_actual=50000
    )
    await crear_mantenimiento(
        cliente,
        headers_autorizacion,
        vehiculo["id"],
        estado="completado",
        kilometraje=1000,
    )

    respuesta = await cliente.get(
        f"/vehiculos/{vehiculo['id']}", headers=headers_autorizacion
    )

    assert respuesta.json()["kilometraje_actual"] == 50000


@pytest.mark.asyncio
async def test_eliminar_mantenimiento_denegado_para_mecanico(
    cliente, headers_autorizacion
):
    """Un mecánico no puede eliminar mantenimientos."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.delete(
        f"/mantenimientos/{creado.json()['id']}", headers=headers_autorizacion
    )

    assert respuesta.status_code == 403
    assert "administrador" in respuesta.json()["detail"]


@pytest.mark.asyncio
async def test_eliminar_mantenimiento_como_admin(
    cliente, headers_autorizacion, headers_admin
):
    """El administrador puede eliminar un mantenimiento."""
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.delete(
        f"/mantenimientos/{creado.json()['id']}", headers=headers_admin
    )

    assert respuesta.status_code == 200
    consulta = await cliente.get(
        f"/mantenimientos/{creado.json()['id']}", headers=headers_admin
    )
    assert consulta.status_code == 404
