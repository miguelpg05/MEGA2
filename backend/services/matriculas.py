"""Aplicación de las matrículas del Access a los usuarios de la plataforma.

Solo afecta a usuarios con rol «estudiante». Profesores y administradores
gestionan sus cursos desde el panel y nunca los toca la sincronización.
Los alumnos que nunca han aparecido en el Access (p. ej. cuentas de demo
creadas a mano) tampoco se tocan: solo los marcados `gestionado_access`.
"""
from sqlalchemy.orm import Session

from models import Curso, MatriculaAccess, Usuario

ROL_ESTUDIANTE = "estudiante"


def aplicar_matriculas_usuario(db: Session, usuario: Usuario) -> bool:
    """Ajusta los cursos de un alumno a lo que dice el Access (se llama al iniciar
    sesión). Devuelve True si el usuario lo gestiona el Access. No hace commit."""
    if usuario.rol != ROL_ESTUDIANTE or not usuario.email:
        return False
    filas = db.query(MatriculaAccess).filter(MatriculaAccess.email == usuario.email.lower()).all()
    if not filas and not usuario.gestionado_access:
        return False  # alumno ajeno al Access: no se toca
    ids = {f.curso_id for f in filas}
    usuario.cursos = db.query(Curso).filter(Curso.id.in_(ids or [-1])).all()
    usuario.gestionado_access = True
    nombre = next((f.nombre for f in filas if f.nombre), None)
    if nombre:
        usuario.nombre = nombre  # el nombre del Access es mejor que el alias del correo
    return True
