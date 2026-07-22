"""Material (PDFs) asociado a cada tema.

El contenido del PDF se guarda en la propia base de datos (columna binaria).
Ten presente el límite de almacenamiento de Neon: el tamaño por archivo se
limita en la app con MAX_PDF_MB.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materiales_tema",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tema_id", sa.Integer(), sa.ForeignKey("temas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nombre_archivo", sa.String(), nullable=False),
        sa.Column("tipo_mime", sa.String(), nullable=True),
        sa.Column("tamano_bytes", sa.Integer(), nullable=True),
        sa.Column("contenido", sa.LargeBinary(), nullable=False),
        sa.Column("fecha_subida", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_materiales_tema_tema_id", "materiales_tema", ["tema_id"])


def downgrade() -> None:
    op.drop_index("ix_materiales_tema_tema_id", table_name="materiales_tema")
    op.drop_table("materiales_tema")
