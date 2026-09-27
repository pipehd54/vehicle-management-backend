from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
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
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Lista todos los vehículos. Requiere autenticación."""
    consulta = select(VehiculoDB).order_by(VehiculoDB.id).offset(skip).limit(limit)
    resultado = await db.execute(consulta)
    return resultado.scalars().all()


@router.get("/{vehiculo_id}", response_model=VehiculoResponse)
async def obtener_vehiculo(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """Obtiene un vehículo por su identificador. Requiere autenticación."""
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo = resultado.scalar_one_or_none()

    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado"
        )

    return vehiculo


@router.get("/{vehiculo_id}/proximo-mantenimiento", response_model=ProximoMantenimientoResponse)
async def proximo_mantenimiento_recomendado(
    vehiculo_id: int,
    db: AsyncSession = Depends(get_db),
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
):
    """
    Calcula el próximo mantenimiento sugerido basado en el manual oficial del taller.

    La lógica sigue este orden:
      1. Si ya hay mantenimientos completados, el siguiente nivel es el que sigue.
      2. Si es la primera vez, se deduce el nivel según el kilometraje actual.
      3. Se consulta una tabla fija para los primeros 5 servicios; más allá,
         se extrapola cada 3000 km.
      4. La fecha sugerida se calcula a partir del último servicio completado
         o, en su defecto, desde la fecha de compra del vehículo.
    """
    consulta = select(VehiculoDB).where(VehiculoDB.id == vehiculo_id)
    resultado = await db.execute(consulta)
    vehiculo = resultado.scalar_one_or_none()

    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado"
        )

    # Contar en SQL y recuperar una sola fecha real de finalización.
    consulta_conteo = select(func.count(MantenimientoDB.id)).where(
        MantenimientoDB.vehiculo_id == vehiculo_id,
        MantenimientoDB.estado == "completado",
        MantenimientoDB.es_revision.is_(True),
    )
    num_completados = await db.scalar(consulta_conteo) or 0
    consulta_ultimo = (
        select(MantenimientoDB.fecha_completado, MantenimientoDB.fecha_creacion)
        .where(
            MantenimientoDB.vehiculo_id == vehiculo_id,
            MantenimientoDB.estado == "completado",
            MantenimientoDB.es_revision.is_(True),
        )
        .order_by(
            MantenimientoDB.fecha_completado.desc().nulls_last(),
            MantenimientoDB.id.desc(),
        )
        .limit(1)
    )
    ultimo_completado = (await db.execute(consulta_ultimo)).first()

    km = vehiculo.kilometraje_actual or 0

    # Determinar el nivel de servicio que correspondería
    if num_completados >= 1:
        # Ya existen mantenimientos previos → se avanza al siguiente nivel
        siguiente_nivel = num_completados + 1
    else:
        # Primera vez: se estima el nivel según el kilometraje acumulado
        # (no hay orden histórica que consultar)
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
            # Más allá de 12000 km, cada 3000 km adicionales suma un nivel
            siguiente_nivel = 5 + (((km - 12000) // 3000) + 1)

    # Tabla oficial del manual para los primeros 5 servicios
    # Cada entrada: (nombre_servicio, km_objetivo, días_hasta_el_siguiente)
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
        # Servicios más allá del 5to: se extrapola el patrón del manual
        num_adicional = siguiente_nivel - 5
        servicio_nombre = f"{siguiente_nivel}ta Revisión de Mantenimiento"
        km_objetivo = 12000 + (num_adicional * 3000)
        dias_desde_anterior = 100

    km_faltantes = max(0, km_objetivo - km)

    # Calcular la fecha sugerida tomando como referencia el último
    # servicio completado o, si no existe, la fecha de compra del vehículo
    fecha_sugerida = None
    if ultimo_completado:
        fecha_completado, fecha_creacion = ultimo_completado
        fecha_ref = fecha_completado or fecha_creacion
        fecha_sugerida = fecha_ref + timedelta(days=dias_desde_anterior)
    elif vehiculo.fecha_compra:
        # Si no hay servicios previos, se cuenta desde la compra:
        # el primer servicio vence a los 60 días, los siguientes cada 100 días
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
