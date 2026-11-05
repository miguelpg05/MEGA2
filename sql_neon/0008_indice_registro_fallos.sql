-- Migración 0008: índice en registro_fallos.alumno_id (acelera el mazo de repaso).
-- Pegar entero en el SQL Editor de Neon y pulsar Run. Comprobar antes que
-- SELECT version_num FROM alembic_version;  devuelve 0007.

BEGIN;

-- Running upgrade 0007 -> 0008

CREATE INDEX IF NOT EXISTS ix_registro_fallos_alumno_id ON registro_fallos (alumno_id);

UPDATE alembic_version SET version_num='0008' WHERE alembic_version.version_num = '0007';

COMMIT;

-- Comprobación: debe salir 0008
SELECT version_num FROM alembic_version;
