
from pydantic import BaseModel
from typing import List, Optional

# (Los resultados de un test ya no los envía el frontend corregidos: se corrigen
#  en el servidor con POST /api/test/entregar, ver routers/progreso_test.py.)

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
    tema: str  # etiqueta/título para el prompt
    tema_nombre: Optional[str] = None
    tema_id: Optional[int] = None
    tema_ids: Optional[List[int]] = None  # varios temas: usa TODOS sus materiales (PDFs)
    material_id: Optional[int] = None     # un PDF concreto sobre el que basar el resumen
    texto: Optional[str] = None           # texto libre aportado por el usuario


class RepasoCompletado(BaseModel):
    fallo_id: int

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
    numero_test: str                      # nombre del test: admite cualquier texto
    tema_ids: Optional[List[int]] = None  # uno o VARIOS temas (el primero es el principal)
    tema_id: Optional[int] = None         # compatibilidad: un único tema
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