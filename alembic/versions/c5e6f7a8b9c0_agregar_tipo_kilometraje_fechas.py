"""agregar tipo kilometraje y fechas a vehiculos y mantenimientos

Revision ID: c5e6f7a8b9c0
Revises: b3a4d5e6f7a8
Create Date: 2026-07-22 13:37:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = "c5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "b3a4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehiculos", sa.Column("tipo", sa.String(length=20), server_default="carro", nullable=False))
    op.add_column("vehiculos", sa.Column("kilometraje_actual", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("vehiculos", sa.Column("fecha_compra", sa.DateTime(timezone=True), nullable=True))

    op.add_column("mantenimientos", sa.Column("kilometraje", sa.Integer(), nullable=True))
    op.add_column("mantenimientos", sa.Column("fecha_programada", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("mantenimientos", "fecha_programada")
    op.drop_column("mantenimientos", "kilometraje")

    op.drop_column("vehiculos", "fecha_compra")
    op.drop_column("vehiculos", "kilometraje_actual")
    op.drop_column("vehiculos", "tipo")
