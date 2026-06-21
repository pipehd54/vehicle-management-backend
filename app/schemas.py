from pydantic import BaseModel, EmailStr, Field


class VehiculoSchema(BaseModel):
    placa: str
    marca: str
    modelo: str


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=50)


class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr
    rol: str
    is_active: bool

    class Config:
        from_attributes = True
