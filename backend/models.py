import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

load_dotenv()

# La cadena de conexión SIEMPRE debe venir de la variable de entorno DATABASE_URL
# (configúrala en Render/local .env). Debe empezar por "postgresql://".
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("Falta la variable de entorno DATABASE_URL con la cadena de conexión a la base de datos.")

# Para PostgreSQL eliminamos el 'check_same_thread' que solo era para SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Función para abrir y cerrar la conexión con la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 0. Cursos (p. ej. "Auxiliar Administrativo del Estado", "Policía Nacional").
# Todo el temario cuelga de un curso, y los usuarios se vinculan a cursos:
#   - "admin" (profesor): los cursos que GESTIONA
#   - "estudiante": los cursos en los que está MATRICULADO
#   - "superadmin": no necesita vínculos, tiene acceso a todos
class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, index=True)
    descripcion = Column(String, nullable=True)

    temas = relationship("Tema", back_populates="curso")

# Tabla intermedia usuario <-> curso (muchos a muchos)
usuario_cursos = Table(
    "usuario_cursos",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("curso_id", Integer, ForeignKey("cursos.id", ondelete="CASCADE"), primary_key=True),
)

# 1. Tabla de Temas y Bloques
class Tema(Base):
    __tablename__ = "temas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    bloque = Column(String) # Ej: "Derecho Constitucional", "Derecho Administrativo"
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=True, index=True)

    curso = relationship("Curso", back_populates="temas")
    # Relación: Un tema tiene muchas preguntas
    preguntas = relationship("Pregunta", back_populates="tema")

# 2. Tabla de Preguntas (El corazón de los tests)
class Pregunta(Base):
    __tablename__ = "preguntas"

    id = Column(Integer, primary_key=True, index=True)
    enunciado = Column(String)
    
    # Opciones
    opcion_a = Column(String)
    opcion_b = Column(String)
    opcion_c = Column(String)
    opcion_d = Column(String)
    
    # Lógica de corrección y flashcard
    respuesta_correcta = Column(String) # Ej: "B"
    explicacion = Column(String)
    
    # Relación con el tema al que pertenece
    tema_id = Column(Integer, ForeignKey("temas.id"))
    test_plantilla_id = Column(Integer, ForeignKey("test_plantillas.id", ondelete="CASCADE"), nullable=True)
    tema = relationship("Tema", back_populates="preguntas")

# 3. Tabla de Fallos (Para el Modo Repaso Automático y Flashcards)
class RegistroFallo(Base):
    __tablename__ = "registro_fallos"

    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer) # ID ficticio del alumno por ahora
    pregunta_id = Column(Integer, ForeignKey("preguntas.id"))
    repasada = Column(Boolean, default=False) # Si está a False, saldrá en el próximo "test de repaso"

# 4. Tabla de Puntuaciones (Para Rankings)
class Puntuacion(Base):
    __tablename__ = "puntuaciones"

    id = Column(Integer, primary_key=True, index=True)
    alumno_nombre = Column(String) # Por ahora usaremos nombres simples
    puntos = Column(Integer)
    fecha = Column(String) # Para poder hacer rankings semanales o diarios

# 5. NUEVA: Tabla de Respuestas Generales (Para calcular el Progreso del 0 al 100%)
class RespuestaAlumno(Base):
    __tablename__ = "respuestas_alumnos"

    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, index=True)
    pregunta_id = Column(Integer, ForeignKey("preguntas.id"))
    es_correcta = Column(Boolean, default=False)

# 6. Tabla de Usuarios (Login por Google)
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    email = Column(String, unique=True, index=True) # unique=True evita que dos se registren con el mismo email
    hashed_password = Column(String, nullable=True) # Histórico: usuarios antiguos con contraseña (ya solo se entra con Google)
    google_sub = Column(String, unique=True, index=True, nullable=True) # ID único de Google (idinfo['sub'])
    sesion_id = Column(String, nullable=True) # Token de la sesión activa actual; cada login lo renueva e invalida el resto
    # "estudiante" | "admin" (profesor: solo sus cursos) | "superadmin" (jefe: todos los cursos)
    rol = Column(String, nullable=False, default="estudiante")

    # Cursos que gestiona (si es admin) o en los que está matriculado (si es estudiante)
    cursos = relationship("Curso", secondary=usuario_cursos, backref="usuarios")

# --- TABLAS PARA EL LISTADO DE TESTS ESPECÍFICOS ---

# 1. Definimos las plantillas de los tests que existen
class TestPlantilla(Base):
    __tablename__ = "test_plantillas"

    id = Column(Integer, primary_key=True, index=True)
    numero_test = Column(String, unique=True, index=True) # Ej: "001", "002"
    tema_id = Column(Integer) # A qué tema pertenece
    total_preguntas = Column(Integer, default=10) # Cuántas preguntas tiene este test

# 2. Guardamos cada intento real que hace un alumno
class TestIntento(Base):
    __tablename__ = "test_intentos"

    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, index=True) # Quién lo hizo
    test_plantilla_id = Column(Integer, index=True) # Qué test hizo
    fecha_intento = Column(DateTime, default=datetime.utcnow) # Cuándo lo hizo
    fallos_ultimo = Column(Integer) # Cuántos fallos tuvo en ESTE intento

# 3. Registro de llamadas a la IA (Gemini) para dar visibilidad de uso y coste
class IALlamada(Base):
    __tablename__ = "ia_llamadas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)
    tipo = Column(String) # "resumen" | "esquema"
    tokens_totales = Column(Integer, nullable=True) # Si la respuesta de Gemini reporta uso de tokens
    fecha = Column(DateTime, default=datetime.utcnow, index=True)

# El esquema de la base de datos lo gestiona Alembic (ver carpeta `alembic/`).
# Ejecuta `alembic upgrade head` para crear/actualizar las tablas.
# (Antes aquí se hacía `Base.metadata.create_all(bind=engine)`, que se ha retirado
# para tener una única fuente de verdad del esquema y migraciones versionadas.)