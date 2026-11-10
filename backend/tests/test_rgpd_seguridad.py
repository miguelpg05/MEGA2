"""Auditoría nov. 2026: conexiones, progreso, ranking privado, RGPD y cabeceras de seguridad."""
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base, Pregunta, RegistroFallo, RespuestaAlumno, TestIntento, Usuario, MaterialTema, exigir_tls
from routers.auth import _liberar_conexion
from routers.ranking import nombre_corto
from tests.test_api_tests import _crear_test, _entregar, entorno  # noqa: F401  (fixture compartida)


# ------------------------------------------------------------ conexiones y TLS

def test_autenticacion_devuelve_la_conexion_al_pool():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add(Usuario(nombre="Ana López", email="ana@x", rol="estudiante")); db.commit()
    u = db.query(Usuario).first()
    assert db.in_transaction()
    _liberar_conexion(db)
    assert not db.in_transaction()          # conexión devuelta
    assert u.nombre == "Ana López"          # los datos siguen cargados (no expirados)
    assert db.expire_on_commit is True       # se restaura la configuración


def test_exigir_tls_en_bases_de_datos_remotas():
    assert exigir_tls("postgresql+psycopg2://u:p@ep-x-pooler.neon.tech/db").endswith("?sslmode=require")
    assert exigir_tls("postgresql+psycopg2://u:p@host/db?x=1").endswith("&sslmode=require")
    assert exigir_tls("postgresql+psycopg2://u:p@host/db?sslmode=verify-full").endswith("verify-full")
    assert exigir_tls("postgresql+psycopg2://u:p@localhost/db") == "postgresql+psycopg2://u:p@localhost/db"
    assert exigir_tls("sqlite://") == "sqlite://"


# ------------------------------------------------------------ progreso por tema

def test_progreso_usa_la_ultima_respuesta_de_cada_pregunta(entorno):
    como, ids, Sesion = entorno
    test_id, pids = _crear_test(como, ids, "Prog", ["A"] * 4)
    _entregar(como, "alumno", test_id, pids, 1)        # 1 de 4 bien
    assert como("alumno").get(f"/api/progreso/tema/{ids['t1']}").json()["porcentaje_actual"] == 25
    _entregar(como, "alumno", test_id, pids, 4)        # ahora las 4 bien
    tema = como("alumno").get(f"/api/progreso/tema/{ids['t1']}").json()
    assert tema["porcentaje_actual"] == 100 and tema["superado"] is True   # (media histórica sería 62 %)

    todos = como("alumno").get("/api/progreso/temas").json()
    assert todos[str(ids["t1"])]["porcentaje_actual"] == 100
    assert str(ids["t2"]) not in todos                  # sin respuestas -> 0 % en el frontend
    assert como("otro").get("/api/progreso/temas").json() == {}   # cada uno solo ve lo suyo


# ------------------------------------------------------------ ranking privado

def test_nombre_corto():
    assert nombre_corto("Lucía Fernández Gutiérrez") == "Lucía F."
    assert nombre_corto("ana") == "ana"
    assert nombre_corto("") == "Alumno"


def test_ranking_nombres_cortos_y_ocultarse(entorno):
    como, ids, Sesion = entorno
    db = Sesion()
    db.get(Usuario, ids["alumno"]).nombre = "Lucía Fernández"
    c1 = db.get(Usuario, ids["profe"]).cursos[0].id
    otra = Usuario(nombre="Pedro Gómez", email="pg@x", rol="estudiante")
    otra.cursos.append(db.get(Usuario, ids["profe"]).cursos[0])
    db.add(otra); db.commit(); ids["pedro"] = otra.id; db.close()

    test_id, pids = _crear_test(como, ids, "Rk", ["A"] * 2)
    _entregar(como, "alumno", test_id, pids, 2)
    _entregar(como, "pedro", test_id, pids, 1)

    vista_pedro = como("pedro").get(f"/api/ranking/clase?curso_id={c1}").json()
    assert [l["nombre"] for l in vista_pedro["lideres"]] == ["Lucía F.", "Pedro Gómez"]  # él se ve entero
    vista_profe = como("profe").get(f"/api/ranking/clase?curso_id={c1}&completo=true").json()
    assert vista_profe["lideres"][0]["nombre"] == "Lucía Fernández" and vista_profe["lideres"][0]["oculto"] is False

    # Lucía se oculta: desaparece para los compañeros (y Pedro pasa a ser 1º), el profesorado la sigue viendo
    assert como("alumno").put("/api/auth/ranking", json={"visible": False}).json() == {"mostrar_en_ranking": False}
    vista_pedro = como("pedro").get(f"/api/ranking/clase?curso_id={c1}").json()
    assert [(l["posicion"], l["nombre"]) for l in vista_pedro["lideres"]] == [(1, "Pedro Gómez")]
    vista_lucia = como("alumno").get(f"/api/ranking/clase?curso_id={c1}").json()
    assert vista_lucia["oculto"] is True and vista_lucia["yo"] is None
    assert como("profe").get(f"/api/ranking/clase?curso_id={c1}&completo=true").json()["lideres"][0]["oculto"] is True


# ------------------------------------------------------------ RGPD

def test_aceptar_privacidad_y_descargar_datos(entorno):
    como, ids, _ = entorno
    me = como("alumno").get("/api/auth/me").json()
    assert me["debe_aceptar_privacidad"] is True and me["mostrar_en_ranking"] is True
    assert como("alumno").post("/api/auth/privacidad/aceptar").json()["aceptada"] is True
    assert como("alumno").get("/api/auth/me").json()["debe_aceptar_privacidad"] is False

    test_id, pids = _crear_test(como, ids, "Datos", ["A", "A"])
    _entregar(como, "alumno", test_id, pids, 1)
    r = como("alumno").get("/api/auth/mis-datos")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    datos = r.json()
    assert datos["usuario"]["email"] == "a@x" and datos["usuario"]["privacidad_version"]
    assert len(datos["intentos_de_test"]) == 1 and len(datos["respuestas"]) == 2
    assert datos["fallos_para_repaso"][0]["repasada"] is False


def test_suprimir_usuario_borra_todo_su_historial(entorno):
    como, ids, Sesion = entorno
    test_id, pids = _crear_test(como, ids, "Borrar", ["A", "A"])
    _entregar(como, "alumno", test_id, pids, 1)

    url = f"/api/admin/usuarios/{ids['alumno']}"
    assert como("profe").delete(url + "?confirmar_email=a@x").status_code == 403       # solo superadmin
    assert como("jefe").delete(url + "?confirmar_email=otro@x").status_code == 400     # confirmación errónea
    assert como("jefe").delete(f"/api/admin/usuarios/{ids['jefe']}?confirmar_email=j@x").status_code == 400  # a sí mismo no
    r = como("jefe").delete(url + "?confirmar_email=A@X")
    assert r.status_code == 200, r.text
    assert r.json()["borrados"]["respuestas"] == 2 and r.json()["borrados"]["intentos"] == 1

    db = Sesion()
    uid = ids["alumno"]
    assert db.get(Usuario, uid) is None
    for modelo in (RespuestaAlumno, RegistroFallo, TestIntento):
        assert db.query(modelo).filter(modelo.alumno_id == uid).count() == 0
    assert db.query(Pregunta).count() > 0          # el contenido de la academia no se toca
    db.close()


# ------------------------------------------------------------ cabeceras, CORS, tamaños, PDF

def test_cabeceras_de_seguridad_y_cors():
    c = TestClient(app)
    r = c.get("/api/test-cors", headers={"Origin": "https://mega-2-rho.vercel.app"})
    assert r.headers["access-control-allow-origin"] == "https://mega-2-rho.vercel.app"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "max-age" in r.headers["strict-transport-security"]
    falso = c.get("/api/test-cors", headers={"Origin": "https://mega-2-falso.vercel.app"})
    assert "access-control-allow-origin" not in falso.headers


def test_peticion_demasiado_grande_y_campos_largos(entorno):
    como, ids, _ = entorno
    r = TestClient(app).post("/api/auth/login", content=b"x", headers={"content-length": str(50 * 1024 * 1024)})
    assert r.status_code == 413
    r = como("alumno").post("/api/ia/resumir", json={"tiempo": 15, "nivel": "Intermedio", "tema": "x", "texto": "a" * 70_000})
    assert r.status_code == 422


def test_solo_pdf_de_verdad_y_descarga_segura(entorno):
    como, ids, Sesion = entorno
    url = f"/api/admin/temas/{ids['t1']}/materiales"
    falso = como("profe").post(url, files={"archivo": ("tema.pdf", io.BytesIO(b"<html><script>alert(1)</script>"), "text/html")})
    assert falso.status_code == 400 and "no es un PDF" in falso.json()["detail"]
    bueno = como("profe").post(url, files={"archivo": ("Tema 1 ñ.pdf", io.BytesIO(b"%PDF-1.4\n%%EOF"), "text/html")})
    assert bueno.status_code == 200, bueno.text
    mid = bueno.json()["id"]
    db = Sesion()
    m = db.get(MaterialTema, mid)
    assert m.tipo_mime == "application/pdf" and m.texto == ""      # texto guardado al subir (aquí vacío)
    db.close()
    r = como("alumno").get(f"/api/temas/{ids['t1']}/materiales/{mid}/descargar")
    assert r.headers["content-type"] == "application/pdf" and r.headers["x-content-type-options"] == "nosniff"
