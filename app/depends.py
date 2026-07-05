from fastapi import Depends, HTTPException, status

from app.models import UsuarioDB
from app.security import obtener_usuario_actual


async def requiere_admin(
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
) -> UsuarioDB:
    """
    Dependencia de autorización que verifica que el usuario autenticado
    tenga el rol 'administrador'.

    Lee el rol directamente del objeto de base de datos que retorna
    obtener_usuario_actual, nunca de un parámetro de la URL ni del token JWT.
    Esto garantiza que el rol sea siempre el que está almacenado en la DB,
    y que no pueda ser manipulado externamente.

    Uso en un router:
        @router.delete("/{id}")
        async def eliminar(admin: UsuarioDB = Depends(requiere_admin)):
            ...
    """
    if usuario_actual.rol != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: se requiere rol de administrador.",
        )
    return usuario_actual