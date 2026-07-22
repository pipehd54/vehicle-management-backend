from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.depends import requiere_admin
from app.models import MantenimientoDB, UsuarioDB, VehiculoDB
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
    """Calcula el próximo mantenimiento sugerido basado en la tabla oficial del manual de mantenimiento."""
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo = resultado.scalar_one_or_none()

    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado"
        )

    # Consultar mantenimientos completados ordenados
    consulta_m = (
        select(MantenimientoDB)
        .where(
            MantenimientoDB.vehiculo_id == vehiculo_id,
            MantenimientoDB.estado == "completado",
        )
        .order_by(MantenimientoDB.fecha_programada.desc(), MantenimientoDB.id.desc())
    )
    res_m = await db.execute(consulta_m)
    completados = res_m.scalars().all()
    num_completados = len(completados)

    km = vehiculo.kilometraje_actual or 0

    if num_completados >= 1:
        siguiente_nivel = num_completados + 1
    else:
        if km < 500:
            siguiente_nivel = 1
        elif km < 3000:
            siguiente_nivel = 2
        elif km < 6000:
            siguiente_nivel = 3
        elif km < 9000:
            siguiente_nivel = 4
        elif km < 12000:
            siguiente_nivel = 5
        else:
            siguiente_nivel = 5 + (((km - 12000) // 3000) + 1)

    tabla_servicios = {
        1: ("1ra Revisión de Mantenimiento", 500, 60),
        2: ("2da Revisión de Mantenimiento", 3000, 100),
        3: ("3ra Revisión de Mantenimiento", 6000, 100),
        4: ("4ta Revisión de Mantenimiento", 9000, 100),
        5: ("5ta Revisión de Mantenimiento", 12000, 100),
    }

    if siguiente_nivel in tabla_servicios:
        servicio_nombre, km_objetivo, dias_desde_anterior = tabla_servicios[siguiente_nivel]
    else:
        num_adicional = siguiente_nivel - 5
        servicio_nombre = f"{siguiente_nivel}ta Revisión de Mantenimiento"
        km_objetivo = 12000 + (num_adicional * 3000)
        dias_desde_anterior = 100

    km_faltantes = max(0, km_objetivo - km)

    # Calcular la fecha sugerida usando la última revisión completada o fecha_compra
    fecha_sugerida = None
    if completados and (completados[0].fecha_programada or completados[0].fecha_creacion):
        fecha_ref = completados[0].fecha_programada or completados[0].fecha_creacion
        fecha_sugerida = fecha_ref + timedelta(days=dias_desde_anterior)
    elif vehiculo.fecha_compra:
        dias_totales = 60 if siguiente_nivel == 1 else 60 + ((siguiente_nivel - 1) * 100)
        fecha_sugerida = vehiculo.fecha_compra + timedelta(days=dias_totales)

    meses_equiv = 2 if siguiente_nivel == 1 else 2 + (siguiente_nivel - 1) * 3
    descripcion = f"{servicio_nombre} (Objetivo: {km_objetivo:,} km. Faltan {km_faltantes:,} km. Plazo: {dias_desde_anterior} días desde el servicio anterior)."

    return ProximoMantenimientoResponse(
        servicio_numero=servicio_nombre,
        kilometraje_objetivo=km_objetivo,
        kilometraje_faltante=km_faltantes,
        meses_desde_compra=meses_equiv,
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
