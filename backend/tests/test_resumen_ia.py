"""Tests del resumen de IA: solo con material real y recorte repartido de los PDFs."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from services.pdf import combinar_materiales, recortar_repartido  # noqa: E402


def test_recortar_repartido_toma_fragmentos_de_todo_el_documento():
    texto = "\n".join(f"Linea {i:04d} " + "x" * 40 for i in range(1000))
    corto, recortado = recortar_repartido(texto, 6000)
    assert recortado and len(corto) <= 6000 + 50
    assert "Linea 0000" in corto and "Linea 0999" in corto      # principio y final
    assert "[…]" in corto
    assert recortar_repartido("breve", 6000) == ("breve", False)


def test_combinar_materiales_reparte_el_cupo():
    docs = [("A", "a" * 20000), ("B", "b" * 20000), ("C", "")]
    texto, recortado = combinar_materiales(docs, 10000)
    assert recortado and texto.count("a") > 3000 and texto.count("b") > 3000
    assert "### C" not in texto
    assert combinar_materiales([], 10000) == ("", False)


@pytest.fixture()
def cliente(monkeypatch):
    import main
    import models
    from models import Base, Curso, Tema, MaterialTema, Usuario
    from routers import auth

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Sesion = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Sesion()
    curso = Curso(nombre="Guardia Civil")
    db.add(curso); db.flush()
    con_pdf = Tema(nombre="La Corona", curso_id=curso.id)
    sin_pdf = Tema(nombre="Las Cortes", curso_id=curso.id)
    db.add_all([con_pdf, sin_pdf]); db.flush()
    db.add(MaterialTema(tema_id=con_pdf.id, nombre_archivo="corona.pdf", contenido=b"%PDF"))
    alumno = Usuario(nombre="Alumno", email="alumno@academiamega.net", rol="estudiante")
    alumno.cursos.append(curso)
    db.add(alumno); db.commit()
    ids = {"con": con_pdf.id, "sin": sin_pdf.id, "alumno": alumno.id}
    db.close()

    def get_db_test():
        s = Sesion()
        try:
            yield s
        finally:
            s.close()

    llamadas = []
    monkeypatch.setattr(main, "extraer_texto_pdf", lambda contenido, max_chars=0: "Art. 57 CE: la Corona es hereditaria. " * 50)
    monkeypatch.setattr(main, "generar_texto", lambda prompt, max_tokens=None: (llamadas.append(prompt) or "## 1. La Corona\ntexto", 100))
    main.app.dependency_overrides[models.get_db] = get_db_test
    def usuario_actual():
        u = Sesion().get(Usuario, ids["alumno"])
        u.cursos  # carga la relación antes de que la sesión se cierre
        return u

    main.app.dependency_overrides[auth.get_current_user] = usuario_actual
    yield TestClient(main.app), ids, llamadas
    main.app.dependency_overrides.clear()


def test_resumen_sin_pdfs_no_se_genera(cliente):
    c, ids, llamadas = cliente
    r = c.post("/api/ia/resumir", json={"tiempo": 15, "nivel": "Intermedio", "tema": "Las Cortes", "tema_ids": [ids["sin"]]})
    assert r.status_code == 400 and "PDF" in r.json()["detail"]
    assert llamadas == []          # no se llama a la IA


def test_resumen_con_pdf_usa_su_texto(cliente):
    c, ids, llamadas = cliente
    r = c.post("/api/ia/resumir", json={"tiempo": 15, "nivel": "Intermedio", "tema": "La Corona",
                                        "tema_ids": [ids["sin"], ids["con"]]})
    assert r.status_code == 200
    datos = r.json()
    assert datos["documentos"] == ["corona.pdf"] and datos["recortado"] is False
    assert "Art. 57 CE" in llamadas[0] and "corona.pdf" in llamadas[0]
