"""Dependencias de seguridad y autorización."""

from fastapi import Depends

from app.enums import RolUsuario
from app.errores import operacion_no_permitida
from app.modelos import UsuarioDB
from app.seguridad import obtener_usuario_actual


async def requiere_admin(
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual),
) -> UsuarioDB:
    """Verifica que el usuario autenticado tenga el rol de administrador.

    Lee el rol directamente del objeto de base de datos que devuelve
    `obtener_usuario_actual`, nunca de un parámetro de la URL ni del token
    JWT. Esto garantiza que el rol sea siempre el que está almacenado en la
    base de datos y que no pueda ser manipulado externamente.

    Uso en un router:
        @router.delete("/{id}")
        async def eliminar(admin: UsuarioDB = Depends(requiere_admin)):
            ...
    """
    if usuario_actual.rol != RolUsuario.ADMINISTRADOR:
        raise operacion_no_permitida(
            "Acceso restringido: se requiere rol de administrador."
        )
    return usuario_actual
