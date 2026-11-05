"""Índice en registro_fallos.alumno_id.

El mazo de repaso y cada entrega de test filtran los fallos por alumno; sin
índice, PostgreSQL recorre la tabla entera, que crece con cada fallo.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-05
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_registro_fallos_alumno_id", "registro_fallos", ["alumno_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_registro_fallos_alumno_id", table_name="registro_fallos", if_exists=True)
