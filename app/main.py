"""Punto de entrada de la API."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_datos import cerrar_engine, get_db
from app.configuracion import settings
from app.routers.mantenimientos import router as mantenimientos_router
from app.routers.usuarios import router as usuarios_router
from app.routers.vehiculos import router as vehiculos_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("taller")


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    """Libera el pool de conexiones al apagar la aplicación."""
    yield
    await cerrar_engine()
    logger.info("Pool de conexiones cerrado")


app = FastAPI(
    title="baken_taller_mecanico",
    description="""
    API REST para gestion de taller mecanico.

    Permite administrar vehiculos, usuarios y ordenes de mantenimiento
    con autenticacion JWT.
    """,
    version="1.0.0",
    lifespan=ciclo_de_vida,
    # En producción la documentación interactiva se desactiva: expone la
    # superficie completa de la API sin necesidad.
    docs_url="/docs" if settings.documentacion_activada else None,
    redoc_url="/redoc" if settings.documentacion_activada else None,
    openapi_url="/openapi.json" if settings.documentacion_activada else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # La autenticación viaja en la cabecera Authorization (Bearer), no en
    # cookies: no hace falta permitir credenciales y así se evita que un
    # origen no autorizado pueda usar cookies del navegador.
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    """Añade cabeceras de seguridad básicas a todas las respuestas."""
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    respuesta.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if request.url.scheme == "https":
        respuesta.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return respuesta


@app.exception_handler(Exception)
async def manejar_error_inesperado(request: Request, error: Exception) -> JSONResponse:
    """Registra los errores no controlados y devuelve un 500 sin detalles.

    El detalle técnico nunca se devuelve al cliente: solo queda en el log,
    junto con la ruta que lo provocó.
    """
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor."},
    )


app.include_router(
    mantenimientos_router, prefix="/mantenimientos", tags=["Mantenimientos"]
)
app.include_router(vehiculos_router, prefix="/vehiculos", tags=["Vehículos"])
app.include_router(usuarios_router, prefix="/usuarios", tags=["Usuarios"])


@app.get("/")
def inicio():
    """Mensaje de bienvenida de la API."""
    return {"mensaje": "API de gestión de taller mecánico"}


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Verifica que la API y la base de datos estén disponibles."""
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos no está disponible.",
        ) from error

    return {"status": "healthy", "database": "connected"}
