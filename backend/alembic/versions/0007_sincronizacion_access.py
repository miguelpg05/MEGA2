"""Sincronización de matrículas con el Access de la academia.

- Tabla `matriculas_access`: correo -> curso, tal como figura en el Access.
- Tabla `sincronizaciones_access`: histórico de sincronizaciones.
- Columna `usuarios.gestionado_access`: sus cursos los controla el Access.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "matriculas_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("curso_id", sa.Integer(), sa.ForeignKey("cursos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("access_id", sa.String(), nullable=True),
        sa.Column("nombre", sa.String(), nullable=True),
        sa.Column("fecha_sync", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("email", "curso_id", name="uq_matricula_access_email_curso"),
    )
    op.create_index("ix_matriculas_access_id", "matriculas_access", ["id"])
    op.create_index("ix_matriculas_access_email", "matriculas_access", ["email"])
    op.create_index("ix_matriculas_access_curso_id", "matriculas_access", ["curso_id"])

    op.create_table(
        "sincronizaciones_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fecha", sa.DateTime(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("archivo", sa.String(), nullable=True),
        sa.Column("alumnos", sa.Integer(), nullable=True),
        sa.Column("matriculas", sa.Integer(), nullable=True),
        sa.Column("altas", sa.Integer(), nullable=True),
        sa.Column("bajas", sa.Integer(), nullable=True),
        sa.Column("errores", sa.Integer(), nullable=True),
    )
    op.create_index("ix_sincronizaciones_access_id", "sincronizaciones_access", ["id"])
    op.create_index("ix_sincronizaciones_access_fecha", "sincronizaciones_access", ["fecha"])

    op.add_column("usuarios", sa.Column("gestionado_access", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("usuarios", "gestionado_access")
    op.drop_index("ix_sincronizaciones_access_fecha", table_name="sincronizaciones_access")
    op.drop_index("ix_sincronizaciones_access_id", table_name="sincronizaciones_access")
    op.drop_table("sincronizaciones_access")
    op.drop_index("ix_matriculas_access_curso_id", table_name="matriculas_access")
    op.drop_index("ix_matriculas_access_email", table_name="matriculas_access")
    op.drop_index("ix_matriculas_access_id", table_name="matriculas_access")
    op.drop_table("matriculas_access")
