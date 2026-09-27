"""Track official revisions and completion timestamps with UTC types.

Revision ID: d4e5f6a7b8c9
Revises: c5e6f7a8b9c0
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "mantenimientos",
        "fecha_creacion",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="fecha_creacion AT TIME ZONE 'UTC'",
    )
    op.add_column(
        "mantenimientos",
        sa.Column("fecha_completado", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "mantenimientos",
        sa.Column(
            "es_revision",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Los registros completados antiguos no guardaban fecha de finalización.
    # fecha_creacion es la única fecha histórica disponible y se asume UTC.
    op.execute(
        sa.text(
            "UPDATE mantenimientos "
            "SET fecha_completado = fecha_creacion "
            "WHERE estado = 'completado'"
        )
    )
    op.create_index(
        "ix_mantenimientos_vehiculo_estado_fecha_completado",
        "mantenimientos",
        ["vehiculo_id", "estado", "es_revision", "fecha_completado"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mantenimientos_vehiculo_estado_fecha_completado",
        table_name="mantenimientos",
    )
    op.drop_column("mantenimientos", "es_revision")
    op.drop_column("mantenimientos", "fecha_completado")
    op.alter_column(
        "mantenimientos",
        "fecha_creacion",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="fecha_creacion AT TIME ZONE 'UTC'",
    )
