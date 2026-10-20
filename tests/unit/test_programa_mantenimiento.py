"""Pruebas unitarias del motor de programa de mantenimiento.

Son pruebas puras: no tocan la base de datos ni HTTP, así que corren en
milisegundos y cubren las reglas del manual del taller.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.servicios.programa_mantenimiento import (
    calcular_recomendacion,
    dias_desde_anterior,
    km_objetivo,
    meses_plan,
    nivel_por_historial,
    nivel_por_kilometraje,
    nombre_servicio,
    siguiente_nivel,
)

FECHA_BASE = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("kilometraje", "nivel_esperado"),
    [
        (0, 1),
        (499, 1),
        (500, 2),
        (2_999, 2),
        (3_000, 3),
        (5_999, 3),
        (6_000, 4),
        (8_999, 4),
        (9_000, 5),
        (11_999, 5),
        (12_000, 6),
        (14_999, 6),
        (15_000, 7),
        (100_000, 35),
    ],
)
def test_nivel_por_kilometraje(kilometraje, nivel_esperado):
    """El kilometraje determina el nivel según la tabla del manual."""
    assert nivel_por_kilometraje(kilometraje) == nivel_esperado


@pytest.mark.parametrize(
    ("revisiones", "nivel_esperado"),
    [(0, 1), (1, 2), (4, 5), (5, 6)],
)
def test_nivel_por_historial(revisiones, nivel_esperado):
    """Cada revisión completada avanza un nivel."""
    assert nivel_por_historial(revisiones) == nivel_esperado


def test_el_nivel_es_el_mayor_entre_kilometraje_e_historial():
    """Un vehículo con historial no puede volver a un nivel inferior.

    Regresión: con una sola revisión completada, un vehículo de 100.000 km
    quedaba anclado en el nivel 2 y se le recomendaba un servicio de 3.000 km.
    """
    assert siguiente_nivel(kilometraje=100_000, revisiones_completadas=1) == 35
    assert siguiente_nivel(kilometraje=1_000, revisiones_completadas=1) == 2
    assert siguiente_nivel(kilometraje=2_500, revisiones_completadas=0) == 2


@pytest.mark.parametrize(
    ("nivel", "km_esperado"),
    [(1, 500), (2, 3_000), (5, 12_000), (6, 15_000), (7, 18_000), (35, 102_000)],
)
def test_km_objetivo(nivel, km_esperado):
    """Los primeros cinco niveles salen de la tabla; los demás se extrapolan."""
    assert km_objetivo(nivel) == km_esperado


def test_dias_desde_anterior():
    """El primer servicio vence a los 60 días y los siguientes cada 100."""
    assert dias_desde_anterior(1) == 60
    assert dias_desde_anterior(2) == 100
    assert dias_desde_anterior(35) == 100


@pytest.mark.parametrize(
    ("nivel", "nombre_esperado"),
    [
        (1, "1ra Revisión de Mantenimiento"),
        (2, "2da Revisión de Mantenimiento"),
        (3, "3ra Revisión de Mantenimiento"),
        (6, "6ta Revisión de Mantenimiento"),
        (7, "7ma Revisión de Mantenimiento"),
        (8, "8va Revisión de Mantenimiento"),
        (11, "11ma Revisión de Mantenimiento"),
    ],
)
def test_nombre_servicio(nivel, nombre_esperado):
    """El ordinal del nombre sigue la ortografía del español."""
    assert nombre_servicio(nivel) == nombre_esperado


def test_meses_plan():
    """El plan asigna 2 meses al primer servicio y 3 más a cada nivel."""
    assert meses_plan(1) == 2
    assert meses_plan(2) == 5
    assert meses_plan(3) == 8


def test_recomendacion_sin_fechas_de_referencia():
    """Sin historial ni fecha de compra no se propone fecha."""
    recomendacion = calcular_recomendacion(kilometraje=2_500)

    assert recomendacion.nivel == 2
    assert recomendacion.km_objetivo == 3_000
    assert recomendacion.km_faltantes == 500
    assert recomendacion.fecha_sugerida is None


def test_recomendacion_desde_el_ultimo_servicio():
    """La fecha sugerida se cuenta desde el último servicio completado."""
    recomendacion = calcular_recomendacion(
        kilometraje=2_500,
        revisiones_completadas=1,
        fecha_ultimo_servicio=FECHA_BASE,
    )

    assert recomendacion.nivel == 2
    assert recomendacion.fecha_sugerida == FECHA_BASE + timedelta(days=100)


def test_recomendacion_desde_la_fecha_de_compra():
    """Sin historial, la fecha se cuenta desde la compra del vehículo."""
    recomendacion = calcular_recomendacion(
        kilometraje=0,
        fecha_compra=FECHA_BASE,
    )

    assert recomendacion.nivel == 1
    assert recomendacion.fecha_sugerida == FECHA_BASE + timedelta(days=60)


def test_recomendacion_describe_servicio_y_kilometraje():
    """La descripción resume servicio, objetivo y faltante."""
    recomendacion = calcular_recomendacion(kilometraje=2_500)

    assert recomendacion.descripcion == (
        "2da Revisión de Mantenimiento (Objetivo: 3,000 km. "
        "Faltan 500 km. Plazo: 100 días desde el servicio anterior)."
    )


def test_recomendacion_nunca_produce_un_faltante_negativo():
    """Un kilometraje absurdo nunca produce un faltante negativo."""
    recomendacion = calcular_recomendacion(kilometraje=-100)

    assert recomendacion.km_faltantes >= 0
