from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VehiculoDB(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(20), unique=True, nullable=False)
    marca = Column(String(50), nullable=False)
    modelo = Column(String(50), nullable=False)


class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(String(225), nullable=False)

    rol: Mapped[str] = mapped_column(String(50), default="mecanico")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class MantenimientoDB(Base):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False, index=True)
    descripcion = Column(Text, nullable=False)
    estado = Column(String(30), nullable=False, default="pendiente")
    costo_estimado = Column(Integer, nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
