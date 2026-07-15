
from pydantic import BaseModel
from typing import List, Optional

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
    rol: str

# --- ESQUEMAS DE PETICIÓN PARA LOS ENDPOINTS DE main.py ---

class FalloRequest(BaseModel):
    pregunta_id: int

class ResumenRequest(BaseModel):
    tiempo: int
    nivel: str
    tema: str

class PuntosRequest(BaseModel):
    puntos: int

class RepasoCompletado(BaseModel):
    fallo_id: int

class EsquemaRequest(BaseModel):
    tema_nombre: str

# --- ESQUEMAS DEL PANEL DE ADMINISTRACIÓN ---

class TemaIn(BaseModel):
    nombre: str
    bloque: Optional[str] = None

class TestPlantillaIn(BaseModel):
    numero_test: str
    tema_id: int
    total_preguntas: int = 10

class PreguntaIn(BaseModel):
    enunciado: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    opcion_d: str
    respuesta_correcta: str  # letra A-D
    explicacion: Optional[str] = None
    tema_id: int
    test_plantilla_id: Optional[int] = None

class RolUpdate(BaseModel):
    rol: str  # "alumno" | "profesor" | "admin"