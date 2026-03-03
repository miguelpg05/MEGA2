from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Configuramos una base de datos SQLite para desarrollo
SQLALCHEMY_DATABASE_URL = "sqlite:///./academia.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
# Función para abrir y cerrar la conexión a la base de datos en cada petición
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

# MUY IMPORTANTE: Esto siempre debe ir al final, después de definir todas las clases
# Creamos las tablas en el archivo academia.db al ejecutar
Base.metadata.create_all(bind=engine)