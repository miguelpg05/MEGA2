"""Tests asignables a varios temas + datos de modo en los intentos.

- Nueva tabla `test_plantilla_temas` (muchos a muchos test <-> tema). Se rellena
  con el `tema_id` actual de cada test, que se mantiene como "tema principal".
- `test_intentos`: columnas `total_preguntas`, `modo` ("practica"/"examen") y
  `personalizado` (tests configurados por el alumno, sin plantilla).

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test_plantilla_temas",
        sa.Column("test_plantilla_id", sa.Integer(), sa.ForeignKey("test_plantillas.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tema_id", sa.Integer(), sa.ForeignKey("temas.id", ondelete="CASCADE"), primary_key=True),
    )
    # Cada test existente queda asignado a su tema actual (si ese tema existe)
    op.execute(
        """
        INSERT INTO test_plantilla_temas (test_plantilla_id, tema_id)
        SELECT tp.id, tp.tema_id
        FROM test_plantillas tp
        JOIN temas t ON t.id = tp.tema_id
        """
    )

    op.add_column("test_intentos", sa.Column("total_preguntas", sa.Integer(), nullable=True))
    op.add_column("test_intentos", sa.Column("modo", sa.String(), nullable=True))
    op.add_column("test_intentos", sa.Column("personalizado", sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("test_intentos", "personalizado")
    op.drop_column("test_intentos", "modo")
    op.drop_column("test_intentos", "total_preguntas")
    op.drop_table("test_plantilla_temas")
