"""Utilidades de administración de la API.

El registro público solo permite crear cuentas de mecánico, y esas cuentas
nacen inactivas: hace falta un administrador para activarlas. Crear el
primer administrador con SQL a mano es frágil, así que esta herramienta lo
hace de forma explícita y verificable:

    python -m app.cli crear-admin --email admin@taller.com

La contraseña se solicita de forma oculta si no se indica con --password.
"""

import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.base_datos import async_session
from app.enums import RolUsuario
from app.modelos import UsuarioDB
from app.seguridad import obtener_hash_password


async def _crear_administrador(email: str, password: str) -> int:
    """Crea una cuenta de administrador activa. Devuelve el código de salida."""
    async with async_session() as sesion:
        existente = await sesion.scalar(
            select(UsuarioDB).where(UsuarioDB.email == email)
        )
        if existente is not None:
            print(f"Ya existe una cuenta con el correo {email}.")
            return 1

        sesion.add(
            UsuarioDB(
                email=email,
                hashed_password=obtener_hash_password(password),
                rol=RolUsuario.ADMINISTRADOR,
                is_active=True,
            )
        )
        try:
            await sesion.commit()
        except IntegrityError:
            await sesion.rollback()
            print("No se pudo crear la cuenta: el correo ya está en uso.")
            return 1

    print(f"Administrador creado correctamente: {email}")
    return 0


def main() -> int:
    """Punto de entrada de la herramienta."""
    parser = argparse.ArgumentParser(
        prog="app.cli",
        description="Utilidades de administración de la API de taller.",
    )
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    crear = subcomandos.add_parser(
        "crear-admin", help="Crea una cuenta de administrador activa."
    )
    crear.add_argument("--email", required=True, help="Correo del administrador.")
    crear.add_argument(
        "--password",
        default=None,
        help="Contraseña. Si se omite, se solicita de forma oculta.",
    )

    argumentos = parser.parse_args()

    if argumentos.comando == "crear-admin":
        email = argumentos.email.strip().lower()
        password = argumentos.password or getpass("Contraseña del administrador: ")
        if len(password) < 8:
            print("La contraseña debe tener al menos 8 caracteres.")
            return 1
        return asyncio.run(_crear_administrador(email, password))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
