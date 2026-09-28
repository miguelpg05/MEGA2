"""Utilidades para las plantillas de test: nombres libres y ordenación.

Los tests se identifican por un NOMBRE que admite cualquier texto
("001", "Simulacro 3", "Repaso bloque I — Constitución"). Históricamente eran
solo números con ceros a la izquierda ("001"); esto sigue funcionando igual.
"""
import re

MAX_LONGITUD_NOMBRE = 120


def normalizar_nombre_test(valor) -> str:
    """Limpia el nombre de un test tal como llega del panel o de un Excel/CSV.

    - Cualquier carácter es válido; solo se recortan espacios y se colapsan los
      espacios internos repetidos.
    - Compatibilidad: si llega un número puro (p. ej. 1 o 1.0 desde Excel, o "7"),
      se conserva el formato histórico de 3 cifras ("001", "007").
    Devuelve "" si el valor está vacío.
    """
    if valor is None:
        return ""
    if isinstance(valor, bool):
        valor = str(valor)
    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and not valor.is_integer():
            texto = str(valor)
        else:
            return str(int(valor)).zfill(3)
    else:
        texto = str(valor)
    texto = re.sub(r"\s+", " ", texto).strip()
    if re.fullmatch(r"\d+(\.0+)?", texto):
        return str(int(float(texto))).zfill(3)
    return texto[:MAX_LONGITUD_NOMBRE]


def clave_orden_natural(nombre) -> list:
    """Clave para ordenar nombres de forma "natural": "Test 2" antes que "Test 10",
    y sin distinguir mayúsculas. Los números se comparan como números."""
    partes = re.split(r"(\d+)", str(nombre or "").casefold())
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in partes if p != ""]
