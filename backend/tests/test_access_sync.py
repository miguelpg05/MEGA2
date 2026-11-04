"""Tests de la sincronización con el Access de la academia."""
import io
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from services.access_sync import correo_desde_access, interpretar_filas, leer_archivo, normalizar, planificar  # noqa: E402

CURSOS = {normalizar("Policía Nacional – Escala Básica"): 1, normalizar("Guardia Civil"): 2, normalizar("Auxiliar Administrativo"): 3}


# ------------------------------------------------------------- funciones puras

def test_lee_csv_con_punto_y_coma_y_tildes_en_cp1252():
    texto = "Nº;DNI;Nombre;Correo;Cursos\n7;1X;José Pérez;JOSE@academiamega.net;Guardia Civil\n"
    filas = leer_archivo("export.csv", texto.encode("cp1252"))
    alumnos, errores, cols = interpretar_filas(filas, CURSOS)
    assert errores == []
    assert alumnos["jose@academiamega.net"].nombre == "José Pérez"
    assert alumnos["jose@academiamega.net"].access_id == "7"
    assert alumnos["jose@academiamega.net"].cursos == {2}


def test_varios_cursos_en_una_celda_y_nombres_flexibles():
    filas = [{"ID": 1, "Nombre": "Ana", "E-mail": "ana@academiamega.net",
              "Curso": "policia nacional - escala basica; GUARDIA CIVIL"}]
    alumnos, errores, _ = interpretar_filas(filas, CURSOS)
    assert errores == [] and alumnos["ana@academiamega.net"].cursos == {1, 2}


def test_errores_correo_ajeno_curso_desconocido_y_columna_ausente():
    filas = [
        {"Nombre": "A", "Correo": "a@gmail.com", "Cursos": "Guardia Civil"},
        {"Nombre": "B", "Correo": "b@academiamega.net", "Cursos": "Guardia Civil; Bombero"},
        {"Nombre": "C", "Correo": "", "Cursos": "Guardia Civil"},
    ]
    alumnos, errores, _ = interpretar_filas(filas, CURSOS)
    assert len(errores) == 3
    assert alumnos["b@academiamega.net"].cursos == {2} and alumnos["b@academiamega.net"].con_errores
    with pytest.raises(ValueError):
        interpretar_filas([{"Nombre": "X", "Cursos": "Guardia Civil"}], CURSOS)


def test_correo_calculado_igual_que_el_access():
    assert correo_desde_access("Ana", 6351) == "ana6351@academiamega.net"
    assert correo_desde_access("María José", 12) == "mariajose12@academiamega.net"
    assert correo_desde_access("Begoña", 7) == "begonya7@academiamega.net"
    assert correo_desde_access("ÁNGEL", 3) == "angel3@academiamega.net"
    assert correo_desde_access(" Íñigo ", 6351.0) == "inyigo6351@academiamega.net"  # Id leído de Excel como float


def test_sin_columna_correo_se_calcula_desde_nombre_e_id():
    filas = [
        {"Id": 6351.0, "DNI": "1X", "Nombre": "Ana", "Apellidos": "García López", "Cursos": "Guardia Civil"},
        {"Id": 12, "DNI": "2Y", "Nombre": "María José", "Apellidos": "Núñez", "Cursos": "Guardia Civil; Auxiliar Administrativo"},
        {"Id": 13, "DNI": "3Z", "Nombre": "Raúl", "Apellidos": "Peña", "Cursos": "Guardia Civil", "Correo": ""},
        {"Id": 14, "DNI": "4W", "Nombre": "Noël", "Apellidos": "Ruiz", "Cursos": "Guardia Civil"},   # ë no la quita el Access
        {"Id": "", "DNI": "5V", "Nombre": "Sin Id", "Apellidos": "", "Cursos": "Guardia Civil"},
    ]
    alumnos, errores, _ = interpretar_filas(filas, CURSOS)
    assert set(alumnos) == {"ana6351@academiamega.net", "mariajose12@academiamega.net", "raul13@academiamega.net"}
    assert alumnos["ana6351@academiamega.net"].nombre == "Ana García López"   # nombre visible con apellidos
    assert alumnos["mariajose12@academiamega.net"].cursos == {2, 3}
    assert len(errores) == 2 and "noël14" in errores[0] and "Id" in errores[1]


def test_correo_explicito_tiene_prioridad_sobre_el_calculado():
    filas = [{"Id": 5, "Nombre": "Ana", "Correo": "ana.real@academiamega.net", "Cursos": "Guardia Civil"},
             {"Id": 6, "Nombre": "Luis", "Correo": "", "Cursos": "Guardia Civil"}]
    alumnos, errores, _ = interpretar_filas(filas, CURSOS)
    assert errores == [] and set(alumnos) == {"ana.real@academiamega.net", "luis6@academiamega.net"}


def test_planificar_altas_bajas_y_proteccion_ante_errores():
    filas = [
        {"Correo": "a@academiamega.net", "Cursos": "Guardia Civil"},           # cambia de curso
        {"Correo": "b@academiamega.net", "Cursos": "Guardia Civil; Bombero"},  # error: conserva lo anterior
    ]
    alumnos, _, _ = interpretar_filas(filas, CURSOS)
    actuales = {"a@academiamega.net": {1}, "b@academiamega.net": {3}, "c@academiamega.net": {1}}
    deseadas, altas, bajas = planificar(alumnos, actuales, {"a@academiamega.net", "c@academiamega.net"})
    assert deseadas == {"a@academiamega.net": {2}, "b@academiamega.net": {2, 3}}
    assert ("a@academiamega.net", 2) in altas and ("b@academiamega.net", 2) in altas
    assert ("a@academiamega.net", 1) in bajas and ("c@academiamega.net", 1) in bajas   # c desaparece
    assert not any(e == "b@academiamega.net" for e, _ in bajas)


# ------------------------------------------------------------- integración

@pytest.fixture()
def entorno(monkeypatch):
    import models
    from models import Base, Curso, Usuario
    from routers import auth
    from main import app

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Sesion = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def get_db_test():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    db = Sesion()
    db.add_all([Curso(nombre="Policía Nacional – Escala Básica"), Curso(nombre="Guardia Civil"),
                Curso(nombre="Auxiliar Administrativo")])
    jefe = Usuario(nombre="Jefe", email="jefe@academiamega.net", rol="superadmin",
                   hashed_password=auth.get_password_hash("secreto123"))
    profe = Usuario(nombre="Profe", email="profe@academiamega.net", rol="admin")
    demo = Usuario(nombre="Demo", email="alumna.demo@academiamega.net", rol="estudiante",
                   hashed_password=auth.get_password_hash("secreto123"))
    prueba = Usuario(nombre="Estudiante", email="estudiante@academiamega.net", rol="estudiante",
                     hashed_password=auth.get_password_hash("secreto123"))
    normal = Usuario(nombre="Normal", email="normal@academiamega.net", rol="estudiante",
                     hashed_password=auth.get_password_hash("secreto123"))
    db.add_all([jefe, profe, demo, prueba, normal]); db.commit()
    db.close()

    app.dependency_overrides[models.get_db] = get_db_test
    # Login con Google simulado: el "access_token" es el propio correo
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setattr(auth, "_verificar_access_token_google",
                        lambda tok: {"email": tok, "email_verified": "true", "sub": "sub-" + tok})
    cliente = TestClient(app)

    def token(email):
        r = cliente.post("/api/auth/google", json={"access_token": email})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    yield cliente, token, Sesion
    app.dependency_overrides.clear()


def _csv(texto):
    return {"archivo": ("alumnos.csv", io.BytesIO(texto.encode("utf-8")), "text/csv")}


def _cursos_de(cliente, cabeceras):
    return sorted(c["nombre"] for c in cliente.get("/api/auth/me", headers=cabeceras).json()["cursos"])


def test_flujo_completo_sincronizacion_y_login(entorno):
    cliente, token, Sesion = entorno
    jefe = token("jefe@academiamega.net")

    # Laura ya había entrado antes de la sincronización (sin cursos)
    laura = token("laura@academiamega.net")
    assert _cursos_de(cliente, laura) == []

    archivo = ("Id;DNI;Nombre;Correo;Cursos\n"
               "1;111A;Laura Martín;laura@academiamega.net;\"Policía Nacional – Escala Básica; Guardia Civil\"\n"
               "2;222B;Sergio Ruiz;sergio@academiamega.net;Guardia Civil\n"
               "3;333C;Profe;profe@academiamega.net;Guardia Civil\n"
               "4;444D;Error;mal@academiamega.net;Bombero\n"
               "5;555E;Nuria Romero;nuria@academiamega.net;Guardia Civil\n")

    # 1) Vista previa: no cambia nada
    r = cliente.post("/api/admin/access/sincronizar?aplicar=false", files=_csv(archivo), headers=jefe)
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["aplicado"] is False and v["alumnos"] == 4 and v["altas_total"] == 4
    assert v["con_cuenta"] == 1 and v["sin_cuenta"] == 3
    assert any("Bombero" in e for e in v["errores"]) and any("profe@" in e for e in v["errores"])
    assert _cursos_de(cliente, laura) == []

    # 2) Aplicar: Laura (ya registrada) recibe sus cursos al momento
    r = cliente.post("/api/admin/access/sincronizar?aplicar=true", files=_csv(archivo), headers=jefe)
    assert r.json()["aplicado"] is True
    assert _cursos_de(cliente, laura) == ["Guardia Civil", "Policía Nacional – Escala Básica"]

    # 3) Sergio entra por primera vez con Google y ya tiene su curso y su nombre del Access
    sergio = token("sergio@academiamega.net")
    me = cliente.get("/api/auth/me", headers=sergio).json()
    assert [c["nombre"] for c in me["cursos"]] == ["Guardia Civil"] and me["nombre"] == "Sergio Ruiz"

    # 4) El profesor no se toca y el estado refleja lo pendiente
    estado = cliente.get("/api/admin/access/estado", headers=jefe).json()
    assert estado["alumnos_en_access"] == 3 and estado["ultima"]["altas"] == 4
    assert [p["email"] for p in estado["sin_cuenta"]] == ["nuria@academiamega.net"]  # mal@ no tenía ningún curso válido

    # 5) Nueva exportación: Laura deja Guardia Civil y Sergio desaparece del Access
    archivo2 = "Id;Nombre;Correo;Cursos\n1;Laura Martín;laura@academiamega.net;Policía Nacional – Escala Básica\n"
    r = cliente.post("/api/admin/access/sincronizar?aplicar=true", files=_csv(archivo2), headers=jefe).json()
    assert r["bajas_total"] == 3  # Laura deja Guardia Civil; Sergio y Nuria desaparecen
    assert _cursos_de(cliente, laura) == ["Policía Nacional – Escala Básica"]
    sergio = token("sergio@academiamega.net")
    assert _cursos_de(cliente, sergio) == []          # sin cursos, pero puede entrar

    # 6) La alumna demo (nunca estuvo en el Access) no se ha tocado
    db = Sesion()
    from models import Usuario
    assert db.query(Usuario).filter_by(email="alumna.demo@academiamega.net").one().gestionado_access is False
    db.close()


def test_solo_superadmin_puede_sincronizar(entorno):
    cliente, token, _ = entorno
    alumno = token("x@academiamega.net")
    r = cliente.post("/api/admin/access/sincronizar", files=_csv("Correo;Cursos\n"), headers=alumno)
    assert r.status_code == 403


def test_contrasena_cerrada_para_alumnos(entorno):
    cliente, token, _ = entorno
    # Registro con contraseña de un alumno: prohibido
    r = cliente.post("/api/auth/registro", json={"nombre": "A", "email": "nuevo@academiamega.net", "password": "secreto123"})
    assert r.status_code == 403
    # Login con contraseña: superadmin sí, cuenta demo sí
    assert cliente.post("/api/auth/login", json={"email": "jefe@academiamega.net", "password": "secreto123"}).status_code == 200
    assert cliente.post("/api/auth/login", json={"email": "alumna.demo@academiamega.net", "password": "secreto123"}).status_code == 200
    # Cuenta de alumno de prueba (CUENTAS_PRUEBA_EMAILS) sí; un alumno cualquiera con contraseña no
    assert cliente.post("/api/auth/login", json={"email": "estudiante@academiamega.net", "password": "secreto123"}).status_code == 200
    assert cliente.post("/api/auth/login", json={"email": "normal@academiamega.net", "password": "secreto123"}).status_code == 403


def test_plantilla_excel(entorno):
    cliente, token, _ = entorno
    r = cliente.get("/api/admin/access/plantilla", headers=token("jefe@academiamega.net"))
    assert r.status_code == 200 and r.content[:2] == b"PK"
    filas = leer_archivo("p.xlsx", r.content)
    assert set(filas[0].keys()) == {"Id", "DNI", "Nombre", "Apellidos", "Cursos"}
    assert filas[0]["Id"] == 6351 and filas[0]["Nombre"] == "Ana"
