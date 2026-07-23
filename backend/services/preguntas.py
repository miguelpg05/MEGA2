"""Utilidades compartidas para trabajar con preguntas y su respuesta correcta.

FORMATO CANÓNICO: `Pregunta.respuesta_correcta` guarda las letras correctas en
mayúscula y ordenadas, SIN separador. Una sola correcta -> "B"; varias -> "AC".
Estas funciones son la ÚNICA fuente de verdad para traducir esas letras al texto
de las opciones, de modo que no haya lógica duplicada en `main.py` (repaso) y en
`routers/progreso_test.py`.

Además toleran formatos antiguos:
  - texto completo de la opción (p. ej. "El Rey"),
  - letra con puntuación ("b)", "A."),
  - separadores ("A,C", "A/C"),
para no romper datos ya existentes.

Este módulo es PURO: no importa modelos ni la base de datos, así que se puede
testear sin conexión a Postgres.
"""
import re

LETRAS_OPCION = ("A", "B", "C", "D")

# Un "código de letras" es un valor formado SOLO por letras A-D y
# separadores/puntuación (espacios, comas, ";", "/", ".", paréntesis).
_SEPARADORES = r"[ABCD\s,;/.\)\(]"


def _limpiar_letra(valor: str) -> str:
    """Quita puntuación de sufijo típica ("A.", "b)", " C ") y devuelve la letra."""
    return valor.strip().rstrip(".) ").strip().upper()


def es_letra_opcion(valor) -> bool:
    """True si `valor` representa UNA sola letra de opción (A–D), admitiendo
    variantes como "A", "a", "A.", "b)"."""
    if valor is None:
        return False
    limpio = _limpiar_letra(str(valor))
    return len(limpio) == 1 and limpio in LETRAS_OPCION


def es_codigo_letras(valor) -> bool:
    """True si `valor` es un código de una o varias letras (p. ej. "A", "AC",
    "A,C", "b)"), en contraposición al texto completo de una opción."""
    if valor is None:
        return False
    s = str(valor).strip().upper()
    if not s:
        return False
    if not any(c in "ABCD" for c in s):
        return False
    # Si al quitar letras y separadores no queda nada, es un código de letras.
    return re.sub(_SEPARADORES, "", s) == ""


def parse_letras(valor) -> list:
    """Extrae la lista ordenada y sin repetidos de letras A-D presentes en `valor`."""
    if valor is None:
        return []
    presentes = {c for c in str(valor).upper() if c in "ABCD"}
    return [l for l in LETRAS_OPCION if l in presentes]


def normalizar_letra(valor) -> str:
    """Devuelve la PRIMERA letra canónica "A"–"D". Si no se reconoce, "A"."""
    letras = parse_letras(valor) if es_codigo_letras(valor) else []
    return letras[0] if letras else "A"


def normalizar_respuesta(valor) -> str:
    """Forma canónica de guardado a partir de un código de letras: letras únicas
    ordenadas y concatenadas (p. ej. "A", "AC"). Devuelve "" si no hay ninguna."""
    return "".join(parse_letras(valor))


def letra_de_texto(texto_correcto: str, opciones) -> str:
    """Dado el TEXTO de la respuesta correcta y la lista [a, b, c, d], devuelve la
    letra canónica. Se usa al sembrar/importar para convertir texto -> letra."""
    objetivo = (texto_correcto or "").strip()
    for letra, opcion in zip(LETRAS_OPCION, opciones):
        if opcion is not None and str(opcion).strip() == objetivo:
            return letra
    return "A"


def letras_correctas(pregunta) -> list:
    """Lista ordenada de letras correctas de una `Pregunta` (una o varias)."""
    valor = (pregunta.respuesta_correcta or "").strip()
    if es_codigo_letras(valor):
        return parse_letras(valor)
    # Formato antiguo: el valor es el texto completo de una opción -> localizarla.
    for letra in LETRAS_OPCION:
        opcion = getattr(pregunta, f"opcion_{letra.lower()}", None)
        if opcion is not None and str(opcion).strip() == valor:
            return [letra]
    return []


def textos_correctos(pregunta) -> list:
    """Lista con el TEXTO de cada opción correcta."""
    return [getattr(pregunta, f"opcion_{l.lower()}") for l in letras_correctas(pregunta)]


def texto_opcion_correcta(pregunta) -> str:
    """TEXTO de la PRIMERA opción correcta (compatibilidad con el código antiguo).
    Para preguntas con varias correctas, usa `textos_correctos`."""
    textos = textos_correctos(pregunta)
    if textos:
        return textos[0]
    # Sin letras reconocidas: devolvemos el valor tal cual (texto antiguo suelto).
    return (pregunta.respuesta_correcta or "").strip()
