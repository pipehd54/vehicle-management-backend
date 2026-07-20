from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import UsuarioDB, VehiculoDB
from app.schemas import VehiculoCreate, VehiculoResponse
from app.security import obtener_usuario_actual

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=VehiculoResponse,
)
async def registrar_vehiculo(
    vehiculo: VehiculoCreate,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Crea un nuevo vehículo. Requiere autenticación."""
    nuevo_vehiculo = VehiculoDB(
        placa=vehiculo.placa,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
    )

    db.add(nuevo_vehiculo)

    try:
        await db.commit()
        await db.refresh(nuevo_vehiculo)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La placa ya existe en la base de datos",
        )

    # Devolvemos el objeto completo. FastAPI usará response_model para serializarlo
    return nuevo_vehiculo


@router.get("/", response_model=list[VehiculoResponse])
async def obtener_vehiculos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los vehículos (público según la documentación actual)."""
    consulta = select(VehiculoDB).offset(skip).limit(limit)
    resultado = await db.execute(consulta)
    vehiculos_guardados = resultado.scalars().all()
    # Devolvemos la lista directamente. response_model=list[...] se encarga de la serialización
    return vehiculos_guardados


@router.get("/{vehiculo_id}", response_model=VehiculoResponse)
async def obtener_vehiculo(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene un vehículo por su identificador."""
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo = resultado.scalar_one_or_none()

    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado"
        )

    return vehiculo


@router.put("/{vehiculo_id}", response_model=VehiculoResponse)
async def actualizar_vehiculo(
    vehiculo_id: int,
    vehiculo_actualizado: VehiculoCreate,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Actualiza un vehículo existente. Requiere autenticación."""
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo_db = resultado.scalar_one_or_none()

    if not vehiculo_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado"
        )

    # Actualizar los campos del registro
    vehiculo_db.placa = vehiculo_actualizado.placa
    vehiculo_db.marca = vehiculo_actualizado.marca
    vehiculo_db.modelo = vehiculo_actualizado.modelo

    try:
        await db.commit()
        await db.refresh(vehiculo_db)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva placa ya esta en uso por otro vehiculo.",
        )

    # Devolvemos el objeto actualizado directamente
    return vehiculo_db


@router.delete("/{vehiculo_id}")
async def eliminar_vehiculo(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Elimina un vehículo. Requiere autenticación."""

    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo_db = resultado.scalar_one_or_none()

    if not vehiculo_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado."
        )

    await db.delete(vehiculo_db)
    await db.commit()

    return {
        "mensaje": f"El vehiculo con ID {vehiculo_id} fue eliminado correctamente del taller."
    }
