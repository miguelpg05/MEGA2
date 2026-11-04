"""Tests de la capa de IA (selección de proveedor y errores de configuración)."""
import pytest

from services.ia import generar_texto, IAError, _proveedor, modelo_groq, MODELO_GROQ_POR_DEFECTO


def test_proveedor_por_defecto_es_groq(monkeypatch):
    monkeypatch.delenv("IA_PROVIDER", raising=False)
    assert _proveedor() == "groq"


def test_groq_sin_clave_lanza_error_500(monkeypatch):
    monkeypatch.setenv("IA_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(IAError) as exc:
        generar_texto("hola")
    assert exc.value.status == 500


def test_gemini_sin_clave_lanza_error_500(monkeypatch):
    monkeypatch.setenv("IA_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(IAError) as exc:
        generar_texto("hola")
    assert exc.value.status == 500


def test_modelo_groq_retirado_usa_el_por_defecto(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    assert modelo_groq() == MODELO_GROQ_POR_DEFECTO
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    assert modelo_groq() == MODELO_GROQ_POR_DEFECTO
    monkeypatch.setenv("GROQ_MODEL", "otro/modelo")
    assert modelo_groq() == "otro/modelo"
