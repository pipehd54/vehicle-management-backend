from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.routers.mantenimientos import router as mantenimientos_router
from app.routers.usuarios import router as usuarios_router
from app.routers.vehiculos import router as vehiculos_router

app = FastAPI(
    title = "baken_taller_mecanico",
    description = """
API REST para gestion de taller mecanico.

Permite administrar vehiculos, usuarios y ordenes de mantenimiento
con autenticacion JWT.
""",
version = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mantenimientos_router, prefix="/mantenimientos", tags=["Mantenimientos"])
app.include_router(vehiculos_router, prefix="/vehiculos", tags=["Vehículos"])
app.include_router(usuarios_router, prefix="/usuarios", tags=["Usuarios"])


@app.get("/")
def inicio():
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
