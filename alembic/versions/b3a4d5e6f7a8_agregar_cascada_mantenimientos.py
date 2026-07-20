"""agregar cascada en mantenimientos

Revision ID: b3a4d5e6f7a8
Revises: 1c6f2b9a4d21
Create Date: 2026-07-19 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b3a4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "1c6f2b9a4d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "mantenimientos_vehiculo_id_fkey", "mantenimientos", type_="foreignkey"
    )
    op.create_foreign_key(
        "mantenimientos_vehiculo_id_fkey",
        "mantenimientos",
        "vehiculos",
        ["vehiculo_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "mantenimientos_vehiculo_id_fkey", "mantenimientos", type_="foreignkey"
    )
    op.create_foreign_key(
        "mantenimientos_vehiculo_id_fkey",
        "mantenimientos",
        "vehiculos",
        ["vehiculo_id"],
        ["id"],
    )
