"""Generación robusta de mapas mentales (Mermaid) a partir de un esquema JSON.

El problema de pedirle a la IA directamente sintaxis `mindmap` de Mermaid es que
es MUY sensible a la indentación: cualquier fallo del modelo y no renderiza nada.
Por eso la IA devuelve un JSON con la jerarquía y AQUÍ construimos el Mermaid con
la indentación correcta, garantizando que siempre sea válido.
"""
import io
import re
import json

MAX_RAMAS = 6
MAX_HIJOS = 8
MAX_CHARS_NODO = 60


def limpiar_nodo(texto) -> str:
    """Quita caracteres que rompen la sintaxis mindmap (paréntesis, corchetes,
    comillas, llaves, |) y normaliza espacios."""
    t = re.sub(r'[()\[\]{}"|]', " ", str(texto or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:MAX_CHARS_NODO] or "..."


def construir_mindmap(data: dict) -> str:
    """Construye un `mindmap` de Mermaid válido a partir de:
    {"titulo": "...", "ramas": [{"titulo": "...", "hijos": ["...", ...]}, ...]}"""
    titulo = limpiar_nodo((data or {}).get("titulo") or "Tema")
    lineas = ["mindmap", f"  root(({titulo}))"]

    ramas = (data or {}).get("ramas") or []
    for rama in ramas[:MAX_RAMAS]:
        if isinstance(rama, str):
            rama = {"titulo": rama, "hijos": []}
        rtit = limpiar_nodo(rama.get("titulo"))
        if not rtit or rtit == "...":
            continue
        lineas.append(f"    {rtit}")
        for hijo in (rama.get("hijos") or [])[:MAX_HIJOS]:
            htit = limpiar_nodo(hijo)
            if htit and htit != "...":
                lineas.append(f"      {htit}")

    # Si no hubo ramas válidas, al menos devolvemos la raíz (mermaid la pinta).
    return "\n".join(lineas)


def extraer_json(texto: str) -> dict:
    """Extrae el primer objeto JSON de la respuesta de la IA, tolerando que venga
    envuelto en ```json ... ``` o con texto alrededor."""
    limpio = (texto or "").strip()
    limpio = re.sub(r"^```(?:json)?", "", limpio).strip()
    limpio = re.sub(r"```$", "", limpio).strip()
    ini, fin = limpio.find("{"), limpio.rfind("}")
    if ini != -1 and fin != -1 and fin > ini:
        limpio = limpio[ini:fin + 1]
    return json.loads(limpio)


def extraer_texto_pdf(contenido: bytes, max_chars: int = 18000) -> str:
    """Extrae texto de un PDF (bytes) para dárselo a la IA. Limita el tamaño para
    controlar el coste de tokens. Devuelve "" si no se puede leer."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("Falta la librería pypdf para extraer texto de PDFs.")
        return ""
    try:
        reader = PdfReader(io.BytesIO(contenido))
        partes, total = [], 0
        for page in reader.pages:
            t = page.extract_text() or ""
            partes.append(t)
            total += len(t)
            if total >= max_chars:
                break
        return "\n".join(partes)[:max_chars].strip()
    except Exception as e:
        print(f"No se pudo extraer texto del PDF: {e}")
        return ""
