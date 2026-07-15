"""Panel de administración: gestión de contenido (temas/tests/preguntas), métricas
para la academia, gestión de roles y limpieza del ranking.

Autorización:
- `require_staff` (profesor o admin): gestión de contenido, importación y métricas.
- `require_admin` (solo admin): gestión de usuarios y roles.
"""
import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import func, cast, Integer
from sqlalchemy.orm import Session

from models import (
    get_db,
    Tema,
    TestPlantilla,
    Pregunta,
    Usuario,
    RegistroFallo,
    RespuestaAlumno,
    TestIntento,
    IALlamada,
    Puntuacion,
)
from schemas import TemaIn, TestPlantillaIn, PreguntaIn, RolUpdate
from routers.auth import require_staff, require_admin
from services.preguntas import normalizar_letra

router = APIRouter(prefix="/api/admin", tags=["Administración"])

# Nombres de los usuarios de demostración que la versión antigua inyectaba en el ranking.
NOMBRES_DEMO = ["Marta V.", "Carlos M.", "Lucía Gómez", "Javier R.", "Ana Ruiz"]
ROLES_VALIDOS = ("alumno", "profesor", "admin")


# ==========================================
# TEMAS
# ==========================================
@router.get("/temas")
def listar_temas(_: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    return db.query(Tema).order_by(Tema.id).all()

@router.post("/temas")
def crear_tema(datos: TemaIn, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    tema = Tema(nombre=datos.nombre.strip(), bloque=(datos.bloque or "").strip() or None)
    db.add(tema)
    db.commit()
    db.refresh(tema)
    return tema

@router.put("/temas/{tema_id}")
def editar_tema(tema_id: int, datos: TemaIn, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    tema = db.query(Tema).filter(Tema.id == tema_id).first()
    if not tema:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    tema.nombre = datos.nombre.strip()
    tema.bloque = (datos.bloque or "").strip() or None
    db.commit()
    db.refresh(tema)
    return tema

@router.delete("/temas/{tema_id}")
def borrar_tema(tema_id: int, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    tema = db.query(Tema).filter(Tema.id == tema_id).first()
    if not tema:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    db.delete(tema)
    db.commit()
    return {"mensaje": "Tema eliminado"}


# ==========================================
# PLANTILLAS DE TEST
# ==========================================
@router.get("/tests")
def listar_tests(tema_id: int = Query(None), _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    query = db.query(TestPlantilla)
    if tema_id:
        query = query.filter(TestPlantilla.tema_id == tema_id)
    return query.order_by(TestPlantilla.numero_test).all()

@router.post("/tests")
def crear_test(datos: TestPlantillaIn, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    existe = db.query(TestPlantilla).filter(TestPlantilla.numero_test == datos.numero_test).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un test con ese número")
    test = TestPlantilla(
        numero_test=datos.numero_test.strip(),
        tema_id=datos.tema_id,
        total_preguntas=datos.total_preguntas,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test

@router.delete("/tests/{test_id}")
def borrar_test(test_id: int, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    test = db.query(TestPlantilla).filter(TestPlantilla.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test no encontrado")
    db.delete(test)
    db.commit()
    return {"mensaje": "Test eliminado"}


# ==========================================
# PREGUNTAS
# ==========================================
@router.get("/preguntas")
def listar_preguntas(
    test_plantilla_id: int = Query(None),
    tema_id: int = Query(None),
    _: Usuario = Depends(require_staff),
    db: Session = Depends(get_db),
):
    query = db.query(Pregunta)
    if test_plantilla_id:
        query = query.filter(Pregunta.test_plantilla_id == test_plantilla_id)
    if tema_id:
        query = query.filter(Pregunta.tema_id == tema_id)
    return query.order_by(Pregunta.id).all()

@router.post("/preguntas")
def crear_pregunta(datos: PreguntaIn, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    pregunta = Pregunta(
        enunciado=datos.enunciado.strip(),
        opcion_a=datos.opcion_a.strip(),
        opcion_b=datos.opcion_b.strip(),
        opcion_c=datos.opcion_c.strip(),
        opcion_d=datos.opcion_d.strip(),
        respuesta_correcta=normalizar_letra(datos.respuesta_correcta),
        explicacion=(datos.explicacion or "").strip() or None,
        tema_id=datos.tema_id,
        test_plantilla_id=datos.test_plantilla_id,
    )
    db.add(pregunta)
    db.commit()
    db.refresh(pregunta)
    return pregunta

@router.put("/preguntas/{pregunta_id}")
def editar_pregunta(pregunta_id: int, datos: PreguntaIn, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    pregunta = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    pregunta.enunciado = datos.enunciado.strip()
    pregunta.opcion_a = datos.opcion_a.strip()
    pregunta.opcion_b = datos.opcion_b.strip()
    pregunta.opcion_c = datos.opcion_c.strip()
    pregunta.opcion_d = datos.opcion_d.strip()
    pregunta.respuesta_correcta = normalizar_letra(datos.respuesta_correcta)
    pregunta.explicacion = (datos.explicacion or "").strip() or None
    pregunta.tema_id = datos.tema_id
    pregunta.test_plantilla_id = datos.test_plantilla_id
    db.commit()
    db.refresh(pregunta)
    return pregunta

@router.delete("/preguntas/{pregunta_id}")
def borrar_pregunta(pregunta_id: int, _: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    pregunta = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    db.delete(pregunta)
    db.commit()
    return {"mensaje": "Pregunta eliminada"}


# ==========================================
# IMPORTACIÓN MASIVA (CSV / XLSX)
# ==========================================
COLUMNAS_IMPORT = ["tema_id", "numero_test", "enunciado", "opcion_a", "opcion_b", "opcion_c", "opcion_d", "respuesta_correcta", "explicacion"]

def _filas_desde_csv(contenido: bytes):
    texto = contenido.decode("utf-8-sig")
    lector = csv.DictReader(io.StringIO(texto))
    return [dict(fila) for fila in lector]

def _filas_desde_xlsx(contenido: bytes):
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise HTTPException(status_code=500, detail="Falta la librería openpyxl para leer .xlsx. Usa un CSV o instálala.")
    wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    hoja = wb.active
    filas = list(hoja.iter_rows(values_only=True))
    if not filas:
        return []
    cabeceras = [str(c).strip() if c is not None else "" for c in filas[0]]
    resultado = []
    for fila in filas[1:]:
        resultado.append({cabeceras[i]: fila[i] for i in range(len(cabeceras)) if i < len(fila)})
    return resultado

@router.post("/preguntas/importar")
async def importar_preguntas(
    archivo: UploadFile = File(...),
    _: Usuario = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Importa preguntas desde un CSV o XLSX con las columnas:
    tema_id, numero_test, enunciado, opcion_a..d, respuesta_correcta, explicacion.
    Crea las plantillas de test que no existan. Añade (no borra lo existente)."""
    contenido = await archivo.read()
    nombre = (archivo.filename or "").lower()

    if nombre.endswith(".csv"):
        filas = _filas_desde_csv(contenido)
    elif nombre.endswith(".xlsx"):
        filas = _filas_desde_xlsx(contenido)
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado. Sube un .csv o .xlsx")

    creadas = 0
    errores = []
    for i, fila in enumerate(filas, start=2):  # fila 1 = cabecera
        try:
            tema_id = int(fila["tema_id"])
            numero_test = str(int(float(fila["numero_test"]))).zfill(3)
            plantilla = db.query(TestPlantilla).filter(
                TestPlantilla.tema_id == tema_id,
                TestPlantilla.numero_test == numero_test,
            ).first()
            if not plantilla:
                plantilla = TestPlantilla(tema_id=tema_id, numero_test=numero_test, total_preguntas=10)
                db.add(plantilla)
                db.commit()
                db.refresh(plantilla)

            pregunta = Pregunta(
                tema_id=tema_id,
                test_plantilla_id=plantilla.id,
                enunciado=str(fila["enunciado"]).strip(),
                opcion_a=str(fila["opcion_a"]).strip(),
                opcion_b=str(fila["opcion_b"]).strip(),
                opcion_c=str(fila["opcion_c"]).strip(),
                opcion_d=str(fila["opcion_d"]).strip(),
                respuesta_correcta=normalizar_letra(fila["respuesta_correcta"]),
                explicacion=(str(fila.get("explicacion") or "").strip() or "Consulta el temario para más detalle."),
            )
            db.add(pregunta)
            creadas += 1
        except Exception as e:
            db.rollback()
            errores.append(f"Fila {i}: {e}")

    db.commit()
    return {"creadas": creadas, "errores": errores}


# ==========================================
# MÉTRICAS
# ==========================================
@router.get("/metricas")
def obtener_metricas(_: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    hace_7d = datetime.utcnow() - timedelta(days=7)
    hoy = datetime.utcnow().date()

    usuarios_total = db.query(func.count(Usuario.id)).scalar() or 0
    alumnos_total = db.query(func.count(Usuario.id)).filter(Usuario.rol == "alumno").scalar() or 0

    alumnos_activos_7d = (
        db.query(func.count(func.distinct(TestIntento.alumno_id)))
        .filter(TestIntento.fecha_intento >= hace_7d)
        .scalar()
        or 0
    )

    # Progreso medio por tema (% de aciertos histórico)
    progreso_rows = (
        db.query(
            Tema.id,
            Tema.nombre,
            func.count(RespuestaAlumno.id),
            func.sum(cast(RespuestaAlumno.es_correcta, Integer)),
        )
        .join(Pregunta, Pregunta.tema_id == Tema.id)
        .join(RespuestaAlumno, RespuestaAlumno.pregunta_id == Pregunta.id)
        .group_by(Tema.id, Tema.nombre)
        .all()
    )
    progreso_por_tema = []
    for tema_id, nombre, total, correctas in progreso_rows:
        total = total or 0
        correctas = correctas or 0
        porcentaje = round((correctas / total) * 100) if total else 0
        progreso_por_tema.append({"tema_id": tema_id, "nombre": nombre, "respuestas": total, "porcentaje": porcentaje})

    # Preguntas más falladas
    fallos_rows = (
        db.query(RegistroFallo.pregunta_id, func.count(RegistroFallo.id).label("veces"))
        .group_by(RegistroFallo.pregunta_id)
        .order_by(func.count(RegistroFallo.id).desc())
        .limit(10)
        .all()
    )
    preguntas_mas_falladas = []
    for pregunta_id, veces in fallos_rows:
        p = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
        preguntas_mas_falladas.append({
            "pregunta_id": pregunta_id,
            "enunciado": p.enunciado if p else "(pregunta eliminada)",
            "veces_fallada": veces,
        })

    # Uso de IA (Gemini)
    ia_total = db.query(func.count(IALlamada.id)).scalar() or 0
    ia_7d = db.query(func.count(IALlamada.id)).filter(IALlamada.fecha >= hace_7d).scalar() or 0
    ia_hoy = db.query(func.count(IALlamada.id)).filter(func.date(IALlamada.fecha) == hoy).scalar() or 0
    ia_tokens = db.query(func.coalesce(func.sum(IALlamada.tokens_totales), 0)).scalar() or 0

    return {
        "usuarios_total": usuarios_total,
        "alumnos_total": alumnos_total,
        "alumnos_activos_7d": alumnos_activos_7d,
        "progreso_por_tema": progreso_por_tema,
        "preguntas_mas_falladas": preguntas_mas_falladas,
        "ia": {"total": ia_total, "ultimos_7d": ia_7d, "hoy": ia_hoy, "tokens_totales": ia_tokens},
    }


# ==========================================
# RANKING: limpieza
# ==========================================
@router.delete("/ranking/demo")
def limpiar_ranking_demo(_: Usuario = Depends(require_staff), db: Session = Depends(get_db)):
    borradas = db.query(Puntuacion).filter(Puntuacion.alumno_nombre.in_(NOMBRES_DEMO)).delete(synchronize_session=False)
    db.commit()
    return {"mensaje": f"Eliminadas {borradas} puntuaciones de demostración."}

@router.delete("/ranking/reset")
def reset_ranking(_: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    borradas = db.query(Puntuacion).delete(synchronize_session=False)
    db.commit()
    return {"mensaje": f"Ranking reiniciado. Eliminadas {borradas} puntuaciones."}


# ==========================================
# USUARIOS Y ROLES (solo admin)
# ==========================================
@router.get("/usuarios")
def listar_usuarios(_: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    usuarios = db.query(Usuario).order_by(Usuario.id).all()
    return [{"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol} for u in usuarios]

@router.put("/usuarios/{usuario_id}/rol")
def cambiar_rol(
    usuario_id: int,
    datos: RolUpdate,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if datos.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Rol no válido. Usa uno de: {', '.join(ROLES_VALIDOS)}")
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.id == admin.id and datos.rol != "admin":
        raise HTTPException(status_code=400, detail="No puedes quitarte a ti mismo el rol de administrador.")
    usuario.rol = datos.rol
    db.commit()
    return {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol}
