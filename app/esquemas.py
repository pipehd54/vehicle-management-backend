from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class VehiculoCreate(BaseModel):
    """Schema para crear o actualizar un vehículo (datos de entrada)."""
    placa: str = Field(..., min_length=3, max_length=20, description="Placa del vehículo")
    marca: str = Field(..., min_length=2, max_length=50)
    modelo: str = Field(..., min_length=1, max_length=50)
    # pattern restringe el tipo a valores fijos del taller — evita
    # clasificaciones inventadas como "camion" o "moto"
    tipo: str = Field(default="carro", pattern="^(carro|motocicleta)$")
    # ge=0 impide valores negativos de kilometraje desde la API
    kilometraje_actual: int | None = Field(default=0, ge=0)
    fecha_compra: datetime | None = Field(default=None)


class VehiculoResponse(BaseModel):
    """Schema de respuesta para vehículos. Incluye el ID generado."""
    id: int
    placa: str
    marca: str
    modelo: str
    tipo: str
    kilometraje_actual: int | None
    fecha_compra: datetime | None

    model_config = ConfigDict(from_attributes=True)


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)

    @field_validator("password")
    @classmethod
    def validar_longitud_bcrypt(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes en UTF-8.")
        return password


class RegistroRespuesta(BaseModel):
    mensaje: str


class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr
    rol: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class MantenimientoCreate(BaseModel):
    vehiculo_id: int
    descripcion: str = Field(..., min_length=5, max_length=500)
    # estado no tiene pattern porque el frontend puede enviar valores
    # como "pendiente", "en_progreso", "completado", etc.
    estado: str = Field(default="pendiente", max_length=30)
    es_revision: bool = Field(
        default=False,
        description="Indica si el mantenimiento cuenta como revisión oficial del vehículo.",
    )
    # ge=0 evita costos negativos (no tendría sentido en un taller)
    costo_estimado: int | None = Field(default=None, ge=0)
    kilometraje: int | None = Field(default=None, ge=0)
    fecha_programada: datetime | None = Field(default=None)


class MantenimientoUpdate(BaseModel):
    descripcion: str = Field(..., min_length=5, max_length=500)
    estado: str = Field(..., max_length=30)
    es_revision: bool | None = None
    costo_estimado: int | None = Field(default=None, ge=0)
    kilometraje: int | None = Field(default=None, ge=0)
    fecha_programada: datetime | None = Field(default=None)


class MantenimientoResponse(BaseModel):
    id: int
    vehiculo_id: int
    descripcion: str
    estado: str
    es_revision: bool
    costo_estimado: int | None
    kilometraje: int | None
    fecha_programada: datetime | None
    fecha_completado: datetime | None
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)


class ProximoMantenimientoResponse(BaseModel):
    servicio_numero: str
    kilometraje_objetivo: int
    kilometraje_faltante: int
    meses_desde_compra: int
    fecha_sugerida: datetime | None = None
    descripcion_sugerida: str
