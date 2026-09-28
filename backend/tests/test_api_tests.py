"""Tests de integración (SQLite en memoria) de las funciones de tests:

- nombres de test con cualquier carácter,
- un mismo test asignado a varios temas (y su alcance por curso),
- "Personaliza tu test",
- registro de intentos con modo / personalizado.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import models  # noqa: E402
from models import Base, Curso, Tema, Pregunta, Usuario  # noqa: E402
from models import TestPlantilla as Plantilla, TestIntento as Intento  # noqa: E402
from routers.auth import get_current_user  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture()
def entorno():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Sesion = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    estado = {"uid": None}

    def get_db_test():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    def usuario_test():
        db = Sesion()
        u = db.get(Usuario, estado["uid"])
        u.cursos  # carga la relación antes de cerrar
        return u

    app.dependency_overrides[models.get_db] = get_db_test
    app.dependency_overrides[get_current_user] = usuario_test

    db = Sesion()
    c1, c2 = Curso(nombre="Auxiliar"), Curso(nombre="Policía")
    db.add_all([c1, c2]); db.commit()
    t1 = Tema(nombre="T1", curso_id=c1.id)
    t2 = Tema(nombre="T2", curso_id=c1.id)
    t3 = Tema(nombre="T3", curso_id=c2.id)
    db.add_all([t1, t2, t3]); db.commit()
    for tema, n in ((t1, 6), (t2, 4), (t3, 3)):
        for i in range(n):
            db.add(Pregunta(enunciado=f"{tema.nombre}-{i}", opcion_a="a", opcion_b="b", opcion_c="c",
                            opcion_d="d", respuesta_correcta="A", tema_id=tema.id))
    jefe = Usuario(nombre="Jefe", email="j@x", rol="superadmin")
    profe = Usuario(nombre="Profe", email="p@x", rol="admin", cursos=[c1])
    alumno = Usuario(nombre="Alumno", email="a@x", rol="estudiante", cursos=[c1, c2])
    otro = Usuario(nombre="Otro", email="o@x", rol="estudiante", cursos=[c2])
    db.add_all([jefe, profe, alumno, otro]); db.commit()
    ids = dict(t1=t1.id, t2=t2.id, t3=t3.id, jefe=jefe.id, profe=profe.id, alumno=alumno.id, otro=otro.id)
    db.close()

    cliente = TestClient(app)

    def como(clave):
        estado["uid"] = ids[clave]
        return cliente

    yield como, ids, Sesion
    app.dependency_overrides.clear()


def test_crear_test_con_nombre_libre_y_varios_temas(entorno):
    como, ids, _ = entorno
    r = como("profe").post("/api/admin/tests", json={"numero_test": "  Simulacro #1 — Bloque I ", "tema_ids": [ids["t2"], ids["t1"]]})
    assert r.status_code == 200, r.text
    test = r.json()
    assert test["numero_test"] == "Simulacro #1 — Bloque I"
    assert test["tema_ids"] == [ids["t2"], ids["t1"]]
    assert test["tema_id"] == ids["t2"]  # el primero es el principal

    # Nombre duplicado -> 400
    r = como("profe").post("/api/admin/tests", json={"numero_test": "Simulacro #1 — Bloque I", "tema_ids": [ids["t1"]]})
    assert r.status_code == 400

    # El profesor no puede asignar temas de cursos ajenos
    r = como("profe").post("/api/admin/tests", json={"numero_test": "X", "tema_ids": [ids["t1"], ids["t3"]]})
    assert r.status_code == 403

    # El test aparece en el banco de ambos temas
    for tema in ("t1", "t2"):
        listado = como("alumno").get(f"/api/test/listado-progreso?tema_id={ids[tema]}").json()
        assert [t["numero_test"] for t in listado] == ["Simulacro #1 — Bloque I"]


def test_profesor_conserva_temas_ajenos_al_editar(entorno):
    como, ids, _ = entorno
    test = como("jefe").post("/api/admin/tests", json={"numero_test": "Compartido", "tema_ids": [ids["t1"], ids["t3"]]}).json()

    # El profesor (solo curso 1) cambia T1 por T2: T3 (curso ajeno) se conserva
    r = como("profe").put(f"/api/admin/tests/{test['id']}", json={"numero_test": "Compartido v2", "tema_ids": [ids["t2"]]})
    assert r.status_code == 200, r.text
    assert set(r.json()["tema_ids"]) == {ids["t2"], ids["t3"]}

    # No puede borrarlo porque afecta a otro curso
    assert como("profe").delete(f"/api/admin/tests/{test['id']}").status_code == 403
    assert como("jefe").delete(f"/api/admin/tests/{test['id']}").status_code == 200


def test_listado_admin_orden_natural(entorno):
    como, ids, _ = entorno
    for nombre in ("Test 10", "Test 2", "001"):
        como("jefe").post("/api/admin/tests", json={"numero_test": nombre, "tema_ids": [ids["t1"]]})
    nombres = [t["numero_test"] for t in como("jefe").get("/api/admin/tests").json()]
    assert nombres == ["001", "Test 2", "Test 10"]


def test_pregunta_debe_pertenecer_a_un_tema_del_test(entorno):
    como, ids, _ = entorno
    test = como("jefe").post("/api/admin/tests", json={"numero_test": "Mixto", "tema_ids": [ids["t1"], ids["t2"]]}).json()
    base = dict(enunciado="¿?", opcion_a="a", opcion_b="b", opcion_c="c", opcion_d="d",
                respuesta_correcta="B", test_plantilla_id=test["id"])
    assert como("jefe").post("/api/admin/preguntas", json={**base, "tema_id": ids["t2"]}).status_code == 200
    assert como("jefe").post("/api/admin/preguntas", json={**base, "tema_id": ids["t3"]}).status_code == 400


def test_test_personalizado(entorno):
    como, ids, _ = entorno
    r = como("alumno").post("/api/test/personalizado", json={"tema_ids": [ids["t1"], ids["t3"]], "num_preguntas": 5})
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["disponibles"] == 9
    assert len(datos["preguntas"]) == 5
    assert {p["tema_id"] for p in datos["preguntas"]} <= {ids["t1"], ids["t3"]}

    # Pide más de las que hay: devuelve todas las disponibles
    r = como("alumno").post("/api/test/personalizado", json={"tema_ids": [ids["t2"]], "num_preguntas": 50})
    assert len(r.json()["preguntas"]) == 4

    # Tema de un curso en el que no está matriculado -> 403
    r = como("otro").post("/api/test/personalizado", json={"tema_ids": [ids["t1"]], "num_preguntas": 5})
    assert r.status_code == 403


def test_temas_incluyen_num_preguntas(entorno):
    como, ids, _ = entorno
    temas = {t["id"]: t for t in como("alumno").get("/api/temas").json()}
    assert temas[ids["t1"]]["num_preguntas"] == 6
    assert temas[ids["t3"]]["curso"] == "Policía"


def test_registrar_intento_personalizado_y_evolucion(entorno):
    como, ids, Sesion = entorno
    r = como("alumno").post("/api/test/registrar-intento",
                           json={"fallos": 3, "total_preguntas": 20, "modo": "examen", "personalizado": True})
    assert r.status_code == 200, r.text
    db = Sesion()
    intento = db.query(Intento).one()
    assert (intento.test_plantilla_id, intento.total_preguntas, intento.modo, intento.personalizado) == (None, 20, "examen", True)
    db.close()

    evo = como("alumno").get("/api/test/evolucion").json()
    assert evo[0]["total"] == 20 and evo[0]["aciertos"] == 17 and evo[0]["numero_test"] == "Personalizado"

    # Sin test y sin marcar personalizado -> 400
    assert como("alumno").post("/api/test/registrar-intento", json={"fallos": 1}).status_code == 400


def test_test_antiguo_sin_filas_intermedias_sigue_visible(entorno):
    como, ids, Sesion = entorno
    db = Sesion()
    db.add(Plantilla(numero_test="007", tema_id=ids["t1"]))  # como los tests previos a la migración
    db.commit(); db.close()
    listado = como("alumno").get(f"/api/test/listado-progreso?tema_id={ids['t1']}").json()
    assert [t["numero_test"] for t in listado] == ["007"]
    admin = como("profe").get("/api/admin/tests").json()
    assert admin[0]["tema_ids"] == [ids["t1"]]


def test_borrar_contenido_ya_respondido_por_alumnos(entorno):
    """Borrar preguntas, tests o temas que los alumnos ya han respondido no debe
    fallar por las claves foráneas de respuestas_alumnos / registro_fallos."""
    from models import RespuestaAlumno, RegistroFallo
    como, ids, Sesion = entorno
    test = como("jefe").post("/api/admin/tests", json={"numero_test": "Con respuestas", "tema_ids": [ids["t1"]]}).json()
    base = dict(opcion_a="a", opcion_b="b", opcion_c="c", opcion_d="d", respuesta_correcta="A",
                tema_id=ids["t1"], test_plantilla_id=test["id"])
    p1 = como("jefe").post("/api/admin/preguntas", json={**base, "enunciado": "P1"}).json()["id"]
    p2 = como("jefe").post("/api/admin/preguntas", json={**base, "enunciado": "P2"}).json()["id"]

    # Un alumno responde y falla ambas
    for pid in (p1, p2):
        como("alumno").post("/api/test/fallo", json={"pregunta_id": pid})
    como("alumno").post("/api/progreso/guardar-resultados",
                        json={"respuestas": [{"pregunta_id": p1, "es_correcta": False}, {"pregunta_id": p2, "es_correcta": True}]})

    assert como("jefe").delete(f"/api/admin/preguntas/{p1}").status_code == 200
    assert como("jefe").delete(f"/api/admin/tests/{test['id']}").status_code == 200
    assert como("jefe").delete(f"/api/admin/temas/{ids['t2']}").status_code == 200  # tema con preguntas

    db = Sesion()
    assert db.query(RespuestaAlumno).filter(RespuestaAlumno.pregunta_id.in_([p1, p2])).count() == 0
    assert db.query(RegistroFallo).filter(RegistroFallo.pregunta_id.in_([p1, p2])).count() == 0
    db.close()
