"""Sincronización de alumnos y matrículas desde el Access de la academia.

Solo superadministradores. Flujo en dos pasos con el MISMO archivo:
  1. POST /sincronizar?aplicar=false -> vista previa (altas, bajas, errores). No cambia nada.
  2. POST /sincronizar?aplicar=true  -> aplica los cambios.

El Access manda: tras sincronizar, cada alumno gestionado tiene exactamente los
cursos del archivo (los que desaparecen se dan de baja; si un alumno desaparece
del todo, se queda sin cursos pero conserva su cuenta e historial).
"""
import io
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Curso, MatriculaAccess, SincronizacionAccess, Usuario, get_db
from routers.auth import require_superadmin
from services.access_sync import interpretar_filas, leer_archivo, normalizar, planificar
from services.matriculas import ROL_ESTUDIANTE, aplicar_matriculas_usuario

router = APIRouter(prefix="/api/admin/access", tags=["Sincronización Access"])

DOMINIO = os.getenv("GOOGLE_HOSTED_DOMAIN", "academiamega.net")
MAX_MB = 10
MAX_LISTA = 300  # elementos máximos devueltos en cada lista de la vista previa


@router.get("/estado")
def estado(_: Usuario = Depends(require_superadmin), db: Session = Depends(get_db)):
    ultima = db.query(SincronizacionAccess).order_by(SincronizacionAccess.fecha.desc()).first()
    autor = db.query(Usuario).filter(Usuario.id == ultima.usuario_id).first() if ultima else None
    emails = [e for (e,) in db.query(MatriculaAccess.email).distinct().all()]
    con_cuenta = {
        e for (e,) in db.query(func.lower(Usuario.email)).filter(func.lower(Usuario.email).in_(emails or ["-"])).all()
    }
    pendientes = sorted(set(emails) - con_cuenta)
    nombres = dict(db.query(MatriculaAccess.email, MatriculaAccess.nombre).filter(MatriculaAccess.email.in_(pendientes or ["-"])).all())
    return {
        "ultima": None if not ultima else {
            "fecha": ultima.fecha, "archivo": ultima.archivo, "autor": autor.nombre if autor else None,
            "alumnos": ultima.alumnos, "matriculas": ultima.matriculas,
            "altas": ultima.altas, "bajas": ultima.bajas, "errores": ultima.errores,
        },
        "alumnos_en_access": len(emails),
        "matriculas": db.query(func.count(MatriculaAccess.id)).scalar() or 0,
        "con_cuenta": len(con_cuenta),
        "sin_cuenta": [{"email": e, "nombre": nombres.get(e)} for e in pendientes[:MAX_LISTA]],
        "sin_cuenta_total": len(pendientes),
    }


@router.post("/sincronizar")
async def sincronizar(
    archivo: UploadFile = File(...),
    aplicar: bool = Query(False),
    admin: Usuario = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    contenido = await archivo.read()
    if len(contenido) > MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"El archivo supera {MAX_MB} MB.")
    try:
        filas = leer_archivo(archivo.filename, contenido)
        cursos = db.query(Curso).all()
        cursos_por_nombre = {normalizar(c.nombre): c.id for c in cursos}
        alumnos, errores, _ = interpretar_filas(filas, cursos_por_nombre, DOMINIO)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo. Comprueba que es un Excel (.xlsx) o CSV válido.")

    nombre_curso = {c.id: c.nombre for c in cursos}

    # Estado actual
    actuales = {}
    for m in db.query(MatriculaAccess).all():
        actuales.setdefault(m.email, set()).add(m.curso_id)
    usuarios = {u.email.lower(): u for u in db.query(Usuario).all() if u.email}
    staff_en_archivo = sorted(e for e in alumnos if e in usuarios and usuarios[e].rol != ROL_ESTUDIANTE)
    for e in staff_en_archivo:
        errores.append(f"{e} es profesor o administrador en la plataforma: sus cursos no se tocan.")
        alumnos.pop(e)
    gestionados = {e for e, u in usuarios.items() if u.gestionado_access and u.rol == ROL_ESTUDIANTE}

    deseadas, altas, bajas = planificar(alumnos, actuales, gestionados)

    def describir(pares):
        return [
            {"email": e, "nombre": (alumnos[e].nombre if e in alumnos else None) or (usuarios[e].nombre if e in usuarios else None),
             "curso": nombre_curso.get(c, f"Curso {c}"), "tiene_cuenta": e in usuarios}
            for e, c in pares[:MAX_LISTA]
        ]

    resumen = {
        "aplicado": False,
        "alumnos": len(alumnos),
        "matriculas": sum(len(v) for v in deseadas.values()),
        "con_cuenta": sum(1 for e in alumnos if e in usuarios),
        "sin_cuenta": sum(1 for e in alumnos if e not in usuarios),
        "altas": describir(altas), "altas_total": len(altas),
        "bajas": describir(bajas), "bajas_total": len(bajas),
        "sin_cursos": sorted(e for e in gestionados | set(actuales) if not deseadas.get(e)),
        "errores": errores[:MAX_LISTA], "errores_total": len(errores),
    }
    if not aplicar:
        return resumen

    # --- Aplicar: el Access pasa a ser la foto completa de matrículas ---
    ahora = datetime.utcnow()
    db.query(MatriculaAccess).delete(synchronize_session=False)
    for email, cursos_ids in deseadas.items():
        al = alumnos.get(email)
        for cid in cursos_ids:
            db.add(MatriculaAccess(email=email, curso_id=cid, access_id=(al.access_id if al else None) or None,
                                   nombre=(al.nombre if al else None) or None, fecha_sync=ahora))
    db.flush()
    # Usuarios que ya tienen cuenta: se actualizan sus cursos al momento
    for email in set(deseadas) | gestionados:
        u = usuarios.get(email)
        if u and u.rol == ROL_ESTUDIANTE:
            aplicar_matriculas_usuario(db, u)
    db.add(SincronizacionAccess(
        fecha=ahora, usuario_id=admin.id, archivo=(archivo.filename or "")[:200],
        alumnos=resumen["alumnos"], matriculas=resumen["matriculas"],
        altas=len(altas), bajas=len(bajas), errores=len(errores),
    ))
    db.commit()
    resumen["aplicado"] = True
    return resumen


@router.get("/plantilla")
def plantilla(_: Usuario = Depends(require_superadmin), db: Session = Depends(get_db)):
    """Excel de ejemplo con el formato esperado y los nombres de curso exactos."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    cursos = [c.nombre for c in db.query(Curso).order_by(Curso.id).all()] or ["Nombre del curso"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Alumnos"
    ws.append(["Id", "DNI", "Nombre", "Correo", "Cursos"])
    ws.append([1, "", "Nombre Apellido Apellido", f"nombre.apellido@{DOMINIO}", cursos[0]])
    if len(cursos) > 1:
        ws.append([2, "", "Otra Alumna Ejemplo", f"otra.alumna@{DOMINIO}", f"{cursos[0]}; {cursos[1]}"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="EA580C")
    for col, ancho in zip("ABCDE", (8, 14, 32, 40, 60)):
        ws.column_dimensions[col].width = ancho
    ref = wb.create_sheet("Cursos válidos")
    ref.append(["Nombres de curso exactos (cópialos tal cual en la columna Cursos)"])
    ref["A1"].font = Font(bold=True)
    for c in cursos:
        ref.append([c])
    ref.column_dimensions["A"].width = 70
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plantilla_alumnos_access.xlsx"'},
    )
