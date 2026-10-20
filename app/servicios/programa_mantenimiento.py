"""Motor de cálculo de la programa de mantenimiento del taller.

Este módulo es **puro**: no conoce FastAPI ni la base de datos, solo recibe
datos y devuelve cálculos. Concentrar aquí las reglas del manual permite
testearlas de forma rápida y reutilizarlas desde cualquier router o script.

Reglas implementadas:

1. El nivel de servicio depende del kilometraje actual del vehículo.
2. El historial de revisiones completadas indica el nivel mínimo siguiente.
3. El nivel real es el mayor de ambos: un vehículo con muchas revisiones
   completadas no puede volver al nivel 2 aunque su kilometraje sea bajo.
4. Más allá del quinto servicio el manual mantiene el patrón: cada 3000 km
   y cada 100 días.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

# --- Parámetros del manual del taller -------------------------------------

#: Kilometraje objetivo de los primeros cinco servicios.
KM_OBJETIVO_POR_NIVEL: dict[int, int] = {
    1: 500,
    2: 3_000,
    3: 6_000,
    4: 9_000,
    5: 12_000,
}

#: Días que deben pasar desde el servicio anterior para cada nivel.
DIAS_DESDE_ANTERIOR_POR_NIVEL: dict[int, int] = {
    1: 60,
    2: 100,
    3: 100,
    4: 100,
    5: 100,
}

#: Último nivel cubierto por la tabla del manual; a partir de aquí se extrapola.
NIVEL_MAXIMO_TABLA = 5

#: Patrón de extrapolación para los servicios posteriores al quinto.
INTERVALO_KM = 3_000
INTERVALO_DIAS = 100

#: El primer servicio vence a los 60 días desde la compra.
DIAS_PRIMER_SERVICIO = 60

#: Meses que el plan asigna a cada nivel (60, 160, 260, ... días desde la compra).
MESES_POR_NIVEL_BASE = 2
MESES_POR_NIVEL_PASO = 3

#: Sufijo del ordinal español según el último dígito del número.
_ORDINAL_POR_ULTIMO_DIGITO: dict[int, str] = {
    0: "ma",
    1: "ma",
    2: "da",
    3: "ra",
    4: "ta",
    5: "ta",
    6: "ta",
    7: "ma",
    8: "va",
    9: "na",
}


@dataclass(frozen=True, slots=True)
class Recomendacion:
    """Resultado del cálculo del próximo mantenimiento de un vehículo."""

    nivel: int
    nombre: str
    km_objetivo: int
    km_faltantes: int
    dias_desde_anterior: int
    meses_desde_compra: int
    fecha_sugerida: datetime | None
    descripcion: str


def nombre_servicio(nivel: int) -> str:
    """Devuelve el nombre del servicio para el nivel indicado (1ra, 2da, ...)."""
    if nivel == 1:
        return "1ra Revisión de Mantenimiento"
    sufijo = _ORDINAL_POR_ULTIMO_DIGITO[nivel % 10]
    return f"{nivel}{sufijo} Revisión de Mantenimiento"


def nivel_por_kilometraje(kilometraje: int) -> int:
    """Deduce el nivel de servicio que corresponde al kilometraje acumulado."""
    if kilometraje < 500:
        return 1
    if kilometraje < 3_000:
        return 2
    if kilometraje < 6_000:
        return 3
    if kilometraje < 9_000:
        return 4
    if kilometraje < 12_000:
        return 5
    # A partir de aquí cada tramo de 3000 km añade un nivel.
    return NIVEL_MAXIMO_TABLA + ((kilometraje - 12_000) // INTERVALO_KM) + 1


def nivel_por_historial(revisiones_completadas: int) -> int:
    """Nivel mínimo siguiente según las revisiones oficiales ya completadas."""
    return revisiones_completadas + 1


def siguiente_nivel(kilometraje: int, revisiones_completadas: int) -> int:
    """Nivel del próximo servicio: el mayor entre el deducido y el histórico.

    Sin esta combinación, un vehículo con una sola revisión completada
    quedaría anclado en el nivel 2 para siempre, aunque su kilometraje
    exigiese un servicio mucho más avanzado.
    """
    return max(
        nivel_por_kilometraje(kilometraje),
        nivel_por_historial(revisiones_completadas),
    )


def km_objetivo(nivel: int) -> int:
    """Kilometraje objetivo del nivel indicado."""
    if nivel <= NIVEL_MAXIMO_TABLA:
        return KM_OBJETIVO_POR_NIVEL[nivel]
    return KM_OBJETIVO_POR_NIVEL[NIVEL_MAXIMO_TABLA] + (
        (nivel - NIVEL_MAXIMO_TABLA) * INTERVALO_KM
    )


def dias_desde_anterior(nivel: int) -> int:
    """Días que deben transcurrir desde el servicio anterior hasta el nivel."""
    if nivel <= NIVEL_MAXIMO_TABLA:
        return DIAS_DESDE_ANTERIOR_POR_NIVEL[nivel]
    return INTERVALO_DIAS


def meses_plan(nivel: int) -> int:
    """Meses que el plan del taller asigna al nivel indicado."""
    return MESES_POR_NIVEL_BASE + ((nivel - 1) * MESES_POR_NIVEL_PASO)


def _dias_desde_compra(nivel: int) -> int:
    """Días transcurridos desde la compra hasta el nivel indicado."""
    if nivel == 1:
        return DIAS_PRIMER_SERVICIO
    return DIAS_PRIMER_SERVICIO + ((nivel - 1) * INTERVALO_DIAS)


def calcular_recomendacion(
    kilometraje: int,
    revisiones_completadas: int = 0,
    fecha_ultimo_servicio: datetime | None = None,
    fecha_compra: datetime | None = None,
) -> Recomendacion:
    """Calcula el próximo mantenimiento sugerido para un vehículo.

    Args:
        kilometraje: Kilometraje actual del vehículo.
        revisiones_completadas: Número de revisiones oficiales completadas.
        fecha_ultimo_servicio: Fecha del último servicio completado, si existe.
        fecha_compra: Fecha de compra del vehículo, si se conoce.

    Returns:
        La recomendación completa con kilometraje objetivo, faltante y fecha.
    """
    nivel = siguiente_nivel(kilometraje, revisiones_completadas)
    objetivo = km_objetivo(nivel)
    dias = dias_desde_anterior(nivel)
    faltantes = max(0, objetivo - kilometraje)

    fecha_sugerida: datetime | None = None
    if fecha_ultimo_servicio is not None:
        fecha_sugerida = fecha_ultimo_servicio + timedelta(days=dias)
    elif fecha_compra is not None:
        fecha_sugerida = fecha_compra + timedelta(days=_dias_desde_compra(nivel))

    nombre = nombre_servicio(nivel)
    descripcion = (
        f"{nombre} (Objetivo: {objetivo:,} km. "
        f"Faltan {faltantes:,} km. "
        f"Plazo: {dias} días desde el servicio anterior)."
    )

    return Recomendacion(
        nivel=nivel,
        nombre=nombre,
        km_objetivo=objetivo,
        km_faltantes=faltantes,
        dias_desde_anterior=dias,
        meses_desde_compra=meses_plan(nivel),
        fecha_sugerida=fecha_sugerida,
        descripcion=descripcion,
    )
