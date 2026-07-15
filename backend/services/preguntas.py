"""Utilidades compartidas para trabajar con preguntas y su respuesta correcta.

FORMATO CANÓNICO: `Pregunta.respuesta_correcta` se almacena como una única letra
mayúscula "A" | "B" | "C" | "D" (igual que hace la importación desde Excel en
`inyectar_preguntas.py`). Estas funciones son la ÚNICA fuente de verdad para
traducir esa letra al texto de la opción, de modo que no haya lógica duplicada
en `main.py` (repaso) y `routers/progreso_test.py`.

Además toleran el formato antiguo (cuando `respuesta_correcta` guardaba el texto
completo de la opción, p. ej. "El Rey"), para no romper datos ya existentes.

Este módulo es PURO: no importa modelos ni la base de datos, así que se puede
testear sin conexión a Postgres.
"""

LETRAS_OPCION = ("A", "B", "C", "D")


def _limpiar_letra(valor: str) -> str:
    """Quita puntuación de sufijo típica ("A.", "b)", " C ") y devuelve la letra."""
    return valor.strip().rstrip(".) ").strip().upper()


def es_letra_opcion(valor) -> bool:
    """True si `valor` representa una sola letra de opción (A–D), admitiendo
    variantes como "A", "a", "A.", "b)"."""
    if valor is None:
        return False
    limpio = _limpiar_letra(str(valor))
    return len(limpio) == 1 and limpio in LETRAS_OPCION


def normalizar_letra(valor) -> str:
    """Devuelve la letra canónica "A"–"D" a partir de la letra en cualquier
    formato. Si no se reconoce, devuelve "A" como valor por defecto defensivo."""
    if es_letra_opcion(valor):
        return _limpiar_letra(str(valor))
    return "A"


def letra_de_texto(texto_correcto: str, opciones) -> str:
    """Dado el TEXTO de la respuesta correcta y la lista [a, b, c, d], devuelve la
    letra canónica. Se usa al sembrar/importar para convertir texto -> letra."""
    objetivo = (texto_correcto or "").strip()
    for letra, opcion in zip(LETRAS_OPCION, opciones):
        if opcion is not None and str(opcion).strip() == objetivo:
            return letra
    return "A"


def texto_opcion_correcta(pregunta) -> str:
    """Devuelve el TEXTO de la opción correcta de una `Pregunta`.

    - Si `respuesta_correcta` es una letra (formato canónico), resuelve la opción.
    - Si es el texto completo (formato antiguo), lo devuelve tal cual.
    """
    valor = (pregunta.respuesta_correcta or "").strip()
    if es_letra_opcion(valor):
        letra = normalizar_letra(valor)
        return getattr(pregunta, f"opcion_{letra.lower()}") or valor
    # Formato antiguo: el propio valor ya es el texto de la respuesta.
    return valor
