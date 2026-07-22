"""Introduce cursos y redefine los roles por alcance.

- Nueva tabla `cursos` y tabla intermedia `usuario_cursos` (muchos a muchos):
  para un "admin" son los cursos que gestiona; para un "estudiante", en los que
  está matriculado. El "superadmin" no necesita vínculos: accede a todo.
- `temas.curso_id`: el temario pasa a colgar de un curso.
- Renombrado de roles (¡el orden importa!):
    admin    -> superadmin   (jefes de la academia: todos los cursos)
    profesor -> admin        (profesores: solo sus cursos)
    alumno   -> estudiante

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- cursos ---
    op.create_table(
        "cursos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True),
    )
    op.create_index("ix_cursos_nombre", "cursos", ["nombre"])

    # --- usuario_cursos (muchos a muchos) ---
    op.create_table(
        "usuario_cursos",
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("curso_id", sa.Integer(), sa.ForeignKey("cursos.id", ondelete="CASCADE"), primary_key=True),
    )

    # --- temas.curso_id ---
    op.add_column("temas", sa.Column("curso_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_temas_curso", "temas", "cursos", ["curso_id"], ["id"])
    op.create_index("ix_temas_curso_id", "temas", ["curso_id"])

    # --- Renombrado de roles. El ORDEN es crítico: primero admin -> superadmin,
    # para no colisionar cuando profesor pase a admin. ---
    op.execute("UPDATE usuarios SET rol = 'superadmin' WHERE rol = 'admin'")
    op.execute("UPDATE usuarios SET rol = 'admin' WHERE rol = 'profesor'")
    op.execute("UPDATE usuarios SET rol = 'estudiante' WHERE rol = 'alumno'")


def downgrade() -> None:
    op.execute("UPDATE usuarios SET rol = 'alumno' WHERE rol = 'estudiante'")
    op.execute("UPDATE usuarios SET rol = 'profesor' WHERE rol = 'admin'")
    op.execute("UPDATE usuarios SET rol = 'admin' WHERE rol = 'superadmin'")

    op.drop_index("ix_temas_curso_id", table_name="temas")
    op.drop_constraint("fk_temas_curso", "temas", type_="foreignkey")
    op.drop_column("temas", "curso_id")

    op.drop_table("usuario_cursos")
    op.drop_index("ix_cursos_nombre", table_name="cursos")
    op.drop_table("cursos")
