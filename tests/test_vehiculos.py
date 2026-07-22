import pytest


async def crear_vehiculo(cliente, headers, placa="ABC-123"):
    return await cliente.post(
        "/vehiculos/",
        json={"placa": placa, "marca": "Toyota", "modelo": "Corolla", "tipo": "carro", "kilometraje_actual": 0},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_crear_vehiculo_autenticado(cliente, headers_autorizacion):
    respuesta = await crear_vehiculo(cliente, headers_autorizacion)

    assert respuesta.status_code == 201
    assert respuesta.json()["placa"] == "ABC-123"
    assert respuesta.json()["tipo"] == "carro"


@pytest.mark.asyncio
async def test_listar_vehiculos_con_paginacion(cliente, headers_autorizacion):
    for indice in range(3):
        respuesta = await crear_vehiculo(cliente, headers_autorizacion, f"ABC-{indice}")
        assert respuesta.status_code == 201

    respuesta = await cliente.get("/vehiculos/?skip=1&limit=1")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["placa"] == "ABC-1"


@pytest.mark.asyncio
async def test_obtener_vehiculo_por_id(cliente, headers_autorizacion):
    creado = await crear_vehiculo(cliente, headers_autorizacion)

    respuesta = await cliente.get(f"/vehiculos/{creado.json()['id']}")

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creado.json()["id"]


@pytest.mark.asyncio
async def test_actualizar_vehiculo(cliente, headers_autorizacion):
    creado = await crear_vehiculo(cliente, headers_autorizacion)

    respuesta = await cliente.put(
        f"/vehiculos/{creado.json()['id']}",
        json={"placa": "XYZ-987", "marca": "Mazda", "modelo": "3", "tipo": "carro", "kilometraje_actual": 15000},
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["marca"] == "Mazda"
    assert respuesta.json()["kilometraje_actual"] == 15000


@pytest.mark.asyncio
async def test_proximo_mantenimiento_recomendado(cliente, headers_autorizacion):
    creado = await cliente.post(
        "/vehiculos/",
        json={
            "placa": "HER-999",
            "marca": "Hero",
            "modelo": "Eco 100",
            "tipo": "motocicleta",
            "kilometraje_actual": 2500,
        },
        headers=headers_autorizacion,
    )
    assert creado.status_code == 201
    vehiculo_id = creado.json()["id"]

    respuesta = await cliente.get(f"/vehiculos/{vehiculo_id}/proximo-mantenimiento")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["servicio_numero"] == "2do Servicio de Mantenimiento"
    assert datos["kilometraje_objetivo"] == 3000
    assert datos["meses_desde_compra"] == 3


@pytest.mark.asyncio
async def test_eliminar_vehiculo_denegado_para_mecanico(cliente, headers_autorizacion):
    creado = await crear_vehiculo(cliente, headers_autorizacion)
    vehiculo_id = creado.json()["id"]

    respuesta = await cliente.delete(f"/vehiculos/{vehiculo_id}", headers=headers_autorizacion)

    assert respuesta.status_code == 403
    assert "administrador" in respuesta.json()["detail"]


@pytest.mark.asyncio
async def test_eliminar_vehiculo_y_mantenimientos_asociados_como_admin(
    cliente, headers_autorizacion, headers_admin
):
    creado = await crear_vehiculo(cliente, headers_autorizacion)
    vehiculo_id = creado.json()["id"]
    mantenimiento = await cliente.post(
        "/mantenimientos/",
        json={"vehiculo_id": vehiculo_id, "descripcion": "Cambio de aceite"},
        headers=headers_autorizacion,
    )

    respuesta = await cliente.delete(f"/vehiculos/{vehiculo_id}", headers=headers_admin)

    assert respuesta.status_code == 200
    assert (await cliente.get(f"/mantenimientos/{mantenimiento.json()['id']}")).status_code == 404
