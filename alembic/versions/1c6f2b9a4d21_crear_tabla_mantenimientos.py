"""crear tabla mantenimientos

Revision ID: 1c6f2b9a4d21
Revises: f700234e0742
Create Date: 2026-06-27 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1c6f2b9a4d21"
down_revision: Union[str, Sequence[str], None] = "f700234e0742"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mantenimientos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vehiculo_id", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("costo_estimado", sa.Integer(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["vehiculo_id"], ["vehiculos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mantenimientos_id"), "mantenimientos", ["id"], unique=False)
    op.create_index(
        op.f("ix_mantenimientos_vehiculo_id"),
        "mantenimientos",
        ["vehiculo_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_mantenimientos_vehiculo_id"), table_name="mantenimientos")
    op.drop_index(op.f("ix_mantenimientos_id"), table_name="mantenimientos")
    op.drop_table("mantenimientos")
