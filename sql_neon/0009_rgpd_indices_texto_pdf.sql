-- Migración 0009: RGPD (privacidad y ranking), texto de los PDF e índices de rendimiento.
-- Pegar ENTERO en el SQL Editor de Neon y pulsar Run. Antes debe estar en 0008.
-- Es aditiva: no borra ni modifica datos existentes.

BEGIN;

-- Running upgrade 0008 -> 0009

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS privacidad_aceptada_en TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS privacidad_version VARCHAR(20);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS mostrar_en_ranking BOOLEAN DEFAULT true NOT NULL;
ALTER TABLE materiales_tema ADD COLUMN IF NOT EXISTS texto TEXT;

CREATE INDEX IF NOT EXISTS ix_preguntas_tema_id ON preguntas (tema_id);
CREATE INDEX IF NOT EXISTS ix_preguntas_test_plantilla_id ON preguntas (test_plantilla_id);
CREATE INDEX IF NOT EXISTS ix_respuestas_alumnos_pregunta_id ON respuestas_alumnos (pregunta_id);
CREATE INDEX IF NOT EXISTS ix_respuestas_alumno_pregunta ON respuestas_alumnos (alumno_id, pregunta_id);

UPDATE alembic_version SET version_num='0009' WHERE alembic_version.version_num = '0008';

COMMIT;

-- Comprobación: debe salir 0009
SELECT version_num FROM alembic_version;
