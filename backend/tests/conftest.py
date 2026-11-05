"""Configuración común de los tests: variables de entorno mínimas para importar la app."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "clave-solo-para-tests-" + "x" * 32)
