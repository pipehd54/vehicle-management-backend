from fastapi import FastAPI

from app.routers.mantenimientos import router as mantenimientos_router
from app.routers.usuarios import router as usuarios_router
from app.routers.vehiculos import router as vehiculos_router

app = FastAPI()

app.include_router(mantenimientos_router, prefix="/mantenimientos", tags=["Mantenimientos"])
app.include_router(vehiculos_router, prefix="/vehiculos", tags=["Vehículos"])
app.include_router(usuarios_router, prefix="/usuarios", tags=["Usuarios"])


@app.get("/")
def inicio():
    return {"mensaje": "API de gestión de taller mecánico"}
