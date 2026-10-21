"""Consultas reutilizadas por los routers.

Centralizar aquí las lecturas más repetidas evita duplicar el patrón
"buscar por id y devolver 404" en cada endpoint y deja los routers reducidos
a la lógica HTTP.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import EstadoMantenimiento
from app.errores import no_encontrado
from app.modelos import MantenimientoDB, UsuarioDB, VehiculoDB


async def obtener_vehiculo_o_404(vehiculo_id: int, db: AsyncSession) -> VehiculoDB:
    """Devuelve el vehículo o lanza un 404 si no existe."""
    resultado = await db.execute(select(VehiculoDB).where(VehiculoDB.id == vehiculo_id))
    vehiculo = resultado.scalar_one_or_none()
    if vehiculo is None:
        raise no_encontrado("Vehiculo", vehiculo_id)
    return vehiculo


async def obtener_mantenimiento_o_404(
    mantenimiento_id: int, db: AsyncSession
) -> MantenimientoDB:
    """Devuelve el mantenimiento o lanza un 404 si no existe."""
    resultado = await db.execute(
        select(MantenimientoDB).where(MantenimientoDB.id == mantenimiento_id)
    )
    mantenimiento = resultado.scalar_one_or_none()
    if mantenimiento is None:
        raise no_encontrado("Mantenimiento", mantenimiento_id)
    return mantenimiento


async def obtener_usuario_o_404(usuario_id: int, db: AsyncSession) -> UsuarioDB:
    """Devuelve el usuario o lanza un 404 si no existe."""
    resultado = await db.execute(select(UsuarioDB).where(UsuarioDB.id == usuario_id))
    usuario = resultado.scalar_one_or_none()
    if usuario is None:
        raise no_encontrado("Usuario", usuario_id)
    return usuario


async def contar_revisiones_completadas(vehiculo_id: int, db: AsyncSession) -> int:
    """Número de revisiones oficiales ya completadas de un vehículo."""
    consulta = select(func.count(MantenimientoDB.id)).where(
        MantenimientoDB.vehiculo_id == vehiculo_id,
        MantenimientoDB.estado == EstadoMantenimiento.COMPLETADO,
        MantenimientoDB.es_revision.is_(True),
    )
    return await db.scalar(consulta) or 0


async def ultima_revision_completada(
    vehiculo_id: int, db: AsyncSession
) -> datetime | None:
    """Fecha de cierre de la última revisión oficial completada, si existe."""
    consulta = (
        select(MantenimientoDB.fecha_completado, MantenimientoDB.fecha_creacion)
        .where(
            MantenimientoDB.vehiculo_id == vehiculo_id,
            MantenimientoDB.estado == EstadoMantenimiento.COMPLETADO,
            MantenimientoDB.es_revision.is_(True),
        )
        .order_by(
            MantenimientoDB.fecha_completado.desc().nulls_last(),
            MantenimientoDB.id.desc(),
        )
        .limit(1)
    )
    fila = (await db.execute(consulta)).first()
    if fila is None:
        return None
    fecha_completado, fecha_creacion = fila
    return fecha_completado or fecha_creacion


def aplicar_cambios_parciales(modelo: object, datos: dict[str, object]) -> None:
    """Aplica al modelo únicamente los campos enviados con valor.

    Es la regla de las actualizaciones parciales: un campo omitido (o enviado
    como null) conserva su valor actual en lugar de sobrescribirse. Sin esto,
    un cliente que actualiza solo la descripcion de un mantenimiento borraria
    su presupuesto, y uno que actualiza solo la marca de un vehiculo
    reiniciaria su kilometraje.
    """
    for campo, valor in datos.items():
        if valor is not None:
            setattr(modelo, campo, valor)


def actualizar_kilometraje_vehiculo(
    vehiculo: VehiculoDB, kilometraje: int | None
) -> bool:
    """Sube el kilometraje del vehículo si el mantenimiento lo reporta.

    El odómetro del vehículo nunca debe retroceder: solo se actualiza cuando
    el kilometraje registrado es mayor que el que ya se conoce.
    """
    if kilometraje is None:
        return False
    if vehiculo.kilometraje_actual is None or kilometraje > vehiculo.kilometraje_actual:
        vehiculo.kilometraje_actual = kilometraje
        return True
    return False
