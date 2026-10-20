"""Modelos ORM de la aplicación."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
)
from sqlalchemy import (
    Enum as TipoEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_datos import Base
from app.enums import EstadoMantenimiento, RolUsuario, TipoVehiculo

# Los enums se declaran sobre columnas VARCHAR (native_enum=False) para no
# cambiar el tipo de las columnas ya existentes en la base de datos. El
# `values_callable` garantiza que en la base se guarde el valor en minúsculas
# ('completado') y no el nombre del miembro ('COMPLETADO').


class VehiculoDB(Base):
    """Vehículo registrado en el taller."""

    __tablename__ = "vehiculos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    placa: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    marca: Mapped[str] = mapped_column(String(50), nullable=False)
    modelo: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo: Mapped[TipoVehiculo] = mapped_column(
        TipoEnum(
            TipoVehiculo,
            native_enum=False,
            length=20,
            values_callable=lambda enumeracion: [m.value for m in enumeracion],
            create_constraint=False,
        ),
        default=TipoVehiculo.CARRO,
        server_default="carro",
        nullable=False,
    )
    kilometraje_actual: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0, server_default="0"
    )
    fecha_compra: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
    """Usuario del sistema, con autenticación JWT y control de acceso por rol."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(225), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        TipoEnum(
            RolUsuario,
            native_enum=False,
            length=50,
            values_callable=lambda enumeracion: [m.value for m in enumeracion],
            create_constraint=False,
        ),
        default=RolUsuario.MECANICO,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MantenimientoDB(Base):
    """Mantenimiento u orden de servicio asociada a un vehículo."""

    __tablename__ = "mantenimientos"
    __table_args__ = (
        # Índice compuesto que acelera el cálculo del próximo mantenimiento:
        # filtra por vehículo, estado, marca de revisión y fecha de cierre.
        Index(
            "ix_mantenimientos_vehiculo_estado_fecha_completado",
            "vehiculo_id",
            "estado",
            "es_revision",
            "fecha_completado",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehiculo_id: Mapped[int] = mapped_column(
        ForeignKey("vehiculos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehiculo: Mapped["VehiculoDB"] = relationship(back_populates="mantenimientos")
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoMantenimiento] = mapped_column(
        TipoEnum(
            EstadoMantenimiento,
            native_enum=False,
            length=30,
            values_callable=lambda enumeracion: [m.value for m in enumeracion],
            create_constraint=False,
        ),
        default=EstadoMantenimiento.PENDIENTE,
        nullable=False,
    )
    es_revision: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    costo_estimado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kilometraje: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_programada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_completado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Se usa default=lambda en lugar de default=datetime.now(...) para que
    # la función se evalúe en el momento de crear el registro (cada vez que
    # se instancia el modelo), no al importar el módulo.
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
