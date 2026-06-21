from fastapi import FastAPI

from app.routers.dispositivos import router as dispositivos_router
from app.routers.proyectos import router as proyectos_router
from app.routers.usuarios import router as usuarios_router
from app.routers.vehiculos import router as vehiculos_router

app = FastAPI()

app.include_router(dispositivos_router, prefix="/dispositivos", tags=["Dispositivos"])
app.include_router(proyectos_router, prefix="/proyectos", tags=["Proyectos"])
app.include_router(vehiculos_router, prefix="/vehiculos", tags=["Vehículos"])
app.include_router(usuarios_router, prefix="/usuarios", tags=["Usuarios"])


@app.get("/")
def inicio():
    return {"mensaje": "Hola Mundo"}
