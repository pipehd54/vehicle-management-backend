"""Pruebas de los endpoints de vehículos."""

import pytest


async def crear_vehiculo(cliente, headers, placa="ABC-123", **extra):
    """Crea un vehículo y devuelve la respuesta de la API."""
    cuerpo = {
        "placa": placa,
        "marca": "Toyota",
        "modelo": "Corolla",
        "tipo": "carro",
        "kilometraje_actual": 0,
    }
    cuerpo.update(extra)
    return await cliente.post("/vehiculos/", json=cuerpo, headers=headers)


@pytest.mark.asyncio
async def test_crear_vehiculo_autenticado(cliente, headers_autorizacion):
    """Se puede registrar un vehículo con un token válido."""
    respuesta = await crear_vehiculo(cliente, headers_autorizacion)

    assert respuesta.status_code == 201
    assert respuesta.json()["placa"] == "ABC-123"
    assert respuesta.json()["tipo"] == "carro"


@pytest.mark.asyncio
async def test_crear_vehiculo_rechaza_tipo_invalido(cliente, headers_autorizacion):
    """El tipo de vehículo se valida contra la lista admitida."""
    respuesta = await crear_vehiculo(cliente, headers_autorizacion, tipo="camion")

    assert respuesta.status_code == 422


@pytest.mark.asyncio
async def test_crear_vehiculo_rechaza_placa_duplicada(cliente, headers_autorizacion):
    """La placa es única en la base de datos."""
    await crear_vehiculo(cliente, headers_autorizacion)
    respuesta = await crear_vehiculo(cliente, headers_autorizacion)

    assert respuesta.status_code == 409
    assert "placa" in respuesta.json()["detail"].lower()


@pytest.mark.asyncio
async def test_listar_vehiculos_con_paginacion(cliente, headers_autorizacion):
    """El listado respeta skip y limit."""
    for indice in range(3):
        respuesta = await crear_vehiculo(cliente, headers_autorizacion, f"ABC-{indice}")
        assert respuesta.status_code == 201

    respuesta = await cliente.get(
        "/vehiculos/?skip=1&limit=1", headers=headers_autorizacion
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["placa"] == "ABC-1"


@pytest.mark.asyncio
async def test_obtener_vehiculo_por_id(cliente, headers_autorizacion):
    """Se puede consultar un vehículo por su identificador."""
    creado = await crear_vehiculo(cliente, headers_autorizacion)

    respuesta = await cliente.get(
        f"/vehiculos/{creado.json()['id']}", headers=headers_autorizacion
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creado.json()["id"]


@pytest.mark.asyncio
async def test_obtener_vehiculo_inexistente(cliente, headers_autorizacion):
    """Un identificador que no existe devuelve 404."""
    respuesta = await cliente.get("/vehiculos/9999", headers=headers_autorizacion)

    assert respuesta.status_code == 404


@pytest.mark.asyncio
async def test_actualizar_vehiculo(cliente, headers_autorizacion):
    """La actualización reemplaza los datos del vehículo."""
    creado = await crear_vehiculo(cliente, headers_autorizacion)

    respuesta = await cliente.put(
        f"/vehiculos/{creado.json()['id']}",
        json={
            "placa": "XYZ-987",
            "marca": "Mazda",
            "modelo": "3",
            "tipo": "carro",
            "kilometraje_actual": 15000,
        },
        headers=headers_autorizacion,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["marca"] == "Mazda"
    assert respuesta.json()["kilometraje_actual"] == 15000


@pytest.mark.asyncio
async def test_proximo_mantenimiento_recomendado(cliente, headers_autorizacion):
    """Sin historial, la recomendación se deduce del kilometraje."""
    creado = await crear_vehiculo(
        cliente,
        headers_autorizacion,
        placa="HER-999",
        marca="Hero",
        modelo="Eco 100",
        tipo="motocicleta",
        kilometraje_actual=2500,
    )
    assert creado.status_code == 201

    respuesta = await cliente.get(
        f"/vehiculos/{creado.json()['id']}/proximo-mantenimiento",
        headers=headers_autorizacion,
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["servicio_numero"] == "2da Revisión de Mantenimiento"
    assert datos["kilometraje_objetivo"] == 3000
    assert datos["kilometraje_faltante"] == 500
    assert datos["meses_desde_compra"] == 5


@pytest.mark.asyncio
async def test_proximo_mantenimiento_usa_el_kilometraje_por_encima_del_historial(
    cliente, headers_autorizacion
):
    """Con historial, el nivel nunca es inferior al que pide el kilometraje.

    Regresión: una sola revisión completada anclaba la recomendación en el
    nivel 2 aunque el kilometraje del vehículo exigiera un nivel muy superior.
    """
    creado = await crear_vehiculo(
        cliente, headers_autorizacion, placa="KIL-001", kilometraje_actual=100000
    )
    vehiculo_id = creado.json()["id"]

    mantenimiento = await cliente.post(
        "/mantenimientos/",
        json={
            "vehiculo_id": vehiculo_id,
            "descripcion": "Revisión oficial de los 100.000 km",
            "estado": "completado",
            "es_revision": True,
        },
        headers=headers_autorizacion,
    )
    assert mantenimiento.status_code == 201

    respuesta = await cliente.get(
        f"/vehiculos/{vehiculo_id}/proximo-mantenimiento",
        headers=headers_autorizacion,
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["kilometraje_objetivo"] == 102000
    assert datos["servicio_numero"] == "35ta Revisión de Mantenimiento"


@pytest.mark.asyncio
async def test_eliminar_vehiculo_denegado_para_mecanico(cliente, headers_autorizacion):
    """Un mecánico no puede eliminar vehículos."""
    creado = await crear_vehiculo(cliente, headers_autorizacion)
    vehiculo_id = creado.json()["id"]

    respuesta = await cliente.delete(
        f"/vehiculos/{vehiculo_id}", headers=headers_autorizacion
    )

    assert respuesta.status_code == 403
    assert "administrador" in respuesta.json()["detail"]


@pytest.mark.asyncio
async def test_eliminar_vehiculo_y_mantenimientos_asociados_como_admin(
    cliente, headers_autorizacion, headers_admin
):
    """Al borrar un vehículo se borran también sus mantenimientos."""
    creado = await crear_vehiculo(cliente, headers_autorizacion)
    vehiculo_id = creado.json()["id"]
    mantenimiento = await cliente.post(
        "/mantenimientos/",
        json={"vehiculo_id": vehiculo_id, "descripcion": "Cambio de aceite"},
        headers=headers_autorizacion,
    )

    respuesta = await cliente.delete(f"/vehiculos/{vehiculo_id}", headers=headers_admin)

    assert respuesta.status_code == 200
    consulta = await cliente.get(
        f"/mantenimientos/{mantenimiento.json()['id']}", headers=headers_admin
    )
    assert consulta.status_code == 404
