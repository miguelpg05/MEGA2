"""Importación masiva de preguntas: formatos de archivo, validación y duplicados."""
import io

import pytest
from openpyxl import Workbook, load_workbook

from services.importar_preguntas import detectar_columnas, interpretar_fila, leer_filas
from tests.test_api_tests import entorno  # noqa: F401  (fixture compartida)

CAB = "tema_id,numero_test,enunciado,opcion_a,opcion_b,opcion_c,opcion_d,respuesta_correcta,explicacion"


def _fila(**kw):
    base = dict(tema_id="1", numero_test="001", enunciado="¿Pregunta?", opcion_a="a", opcion_b="b",
                opcion_c="c", opcion_d="d", respuesta_correcta="A", explicacion="")
    base.update(kw)
    return base


COLS = {c: c for c in CAB.split(",")}


# ------------------------------------------------------------------ lógica pura

def test_lee_csv_del_excel_espanol_y_utf8():
    excel_es = ("tema_id;numero_test;enunciado;opcion_a;opcion_b;opcion_c;opcion_d;respuesta_correcta;explicacion\r\n"
                "1;001;¿Qué artículo?;a;b;c;d;C;sí\r\n").encode("cp1252")
    filas = leer_filas("preguntas.csv", excel_es)
    assert filas[0]["enunciado"] == "¿Qué artículo?" and filas[0]["respuesta_correcta"] == "C"
    utf8 = (CAB + "\n1,001,\"Uno, dos\",a,b,c,d,B,\n").encode("utf-8")
    assert leer_filas("p.CSV", utf8)[0]["enunciado"] == "Uno, dos"
    with pytest.raises(ValueError):
        leer_filas("p.pdf", b"")


def test_encabezados_flexibles():
    cols = detectar_columnas(["Tema ID", "Test", "Pregunta", "Opción A", "Opción B", "Opción C", "Opción D", "Correcta", "Explicación"])
    assert cols["opcion_a"] == "Opción A" and cols["respuesta_correcta"] == "Correcta" and cols["tema_id"] == "Tema ID"
    with pytest.raises(ValueError, match="respuesta_correcta"):
        detectar_columnas(["tema_id", "numero_test", "enunciado", "opcion_a", "opcion_b"])


@pytest.mark.parametrize("respuesta,esperado", [("A", "A"), ("b", "B"), ("C,A", "AC"), ("a, d", "AD"), ("b)", "B"), ("  c  ", "C")])
def test_respuestas_validas(respuesta, esperado):
    assert interpretar_fila(_fila(respuesta_correcta=respuesta), COLS)["respuesta_correcta"] == esperado


def test_respuesta_por_texto_de_la_opcion():
    fila = _fila(opcion_a="Madrid", opcion_b="Barcelona", respuesta_correcta="barcelona")
    assert interpretar_fila(fila, COLS)["respuesta_correcta"] == "B"


@pytest.mark.parametrize("respuesta,mensaje", [
    ("", "falta la respuesta correcta"),
    ("E", "no es válida"),
    ("Sevilla", "no es válida"),     # antes se convertía en «A» sin avisar
    ("D", "opción está vacía"),
])
def test_respuestas_invalidas_se_rechazan(respuesta, mensaje):
    fila = _fila(respuesta_correcta=respuesta, opcion_d="" if respuesta == "D" else "d")
    with pytest.raises(ValueError, match=mensaje):
        interpretar_fila(fila, COLS)


def test_otras_validaciones():
    with pytest.raises(ValueError, match="no es un número"):
        interpretar_fila(_fila(tema_id="Tema 1"), COLS)
    with pytest.raises(ValueError, match="enunciado"):
        interpretar_fila(_fila(enunciado="  "), COLS)
    with pytest.raises(ValueError, match="opciones A y B"):
        interpretar_fila(_fila(opcion_b=""), COLS)
    d = interpretar_fila(_fila(tema_id=3.0, opcion_c="", opcion_d="", explicacion=None), COLS)  # Excel: 3.0
    assert d["tema_id"] == 3 and d["opcion_c"] is None and d["explicacion"]


# ------------------------------------------------------------------ endpoint

def _subir(como, nombre, contenido, quien="jefe"):
    return como(quien).post("/api/admin/preguntas/importar", files={"archivo": (nombre, io.BytesIO(contenido), "application/octet-stream")})


def test_importar_csv_excel_espanol_errores_y_duplicados(entorno):
    from models import Pregunta
    como, ids, Sesion = entorno
    t1 = ids["t1"]
    csv_es = (
        "tema_id;numero_test;enunciado;opcion_a;opcion_b;opcion_c;opcion_d;respuesta_correcta;explicacion\r\n"
        f"{t1};Importado;¿Qué artículo regula la Corona?;56;57;58;59;A;Título II\r\n"
        f"{t1};Importado;¿Cuántas correctas?;Una;Otra;Ninguna;;AB;\r\n"
        f"{t1};Importado;Sin respuesta;a;b;c;d;;\r\n"
        f"{t1};Importado;Respuesta rara;a;b;c;d;Z;\r\n"
        f"99999;Importado;Tema que no existe;a;b;c;d;A;\r\n"
        ";;;;;;;;\r\n"
    ).encode("cp1252")
    r = _subir(como, "preguntas.csv", csv_es)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["creadas"] == 2 and res["omitidas"] == 0 and res["filas"] == 5
    assert [e.split(":")[0] for e in res["errores"]] == ["Fila 4", "Fila 5", "Fila 6"]
    assert "falta la respuesta correcta" in res["errores"][0] and "«Z» no es válida" in res["errores"][1]

    db = Sesion()
    p = db.query(Pregunta).filter(Pregunta.enunciado == "¿Cuántas correctas?").one()
    assert p.respuesta_correcta == "AB" and p.opcion_d is None
    db.close()

    # Reimportar el mismo archivo no duplica (y el enunciado con otras mayúsculas/espacios tampoco)
    res = _subir(como, "preguntas.csv", csv_es).json()
    assert res["creadas"] == 0 and res["omitidas"] == 2
    otra = (CAB + f"\n{t1},Importado,  ¿qué artículo   regula la corona? ,56,57,58,59,A,\n").encode()
    assert _subir(como, "x.csv", otra).json()["omitidas"] == 1


def test_importar_sin_acceso_y_archivos_invalidos(entorno):
    como, ids, _ = entorno
    fila = (CAB + f"\n{ids['t3']},Ajeno,Pregunta,a,b,c,d,A,\n").encode()
    res = _subir(como, "x.csv", fila, quien="profe").json()   # t3 es de un curso que no da
    assert res["creadas"] == 0 and "Fila 2" in res["errores"][0]
    assert _subir(como, "x.pdf", b"%PDF").status_code == 400
    assert _subir(como, "x.csv", b"columna1,columna2\n1,2\n").status_code == 400
    assert _subir(como, "x.csv", (CAB + "\n").encode()).status_code == 400


def test_plantilla_y_reimportarla(entorno):
    como, ids, _ = entorno
    r = como("profe").get("/api/admin/preguntas/plantilla")
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Preguntas", "Temas", "Instrucciones"]
    temas = [fila[0] for fila in wb["Temas"].iter_rows(min_row=2, values_only=True)]
    assert ids["t3"] not in temas and ids["t1"] in temas     # solo sus temas
    # La plantilla tal cual (con sus 2 ejemplos) se importa bien, aunque la hoja activa sea otra
    wb.active = 1
    buf = io.BytesIO(); wb.save(buf)
    res = _subir(como, "plantilla.xlsx", buf.getvalue(), quien="profe").json()
    assert res["creadas"] == 2 and res["errores"] == []
    assert como("alumno").get("/api/admin/preguntas/plantilla").status_code == 403


def test_xlsx_simple_primera_hoja(entorno):
    como, ids, _ = entorno
    wb = Workbook(); ws = wb.active
    ws.append(CAB.split(","))
    ws.append([ids["t1"], 7, "Test con número", "a", "b", None, None, "B", None])
    buf = io.BytesIO(); wb.save(buf)
    res = _subir(como, "p.xlsx", buf.getvalue()).json()
    assert res["creadas"] == 1, res
