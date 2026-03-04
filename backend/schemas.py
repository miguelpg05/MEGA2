
from pydantic import BaseModel
from typing import List

# Representa una respuesta individual a una pregunta
class RespuestaEnvio(BaseModel):
    pregunta_id: int
    es_correcta: bool

# Representa todo el paquete de datos que nos envía el frontend al terminar el test
class TestResultado(BaseModel):
    alumno_id: int
    respuestas: List[RespuestaEnvio]

# --- ESQUEMAS PARA AUTENTICACIÓN ---

class UsuarioRegistro(BaseModel):
    nombre: str
    email: str
    password: str

class UsuarioLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario_id: int
    nombre: str