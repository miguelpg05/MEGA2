"""Extracción de texto de PDFs (material de los temas) para dárselo a la IA."""
import io
import re


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


def _limpiar(texto: str) -> str:
    """Quita espacios y saltos de línea sobrantes (ahorra tokens sin perder contenido)."""
    texto = re.sub(r"[ \t]+", " ", texto or "")
    texto = re.sub(r"\n\s*\n+", "\n\n", texto)
    return texto.strip()


def recortar_repartido(texto: str, max_chars: int, trozos: int = 6):
    """Si el texto cabe, lo devuelve entero. Si no, toma `trozos` fragmentos
    repartidos a lo largo de TODO el documento (principio, medio y final), en vez
    de quedarse solo con las primeras páginas.
    Devuelve (texto, recortado: bool)."""
    texto = _limpiar(texto)
    if len(texto) <= max_chars:
        return texto, False
    trozos = max(1, min(trozos, max_chars // 400 or 1))
    largo = max_chars // trozos
    paso = (len(texto) - largo) / max(1, trozos - 1) if trozos > 1 else 0
    fragmentos = []
    for i in range(trozos):
        inicio = int(round(i * paso))
        # Empieza en el siguiente inicio de línea para no cortar a media frase
        if inicio > 0:
            salto = texto.find("\n", inicio, inicio + 200)
            if salto != -1:
                inicio = salto + 1
        fragmentos.append(texto[inicio:inicio + largo].strip())
    return "\n[…]\n".join(f for f in fragmentos if f), True


def combinar_materiales(documentos, tope_total: int):
    """Reparte el cupo de caracteres a partes iguales entre varios documentos.
    `documentos`: lista de (etiqueta, texto). Devuelve (texto_combinado, recortado)."""
    documentos = [(e, t) for e, t in documentos if t and t.strip()]
    if not documentos:
        return "", False
    cupo = tope_total // len(documentos)
    partes, recortado = [], False
    for etiqueta, texto in documentos:
        trozo, rec = recortar_repartido(texto, cupo)
        recortado = recortado or rec
        partes.append(f"### {etiqueta}\n{trozo}")
    return "\n\n".join(partes), recortado
