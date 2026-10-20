from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VehiculoDB(Base):
    __tablename__ = "vehiculos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    placa: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    marca: Mapped[str] = mapped_column(String(50), nullable=False)
    modelo: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="carro", nullable=False)
    kilometraje_actual: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    fecha_compra: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relación uno-a-muchos: al eliminar un vehículo se borran en cascada
    # todos sus mantenimientos asociados (delete-orphan).
    # passive_deletes=True permite que la DB maneje el CASCADE a nivel
    # SQL en lugar de que SQLAlchemy lo haga en memoria.
    mantenimientos: Mapped[list["MantenimientoDB"]] = relationship(
        back_populates="vehiculo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


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

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehiculo_id: Mapped[int] = mapped_column(
        ForeignKey("vehiculos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehiculo: Mapped["VehiculoDB"] = relationship(back_populates="mantenimientos")
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")
    es_revision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    costo_estimado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kilometraje: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_programada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_completado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Se usa default=lambda en lugar de default=datetime.now(...) para que
    # la función se evalúe en el momento de crear el registro (cada vez que
    # se instancia el modelo), no al importar el módulo.
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
