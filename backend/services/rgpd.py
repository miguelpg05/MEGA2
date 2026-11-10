"""RGPD: aceptación de la política de privacidad y supresión de datos.

La academia es la responsable del tratamiento. La supresión la ejecuta un
superadministrador desde el panel (el alumno la solicita a la academia), así queda
constancia. La copia de los datos también se solicita a la academia.
"""
import os
from datetime import datetime

from sqlalchemy.orm import Session

from models import (
    IALlamada, MatriculaAccess, RegistroFallo, RespuestaAlumno,
    SincronizacionAccess, TestIntento, Usuario,
)

# Cambiar esta versión (variable de entorno) obliga a todos a aceptar de nuevo.
VERSION_PRIVACIDAD = os.getenv("VERSION_PRIVACIDAD", "2026-11")


def debe_aceptar_privacidad(usuario: Usuario) -> bool:
    return usuario.privacidad_version != VERSION_PRIVACIDAD


def registrar_aceptacion(db: Session, usuario: Usuario) -> None:
    usuario.privacidad_aceptada_en = datetime.utcnow()
    usuario.privacidad_version = VERSION_PRIVACIDAD
    db.commit()


def suprimir_usuario(db: Session, usuario: Usuario) -> dict:
    """Borrado definitivo de la cuenta y de todo su historial, en UNA transacción.
    Las matrículas del Access de ese correo también se borran (si el alumno sigue en
    el Access, la próxima sincronización las volverá a crear: hay que darle de baja allí)."""
    uid, email = usuario.id, usuario.email
    borrados = {}
    try:
        for nombre, modelo, columna in (
            ("respuestas", RespuestaAlumno, RespuestaAlumno.alumno_id),
            ("fallos", RegistroFallo, RegistroFallo.alumno_id),
            ("intentos", TestIntento, TestIntento.alumno_id),
            ("uso_ia", IALlamada, IALlamada.usuario_id),
        ):
            borrados[nombre] = db.query(modelo).filter(columna == uid).delete(synchronize_session=False)
        borrados["matriculas_access"] = db.query(MatriculaAccess).filter(
            MatriculaAccess.email == (email or "").lower()).delete(synchronize_session=False)
        db.query(SincronizacionAccess).filter(SincronizacionAccess.usuario_id == uid).update(
            {SincronizacionAccess.usuario_id: None}, synchronize_session=False)
        db.delete(usuario)   # usuario_cursos y puntuaciones caen en cascada
        db.commit()
    except Exception:
        db.rollback()
        raise
    return borrados
