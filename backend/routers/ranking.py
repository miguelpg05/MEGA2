"""Ranking de la clase, por curso.

Puntuación de cada alumno = suma, para cada test del BANCO del curso, del % de
aciertos de su MEJOR intento (0-100 puntos por test). Así:
  - premia hacer bien muchos tests distintos,
  - repetir un test solo sirve para mejorar su nota (no para acumular puntos),
  - los tests personalizados NO cuentan (no son iguales para todos).
Se calcula siempre a partir de `test_intentos`, que el servidor guarda al corregir
(POST /api/test/entregar), así que no se puede manipular desde el navegador.
"""
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models import get_db, Curso, Pregunta, Tema, TestIntento, TestPlantilla, Usuario, usuario_cursos
from routers.auth import ROL_ESTUDIANTE, get_current_user, verificar_acceso_curso

router = APIRouter(prefix="/api/ranking", tags=["Ranking"])

TOP_ALUMNOS = 5


def _tests_del_curso(db: Session, curso_id: int) -> set:
    """Tests del banco asignados a algún tema del curso (incluye tests multi-tema)."""
    tema_ids = [t for (t,) in db.query(Tema.id).filter(Tema.curso_id == curso_id).all()]
    if not tema_ids:
        return set()
    filas = db.query(TestPlantilla.id).filter(or_(
        TestPlantilla.tema_id.in_(tema_ids),
        TestPlantilla.temas.any(Tema.id.in_(tema_ids)),
    )).all()
    return {t for (t,) in filas}


def calcular_ranking(db: Session, curso_id: int) -> list:
    """Lista ordenada [{posicion, usuario_id, nombre, puntos, tests}] de los alumnos
    del curso con al menos un test del banco hecho. Empates: misma posición."""
    test_ids = _tests_del_curso(db, curso_id)
    alumnos = {
        u.id: u for u in db.query(Usuario)
        .join(usuario_cursos, usuario_cursos.c.usuario_id == Usuario.id)
        .filter(usuario_cursos.c.curso_id == curso_id, Usuario.rol == ROL_ESTUDIANTE)
        .all()
    }
    if not test_ids or not alumnos:
        return []

    intentos = db.query(
        TestIntento.alumno_id, TestIntento.test_plantilla_id,
        TestIntento.fallos_ultimo, TestIntento.total_preguntas,
    ).filter(
        TestIntento.alumno_id.in_(list(alumnos)),
        TestIntento.test_plantilla_id.in_(list(test_ids)),
        or_(TestIntento.personalizado.is_(None), TestIntento.personalizado == False),  # noqa: E712
    ).all()

    # Intentos antiguos sin total guardado: se usa el nº de preguntas del test
    preguntas_por_test = dict(
        db.query(Pregunta.test_plantilla_id, func.count(Pregunta.id))
        .filter(Pregunta.test_plantilla_id.in_(list(test_ids)))
        .group_by(Pregunta.test_plantilla_id).all()
    )

    mejor = defaultdict(dict)  # alumno -> {test: mejor %}
    for alumno_id, test_id, fallos, total in intentos:
        total = total or preguntas_por_test.get(test_id) or 0
        if total <= 0:
            continue
        pct = max(0.0, min(100.0, (total - (fallos or 0)) * 100.0 / total))
        if pct > mejor[alumno_id].get(test_id, -1):
            mejor[alumno_id][test_id] = pct

    filas = [
        {
            "usuario_id": uid,
            "nombre": alumnos[uid].nombre,
            "puntos": round(sum(por_test.values())),
            "tests": len(por_test),
        }
        for uid, por_test in mejor.items() if por_test
    ]
    filas.sort(key=lambda f: (-f["puntos"], -f["tests"], (f["nombre"] or "").lower()))

    posicion, anterior = 0, None
    for i, f in enumerate(filas, start=1):
        if f["puntos"] != anterior:
            posicion, anterior = i, f["puntos"]
        f["posicion"] = posicion
    return filas


@router.get("/clase")
def ranking_de_la_clase(
    curso_id: int = Query(..., description="Curso del que se muestra el ranking"),
    completo: bool = Query(False, description="Lista completa (solo profesores y administradores)"),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Top 5 del curso y la posición del propio alumno. Requiere sesión y acceso al curso.
    Con `completo=true` (solo staff) devuelve todos los alumnos."""
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")
    verificar_acceso_curso(usuario, curso_id)
    if completo and usuario.rol == ROL_ESTUDIANTE:
        raise HTTPException(status_code=403, detail="Solo el profesorado puede ver el ranking completo.")

    filas = calcular_ranking(db, curso_id)
    yo: Optional[dict] = next((f for f in filas if f["usuario_id"] == usuario.id), None)
    lideres = filas if completo else filas[:TOP_ALUMNOS]

    def publico(f):
        return {
            "posicion": f["posicion"],
            "nombre": f["nombre"],
            "puntos": f["puntos"],
            "tests": f["tests"],
            "soy_yo": f["usuario_id"] == usuario.id,
        }

    return {
        "curso_id": curso.id,
        "curso": curso.nombre,
        "participantes": len(filas),
        "lideres": [publico(f) for f in lideres],
        "yo": publico(yo) if yo else None,
    }
