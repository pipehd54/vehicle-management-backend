from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MantenimientoDB, UsuarioDB, VehiculoDB
from app.schemas import (
    MantenimientoCreate,
    MantenimientoResponse,
    MantenimientoUpdate,
)
from app.security import obtener_usuario_actual

router = APIRouter()


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
        costo_estimado=mantenimiento.costo_estimado,
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
):
    consulta = select(MantenimientoDB)

    if vehiculo_id is not None:
        consulta = consulta.where(MantenimientoDB.vehiculo_id == vehiculo_id)

    resultado = await db.execute(consulta.offset(skip).limit(limit))
    return resultado.scalars().all()


@router.get("/{mantenimiento_id}", response_model=MantenimientoResponse)
async def obtener_mantenimiento(
    mantenimiento_id: int,
    db: AsyncSession = Depends(get_db),
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

    mantenimiento.descripcion = mantenimiento_actualizado.descripcion
    mantenimiento.estado = mantenimiento_actualizado.estado
    mantenimiento.costo_estimado = mantenimiento_actualizado.costo_estimado

    await db.commit()
    await db.refresh(mantenimiento)

    return mantenimiento


@router.delete("/{mantenimiento_id}")
async def eliminar_mantenimiento(
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

    await db.delete(mantenimiento)
    await db.commit()

    return {"mensaje": "Mantenimiento eliminado correctamente."}
