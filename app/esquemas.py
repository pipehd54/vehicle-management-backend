"""Modelos de validación de entrada y salida (Pydantic v2)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.enums import EstadoMantenimiento, RolUsuario, TipoVehiculo


class VehiculoCreate(BaseModel):
    """Datos de entrada para crear un vehículo."""

    placa: str = Field(
        ..., min_length=3, max_length=20, description="Placa del vehículo"
    )
    marca: str = Field(..., min_length=2, max_length=50)
    modelo: str = Field(..., min_length=1, max_length=50)
    # El tipo se restringe a los valores admitidos por el taller: evita
    # clasificaciones inventadas como "camion" o "moto".
    tipo: TipoVehiculo = Field(default=TipoVehiculo.CARRO)
    # ge=0 impide valores negativos de kilometraje desde la API.
    kilometraje_actual: int | None = Field(default=0, ge=0)
    fecha_compra: datetime | None = Field(default=None)


class VehiculoPatch(BaseModel):
    """Actualización parcial de un vehículo.

    Todos los campos son opcionales: solo se modifican los que llegan en el
    cuerpo de la petición. Un campo omitido conserva su valor actual.
    """

    placa: str | None = Field(default=None, min_length=3, max_length=20)
    marca: str | None = Field(default=None, min_length=2, max_length=50)
    modelo: str | None = Field(default=None, min_length=1, max_length=50)
    tipo: TipoVehiculo | None = None
    kilometraje_actual: int | None = Field(default=None, ge=0)
    fecha_compra: datetime | None = None


class VehiculoResponse(BaseModel):
    """Vehículo devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    placa: str
    marca: str
    modelo: str
    tipo: TipoVehiculo
    kilometraje_actual: int | None
    fecha_compra: datetime | None


class UsuarioCreate(BaseModel):
    """Datos para registrar un usuario nuevo."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, email: str) -> str:
        """Normaliza el correo a minúsculas.

        Evita que "Taller@Example.com" y "taller@example.com" se registren
        como dos cuentas distintas.
        """
        return email.lower()

    @field_validator("password")
    @classmethod
    def validar_longitud_bcrypt(cls, password: str) -> str:
        """Bcrypt solo procesa los primeros 72 bytes de la contraseña."""
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes en UTF-8.")
        return password


class RegistroRespuesta(BaseModel):
    """Respuesta genérica del registro de usuarios."""

    mensaje: str


class UsuarioResponse(BaseModel):
    """Usuario devuelto por la API (nunca incluye la contraseña)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    rol: RolUsuario
    is_active: bool


class MantenimientoCreate(BaseModel):
    """Datos para registrar un mantenimiento."""

    vehiculo_id: int = Field(..., ge=1)
    descripcion: str = Field(..., min_length=5, max_length=500)
    estado: EstadoMantenimiento = Field(default=EstadoMantenimiento.PENDIENTE)
    es_revision: bool = Field(
        default=False,
        description=(
            "Indica si el mantenimiento cuenta como revisión oficial del vehículo."
        ),
    )
    # ge=0 evita costos negativos (no tendría sentido en un taller).
    costo_estimado: int | None = Field(default=None, ge=0)
    kilometraje: int | None = Field(default=None, ge=0)
    fecha_programada: datetime | None = Field(default=None)


class MantenimientoUpdate(BaseModel):
    """Actualización parcial de un mantenimiento.

    Todos los campos son opcionales: solo se modifican los que llegan en el
    cuerpo de la petición. Un campo omitido conserva su valor actual.
    """

    descripcion: str | None = Field(default=None, min_length=5, max_length=500)
    estado: EstadoMantenimiento | None = None
    es_revision: bool | None = None
    costo_estimado: int | None = Field(default=None, ge=0)
    kilometraje: int | None = Field(default=None, ge=0)
    fecha_programada: datetime | None = None


class CambiarPassword(BaseModel):
    """Cambio de contraseña del usuario autenticado."""

    password_actual: str = Field(..., min_length=1, max_length=72)
    password_nuevo: str = Field(..., min_length=8, max_length=50)

    @field_validator("password_nuevo")
    @classmethod
    def validar_longitud_bcrypt(cls, password: str) -> str:
        """Bcrypt solo procesa los primeros 72 bytes de la contraseña."""
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes en UTF-8.")
        return password


class MantenimientoResponse(BaseModel):
    """Mantenimiento devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vehiculo_id: int
    descripcion: str
    estado: EstadoMantenimiento
    es_revision: bool
    costo_estimado: int | None
    kilometraje: int | None
    fecha_programada: datetime | None
    fecha_completado: datetime | None
    fecha_creacion: datetime


class ProximoMantenimientoResponse(BaseModel):
    """Recomendación del próximo mantenimiento de un vehículo."""

    servicio_numero: str = Field(
        ...,
        description=(
            "Nombre del servicio recomendado, por ejemplo "
            "'2da Revisión de Mantenimiento'."
        ),
    )
    kilometraje_objetivo: int = Field(
        ..., description="Kilometraje objetivo del servicio recomendado."
    )
    kilometraje_faltante: int = Field(
        ..., description="Kilometraje que falta por recorrer."
    )
    meses_desde_compra: int = Field(
        ...,
        description=(
            "Meses que el plan del taller asigna a este nivel de servicio "
            "desde la fecha de compra del vehículo."
        ),
    )
    fecha_sugerida: datetime | None = Field(
        default=None,
        description=(
            "Fecha estimada del próximo servicio, si hay una fecha de "
            "referencia conocida."
        ),
    )
    descripcion_sugerida: str
