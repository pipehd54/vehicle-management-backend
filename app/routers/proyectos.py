from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Proyecto(BaseModel):
    titulo: str
    descripcion: str
    lineas_codigo: int
    activo: bool = True

proyectos_db: list[Proyecto] = []

@router.post("/")
def crear_proyecto(proyecto: Proyecto):
    proyectos_db.append(proyecto)
    return {"mensaje": "Proyecto creado", "datos": proyecto}

@router.get("/")
def obtener_proyectos(antiguedad_dias: int = 0):
    return {"mensaje": "Proyectos obtenidos", "datos": proyectos_db}
