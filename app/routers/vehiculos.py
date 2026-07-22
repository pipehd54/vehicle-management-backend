from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.depends import requiere_admin
from app.models import UsuarioDB, VehiculoDB
from app.schemas import ProximoMantenimientoResponse, VehiculoCreate, VehiculoResponse
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
        tipo=vehiculo.tipo,
        kilometraje_actual=vehiculo.kilometraje_actual,
        fecha_compra=vehiculo.fecha_compra,
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

    return nuevo_vehiculo


@router.get("/", response_model=list[VehiculoResponse])
async def obtener_vehiculos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los vehículos."""
    consulta = select(VehiculoDB).offset(skip).limit(limit)
    resultado = await db.execute(consulta)
    return resultado.scalars().all()


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


@router.get("/{vehiculo_id}/proximo-mantenimiento", response_model=ProximoMantenimientoResponse)
async def proximo_mantenimiento_recomendado(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    """Calcula el próximo mantenimiento sugerido basado en kilometraje y tiempo de compra."""
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo = resultado.scalar_one_or_none()

    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado"
        )

    km = vehiculo.kilometraje_actual or 0

    if km < 500:
        servicio_nombre = "1er Servicio de Mantenimiento"
        km_objetivo = 500
        meses = 2
    elif km < 3000:
        servicio_nombre = "2do Servicio de Mantenimiento"
        km_objetivo = 3000
        meses = 3
    elif km < 6000:
        servicio_nombre = "3er Servicio de Mantenimiento"
        km_objetivo = 6000
        meses = 6
    elif km < 9000:
        servicio_nombre = "4to Servicio de Mantenimiento"
        km_objetivo = 9000
        meses = 9
    elif km < 12000:
        servicio_nombre = "5to Servicio de Mantenimiento"
        km_objetivo = 12000
        meses = 12
    else:
        num_adicional = ((km - 12000) // 3000) + 1
        num_servicio = 5 + num_adicional
        servicio_nombre = f"{num_servicio}to Servicio de Mantenimiento"
        km_objetivo = 12000 + (num_adicional * 3000)
        meses = 12 + (num_adicional * 3)

    fecha_sugerida = None
    if vehiculo.fecha_compra:
        fecha_sugerida = vehiculo.fecha_compra + timedelta(days=30 * meses)

    descripcion = f"{servicio_nombre} (Revisión preventiva a los {km_objetivo:,} km o {meses} meses desde la compra)."

    return ProximoMantenimientoResponse(
        servicio_numero=servicio_nombre,
        kilometraje_objetivo=km_objetivo,
        meses_desde_compra=meses,
        fecha_sugerida=fecha_sugerida,
        descripcion_sugerida=descripcion,
    )


@router.put("/{vehiculo_id}", response_model=VehiculoResponse)
async def actualizar_vehiculo(
    vehiculo_id: int,
    vehiculo_actualizado: VehiculoCreate,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Actualiza un vehículo existente."""
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo_db = resultado.scalar_one_or_none()

    if not vehiculo_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado"
        )

    vehiculo_db.placa = vehiculo_actualizado.placa
    vehiculo_db.marca = vehiculo_actualizado.marca
    vehiculo_db.modelo = vehiculo_actualizado.modelo
    vehiculo_db.tipo = vehiculo_actualizado.tipo
    vehiculo_db.kilometraje_actual = vehiculo_actualizado.kilometraje_actual
    vehiculo_db.fecha_compra = vehiculo_actualizado.fecha_compra

    try:
        await db.commit()
        await db.refresh(vehiculo_db)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva placa ya esta en uso por otro vehiculo.",
        )

    return vehiculo_db


@router.delete("/{vehiculo_id}")
async def eliminar_vehiculo(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Elimina un vehículo. Requiere rol de administrador."""
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
