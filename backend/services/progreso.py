from sqlalchemy.orm import Session
# Importamos los modelos directamente ya que models.py está en la raíz de backend
from models import Pregunta, RespuestaAlumno 

def calcular_progreso_tema(db: Session, alumno_id: int, tema_id: int) -> float:
    # 1. Contamos el total de preguntas que pertenecen a este tema
    total_preguntas = db.query(Pregunta).filter(Pregunta.tema_id == tema_id).count()
    
    if total_preguntas == 0:
        return 0.0

    # 2. Contamos cuántas preguntas ÚNICAS ha acertado el alumno en este tema
    preguntas_acertadas = db.query(RespuestaAlumno.pregunta_id).join(
        Pregunta, RespuestaAlumno.pregunta_id == Pregunta.id
    ).filter(
        RespuestaAlumno.alumno_id == alumno_id,
        Pregunta.tema_id == tema_id,
        RespuestaAlumno.es_correcta == True
    ).distinct().count()
    
    # 3. Calculamos el porcentaje
    porcentaje = (preguntas_acertadas / total_preguntas) * 100
    
    return round(porcentaje, 1)