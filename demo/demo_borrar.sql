-- =====================================================================
-- BORRA la demo de Academia MEGA: sus 3 cursos (con temas, tests,
-- preguntas y respuestas) y los 8 usuarios de ejemplo. Todo o nada.
-- OJO: borra por NOMBRE de curso; no lo uses si has creado cursos reales
-- con esos mismos nombres.
-- =====================================================================
BEGIN;
CREATE TEMP TABLE d_c ON COMMIT DROP AS SELECT id FROM cursos WHERE nombre IN ('Auxiliar Administrativo del Estado', 'Policía Nacional – Escala Básica', 'Guardia Civil – Cabos y Guardias');
CREATE TEMP TABLE d_u ON COMMIT DROP AS SELECT id FROM usuarios WHERE email IN ('alumna.demo@academiamega.net', 'profesor.demo@academiamega.net', 'sergio.demo@academiamega.net', 'elena.demo@academiamega.net', 'david.demo@academiamega.net', 'carmen.demo@academiamega.net', 'pablo.demo@academiamega.net', 'nuria.demo@academiamega.net');
CREATE TEMP TABLE d_t ON COMMIT DROP AS SELECT id FROM temas WHERE curso_id IN (SELECT id FROM d_c);
CREATE TEMP TABLE d_tp ON COMMIT DROP AS
  SELECT test_plantilla_id AS id FROM test_plantilla_temas WHERE tema_id IN (SELECT id FROM d_t)
  UNION SELECT id FROM test_plantillas WHERE tema_id IN (SELECT id FROM d_t);
CREATE TEMP TABLE d_p ON COMMIT DROP AS SELECT id FROM preguntas
  WHERE tema_id IN (SELECT id FROM d_t) OR test_plantilla_id IN (SELECT id FROM d_tp);
DELETE FROM respuestas_alumnos WHERE pregunta_id IN (SELECT id FROM d_p) OR alumno_id IN (SELECT id FROM d_u);
DELETE FROM registro_fallos WHERE pregunta_id IN (SELECT id FROM d_p) OR alumno_id IN (SELECT id FROM d_u);
DELETE FROM test_intentos WHERE test_plantilla_id IN (SELECT id FROM d_tp) OR alumno_id IN (SELECT id FROM d_u);
DELETE FROM puntuaciones WHERE usuario_id IN (SELECT id FROM d_u);
DELETE FROM ia_llamadas WHERE usuario_id IN (SELECT id FROM d_u);
DELETE FROM preguntas WHERE id IN (SELECT id FROM d_p);
DELETE FROM test_plantilla_temas WHERE test_plantilla_id IN (SELECT id FROM d_tp) OR tema_id IN (SELECT id FROM d_t);
DELETE FROM test_plantillas WHERE id IN (SELECT id FROM d_tp);
DELETE FROM materiales_tema WHERE tema_id IN (SELECT id FROM d_t);
DELETE FROM temas WHERE id IN (SELECT id FROM d_t);
DELETE FROM usuario_cursos WHERE curso_id IN (SELECT id FROM d_c) OR usuario_id IN (SELECT id FROM d_u);
DELETE FROM cursos WHERE id IN (SELECT id FROM d_c);
DELETE FROM usuarios WHERE id IN (SELECT id FROM d_u);
COMMIT;
