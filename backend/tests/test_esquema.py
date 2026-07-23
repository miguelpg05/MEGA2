"""Tests del constructor de mapas mentales (JSON -> Mermaid mindmap).

Al construir el Mermaid nosotros a partir de un JSON, garantizamos que la
sintaxis (y la indentación) sea siempre válida, sin depender de que la IA la
genere bien.
"""
from services.esquema import limpiar_nodo, construir_mindmap, extraer_json


def test_limpiar_nodo_quita_caracteres_problematicos():
    assert limpiar_nodo("Poder (Judicial)") == "Poder Judicial"
    assert limpiar_nodo("A [B] {C}") == "A B C"
    assert limpiar_nodo("   varios   espacios ") == "varios espacios"
    assert limpiar_nodo("") == "..."


def test_construir_mindmap_estructura_valida():
    data = {
        "titulo": "La Constitución",
        "ramas": [
            {"titulo": "Título Preliminar", "hijos": ["Valores", "Soberanía"]},
            {"titulo": "Derechos", "hijos": ["Fundamentales"]},
        ],
    }
    codigo = construir_mindmap(data)
    lineas = codigo.splitlines()
    assert lineas[0] == "mindmap"
    assert lineas[1] == "  root((La Constitución))"
    assert "    Título Preliminar" in lineas
    assert "      Valores" in lineas
    # La indentación de los hijos es mayor que la de las ramas
    assert lineas[2].startswith("    ")
    assert lineas[3].startswith("      ")


def test_construir_mindmap_limita_ramas_e_hijos():
    data = {"titulo": "T", "ramas": [{"titulo": f"R{i}", "hijos": [f"h{j}" for j in range(20)]} for i in range(20)]}
    codigo = construir_mindmap(data)
    # Máximo 6 ramas
    ramas = [l for l in codigo.splitlines() if l.startswith("    ") and not l.startswith("      ")]
    assert len(ramas) <= 6


def test_construir_mindmap_tolera_datos_vacios():
    assert construir_mindmap({}).startswith("mindmap")
    assert construir_mindmap({"titulo": "Solo raíz", "ramas": []}).splitlines()[1] == "  root((Solo raíz))"


def test_extraer_json_con_fences_y_texto_alrededor():
    crudo = 'Aquí tienes:\n```json\n{"titulo": "X", "ramas": []}\n```\nUn saludo'
    data = extraer_json(crudo)
    assert data["titulo"] == "X"
    assert data["ramas"] == []
