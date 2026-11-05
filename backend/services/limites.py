"""Límites de peticiones (anti abuso) con slowapi, en memoria del proceso.

- Login con contraseña / registro / Google: por IP (generosos, porque los alumnos
  de una misma academia pueden compartir la IP de la wifi) + bloqueo por CUENTA
  tras varios intentos fallidos (ver `IntentosFallidos`), que es lo que de verdad
  frena a quien prueba contraseñas.
- IA: por usuario (se identifica por el token), para que nadie agote el cupo diario
  de toda la academia.
Nota: el almacenamiento es en memoria; con varios procesos/instancias cada uno lleva
su cuenta (para eso habría que usar Redis: `storage_uri`).
"""
import os
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

LIMITES_ACTIVOS = os.getenv("LIMITES_ACTIVOS", "1").lower() not in ("0", "false", "no")

LIMITE_LOGIN = os.getenv("LIMITE_LOGIN", "20/minute")
LIMITE_REGISTRO = os.getenv("LIMITE_REGISTRO", "5/minute")
LIMITE_GOOGLE = os.getenv("LIMITE_GOOGLE", "30/minute")
LIMITE_IA = os.getenv("LIMITE_IA", "5/minute;40/day")


def ip_cliente(request: Request) -> str:
    """IP real del cliente detrás del proxy de Render/Cloudflare."""
    for cabecera in ("cf-connecting-ip", "true-client-ip"):
        valor = request.headers.get(cabecera)
        if valor:
            return valor.strip()
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


def clave_usuario(request: Request) -> str:
    """Usuario del token (sin validar firma: solo sirve para contar peticiones;
    la autenticación real la hace get_current_user). Si no hay token, la IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            sub = jwt.get_unverified_claims(auth[7:]).get("sub")
            if sub:
                return f"usuario:{sub}"
        except Exception:
            pass
    return f"ip:{ip_cliente(request)}"


limiter = Limiter(key_func=ip_cliente, enabled=LIMITES_ACTIVOS)


def respuesta_limite_superado(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    if request.url.path.startswith("/api/ia/"):
        detalle = "Has pedido muchos resúmenes seguidos. Espera un poco y vuelve a intentarlo."
    else:
        detalle = "Demasiados intentos seguidos. Espera un minuto y vuelve a intentarlo."
    return JSONResponse(status_code=429, content={"detail": detalle})


class IntentosFallidos:
    """Bloquea una cuenta tras `maximo` contraseñas erróneas en `ventana` segundos."""

    def __init__(self, maximo: int = 5, ventana: int = 15 * 60):
        self.maximo = maximo
        self.ventana = ventana
        self._fallos = defaultdict(deque)

    def _limpiar(self, clave: str, ahora: float) -> deque:
        cola = self._fallos[clave]
        while cola and ahora - cola[0] > self.ventana:
            cola.popleft()
        return cola

    def bloqueada(self, email: str) -> bool:
        if not LIMITES_ACTIVOS:
            return False
        return len(self._limpiar((email or "").lower(), time.monotonic())) >= self.maximo

    def registrar_fallo(self, email: str) -> None:
        clave = (email or "").lower()
        self._limpiar(clave, time.monotonic()).append(time.monotonic())

    def limpiar(self, email: str = None) -> None:
        if email is None:
            self._fallos.clear()
        else:
            self._fallos.pop((email or "").lower(), None)


intentos_login = IntentosFallidos()
