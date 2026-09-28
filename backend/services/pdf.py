"""Extracción de texto de PDFs (material de los temas) para dárselo a la IA."""
import io


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
