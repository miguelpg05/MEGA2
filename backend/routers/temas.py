"""Temas visibles para el usuario autenticado (lo que se pinta en el Dashboard).

Alcance:
- superadmin: todos los temas.
- admin (profesor) / estudiante: los temas de sus cursos.

Además siempre se incluyen los temas SIN curso asignado (`curso_id IS NULL`),
para no ocultar el temario antiguo mientras se reorganiza en cursos.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import get_db, Tema, Usuario
from routers.auth import get_current_user, es_superadmin

router = APIRouter(prefix="/api/temas", tags=["Temas"])


@router.get("")
def listar_temas_del_usuario(
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Tema)

    if not es_superadmin(usuario):
        ids_cursos = [c.id for c in usuario.cursos]
        if ids_cursos:
            query = query.filter(or_(Tema.curso_id.in_(ids_cursos), Tema.curso_id.is_(None)))
        else:
            # Sin cursos asignados solo ve el temario aún no clasificado
            query = query.filter(Tema.curso_id.is_(None))

    return [
        {
            "id": t.id,
            "nombre": t.nombre,
            "bloque": t.bloque,
            "curso_id": t.curso_id,
            "curso": t.curso.nombre if t.curso else None,
        }
        for t in query.order_by(Tema.id).all()
    ]
