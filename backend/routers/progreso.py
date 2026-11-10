"""Indicadores de progreso por tema («Llevas este tema al 62 % · Nivel aprobado: 80 %»).

El porcentaje se calcula con la ÚLTIMA respuesta del alumno a cada pregunta del
tema: refleja cómo está ahora (si corrige un fallo, el porcentaje sube), no la
media de todo lo que ha respondido desde el principio.
Todo se agrega en PostgreSQL (una consulta), sin traer las respuestas a Python.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models import get_db, RespuestaAlumno, Pregunta, Usuario
from routers.auth import get_current_user

router = APIRouter(prefix="/api/progreso", tags=["Indicadores de Progreso"])

NIVEL_APROBADO = 80.0


def progreso_por_tema(db: Session, alumno_id: int, tema_id: int = None) -> dict:
    """{tema_id: (preguntas_respondidas, correctas)} según la última respuesta a cada pregunta."""
    ultimas = (
        db.query(func.max(RespuestaAlumno.id).label("id"))
        .filter(RespuestaAlumno.alumno_id == alumno_id)
        .group_by(RespuestaAlumno.pregunta_id)
        .subquery()
    )
    q = (
        db.query(
            Pregunta.tema_id,
            func.count(RespuestaAlumno.id),
            func.sum(case((RespuestaAlumno.es_correcta.is_(True), 1), else_=0)),
        )
        .select_from(RespuestaAlumno)
        .join(ultimas, ultimas.c.id == RespuestaAlumno.id)
        .join(Pregunta, Pregunta.id == RespuestaAlumno.pregunta_id)
    )
    if tema_id is not None:
        q = q.filter(Pregunta.tema_id == tema_id)
    return {t: (int(n or 0), int(c or 0)) for t, n, c in q.group_by(Pregunta.tema_id).all()}


def _indicador(tema_id: int, respondidas: int, correctas: int) -> dict:
    porcentaje = round(correctas * 100 / respondidas) if respondidas else 0
    return {
        "tema_id": tema_id,
        "porcentaje_actual": porcentaje,
        "nivel_aprobado": NIVEL_APROBADO,
        "superado": porcentaje >= NIVEL_APROBADO,
        "preguntas_respondidas": respondidas,
        "indicador_texto": f"Tienes este tema al {porcentaje}% · Nivel aprobado: {NIVEL_APROBADO:g}%",
    }


@router.get("/temas")
def progreso_de_todos_los_temas(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Progreso de TODOS los temas en una sola petición (lo usa el inicio).
    Devuelve {tema_id: indicador}; los temas sin respuestas no aparecen (= 0 %)."""
    return {str(t): _indicador(t, n, c) for t, (n, c) in progreso_por_tema(db, usuario.id).items()}


@router.get("/tema/{tema_id}")
def obtener_indicador_tema(tema_id: int, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Progreso de un tema (se mantiene por compatibilidad). Solo datos del propio alumno."""
    n, c = progreso_por_tema(db, usuario.id, tema_id).get(tema_id, (0, 0))
    return _indicador(tema_id, n, c)

# Los resultados de los tests se guardan con POST /api/test/entregar
# (routers/progreso_test.py), que corrige en el servidor.
