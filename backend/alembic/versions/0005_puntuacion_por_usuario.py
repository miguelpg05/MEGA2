"""Ranking por usuario y acumulativo: añade puntuaciones.usuario_id.

A partir de ahora hay UNA fila por usuario (se acumula la puntuación). Las filas
antiguas (una por intento, sin usuario_id) quedan con usuario_id NULL y el
ranking las ignora, de modo que dejan de duplicar/contaminar la clasificación.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("puntuaciones", sa.Column("usuario_id", sa.Integer(), nullable=True))
    op.create_index("ix_puntuaciones_usuario_id", "puntuaciones", ["usuario_id"])
    op.create_foreign_key(
        "fk_puntuaciones_usuario", "puntuaciones", "usuarios", ["usuario_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("fk_puntuaciones_usuario", "puntuaciones", type_="foreignkey")
    op.drop_index("ix_puntuaciones_usuario_id", table_name="puntuaciones")
    op.drop_column("puntuaciones", "usuario_id")
