-- Migración 0007: sincronización de alumnos y matrículas con el Access.
-- Pegar entero en el SQL Editor de Neon y pulsar Run. Comprobar antes que
-- SELECT version_num FROM alembic_version;  devuelve 0006.

BEGIN;

-- Running upgrade 0006 -> 0007

CREATE TABLE matriculas_access (
    id SERIAL NOT NULL, 
    email VARCHAR NOT NULL, 
    curso_id INTEGER NOT NULL, 
    access_id VARCHAR, 
    nombre VARCHAR, 
    fecha_sync TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_matricula_access_email_curso UNIQUE (email, curso_id), 
    FOREIGN KEY(curso_id) REFERENCES cursos (id) ON DELETE CASCADE
);

CREATE INDEX ix_matriculas_access_id ON matriculas_access (id);

CREATE INDEX ix_matriculas_access_email ON matriculas_access (email);

CREATE INDEX ix_matriculas_access_curso_id ON matriculas_access (curso_id);

CREATE TABLE sincronizaciones_access (
    id SERIAL NOT NULL, 
    fecha TIMESTAMP WITHOUT TIME ZONE, 
    usuario_id INTEGER, 
    archivo VARCHAR, 
    alumnos INTEGER, 
    matriculas INTEGER, 
    altas INTEGER, 
    bajas INTEGER, 
    errores INTEGER, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_sincronizaciones_access_id ON sincronizaciones_access (id);

CREATE INDEX ix_sincronizaciones_access_fecha ON sincronizaciones_access (fecha);

ALTER TABLE usuarios ADD COLUMN gestionado_access BOOLEAN DEFAULT false NOT NULL;

UPDATE alembic_version SET version_num='0007' WHERE alembic_version.version_num = '0006';

COMMIT;

