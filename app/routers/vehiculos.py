from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import VehiculoDB
from app.schemas import VehiculoSchema
from app.security import obtener_usuario_actual

router = APIRouter()


@router.post("/")
async def registrar_vehiculo(
    vehiculo: VehiculoSchema,
    db: AsyncSession = Depends(get_db),
    usuario_actual: str = Depends(obtener_usuario_actual),
):
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
            status_code=400,
            detail="La placa ya existe en la base de datos",
        )

    return {
        "mensaje": "Vehículo registrado en PostgreSQL",
        "data": {
            "id": nuevo_vehiculo.id,
            "placa": nuevo_vehiculo.placa,
        },
    }


@router.get("/")
async def obtener_vehiculos(db: AsyncSession = Depends(get_db)):
    consulta = select(VehiculoDB)
    resultado = await db.execute(consulta)
    vehiculos_guardados = resultado.scalars().all()
    return {"vehiculos": vehiculos_guardados}


@router.put("/{vehiculo_id}")
async def actualizar_vehiculo(
    vehiculo_id: int,
    vehiculo_actualizado: VehiculoSchema,
    db: AsyncSession = Depends(get_db),
    # 🔒 El candado:
    usuario_actual: str = Depends(obtener_usuario_actual),
):

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

    return {"mensaje": "Vehiculo actualizado con exito", "vehiculo": vehiculo_db}


@router.delete("/{vehiculo_id}")
async def eliminar_vehiculo(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    # 🔒 El candado:
    usuario_actual: str = Depends(obtener_usuario_actual),
):

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
