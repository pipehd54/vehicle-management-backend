"""Endpoints de vehículos del taller."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_datos import get_db
from app.dependencias import requiere_admin
from app.errores import conflicto_integridad
from app.esquemas import (
    ProximoMantenimientoResponse,
    VehiculoCreate,
    VehiculoResponse,
)
from app.modelos import UsuarioDB, VehiculoDB
from app.repositorio import (
    contar_revisiones_completadas,
    obtener_vehiculo_o_404,
    ultima_revision_completada,
)
from app.seguridad import obtener_usuario_actual
from app.servicios.programa_mantenimiento import calcular_recomendacion

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
    except IntegrityError as error:
        await db.rollback()
        raise conflicto_integridad("La placa ya existe en la base de datos") from error

    return nuevo_vehiculo


@router.get("/", response_model=list[VehiculoResponse])
async def obtener_vehiculos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Lista todos los vehículos. Requiere autenticación."""
    consulta = select(VehiculoDB).order_by(VehiculoDB.id).offset(skip).limit(limit)
    resultado = await db.execute(consulta)
    return list(resultado.scalars().all())


@router.get("/{vehiculo_id}", response_model=VehiculoResponse)
async def obtener_vehiculo(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Obtiene un vehículo por su identificador. Requiere autenticación."""
    return await obtener_vehiculo_o_404(vehiculo_id, db)


@router.get(
    "/{vehiculo_id}/proximo-mantenimiento", response_model=ProximoMantenimientoResponse
)
async def proximo_mantenimiento_recomendado(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Calcula el próximo mantenimiento sugerido según el manual del taller.

    El cálculo vive en `app.servicios.programa_mantenimiento`; este endpoint
    solo recopila los datos del vehículo y su historial.
    """
    vehiculo = await obtener_vehiculo_o_404(vehiculo_id, db)

    revisiones_completadas = await contar_revisiones_completadas(vehiculo_id, db)
    fecha_ultimo_servicio = await ultima_revision_completada(vehiculo_id, db)

    recomendacion = calcular_recomendacion(
        kilometraje=vehiculo.kilometraje_actual or 0,
        revisiones_completadas=revisiones_completadas,
        fecha_ultimo_servicio=fecha_ultimo_servicio,
        fecha_compra=vehiculo.fecha_compra,
    )

    return ProximoMantenimientoResponse(
        servicio_numero=recomendacion.nombre,
        kilometraje_objetivo=recomendacion.km_objetivo,
        kilometraje_faltante=recomendacion.km_faltantes,
        meses_desde_compra=recomendacion.meses_desde_compra,
        fecha_sugerida=recomendacion.fecha_sugerida,
        descripcion_sugerida=recomendacion.descripcion,
    )


@router.put("/{vehiculo_id}", response_model=VehiculoResponse)
async def actualizar_vehiculo(
    vehiculo_id: int,
    vehiculo_actualizado: VehiculoCreate,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Reemplaza los datos de un vehículo existente."""
    vehiculo_db = await obtener_vehiculo_o_404(vehiculo_id, db)

    vehiculo_db.placa = vehiculo_actualizado.placa
    vehiculo_db.marca = vehiculo_actualizado.marca
    vehiculo_db.modelo = vehiculo_actualizado.modelo
    vehiculo_db.tipo = vehiculo_actualizado.tipo
    vehiculo_db.kilometraje_actual = vehiculo_actualizado.kilometraje_actual
    vehiculo_db.fecha_compra = vehiculo_actualizado.fecha_compra

    try:
        await db.commit()
        await db.refresh(vehiculo_db)
    except IntegrityError as error:
        await db.rollback()
        raise conflicto_integridad(
            "La nueva placa ya esta en uso por otro vehiculo."
        ) from error

    return vehiculo_db


@router.delete("/{vehiculo_id}")
async def eliminar_vehiculo(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    admin_actual: UsuarioDB = Depends(requiere_admin),
):
    """Elimina un vehículo y sus mantenimientos. Requiere rol de administrador."""
    vehiculo_db = await obtener_vehiculo_o_404(vehiculo_id, db)

    await db.delete(vehiculo_db)
    await db.commit()

    return {
        "mensaje": (
            f"El vehiculo con ID {vehiculo_id} fue eliminado correctamente del taller."
        )
    }
