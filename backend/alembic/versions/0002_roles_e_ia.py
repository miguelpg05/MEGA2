"""Añade el rol de usuario y la tabla de uso de IA.

- usuarios.rol: "alumno" | "profesor" | "admin" (por defecto "alumno").
- ia_llamadas: registro de cada llamada a Gemini para dar visibilidad de uso/coste.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default asegura que las filas ya existentes queden como "alumno".
    op.add_column(
        "usuarios",
        sa.Column("rol", sa.String(), nullable=False, server_default="alumno"),
    )
    # Quitamos el server_default: a partir de ahora el default lo pone la app (models.py).
    op.alter_column("usuarios", "rol", server_default=None)

    op.create_table(
        "ia_llamadas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(), nullable=True),
        sa.Column("tokens_totales", sa.Integer(), nullable=True),
        sa.Column("fecha", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ia_llamadas_usuario_id", "ia_llamadas", ["usuario_id"])
    op.create_index("ix_ia_llamadas_fecha", "ia_llamadas", ["fecha"])


def downgrade() -> None:
    op.drop_index("ix_ia_llamadas_fecha", table_name="ia_llamadas")
    op.drop_index("ix_ia_llamadas_usuario_id", table_name="ia_llamadas")
    op.drop_table("ia_llamadas")
    op.drop_column("usuarios", "rol")
