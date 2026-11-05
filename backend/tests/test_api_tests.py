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


def _crear_test(como, ids, nombre, correctas):
    """Crea un test en T1 con una pregunta por cada respuesta correcta indicada."""
    test = como("jefe").post("/api/admin/tests", json={"numero_test": nombre, "tema_ids": [ids["t1"]]}).json()
    pids = []
    for n, letra in enumerate(correctas):
        r = como("jefe").post("/api/admin/preguntas", json=dict(
            enunciado=f"{nombre}-{n}", opcion_a="a", opcion_b="b", opcion_c="c", opcion_d="d",
            respuesta_correcta=letra, tema_id=ids["t1"], test_plantilla_id=test["id"]))
        assert r.status_code == 200, r.text
        pids.append(r.json()["id"])
    return test["id"], pids


def test_entregar_corrige_en_el_servidor_y_guarda_todo(entorno):
    from models import RespuestaAlumno, RegistroFallo, Puntuacion
    como, ids, Sesion = entorno
    test_id, (p1, p2, p3, p4) = _crear_test(como, ids, "Entrega", ["A", "B", "AC", "D"])

    # p1 bien, p2 mal, p3 (varias correctas) bien, p4 sin enviar -> en blanco
    r = como("alumno").post("/api/test/entregar", json={
        "test_plantilla_id": test_id, "modo": "examen",
        "respuestas": [{"pregunta_id": p1, "seleccion": ["a"]},
                       {"pregunta_id": p2, "seleccion": ["C"]},
                       {"pregunta_id": p3, "seleccion": ["C", "A"]}]})
    assert r.status_code == 200, r.text
    res = r.json()
    assert (res["aciertos"], res["fallos"], res["en_blanco"], res["total"]) == (2, 1, 1, 4)
    assert res["nota"] == 5.0 and res["porcentaje"] == 50

    db = Sesion()
    intento = db.query(Intento).one()
    assert (intento.fallos_ultimo, intento.total_preguntas, intento.modo, intento.personalizado) == (2, 4, "examen", False)
    assert db.query(RespuestaAlumno).filter_by(alumno_id=ids["alumno"]).count() == 4
    assert {f.pregunta_id for f in db.query(RegistroFallo).filter_by(alumno_id=ids["alumno"])} == {p2, p4}
    assert db.query(Puntuacion).filter_by(usuario_id=ids["alumno"]).one().puntos == 2
    db.close()

    # Segunda entrega fallando p2 otra vez: no se duplica la carta de repaso y los puntos se acumulan
    como("alumno").post("/api/test/entregar", json={"test_plantilla_id": test_id, "modo": "practica",
                        "respuestas": [{"pregunta_id": p1, "seleccion": ["A"]}, {"pregunta_id": p2, "seleccion": ["A"]}]})
    db = Sesion()
    assert db.query(RegistroFallo).filter_by(alumno_id=ids["alumno"], pregunta_id=p2).count() == 1
    assert db.query(Puntuacion).filter_by(usuario_id=ids["alumno"]).one().puntos == 3
    db.close()

    evo = como("alumno").get("/api/test/evolucion").json()
    assert [e["aciertos"] for e in evo] == [2, 1] and evo[0]["total"] == 4


def test_entregar_rechaza_entregas_invalidas_sin_guardar_nada(entorno):
    from models import RespuestaAlumno
    como, ids, Sesion = entorno
    test_id, (p1,) = _crear_test(como, ids, "Validación", ["A"])
    otra = Sesion().query(Pregunta).filter(Pregunta.tema_id == ids["t3"]).first().id

    # Pregunta que no es de ese test
    r = como("alumno").post("/api/test/entregar", json={"test_plantilla_id": test_id,
                            "respuestas": [{"pregunta_id": otra, "seleccion": ["A"]}]})
    assert r.status_code == 400
    # Alumno sin acceso al curso del test
    r = como("otro").post("/api/test/entregar", json={"test_plantilla_id": test_id,
                          "respuestas": [{"pregunta_id": p1, "seleccion": ["A"]}]})
    assert r.status_code == 403
    # Test que no existe / sin indicar test
    assert como("alumno").post("/api/test/entregar", json={"test_plantilla_id": 9999,
                               "respuestas": [{"pregunta_id": p1, "seleccion": []}]}).status_code == 404
    assert como("alumno").post("/api/test/entregar", json={
        "respuestas": [{"pregunta_id": p1, "seleccion": []}]}).status_code == 400
    # Los endpoints antiguos que se fiaban del navegador ya no existen
    assert como("alumno").post("/api/ranking/guardar", json={"puntos": 9999}).status_code in (404, 405)
    assert como("alumno").post("/api/progreso/guardar-resultados", json={"respuestas": []}).status_code in (404, 405)
    assert como("alumno").post("/api/test/registrar-intento", json={"fallos": 0}).status_code in (404, 405)

    db = Sesion()
    assert db.query(Intento).count() == 0 and db.query(RespuestaAlumno).count() == 0
    db.close()


def test_entregar_personalizado(entorno):
    como, ids, Sesion = entorno
    preguntas = como("alumno").post("/api/test/personalizado",
                                    json={"tema_ids": [ids["t2"]], "num_preguntas": 3}).json()["preguntas"]
    respuestas = [{"pregunta_id": p["id"], "seleccion": ["A"]} for p in preguntas]  # en T2 la correcta es A
    r = como("alumno").post("/api/test/entregar", json={"personalizado": True, "modo": "examen", "respuestas": respuestas})
    assert r.status_code == 200, r.text
    assert (r.json()["aciertos"], r.json()["total"]) == (3, 3)
    evo = como("alumno").get("/api/test/evolucion").json()
    assert evo[0]["numero_test"] == "Personalizado" and evo[0]["porcentaje"] == 100

    # Preguntas de un tema de otro curso -> 403
    ajena = Sesion().query(Pregunta).filter(Pregunta.tema_id == ids["t1"]).first().id
    r = como("otro").post("/api/test/entregar", json={"personalizado": True,
                          "respuestas": [{"pregunta_id": ajena, "seleccion": ["A"]}]})
    assert r.status_code == 403


def test_fallo_suelto_no_duplica_y_valida_pregunta(entorno):
    from models import RegistroFallo
    como, ids, Sesion = entorno
    pid = Sesion().query(Pregunta).filter(Pregunta.tema_id == ids["t1"]).first().id
    for _ in range(3):
        assert como("alumno").post("/api/test/fallo", json={"pregunta_id": pid}).status_code == 200
    assert Sesion().query(RegistroFallo).filter_by(alumno_id=ids["alumno"]).count() == 1
    assert como("alumno").post("/api/test/fallo", json={"pregunta_id": 99999}).status_code == 404


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
    como("alumno").post("/api/test/entregar", json={"test_plantilla_id": test["id"], "modo": "examen",
                        "respuestas": [{"pregunta_id": p1, "seleccion": ["B"]}, {"pregunta_id": p2, "seleccion": ["A"]}]})

    assert como("jefe").delete(f"/api/admin/preguntas/{p1}").status_code == 200
    assert como("jefe").delete(f"/api/admin/tests/{test['id']}").status_code == 200
    assert como("jefe").delete(f"/api/admin/temas/{ids['t2']}").status_code == 200  # tema con preguntas

    db = Sesion()
    assert db.query(RespuestaAlumno).filter(RespuestaAlumno.pregunta_id.in_([p1, p2])).count() == 0
    assert db.query(RegistroFallo).filter(RegistroFallo.pregunta_id.in_([p1, p2])).count() == 0
    db.close()


def test_secret_key_obligatoria_y_segura():
    from routers.auth import cargar_secret_key
    for mala in (None, "", "corta", "mi_clave_super_secreta_para_el_mvp", "cambia-esto-por-una-clave-larga-y-aleatoria"):
        with pytest.raises(RuntimeError):
            cargar_secret_key(mala)
    assert cargar_secret_key("  " + "k" * 40 + " ") == "k" * 40


def test_pool_de_conexiones_para_postgres():
    from models import opciones_engine
    assert opciones_engine("sqlite://") == {}
    op = opciones_engine("postgresql+psycopg2://u:p@host/db")
    assert op["pool_pre_ping"] is True and op["pool_recycle"] == 300 and op["pool_size"] >= 5
