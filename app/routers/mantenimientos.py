"""Endpoints de mantenimientos asociados a los vehículos."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_datos import get_db
from app.dependencias import requiere_admin
from app.enums import EstadoMantenimiento
from app.esquemas import (
    MantenimientoCreate,
    MantenimientoResponse,
    MantenimientoUpdate,
)
from app.modelos import MantenimientoDB, UsuarioDB
from app.repositorio import (
    actualizar_kilometraje_vehiculo,
    obtener_mantenimiento_o_404,
    obtener_vehiculo_o_404,
)
from app.seguridad import obtener_usuario_actual

router = APIRouter()


def _fecha_de_cierre(estado: EstadoMantenimiento) -> datetime | None:
    """Fecha de cierre de un mantenimiento recién creado."""
    if estado == EstadoMantenimiento.COMPLETADO:
        return datetime.now(UTC)
    return None


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=MantenimientoResponse,
)
async def crear_mantenimiento(
    mantenimiento: MantenimientoCreate,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Registra un mantenimiento para un vehículo existente."""
    vehiculo = await obtener_vehiculo_o_404(mantenimiento.vehiculo_id, db)

    nuevo_mantenimiento = MantenimientoDB(
        vehiculo_id=vehiculo.id,
        descripcion=mantenimiento.descripcion,
        estado=mantenimiento.estado,
        es_revision=mantenimiento.es_revision,
        costo_estimado=mantenimiento.costo_estimado,
        kilometraje=mantenimiento.kilometraje,
        fecha_programada=mantenimiento.fecha_programada,
        fecha_completado=_fecha_de_cierre(mantenimiento.estado),
    )

    db.add(nuevo_mantenimiento)
    if nuevo_mantenimiento.estado == EstadoMantenimiento.COMPLETADO:
        actualizar_kilometraje_vehiculo(vehiculo, nuevo_mantenimiento.kilometraje)

    await db.commit()
    await db.refresh(nuevo_mantenimiento)

    return nuevo_mantenimiento


@router.get("/", response_model=list[MantenimientoResponse])
async def listar_mantenimientos(
    vehiculo_id: int | None = Query(default=None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Lista los mantenimientos, opcionalmente filtrados por vehículo."""
    consulta = select(MantenimientoDB)

    if vehiculo_id is not None:
        consulta = consulta.where(MantenimientoDB.vehiculo_id == vehiculo_id)

    resultado = await db.execute(
        consulta.order_by(MantenimientoDB.id).offset(skip).limit(limit)
    )
    return list(resultado.scalars().all())


@router.get("/{mantenimiento_id}", response_model=MantenimientoResponse)
async def obtener_mantenimiento(
    mantenimiento_id: int,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Obtiene un mantenimiento por su identificador."""
    return await obtener_mantenimiento_o_404(mantenimiento_id, db)


@router.put("/{mantenimiento_id}", response_model=MantenimientoResponse)
async def actualizar_mantenimiento(
    mantenimiento_id: int,
    mantenimiento_actualizado: MantenimientoUpdate,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Actualiza un mantenimiento existente.

    La fecha de cierre se registra al pasar a "completado" y **se conserva**
    cuando el estado cambia después: es un dato histórico del servicio
    realizado y no debe borrarse al reordenar la orden de trabajo.
    """
    mantenimiento = await obtener_mantenimiento_o_404(mantenimiento_id, db)

    estado_anterior = mantenimiento.estado
    mantenimiento.descripcion = mantenimiento_actualizado.descripcion
    mantenimiento.estado = mantenimiento_actualizado.estado
    if mantenimiento_actualizado.es_revision is not None:
        mantenimiento.es_revision = mantenimiento_actualizado.es_revision
    mantenimiento.costo_estimado = mantenimiento_actualizado.costo_estimado
    mantenimiento.kilometraje = mantenimiento_actualizado.kilometraje
    mantenimiento.fecha_programada = mantenimiento_actualizado.fecha_programada

    if mantenimiento.estado == EstadoMantenimiento.COMPLETADO:
        # La fecha se sella al completar el servicio y se conserva después.
        if (
            estado_anterior != EstadoMantenimiento.COMPLETADO
            or mantenimiento.fecha_completado is None
        ):
            mantenimiento.fecha_completado = datetime.now(UTC)
        vehiculo = await obtener_vehiculo_o_404(mantenimiento.vehiculo_id, db)
        actualizar_kilometraje_vehiculo(vehiculo, mantenimiento.kilometraje)

    await db.commit()
    await db.refresh(mantenimiento)

    return mantenimiento


@router.delete("/{mantenimiento_id}")
async def eliminar_mantenimiento(
    mantenimiento_id: int,
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Elimina un mantenimiento. Requiere rol de administrador."""
    mantenimiento = await obtener_mantenimiento_o_404(mantenimiento_id, db)

    await db.delete(mantenimiento)
    await db.commit()

    return {"mensaje": "Mantenimiento eliminado correctamente."}
