import pytest


async def crear_vehiculo(cliente, headers):
    respuesta = await cliente.post(
        "/vehiculos/",
        json={"placa": "MNT-123", "marca": "Renault", "modelo": "Logan"},
        headers=headers,
    )
    return respuesta.json()


async def crear_mantenimiento(cliente, headers, vehiculo_id):
    return await cliente.post(
        "/mantenimientos/",
        json={
            "vehiculo_id": vehiculo_id,
            "descripcion": "Cambio de aceite y filtros",
            "estado": "pendiente",
            "costo_estimado": 120000,
        },
        headers=headers,
    )


@pytest.mark.asyncio
async def test_crear_mantenimiento_para_vehiculo_existente(cliente, headers_autorizacion):
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    respuesta = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    assert respuesta.status_code == 201
    assert respuesta.json()["vehiculo_id"] == vehiculo["id"]


@pytest.mark.asyncio
async def test_listar_mantenimientos_filtrados_por_vehiculo(cliente, headers_autorizacion):
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.get(f"/mantenimientos/?vehiculo_id={vehiculo['id']}&skip=0&limit=20")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["vehiculo_id"] == vehiculo["id"]


@pytest.mark.asyncio
async def test_obtener_mantenimiento_por_id(cliente, headers_autorizacion):
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.get(f"/mantenimientos/{creado.json()['id']}")

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creado.json()["id"]


@pytest.mark.asyncio
async def test_actualizar_mantenimiento(cliente, headers_autorizacion):
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.put(
        f"/mantenimientos/{creado.json()['id']}",
        json={"descripcion": "Frenos revisados", "estado": "completado", "costo_estimado": 90000},
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "completado"


@pytest.mark.asyncio
async def test_eliminar_mantenimiento_denegado_para_mecanico(cliente, headers_autorizacion):
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.delete(
        f"/mantenimientos/{creado.json()['id']}", headers=headers_autorizacion
    )

    assert respuesta.status_code == 403
    assert "administrador" in respuesta.json()["detail"]


@pytest.mark.asyncio
async def test_eliminar_mantenimiento_como_admin(cliente, headers_autorizacion, headers_admin):
    vehiculo = await crear_vehiculo(cliente, headers_autorizacion)
    creado = await crear_mantenimiento(cliente, headers_autorizacion, vehiculo["id"])

    respuesta = await cliente.delete(
        f"/mantenimientos/{creado.json()['id']}", headers=headers_admin
    )

    assert respuesta.status_code == 200
    assert (await cliente.get(f"/mantenimientos/{creado.json()['id']}")).status_code == 404
