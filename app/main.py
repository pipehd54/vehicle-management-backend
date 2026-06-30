from fastapi import FastAPI

from app.routers.mantenimientos import router as mantenimientos_router
from app.routers.usuarios import router as usuarios_router
from app.routers.vehiculos import router as vehiculos_router

app = FastAPI(
    title = "baken_taller_mecanico",
    descripcion = """
API REST para gestion de taller mecanico.

Permite administrar vehiculos, usuarios y ordenes de mantenimiento
con autenticacion JWT.
""",
version = "1.0.0",
)

app.include_router(mantenimientos_router, prefix="/mantenimientos", tags=["Mantenimientos"])
app.include_router(vehiculos_router, prefix="/vehiculos", tags=["Vehículos"])
app.include_router(usuarios_router, prefix="/usuarios", tags=["Usuarios"])


@app.get("/")
def inicio():
    return {"mensaje": "API de gestión de taller mecánico"}
