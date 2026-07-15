import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
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

# 1. Tabla de Temas y Bloques
class Tema(Base):
    __tablename__ = "temas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    bloque = Column(String) # Ej: "Derecho Constitucional", "Derecho Administrativo"
    
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

# 6. Tabla de Usuarios (Login por email/contraseña o por Google)
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    email = Column(String, unique=True, index=True) # unique=True evita que dos se registren con el mismo email
    hashed_password = Column(String, nullable=True) # Null si el usuario entra solo con Google
    google_sub = Column(String, unique=True, index=True, nullable=True) # ID único de Google (idinfo['sub'])
    sesion_id = Column(String, nullable=True) # Token de la sesión activa actual; cada login lo renueva e invalida el resto

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

Base.metadata.create_all(bind=engine)