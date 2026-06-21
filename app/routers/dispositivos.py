from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Dispositivo(BaseModel):
    nombre: str
    ip: str
    puertos_abiertos: int
    en_linea: bool = True

dispositivos_db: list[Dispositivo] = []

@router.post("/")
def crear_dispositivo(dispositivo: Dispositivo):
    dispositivos_db.append(dispositivo)
    return {"mensaje": "Dispositivo creado", "datos": dispositivo}

@router.get("/")
def obtener_dispositivos(antiguedad_dias: int = 0):
    return {"mensaje": "Dispositivos obtenidos", "datos": dispositivos_db}