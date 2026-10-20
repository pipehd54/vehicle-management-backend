"""Enumeraciones compartidas del dominio.

Centralizar los valores permitidos evita que el mismo estado se escriba de
varias formas ("completado", "Completado", "completado ") y que la lógica de
negocio deje de reconocer registros válidos.
"""

from enum import StrEnum


class RolUsuario(StrEnum):
    """Roles de usuario con permisos sobre la API."""

    MECANICO = "mecanico"
    ADMINISTRADOR = "administrador"


class EstadoMantenimiento(StrEnum):
    """Estados posibles de un mantenimiento en el taller."""

    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


class TipoVehiculo(StrEnum):
    """Tipos de vehículo admitidos por el taller."""

    CARRO = "carro"
    MOTOCIClETA = "motocicleta"
