"""Tests del helper `services.preguntas`, que es la fuente de verdad para traducir
la respuesta correcta (letra canónica A–D o texto antiguo) al texto de la opción.

Cubre el bug histórico: el seed guardaba el TEXTO ("El Rey") mientras que el
consumo asumía una LETRA y hacía `[0]`, eligiendo mal la respuesta.
"""
from types import SimpleNamespace

from services.preguntas import (
    es_letra_opcion,
    es_codigo_letras,
    parse_letras,
    normalizar_letra,
    normalizar_respuesta,
    letra_de_texto,
    letras_correctas,
    textos_correctos,
    texto_opcion_correcta,
)


def _pregunta(**kwargs):
    base = dict(opcion_a="El Presidente", opcion_b="El Rey", opcion_c="El Congreso", opcion_d="El TC")
    base.update(kwargs)
    return SimpleNamespace(**base)


# --- es_letra_opcion ---
def test_es_letra_opcion_reconoce_variantes():
    assert es_letra_opcion("A")
    assert es_letra_opcion("b")
    assert es_letra_opcion("C.")
    assert es_letra_opcion(" d) ")


def test_es_letra_opcion_rechaza_texto_y_none():
    assert not es_letra_opcion("El Rey")
    assert not es_letra_opcion("")
    assert not es_letra_opcion(None)
    assert not es_letra_opcion("AB")


# --- normalizar_letra ---
def test_normalizar_letra():
    assert normalizar_letra("a") == "A"
    assert normalizar_letra("B.") == "B"
    assert normalizar_letra("El Rey") == "A"  # fallback defensivo


# --- letra_de_texto (usado por el seed/importación) ---
def test_letra_de_texto_encuentra_la_opcion():
    opciones = ["El Presidente", "El Rey", "El Congreso", "El TC"]
    assert letra_de_texto("El Rey", opciones) == "B"
    assert letra_de_texto("El TC", opciones) == "D"


def test_letra_de_texto_fallback_si_no_coincide():
    assert letra_de_texto("Otro", ["a", "b", "c", "d"]) == "A"


# --- texto_opcion_correcta: FORMATO CANÓNICO (letra) ---
def test_texto_desde_letra_canonica():
    p = _pregunta(respuesta_correcta="B")
    assert texto_opcion_correcta(p) == "El Rey"


def test_texto_desde_letra_con_puntuacion():
    p = _pregunta(respuesta_correcta="b)")
    assert texto_opcion_correcta(p) == "El Rey"


# --- texto_opcion_correcta: FORMATO ANTIGUO (texto completo) ---
def test_texto_desde_formato_antiguo():
    # Antes el seed guardaba el texto completo; debe seguir funcionando.
    p = _pregunta(respuesta_correcta="El Rey")
    assert texto_opcion_correcta(p) == "El Rey"


def test_regresion_bug_no_devuelve_primera_opcion_por_error():
    # Con el bug antiguo (`[0]` de "El Rey" -> 'e' -> 'a'), esto devolvía
    # incorrectamente la opción A. Ahora debe devolver la B.
    p = _pregunta(respuesta_correcta="B")
    assert texto_opcion_correcta(p) != p.opcion_a
    assert texto_opcion_correcta(p) == p.opcion_b


# --- MÚLTIPLES RESPUESTAS CORRECTAS ---
def test_es_codigo_letras_distingue_codigo_de_texto():
    assert es_codigo_letras("A")
    assert es_codigo_letras("AC")
    assert es_codigo_letras("A,C")
    assert es_codigo_letras("b)")
    assert not es_codigo_letras("El Rey")
    assert not es_codigo_letras("La villa de Madrid")  # contiene A/D pero es texto
    assert not es_codigo_letras("")


def test_parse_letras_ordena_y_deduplica():
    assert parse_letras("CA") == ["A", "C"]
    assert parse_letras("A,C") == ["A", "C"]
    assert parse_letras("AAC") == ["A", "C"]
    assert parse_letras("ABCD") == ["A", "B", "C", "D"]


def test_normalizar_respuesta_forma_canonica():
    assert normalizar_respuesta("a c") == "AC"
    assert normalizar_respuesta("C,A") == "AC"
    assert normalizar_respuesta("b") == "B"
    assert normalizar_respuesta("") == ""
    assert normalizar_respuesta("xyz ñ 123") == ""


def test_letras_y_textos_correctos_varias():
    p = _pregunta(respuesta_correcta="AC")
    assert letras_correctas(p) == ["A", "C"]
    assert textos_correctos(p) == [p.opcion_a, p.opcion_c]


def test_una_sola_correcta_sigue_funcionando():
    p = _pregunta(respuesta_correcta="D")
    assert letras_correctas(p) == ["D"]
    assert textos_correctos(p) == [p.opcion_d]
    assert texto_opcion_correcta(p) == p.opcion_d
