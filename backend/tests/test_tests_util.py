"""Tests de los nombres libres de test y su ordenación natural."""
from services.tests_util import normalizar_nombre_test, clave_orden_natural


def test_nombres_admiten_cualquier_caracter():
    assert normalizar_nombre_test("Simulacro 3 — Bloque I") == "Simulacro 3 — Bloque I"
    assert normalizar_nombre_test("  Repaso   final (A/B) ¿? ") == "Repaso final (A/B) ¿?"
    assert normalizar_nombre_test("T-1_ñ") == "T-1_ñ"


def test_numeros_conservan_formato_historico():
    assert normalizar_nombre_test(1) == "001"
    assert normalizar_nombre_test(1.0) == "001"  # Excel devuelve floats
    assert normalizar_nombre_test("7") == "007"
    assert normalizar_nombre_test("12.0") == "012"
    assert normalizar_nombre_test("001") == "001"


def test_vacios():
    assert normalizar_nombre_test(None) == ""
    assert normalizar_nombre_test("   ") == ""


def test_orden_natural():
    nombres = ["Test 10", "test 2", "001", "Simulacro B", "010", "Simulacro a", "Test 1"]
    ordenados = sorted(nombres, key=clave_orden_natural)
    assert ordenados == ["001", "010", "Simulacro a", "Simulacro B", "Test 1", "test 2", "Test 10"]
