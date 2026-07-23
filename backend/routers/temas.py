"""Temas visibles para el usuario autenticado (lo que se pinta en el Dashboard).

Alcance:
- superadmin: todos los temas.
- admin (profesor) / estudiante: los temas de sus cursos.

Además siempre se incluyen los temas SIN curso asignado (`curso_id IS NULL`),
para no ocultar el temario antiguo mientras se reorganiza en cursos.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import get_db, Tema, MaterialTema, Usuario
from routers.auth import get_current_user, es_superadmin

router = APIRouter(prefix="/api/temas", tags=["Temas"])


def _tema_accesible(db: Session, usuario: Usuario, tema_id: int) -> Tema:
    """Devuelve el tema si el usuario puede verlo; si no, 403/404."""
    tema = db.query(Tema).filter(Tema.id == tema_id).first()
    if not tema:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    if es_superadmin(usuario):
        return tema
    if tema.curso_id is None or tema.curso_id in [c.id for c in usuario.cursos]:
        return tema
    raise HTTPException(status_code=403, detail="No tienes acceso a este tema.")


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


@router.get("/materiales")
def listar_todos_los_materiales(
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Todos los PDFs a los que el usuario tiene acceso (para elegir en el resumen).
    Incluye el nombre del tema al que pertenece cada uno."""
    query = db.query(MaterialTema).join(Tema, Tema.id == MaterialTema.tema_id)
    if not es_superadmin(usuario):
        ids_cursos = [c.id for c in usuario.cursos]
        if ids_cursos:
            query = query.filter(or_(Tema.curso_id.in_(ids_cursos), Tema.curso_id.is_(None)))
        else:
            query = query.filter(Tema.curso_id.is_(None))
    return [
        {
            "id": m.id,
            "nombre_archivo": m.nombre_archivo,
            "tema_id": m.tema_id,
            "tema_nombre": m.tema.nombre if m.tema else None,
        }
        for m in query.order_by(MaterialTema.tema_id, MaterialTema.id).all()
    ]


@router.get("/{tema_id}/materiales")
def listar_materiales_del_tema(
    tema_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """PDFs del tema (solo metadatos; el contenido se pide en /descargar)."""
    tema = _tema_accesible(db, usuario, tema_id)
    return [
        {
            "id": m.id,
            "nombre_archivo": m.nombre_archivo,
            "tamano_bytes": m.tamano_bytes,
            "fecha_subida": m.fecha_subida,
        }
        for m in tema.materiales
    ]


@router.get("/{tema_id}/materiales/{material_id}/descargar")
def descargar_material(
    tema_id: int,
    material_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _tema_accesible(db, usuario, tema_id)
    material = db.query(MaterialTema).filter(
        MaterialTema.id == material_id,
        MaterialTema.tema_id == tema_id,
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    # Saneamos el nombre para la cabecera (sin comillas ni saltos de línea)
    nombre = material.nombre_archivo.replace('"', "").replace("\n", "").replace("\r", "")
    return Response(
        content=material.contenido,
        media_type=material.tipo_mime or "application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )
