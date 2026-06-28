from pydantic import BaseModel, EmailStr, Field


class VehiculoSchema(BaseModel):
    placa: str
    marca: str
    modelo: str


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)


class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr
    rol: str
    is_active: bool

    class Config:
        from_attributes = True


class MantenimientoCreate(BaseModel):
    vehiculo_id: int
    descripcion: str = Field(..., min_length=5, max_length=500)
    estado: str = Field(default="pendiente", max_length=30)
    costo_estimado: int | None = Field(default=None, ge=0)


class MantenimientoUpdate(BaseModel):
    descripcion: str = Field(..., min_length=5, max_length=500)
    estado: str = Field(..., max_length=30)
    costo_estimado: int | None = Field(default=None, ge=0)


class MantenimientoResponse(BaseModel):
    id: int
    vehiculo_id: int
    descripcion: str
    estado: str
    costo_estimado: int | None

    class Config:
        from_attributes = True
