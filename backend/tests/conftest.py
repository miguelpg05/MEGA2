"""Configuración común de los tests: variables de entorno mínimas para importar la app."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "clave-solo-para-tests-" + "x" * 32)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reiniciar_limites():
    """Cada test empieza con los contadores de límites a cero."""
    from services.limites import limiter, intentos_login
    limiter.reset()
    intentos_login.limpiar()
    yield
