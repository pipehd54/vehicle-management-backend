from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter()

# 1. El Guardián: La función de la dependencia
def verificar_admin(rol: str = Query(...)):
    # Pista: Evalúa si el rol es DIFERENTE a "administrador"
    if rol != "administrador":
        # Pista: Lanza el error con el código de estado correcto para "Prohibido"
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    
    # Si todo está bien, retornamos el rol
    return rol


# 2. La Ruta Protegida
@router.post("/configuracion/")
def actualizar_configuracion(admin_rol: str = Depends(verificar_admin)):
    # Si la dependencia falla, FastAPI corta la comunicación antes de entrar aquí.
    # Si pasa, se ejecuta este bloque con seguridad.
    return {"mensaje": "Configuración del taller actualizada con éxito"}