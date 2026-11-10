"""RGPD, índices de rendimiento y texto de los PDF.

- usuarios: privacidad_aceptada_en, privacidad_version, mostrar_en_ranking.
- materiales_tema.texto: texto extraído del PDF (evita reprocesarlo en cada resumen).
- Índices: preguntas(tema_id), preguntas(test_plantilla_id), respuestas_alumnos(pregunta_id)
  y respuestas_alumnos(alumno_id, pregunta_id).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("privacidad_aceptada_en", sa.DateTime(), nullable=True))
    op.add_column("usuarios", sa.Column("privacidad_version", sa.String(length=20), nullable=True))
    op.add_column("usuarios", sa.Column("mostrar_en_ranking", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("materiales_tema", sa.Column("texto", sa.Text(), nullable=True))
    op.create_index("ix_preguntas_tema_id", "preguntas", ["tema_id"], if_not_exists=True)
    op.create_index("ix_preguntas_test_plantilla_id", "preguntas", ["test_plantilla_id"], if_not_exists=True)
    op.create_index("ix_respuestas_alumnos_pregunta_id", "respuestas_alumnos", ["pregunta_id"], if_not_exists=True)
    op.create_index("ix_respuestas_alumno_pregunta", "respuestas_alumnos", ["alumno_id", "pregunta_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_respuestas_alumno_pregunta", table_name="respuestas_alumnos", if_exists=True)
    op.drop_index("ix_respuestas_alumnos_pregunta_id", table_name="respuestas_alumnos", if_exists=True)
    op.drop_index("ix_preguntas_test_plantilla_id", table_name="preguntas", if_exists=True)
    op.drop_index("ix_preguntas_tema_id", table_name="preguntas", if_exists=True)
    op.drop_column("materiales_tema", "texto")
    op.drop_column("usuarios", "mostrar_en_ranking")
    op.drop_column("usuarios", "privacidad_version")
    op.drop_column("usuarios", "privacidad_aceptada_en")
