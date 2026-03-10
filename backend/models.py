import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from datetime import datetime
# Pega aquí exactamente tu enlace de Neon.tech
# IMPORTANTE: Asegúrate de que empieza por "postgresql://" y no solo "postgres://"
URL_NEON = "postgresql://neondb_owner:npg_I4Umhsfa0iRx@ep-rough-heart-agbtnl6n-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", URL_NEON)

# Para PostgreSQL eliminamos el 'check_same_thread' que solo era para SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Función para abrir y cerrar la conexión... (el resto del archivo sigue igual)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ... (Aquí debajo siguen tus clases Tema, Pregunta, etc.) ...
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

# 6. NUEVA: Tabla de Usuarios (Para el Login Real)
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    email = Column(String, unique=True, index=True) # unique=True evita que dos se registren con el mismo email
    hashed_password = Column(String) # Aquí guardaremos la contraseña ya encriptada (ilegible)
# MUY IMPORTANTE: Esto siempre debe ir al final, después de definir todas las clases
# Creamos las tablas en el archivo academia.db al ejecutar
# --- NUEVAS TABLAS PARA EL LISTADO DE TESTS ESPECÍFICOS ---

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