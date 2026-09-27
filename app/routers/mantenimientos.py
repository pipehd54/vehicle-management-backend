from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.depends import requiere_admin
from app.models import MantenimientoDB, UsuarioDB, VehiculoDB
from app.schemas import (
    MantenimientoCreate,
    MantenimientoResponse,
    MantenimientoUpdate,
)
from app.security import obtener_usuario_actual

router = APIRouter()


# Helper reutilizable: verifica que el vehículo exista antes de crear
# un mantenimiento asociado. Evita duplicar la lógica de "404 si no existe"
# en cada endpoint que recibe un vehiculo_id.
async def obtener_vehiculo_o_404(vehiculo_id: int, db: AsyncSession) -> VehiculoDB:
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo = resultado.scalar_one_or_none()

    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no encontrado.",
        )

    return vehiculo


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
    await obtener_vehiculo_o_404(mantenimiento.vehiculo_id, db)

    nuevo_mantenimiento = MantenimientoDB(
        vehiculo_id=mantenimiento.vehiculo_id,
        descripcion=mantenimiento.descripcion,
        estado=mantenimiento.estado,
        es_revision=mantenimiento.es_revision,
        costo_estimado=mantenimiento.costo_estimado,
        kilometraje=mantenimiento.kilometraje,
        fecha_programada=mantenimiento.fecha_programada,
        fecha_completado=(
            datetime.now(timezone.utc) if mantenimiento.estado == "completado" else None
        ),
    )

    db.add(nuevo_mantenimiento)
    await db.commit()
    await db.refresh(nuevo_mantenimiento)

    return nuevo_mantenimiento


@router.get("/", response_model=list[MantenimientoResponse])
async def listar_mantenimientos(
    vehiculo_id: int | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    consulta = select(MantenimientoDB)

    if vehiculo_id is not None:
        consulta = consulta.where(MantenimientoDB.vehiculo_id == vehiculo_id)

    resultado = await db.execute(
        consulta.order_by(MantenimientoDB.id).offset(skip).limit(limit)
    )
    return resultado.scalars().all()


@router.get("/{mantenimiento_id}", response_model=MantenimientoResponse)
async def obtener_mantenimiento(
    mantenimiento_id: int,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    consulta = select(MantenimientoDB).where(MantenimientoDB.id == mantenimiento_id)
    resultado = await db.execute(consulta)
    mantenimiento = resultado.scalar_one_or_none()

    if not mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado.",
        )

    return mantenimiento


@router.put("/{mantenimiento_id}", response_model=MantenimientoResponse)
async def actualizar_mantenimiento(
    mantenimiento_id: int,
    mantenimiento_actualizado: MantenimientoUpdate,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    consulta = select(MantenimientoDB).where(MantenimientoDB.id == mantenimiento_id)
    resultado = await db.execute(consulta)
    mantenimiento = resultado.scalar_one_or_none()

    if not mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado.",
        )

    estado_anterior = mantenimiento.estado
    mantenimiento.descripcion = mantenimiento_actualizado.descripcion
    mantenimiento.estado = mantenimiento_actualizado.estado
    if mantenimiento_actualizado.es_revision is not None:
        mantenimiento.es_revision = mantenimiento_actualizado.es_revision
    mantenimiento.costo_estimado = mantenimiento_actualizado.costo_estimado
    mantenimiento.kilometraje = mantenimiento_actualizado.kilometraje
    mantenimiento.fecha_programada = mantenimiento_actualizado.fecha_programada
    if mantenimiento.estado == "completado":
        if estado_anterior != "completado" or mantenimiento.fecha_completado is None:
            mantenimiento.fecha_completado = datetime.now(timezone.utc)
    else:
        mantenimiento.fecha_completado = None

    await db.commit()
    await db.refresh(mantenimiento)

    return mantenimiento


@router.delete("/{mantenimiento_id}")
async def eliminar_mantenimiento(
    mantenimiento_id: int,
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    consulta = select(MantenimientoDB).where(MantenimientoDB.id == mantenimiento_id)
    resultado = await db.execute(consulta)
    mantenimiento = resultado.scalar_one_or_none()

    if not mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado.",
        )

    await db.delete(mantenimiento)
    await db.commit()

    return {"mensaje": "Mantenimiento eliminado correctamente."}
