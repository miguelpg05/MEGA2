from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# IMPORTANTE: Hemos añadido 'Pregunta' a las importaciones para poder filtrar por tema
from models import get_db, RespuestaAlumno, Pregunta, Usuario
from schemas import TestResultado
from routers.auth import get_current_user

router = APIRouter(prefix="/api/progreso", tags=["Indicadores de Progreso"])

# ENDPOINT 1: Ahora calcula la MEDIA HISTÓRICA REAL (del alumno autenticado)
@router.get("/tema/{tema_id}")
def obtener_indicador_tema(tema_id: int, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Buscamos todas las respuestas históricas de este alumno, cruzándolas con
    # la tabla Pregunta para asegurarnos de que solo cogemos las de este tema_id
    respuestas_historicas = db.query(RespuestaAlumno).join(Pregunta).filter(
        RespuestaAlumno.alumno_id == usuario.id,
        Pregunta.tema_id == tema_id
    ).all()

    # 2. Hacemos el recuento matemático
    total_respuestas = len(respuestas_historicas)
    correctas = sum(1 for r in respuestas_historicas if r.es_correcta)

    # 3. Calculamos la media global (evitando dividir por cero si es nuevo)
    if total_respuestas > 0:
        porcentaje_actual = round((correctas / total_respuestas) * 100)
    else:
        porcentaje_actual = 0  # Si nunca ha hecho un test de este tema, está al 0%

    nivel_objetivo = 80.0
    superado = porcentaje_actual >= nivel_objetivo
    
    return {
        "tema_id": tema_id,
        "porcentaje_actual": porcentaje_actual,
        "nivel_aprobado": nivel_objetivo,
        "superado": superado,
        "indicador_texto": f"Tienes este tema al {porcentaje_actual}% · Nivel aprobado: {nivel_objetivo}%"
    }

# ENDPOINT 2: El que guarda los resultados del test
@router.post("/guardar-resultados")
def guardar_resultados(resultado: TestResultado, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # Recorremos cada respuesta que ha enviado el alumno
    for resp in resultado.respuestas:
        # Creamos un registro nuevo en la tabla respuestas_alumnos
        nueva_respuesta = RespuestaAlumno(
            alumno_id=usuario.id,
            pregunta_id=resp.pregunta_id,
            es_correcta=resp.es_correcta
        )
        db.add(nueva_respuesta)
    
    # Confirmamos y guardamos todos los cambios de golpe en SQLite
    db.commit()
    
    return {"mensaje": "¡Resultados guardados y progreso actualizado con éxito!"}