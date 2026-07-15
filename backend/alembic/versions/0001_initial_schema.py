"""Esquema inicial (temas, preguntas, usuarios, tests, progreso...).

Refleja el estado de models.py, incluyendo las columnas `google_sub` y `sesion_id`
de `usuarios` que antes se añadían con ALTER TABLE en el arranque de la app.

IMPORTANTE — bases de datos que YA existen (producción en Neon):
    Las tablas ya están creadas. NO ejecutes `upgrade` sobre ellas o fallará por
    "tabla ya existe". En su lugar, marca la BD como ya migrada:
        alembic stamp head
    A partir de ahí, las siguientes migraciones se aplican con `alembic upgrade head`.

Bases de datos NUEVAS (local/staging):
        alembic upgrade head   # crea todo el esquema

Revision ID: 0001
Revises:
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- temas ---
    op.create_table(
        "temas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=True),
        sa.Column("bloque", sa.String(), nullable=True),
    )
    op.create_index("ix_temas_nombre", "temas", ["nombre"])

    # --- test_plantillas ---
    op.create_table(
        "test_plantillas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero_test", sa.String(), nullable=True),
        sa.Column("tema_id", sa.Integer(), nullable=True),
        sa.Column("total_preguntas", sa.Integer(), nullable=True),
    )
    op.create_index("ix_test_plantillas_numero_test", "test_plantillas", ["numero_test"], unique=True)

    # --- preguntas ---
    op.create_table(
        "preguntas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enunciado", sa.String(), nullable=True),
        sa.Column("opcion_a", sa.String(), nullable=True),
        sa.Column("opcion_b", sa.String(), nullable=True),
        sa.Column("opcion_c", sa.String(), nullable=True),
        sa.Column("opcion_d", sa.String(), nullable=True),
        sa.Column("respuesta_correcta", sa.String(), nullable=True),
        sa.Column("explicacion", sa.String(), nullable=True),
        sa.Column("tema_id", sa.Integer(), sa.ForeignKey("temas.id"), nullable=True),
        sa.Column(
            "test_plantilla_id",
            sa.Integer(),
            sa.ForeignKey("test_plantillas.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )

    # --- usuarios ---
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("google_sub", sa.String(), nullable=True),
        sa.Column("sesion_id", sa.String(), nullable=True),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)
    op.create_index("ix_usuarios_google_sub", "usuarios", ["google_sub"], unique=True)

    # --- registro_fallos ---
    op.create_table(
        "registro_fallos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alumno_id", sa.Integer(), nullable=True),
        sa.Column("pregunta_id", sa.Integer(), sa.ForeignKey("preguntas.id"), nullable=True),
        sa.Column("repasada", sa.Boolean(), nullable=True),
    )

    # --- puntuaciones ---
    op.create_table(
        "puntuaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alumno_nombre", sa.String(), nullable=True),
        sa.Column("puntos", sa.Integer(), nullable=True),
        sa.Column("fecha", sa.String(), nullable=True),
    )

    # --- respuestas_alumnos ---
    op.create_table(
        "respuestas_alumnos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alumno_id", sa.Integer(), nullable=True),
        sa.Column("pregunta_id", sa.Integer(), sa.ForeignKey("preguntas.id"), nullable=True),
        sa.Column("es_correcta", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_respuestas_alumnos_alumno_id", "respuestas_alumnos", ["alumno_id"])

    # --- test_intentos ---
    op.create_table(
        "test_intentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alumno_id", sa.Integer(), nullable=True),
        sa.Column("test_plantilla_id", sa.Integer(), nullable=True),
        sa.Column("fecha_intento", sa.DateTime(), nullable=True),
        sa.Column("fallos_ultimo", sa.Integer(), nullable=True),
    )
    op.create_index("ix_test_intentos_alumno_id", "test_intentos", ["alumno_id"])
    op.create_index("ix_test_intentos_test_plantilla_id", "test_intentos", ["test_plantilla_id"])


def downgrade() -> None:
    op.drop_table("test_intentos")
    op.drop_index("ix_respuestas_alumnos_alumno_id", table_name="respuestas_alumnos")
    op.drop_table("respuestas_alumnos")
    op.drop_table("puntuaciones")
    op.drop_table("registro_fallos")
    op.drop_index("ix_usuarios_google_sub", table_name="usuarios")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_table("preguntas")
    op.drop_index("ix_test_plantillas_numero_test", table_name="test_plantillas")
    op.drop_table("test_plantillas")
    op.drop_index("ix_temas_nombre", table_name="temas")
    op.drop_table("temas")
