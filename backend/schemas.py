
from pydantic import BaseModel, Field
from typing import List, Optional

# (Los resultados de un test ya no los envía el frontend corregidos: se corrigen
#  en el servidor con POST /api/test/entregar, ver routers/progreso_test.py.)

# --- ESQUEMAS PARA AUTENTICACIÓN ---

# Longitudes máximas: evitan cuerpos enormes (memoria) y datos absurdos.
class UsuarioRegistro(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

class UsuarioLogin(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

class GoogleLogin(BaseModel):
    access_token: Optional[str] = Field(default=None, max_length=4096)  # OAuth2 access token
    credential: Optional[str] = Field(default=None, max_length=8192)    # id_token (flujo antiguo)

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
    # RGPD
    debe_aceptar_privacidad: bool = False
    privacidad_version: Optional[str] = None
    mostrar_en_ranking: bool = True

# --- ESQUEMAS DE PETICIÓN PARA LOS ENDPOINTS DE main.py ---

class FalloRequest(BaseModel):
    pregunta_id: int

class ResumenRequest(BaseModel):
    tiempo: int = Field(ge=1, le=120)
    nivel: str = Field(max_length=30)
    tema: str = Field(default="", max_length=2000)  # etiqueta/título para el prompt
    tema_nombre: Optional[str] = Field(default=None, max_length=300)
    tema_id: Optional[int] = None
    tema_ids: Optional[List[int]] = Field(default=None, max_length=100)  # varios temas: usa sus PDFs
    material_id: Optional[int] = None     # un PDF concreto sobre el que basar el resumen
    texto: Optional[str] = Field(default=None, max_length=60_000)  # texto libre del usuario


class RepasoCompletado(BaseModel):
    pregunta_id: Optional[int] = None   # marca como repasados todos sus fallos pendientes
    fallo_id: Optional[int] = None      # compatibilidad con la versión anterior

# --- ESQUEMAS DEL PANEL DE ADMINISTRACIÓN ---

class CursoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: Optional[str] = Field(default=None, max_length=1000)

class CursosUsuarioUpdate(BaseModel):
    curso_ids: List[int] = Field(max_length=200)

class TemaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=300)
    bloque: Optional[str] = Field(default=None, max_length=200)
    curso_id: Optional[int] = None

class TestPlantillaIn(BaseModel):
    numero_test: str = Field(min_length=1, max_length=200)  # nombre del test: cualquier texto
    tema_ids: Optional[List[int]] = Field(default=None, max_length=200)  # uno o VARIOS temas
    tema_id: Optional[int] = None         # compatibilidad: un único tema
    total_preguntas: int = 10

class PreguntaIn(BaseModel):
    enunciado: str = Field(min_length=1, max_length=4000)
    opcion_a: str = Field(max_length=1000)
    opcion_b: str = Field(max_length=1000)
    opcion_c: str = Field(max_length=1000)
    opcion_d: str = Field(max_length=1000)
    respuesta_correcta: str = Field(max_length=20)  # letras A-D ("A" o "AC")
    explicacion: Optional[str] = Field(default=None, max_length=8000)
    tema_id: int
    test_plantilla_id: Optional[int] = None

class RolUpdate(BaseModel):
    rol: str = Field(max_length=20)  # "estudiante" | "admin" (profesor) | "superadmin" (jefe)


class RankingVisible(BaseModel):
    visible: bool