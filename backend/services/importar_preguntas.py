"""Importación masiva de preguntas (CSV o Excel) — lógica pura, sin base de datos.

Acepta los mismos formatos que el importador del Access: Excel (.xlsx) y CSV con
«,», «;» o tabulador, en UTF-8 o en la codificación de Windows (el «Guardar como
CSV» del Excel en español). Los encabezados se reconocen sin importar mayúsculas,
tildes ni espacios («Opción A», «opcion_a», «A»...).
"""
import io
import re

from services.access_sync import _filas_csv, _normalizar_encabezado, _texto
from services.preguntas import LETRAS_OPCION, es_codigo_letras, parse_letras

HOJA_PREGUNTAS = "Preguntas"

ENCABEZADOS = ["tema_id", "numero_test", "enunciado", "opcion_a", "opcion_b",
               "opcion_c", "opcion_d", "respuesta_correcta", "explicacion"]

# campo -> encabezados aceptados (ya normalizados: minúsculas, sin tildes, «_» -> espacio)
COLUMNAS = {
    "tema_id": {"tema id", "id tema", "tema", "id del tema"},
    "numero_test": {"numero test", "test", "nombre test", "nombre del test", "n test", "num test"},
    "enunciado": {"enunciado", "pregunta"},
    "opcion_a": {"opcion a", "a", "respuesta a"},
    "opcion_b": {"opcion b", "b", "respuesta b"},
    "opcion_c": {"opcion c", "c", "respuesta c"},
    "opcion_d": {"opcion d", "d", "respuesta d"},
    "respuesta_correcta": {"respuesta correcta", "correcta", "correctas", "respuesta", "solucion"},
    "explicacion": {"explicacion", "justificacion", "comentario"},
}
OBLIGATORIAS = ("tema_id", "numero_test", "enunciado", "opcion_a", "opcion_b", "respuesta_correcta")


def _filas_xlsx(contenido: bytes):
    """Lee la hoja «Preguntas» si existe (la plantilla tiene también la hoja «Temas»)
    y, si no, la primera hoja."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    hoja = wb[HOJA_PREGUNTAS] if HOJA_PREGUNTAS in wb.sheetnames else wb.worksheets[0]
    filas = [f for f in hoja.iter_rows(values_only=True) if f and any(c not in (None, "") for c in f)]
    if not filas:
        return []
    cab = ["" if c is None else str(c) for c in filas[0]]
    return [{cab[i]: (f[i] if i < len(f) else None) for i in range(len(cab))} for f in filas[1:]]


def leer_filas(nombre: str, contenido: bytes):
    n = (nombre or "").lower()
    if n.endswith(".xlsx"):
        return _filas_xlsx(contenido)
    if n.endswith(".csv") or n.endswith(".txt"):
        return _filas_csv(contenido)
    raise ValueError("Formato no soportado. Sube un Excel (.xlsx) o un CSV.")


def detectar_columnas(encabezados) -> dict:
    """{campo: encabezado original}. Lanza ValueError si falta alguna obligatoria."""
    mapa = {}
    for original in encabezados:
        clave = _normalizar_encabezado(str(original).replace("_", " "))
        for campo, alias in COLUMNAS.items():
            if (clave == campo.replace("_", " ") or clave in alias) and campo not in mapa:
                mapa[campo] = original
    faltan = [c for c in OBLIGATORIAS if c not in mapa]
    if faltan:
        raise ValueError(
            "Faltan columnas: " + ", ".join(faltan)
            + ". Descarga la plantilla para ver el formato. Columnas del archivo: "
            + ", ".join(str(e) for e in encabezados)
        )
    return mapa


def clave_enunciado(texto) -> str:
    """Para detectar preguntas repetidas: sin mayúsculas ni espacios de más."""
    return re.sub(r"\s+", " ", str(texto or "")).strip().lower()


def interpretar_fila(fila: dict, columnas: dict) -> dict:
    """Valida una fila y devuelve los datos de la pregunta. Lanza ValueError con
    un mensaje claro si algo está mal (sin «adivinar» la respuesta correcta)."""
    valor = lambda campo: _texto(fila.get(columnas[campo])) if campo in columnas else ""  # noqa: E731

    tema = valor("tema_id")
    try:
        tema_id = int(float(tema))
    except ValueError:
        raise ValueError(f"el tema «{tema}» no es un número (usa el ID de la hoja «Temas» de la plantilla)" if tema
                         else "falta el ID del tema (columna tema_id)")

    numero_test = valor("numero_test")
    if not numero_test:
        raise ValueError("falta el nombre del test (columna numero_test)")
    enunciado = valor("enunciado")
    if not enunciado:
        raise ValueError("falta el enunciado de la pregunta")

    opciones = {l: valor(f"opcion_{l.lower()}") for l in LETRAS_OPCION}
    if not opciones["A"] or not opciones["B"]:
        raise ValueError("hacen falta al menos las opciones A y B")
    if opciones["D"] and not opciones["C"]:
        raise ValueError("hay opción D pero falta la C")

    bruta = valor("respuesta_correcta")
    if es_codigo_letras(bruta):
        letras = parse_letras(bruta)
    else:
        # También se admite el TEXTO exacto de la opción correcta
        letras = [l for l in LETRAS_OPCION if bruta and opciones[l] and opciones[l].strip().lower() == bruta.lower()][:1]
    if not letras:
        raise ValueError(
            f"la respuesta correcta «{bruta}» no es válida: usa A, B, C o D (varias juntas, p. ej. «AC»)"
            if bruta else "falta la respuesta correcta (A, B, C o D)"
        )
    vacias = [l for l in letras if not opciones[l]]
    if vacias:
        raise ValueError(f"la respuesta correcta es {', '.join(vacias)} pero esa opción está vacía")

    return {
        "tema_id": tema_id,
        "numero_test": numero_test,
        "enunciado": enunciado,
        "opcion_a": opciones["A"],
        "opcion_b": opciones["B"],
        "opcion_c": opciones["C"] or None,
        "opcion_d": opciones["D"] or None,
        "respuesta_correcta": "".join(letras),
        "explicacion": valor("explicacion") or "Consulta el temario para más detalle.",
    }
