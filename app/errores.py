"""Errores HTTP reutilizables.

Un único punto para construir las respuestas de error mantiene el mismo
criterio en todos los routers: 404 para recursos ausentes y 409/400 para
conflictos de integridad.
"""

from fastapi import HTTPException, status


def no_encontrado(entidad: str, identificador: int | None = None) -> HTTPException:
    """Construye el 404 de un recurso que no existe."""
    detalle = f"{entidad} no encontrado."
    if identificador is not None:
        detalle = f"{entidad} con ID {identificador} no encontrado."
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detalle)


def conflicto_integridad(mensaje: str) -> HTTPException:
    """Construye el 409 de una violación de unicidad o integridad."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=mensaje)


def operacion_no_permitida(mensaje: str) -> HTTPException:
    """Construye el 403 de una operación restringida por rol."""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mensaje)


def credenciales_invalidas() -> HTTPException:
    """Construye el 401 de credenciales incorrectas o ausentes."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
