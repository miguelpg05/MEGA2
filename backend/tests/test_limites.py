"""Límites de peticiones: login (por IP y por cuenta) e IA (por usuario)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from main import app


@pytest.fixture(autouse=True)
def bd_vacia():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    models.Base.metadata.create_all(bind=engine)
    Sesion = sessionmaker(bind=engine)

    def get_db_test():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[models.get_db] = get_db_test
    yield
    app.dependency_overrides.clear()


def test_login_bloquea_cuenta_tras_5_fallos():
    cliente = TestClient(app)
    for _ in range(5):
        r = cliente.post("/api/auth/login", json={"email": "nadie@academiamega.net", "password": "mala"})
        assert r.status_code == 400
    r = cliente.post("/api/auth/login", json={"email": "nadie@academiamega.net", "password": "mala"})
    assert r.status_code == 429 and "15 minutos" in r.json()["detail"]
    # Otra cuenta desde la misma IP no está bloqueada por esa
    r = cliente.post("/api/auth/login", json={"email": "otra@academiamega.net", "password": "mala"})
    assert r.status_code != 429


def test_login_limite_por_ip():
    from services import limites
    cliente = TestClient(app)
    codigos = [cliente.post("/api/auth/login", json={"email": f"u{i}@academiamega.net", "password": "x"}).status_code
               for i in range(25)]
    assert 429 in codigos and codigos.index(429) == 20  # LIMITE_LOGIN = 20/minute
    assert limites.LIMITE_LOGIN == "20/minute"


def test_ia_limite_por_usuario():
    from services.limites import clave_usuario
    from jose import jwt

    class Peticion:
        def __init__(self, auth):
            self.headers = {"authorization": auth} if auth else {}
            self.client = type("C", (), {"host": "1.2.3.4"})()

    token = jwt.encode({"sub": "42"}, "x" * 40, algorithm="HS256")
    assert clave_usuario(Peticion(f"Bearer {token}")) == "usuario:42"
    assert clave_usuario(Peticion(None)) == "ip:1.2.3.4"
