
from pydantic import BaseModel
from typing import List

# Representa una respuesta individual a una pregunta
class RespuestaEnvio(BaseModel):
    pregunta_id: int
    es_correcta: bool

# Representa todo el paquete de datos que nos envía el frontend al terminar el test
# (el alumno_id ya NO viaja aquí: lo determina el backend a partir del token)
class TestResultado(BaseModel):
    respuestas: List[RespuestaEnvio]

# --- ESQUEMAS PARA AUTENTICACIÓN ---

class UsuarioRegistro(BaseModel):
    nombre: str
    email: str
    password: str

class UsuarioLogin(BaseModel):
    email: str
    password: str

class GoogleLogin(BaseModel):
    credential: str  # ID token (JWT) que entrega Google Identity Services

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario_id: int
    nombre: str

class UsuarioActual(BaseModel):
    usuario_id: int
    nombre: str
    email: str