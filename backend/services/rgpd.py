"""RGPD: aceptación de la política de privacidad, exportación y supresión de datos.

La academia es la responsable del tratamiento. La supresión la ejecuta un
superadministrador desde el panel (el alumno la solicita a la academia), así queda
constancia; el alumno sí puede descargar sus datos desde «Mi cuenta».
"""
import os
from datetime import datetime

from sqlalchemy.orm import Session

from models import (
    IALlamada, MatriculaAccess, Pregunta, RegistroFallo, RespuestaAlumno,
    SincronizacionAccess, TestIntento, TestPlantilla, Usuario,
)

# Cambiar esta versión (variable de entorno) obliga a todos a aceptar de nuevo.
VERSION_PRIVACIDAD = os.getenv("VERSION_PRIVACIDAD", "2026-11")


def debe_aceptar_privacidad(usuario: Usuario) -> bool:
    return usuario.privacidad_version != VERSION_PRIVACIDAD


def registrar_aceptacion(db: Session, usuario: Usuario) -> None:
    usuario.privacidad_aceptada_en = datetime.utcnow()
    usuario.privacidad_version = VERSION_PRIVACIDAD
    db.commit()


def exportar_datos(db: Session, usuario: Usuario) -> dict:
    """Todo lo que la plataforma guarda del usuario (derechos de acceso y portabilidad)."""
    uid = usuario.id
    nombres_test = dict(db.query(TestPlantilla.id, TestPlantilla.numero_test).all())
    respuestas = (
        db.query(RespuestaAlumno.id, RespuestaAlumno.pregunta_id, RespuestaAlumno.es_correcta, Pregunta.enunciado)
        .outerjoin(Pregunta, Pregunta.id == RespuestaAlumno.pregunta_id)
        .filter(RespuestaAlumno.alumno_id == uid).order_by(RespuestaAlumno.id).all()
    )
    fallos = (
        db.query(RegistroFallo.pregunta_id, RegistroFallo.repasada, Pregunta.enunciado)
        .outerjoin(Pregunta, Pregunta.id == RegistroFallo.pregunta_id)
        .filter(RegistroFallo.alumno_id == uid).order_by(RegistroFallo.id).all()
    )
    intentos = db.query(TestIntento).filter(TestIntento.alumno_id == uid).order_by(TestIntento.id).all()
    ia = db.query(IALlamada).filter(IALlamada.usuario_id == uid).order_by(IALlamada.id).all()
    return {
        "generado_en": datetime.utcnow().isoformat() + "Z",
        "usuario": {
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "cursos": [c.nombre for c in usuario.cursos],
            "acceso_con_google": bool(usuario.google_sub),
            "privacidad_aceptada_en": usuario.privacidad_aceptada_en.isoformat() if usuario.privacidad_aceptada_en else None,
            "privacidad_version": usuario.privacidad_version,
            "aparece_en_ranking": usuario.mostrar_en_ranking is not False,
        },
        "intentos_de_test": [
            {
                "fecha": i.fecha_intento.isoformat() if i.fecha_intento else None,
                "test": nombres_test.get(i.test_plantilla_id) if i.test_plantilla_id else "Personalizado",
                "modo": i.modo,
                "preguntas": i.total_preguntas,
                "fallos_y_en_blanco": i.fallos_ultimo,
            }
            for i in intentos
        ],
        "respuestas": [{"pregunta": e, "correcta": bool(c)} for _, _, c, e in respuestas],
        "fallos_para_repaso": [{"pregunta": e, "repasada": bool(r)} for _, r, e in fallos],
        "uso_de_la_ia": [
            {"fecha": x.fecha.isoformat() if x.fecha else None, "tipo": getattr(x, "tipo", None)} for x in ia
        ],
    }


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
