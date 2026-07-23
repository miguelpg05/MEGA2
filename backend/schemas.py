
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
    access_token: Optional[str] = None  # OAuth2 access token (flujo con selector de cuenta)
    credential: Optional[str] = None    # id_token (flujo antiguo, por compatibilidad)

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario_id: int
    nombre: str

class CursoResumen(BaseModel):
    id: int
    nombre: str

class UsuarioActual(BaseModel):
    usuario_id: int
    nombre: str
    email: str
    rol: str
    cursos: List[CursoResumen] = []

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
    tema_id: Optional[int] = None
    material_id: Optional[int] = None  # PDF concreto del tema sobre el que basar el esquema
    texto: Optional[str] = None        # texto libre aportado por el usuario

# --- ESQUEMAS DEL PANEL DE ADMINISTRACIÓN ---

class CursoIn(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class CursosUsuarioUpdate(BaseModel):
    curso_ids: List[int]

class TemaIn(BaseModel):
    nombre: str
    bloque: Optional[str] = None
    curso_id: Optional[int] = None

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
    rol: str  # "estudiante" | "admin" (profesor) | "superadmin" (jefe)