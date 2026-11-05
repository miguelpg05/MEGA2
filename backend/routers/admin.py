"""Panel de administración con alcance por curso.

Roles:
- `superadmin` (jefes de la academia): acceso total. Único que gestiona cursos,
  usuarios y roles.
- `admin` (profesores): gestiona el temario/tests SOLO de los cursos que tiene
  asignados. Cada operación valida el curso implicado.
- `estudiante`: no entra aquí.
"""
import io
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, cast, Integer, or_
from sqlalchemy.orm import Session

from models import (
    get_db,
    Curso,
    Tema,
    MaterialTema,
    TestPlantilla,
    Pregunta,
    Usuario,
    RegistroFallo,
    RespuestaAlumno,
    TestIntento,
    IALlamada,
)
from schemas import CursoIn, CursosUsuarioUpdate, TemaIn, TestPlantillaIn, PreguntaIn, RolUpdate
from routers.auth import (
    require_gestor,
    require_superadmin,
    es_superadmin,
    cursos_permitidos_ids,
    verificar_acceso_curso,
    ROLES_VALIDOS,
)
from services.preguntas import normalizar_respuesta, letras_correctas
from services.tests_util import normalizar_nombre_test, clave_orden_natural
from services.importar_preguntas import (
    ENCABEZADOS, HOJA_PREGUNTAS, clave_enunciado, detectar_columnas, interpretar_fila, leer_filas,
)
from services.access_sync import _texto

router = APIRouter(prefix="/api/admin", tags=["Administración"])

# ==========================================
# HELPERS DE ALCANCE
# ==========================================
def _borrar_rastro_de_preguntas(db: Session, pregunta_ids) -> None:
    """Borra las respuestas y fallos de alumnos ligados a esas preguntas.
    Sin esto la BD impide borrar una pregunta que ya se ha respondido
    (claves foráneas de respuestas_alumnos y registro_fallos)."""
    ids = list(pregunta_ids)
    if not ids:
        return
    db.query(RespuestaAlumno).filter(RespuestaAlumno.pregunta_id.in_(ids)).delete(synchronize_session=False)
    db.query(RegistroFallo).filter(RegistroFallo.pregunta_id.in_(ids)).delete(synchronize_session=False)

def _tema_o_404(db: Session, tema_id: int) -> Tema:
    tema = db.query(Tema).filter(Tema.id == tema_id).first()
    if not tema:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    return tema

def _curso_id_de_tema(db: Session, tema_id) -> object:
    """curso_id del tema, o None si el tema ya no existe (tests/preguntas huérfanos).
    No lanza 404: así un superadmin puede borrar contenido cuyo tema se eliminó."""
    tema = db.query(Tema).filter(Tema.id == tema_id).first()
    return tema.curso_id if tema else None

def _temas_permitidos_ids(db: Session, usuario: Usuario):
    """IDs de temas accesibles. None = todos (superadmin)."""
    permitidos = cursos_permitidos_ids(usuario)
    if permitidos is None:
        return None
    if not permitidos:
        return []
    return [t[0] for t in db.query(Tema.id).filter(Tema.curso_id.in_(permitidos)).all()]

def _filtro_tests_de_temas(tema_ids):
    """Condición SQL: tests asignados a alguno de esos temas (tabla intermedia o
    tema principal, para tolerar tests antiguos)."""
    ids = list(tema_ids) or [-1]
    return or_(TestPlantilla.tema_id.in_(ids), TestPlantilla.temas.any(Tema.id.in_(ids)))

def _tests_permitidos_ids(db: Session, usuario: Usuario):
    """IDs de plantillas de test accesibles. None = todas (superadmin)."""
    temas = _temas_permitidos_ids(db, usuario)
    if temas is None:
        return None
    if not temas:
        return []
    return [t[0] for t in db.query(TestPlantilla.id).filter(_filtro_tests_de_temas(temas)).all()]


# ==========================================
# CURSOS
# ==========================================
@router.get("/cursos")
def listar_cursos(usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    """El superadmin ve todos los cursos; el admin, solo los suyos."""
    permitidos = cursos_permitidos_ids(usuario)
    query = db.query(Curso)
    if permitidos is not None:
        query = query.filter(Curso.id.in_(permitidos or [-1]))
    return query.order_by(Curso.nombre).all()

@router.post("/cursos")
def crear_curso(datos: CursoIn, _: Usuario = Depends(require_superadmin), db: Session = Depends(get_db)):
    curso = Curso(nombre=datos.nombre.strip(), descripcion=(datos.descripcion or "").strip() or None)
    db.add(curso)
    db.commit()
    db.refresh(curso)
    return curso

@router.put("/cursos/{curso_id}")
def editar_curso(curso_id: int, datos: CursoIn, _: Usuario = Depends(require_superadmin), db: Session = Depends(get_db)):
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    curso.nombre = datos.nombre.strip()
    curso.descripcion = (datos.descripcion or "").strip() or None
    db.commit()
    db.refresh(curso)
    return curso

@router.delete("/cursos/{curso_id}")
def borrar_curso(curso_id: int, _: Usuario = Depends(require_superadmin), db: Session = Depends(get_db)):
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if db.query(Tema).filter(Tema.curso_id == curso_id).first():
        raise HTTPException(status_code=400, detail="No se puede borrar: el curso todavía tiene temas.")
    db.delete(curso)
    db.commit()
    return {"mensaje": "Curso eliminado"}


# ==========================================
# TEMAS
# ==========================================
@router.get("/temas")
def listar_temas(
    curso_id: int = Query(None),
    usuario: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
):
    permitidos = cursos_permitidos_ids(usuario)
    query = db.query(Tema)
    if permitidos is not None:
        query = query.filter(Tema.curso_id.in_(permitidos or [-1]))
    if curso_id:
        verificar_acceso_curso(usuario, curso_id)
        query = query.filter(Tema.curso_id == curso_id)
    return [
        {
            "id": t.id,
            "nombre": t.nombre,
            "bloque": t.bloque,
            "curso_id": t.curso_id,
            "curso": t.curso.nombre if t.curso else None,  # para agrupar en el panel
        }
        for t in query.order_by(Tema.id).all()
    ]

@router.post("/temas")
def crear_tema(datos: TemaIn, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    verificar_acceso_curso(usuario, datos.curso_id)
    tema = Tema(
        nombre=datos.nombre.strip(),
        bloque=(datos.bloque or "").strip() or None,
        curso_id=datos.curso_id,
    )
    db.add(tema)
    db.commit()
    db.refresh(tema)
    return tema

@router.put("/temas/{tema_id}")
def editar_tema(tema_id: int, datos: TemaIn, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    tema = _tema_o_404(db, tema_id)
    verificar_acceso_curso(usuario, tema.curso_id)      # curso actual
    verificar_acceso_curso(usuario, datos.curso_id)     # curso destino
    tema.nombre = datos.nombre.strip()
    tema.bloque = (datos.bloque or "").strip() or None
    tema.curso_id = datos.curso_id
    db.commit()
    db.refresh(tema)
    return tema

@router.delete("/temas/{tema_id}")
def borrar_tema(tema_id: int, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    tema = _tema_o_404(db, tema_id)
    verificar_acceso_curso(usuario, tema.curso_id)
    # Tests multi-tema cuyo tema PRINCIPAL es este: pasa a serlo otro de sus temas
    for test in db.query(TestPlantilla).filter(TestPlantilla.tema_id == tema.id).all():
        otros = [t.id for t in test.temas if t.id != tema.id]
        if otros:
            test.tema_id = otros[0]
    # Sus preguntas (y lo que los alumnos respondieron en ellas) se borran con él
    ids_preguntas = [p[0] for p in db.query(Pregunta.id).filter(Pregunta.tema_id == tema.id).all()]
    _borrar_rastro_de_preguntas(db, ids_preguntas)
    if ids_preguntas:
        db.query(Pregunta).filter(Pregunta.id.in_(ids_preguntas)).delete(synchronize_session=False)
    db.delete(tema)
    db.commit()
    return {"mensaje": "Tema eliminado"}


# ==========================================
# MATERIAL DEL TEMA (PDFs)
# ==========================================
# El PDF se guarda en la propia base de datos. Neon (free) son 0,5 GB en total,
# así que limitamos el tamaño por archivo.
MAX_PDF_MB = int(os.getenv("MAX_PDF_MB", "10"))

def _material_resumen(m: MaterialTema) -> dict:
    return {
        "id": m.id,
        "tema_id": m.tema_id,
        "nombre_archivo": m.nombre_archivo,
        "tamano_bytes": m.tamano_bytes,
        "fecha_subida": m.fecha_subida,
    }

@router.get("/temas/{tema_id}/materiales")
def listar_materiales(tema_id: int, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    tema = _tema_o_404(db, tema_id)
    verificar_acceso_curso(usuario, tema.curso_id)
    return [_material_resumen(m) for m in tema.materiales]

@router.post("/temas/{tema_id}/materiales")
async def subir_material(
    tema_id: int,
    archivo: UploadFile = File(...),
    usuario: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
):
    tema = _tema_o_404(db, tema_id)
    verificar_acceso_curso(usuario, tema.curso_id)

    nombre = (archivo.filename or "").strip()
    if not nombre.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se admiten archivos PDF.")

    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(contenido) > MAX_PDF_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"El PDF supera el máximo permitido de {MAX_PDF_MB} MB.")

    material = MaterialTema(
        tema_id=tema_id,
        nombre_archivo=nombre,
        tipo_mime=archivo.content_type or "application/pdf",
        tamano_bytes=len(contenido),
        contenido=contenido,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return _material_resumen(material)

@router.delete("/materiales/{material_id}")
def borrar_material(material_id: int, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    material = db.query(MaterialTema).filter(MaterialTema.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    verificar_acceso_curso(usuario, _tema_o_404(db, material.tema_id).curso_id)
    db.delete(material)
    db.commit()
    return {"mensaje": "Material eliminado"}


# ==========================================
# PLANTILLAS DE TEST (nombre libre y uno o VARIOS temas)
# ==========================================
def _test_dict(test: TestPlantilla, nombres_temas: dict, num_preguntas: int = 0) -> dict:
    ids = test.tema_ids
    return {
        "id": test.id,
        "numero_test": test.numero_test,   # nombre del test (cualquier texto)
        "tema_id": test.tema_id,           # tema principal
        "tema_ids": ids,                   # todos los temas asignados
        "temas": [{"id": i, "nombre": nombres_temas.get(i, f"Tema {i}")} for i in ids],
        "total_preguntas": test.total_preguntas,
        "num_preguntas": num_preguntas,
    }

def _nombres_temas(db: Session) -> dict:
    return {tid: nombre for tid, nombre in db.query(Tema.id, Tema.nombre).all()}

def _validar_nombre_test(db: Session, nombre_crudo, excluir_id=None) -> str:
    nombre = normalizar_nombre_test(nombre_crudo)
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del test no puede estar vacío.")
    q = db.query(TestPlantilla).filter(TestPlantilla.numero_test == nombre)
    if excluir_id is not None:
        q = q.filter(TestPlantilla.id != excluir_id)
    if q.first():
        raise HTTPException(status_code=400, detail=f"Ya existe un test llamado «{nombre}».")
    return nombre

def _ids_pedidos(datos: TestPlantillaIn) -> list:
    """Temas pedidos, sin duplicados y conservando el orden (el primero = principal)."""
    ids = list(datos.tema_ids or [])
    if not ids and datos.tema_id:
        ids = [datos.tema_id]
    vistos, resultado = set(), []
    for i in ids:
        if i not in vistos:
            vistos.add(i)
            resultado.append(int(i))
    return resultado

def _temas_validados(db: Session, usuario: Usuario, ids: list) -> list:
    """Carga los temas y comprueba el acceso del usuario a cada uno."""
    temas = []
    for tid in ids:
        tema = _tema_o_404(db, tid)
        verificar_acceso_curso(usuario, tema.curso_id)
        temas.append(tema)
    return temas

def _puede_ver_test(db: Session, usuario: Usuario, test: TestPlantilla) -> bool:
    permitidos = _temas_permitidos_ids(db, usuario)
    if permitidos is None:
        return True
    ids = test.tema_ids
    # Tests huérfanos (sin temas existentes) solo los gestiona el superadmin
    return any(i in permitidos for i in ids)

@router.get("/tests")
def listar_tests(
    tema_id: int = Query(None),
    usuario: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
):
    query = db.query(TestPlantilla)
    permitidos = _temas_permitidos_ids(db, usuario)
    if permitidos is not None:
        query = query.filter(_filtro_tests_de_temas(permitidos))
    if tema_id:
        verificar_acceso_curso(usuario, _tema_o_404(db, tema_id).curso_id)
        query = query.filter(_filtro_tests_de_temas([tema_id]))
    tests = sorted(query.all(), key=lambda t: clave_orden_natural(t.numero_test))

    conteo = dict(
        db.query(Pregunta.test_plantilla_id, func.count(Pregunta.id))
        .filter(Pregunta.test_plantilla_id.in_([t.id for t in tests] or [-1]))
        .group_by(Pregunta.test_plantilla_id)
        .all()
    )
    nombres = _nombres_temas(db)
    return [_test_dict(t, nombres, conteo.get(t.id, 0)) for t in tests]

@router.post("/tests")
def crear_test(datos: TestPlantillaIn, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    ids = _ids_pedidos(datos)
    if not ids:
        raise HTTPException(status_code=400, detail="Asigna el test al menos a un tema.")
    temas = _temas_validados(db, usuario, ids)
    test = TestPlantilla(
        numero_test=_validar_nombre_test(db, datos.numero_test),
        tema_id=temas[0].id,
        total_preguntas=datos.total_preguntas,
    )
    test.temas = temas
    db.add(test)
    db.commit()
    db.refresh(test)
    return _test_dict(test, _nombres_temas(db))

@router.put("/tests/{test_id}")
def editar_test(test_id: int, datos: TestPlantillaIn, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    test = db.query(TestPlantilla).filter(TestPlantilla.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test no encontrado")
    if not _puede_ver_test(db, usuario, test):
        raise HTTPException(status_code=403, detail="No tienes acceso a este test.")

    pedidos = _ids_pedidos(datos)
    permitidos = _temas_permitidos_ids(db, usuario)
    # Un profesor solo cambia las asignaciones de SUS temas: las de temas de otros
    # cursos (si el test está compartido) se conservan tal cual.
    ajenos = [] if permitidos is None else [i for i in test.tema_ids if i not in permitidos]
    ids = [i for i in pedidos if i not in ajenos] + ajenos
    if not ids:
        raise HTTPException(status_code=400, detail="Asigna el test al menos a un tema.")
    temas_propios = _temas_validados(db, usuario, [i for i in ids if i not in ajenos])
    temas_ajenos = db.query(Tema).filter(Tema.id.in_(ajenos or [-1])).all()
    temas = temas_propios + temas_ajenos
    if not temas:
        raise HTTPException(status_code=400, detail="Asigna el test al menos a un tema.")

    test.numero_test = _validar_nombre_test(db, datos.numero_test, excluir_id=test_id)
    test.temas = temas
    # El tema principal se conserva si sigue asignado; si no, pasa a ser el primero
    if test.tema_id not in [t.id for t in temas]:
        test.tema_id = temas[0].id
    test.total_preguntas = datos.total_preguntas
    db.commit()
    db.refresh(test)
    return _test_dict(test, _nombres_temas(db))

@router.delete("/tests/{test_id}")
def borrar_test(test_id: int, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    test = db.query(TestPlantilla).filter(TestPlantilla.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test no encontrado")
    permitidos = _temas_permitidos_ids(db, usuario)
    if permitidos is not None:
        ids = test.tema_ids
        if not ids or any(i not in permitidos for i in ids):
            raise HTTPException(
                status_code=403,
                detail="Este test está asignado también a temas de otros cursos. Quita tus temas del test en lugar de borrarlo.",
            )
    ids_preguntas = [p[0] for p in db.query(Pregunta.id).filter(Pregunta.test_plantilla_id == test.id).all()]
    _borrar_rastro_de_preguntas(db, ids_preguntas)
    if ids_preguntas:
        db.query(Pregunta).filter(Pregunta.id.in_(ids_preguntas)).delete(synchronize_session=False)
    db.delete(test)
    db.commit()
    return {"mensaje": "Test eliminado"}


# ==========================================
# PREGUNTAS
# ==========================================
def _pregunta_dict(p: Pregunta) -> dict:
    return {
        "id": p.id,
        "enunciado": p.enunciado,
        "opcion_a": p.opcion_a,
        "opcion_b": p.opcion_b,
        "opcion_c": p.opcion_c,
        "opcion_d": p.opcion_d,
        "respuesta_correcta": p.respuesta_correcta,      # código canónico, p. ej. "AC"
        "respuestas_correctas": letras_correctas(p),     # lista, p. ej. ["A", "C"]
        "explicacion": p.explicacion,
        "tema_id": p.tema_id,
        "test_plantilla_id": p.test_plantilla_id,
    }

def _validar_tema_de_pregunta(db: Session, datos: PreguntaIn) -> None:
    """Si la pregunta va dentro de un test, su tema debe ser uno de los del test."""
    if not datos.test_plantilla_id:
        return
    test = db.query(TestPlantilla).filter(TestPlantilla.id == datos.test_plantilla_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test no encontrado")
    if datos.tema_id not in test.tema_ids:
        raise HTTPException(status_code=400, detail="El tema de la pregunta debe ser uno de los temas asignados al test.")

def _validar_respuesta(datos: PreguntaIn) -> str:
    """Normaliza y valida las letras correctas (una o varias)."""
    codigo = normalizar_respuesta(datos.respuesta_correcta)
    if not codigo:
        raise HTTPException(status_code=400, detail="Indica al menos una respuesta correcta (A, B, C o D).")
    return codigo

@router.get("/preguntas")
def listar_preguntas(
    test_plantilla_id: int = Query(None),
    tema_id: int = Query(None),
    usuario: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
):
    query = db.query(Pregunta)
    permitidos = _temas_permitidos_ids(db, usuario)
    if permitidos is not None:
        query = query.filter(Pregunta.tema_id.in_(permitidos or [-1]))
    if test_plantilla_id:
        query = query.filter(Pregunta.test_plantilla_id == test_plantilla_id)
    if tema_id:
        verificar_acceso_curso(usuario, _tema_o_404(db, tema_id).curso_id)
        query = query.filter(Pregunta.tema_id == tema_id)
    return [_pregunta_dict(p) for p in query.order_by(Pregunta.id).all()]

@router.post("/preguntas")
def crear_pregunta(datos: PreguntaIn, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    verificar_acceso_curso(usuario, _tema_o_404(db, datos.tema_id).curso_id)
    _validar_tema_de_pregunta(db, datos)
    pregunta = Pregunta(
        enunciado=datos.enunciado.strip(),
        opcion_a=datos.opcion_a.strip(),
        opcion_b=datos.opcion_b.strip(),
        opcion_c=datos.opcion_c.strip(),
        opcion_d=datos.opcion_d.strip(),
        respuesta_correcta=_validar_respuesta(datos),
        explicacion=(datos.explicacion or "").strip() or None,
        tema_id=datos.tema_id,
        test_plantilla_id=datos.test_plantilla_id,
    )
    db.add(pregunta)
    db.commit()
    db.refresh(pregunta)
    return _pregunta_dict(pregunta)

@router.put("/preguntas/{pregunta_id}")
def editar_pregunta(pregunta_id: int, datos: PreguntaIn, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    pregunta = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    verificar_acceso_curso(usuario, _curso_id_de_tema(db, pregunta.tema_id))
    verificar_acceso_curso(usuario, _tema_o_404(db, datos.tema_id).curso_id)
    _validar_tema_de_pregunta(db, datos)
    pregunta.enunciado = datos.enunciado.strip()
    pregunta.opcion_a = datos.opcion_a.strip()
    pregunta.opcion_b = datos.opcion_b.strip()
    pregunta.opcion_c = datos.opcion_c.strip()
    pregunta.opcion_d = datos.opcion_d.strip()
    pregunta.respuesta_correcta = _validar_respuesta(datos)
    pregunta.explicacion = (datos.explicacion or "").strip() or None
    pregunta.tema_id = datos.tema_id
    pregunta.test_plantilla_id = datos.test_plantilla_id
    db.commit()
    db.refresh(pregunta)
    return _pregunta_dict(pregunta)

@router.delete("/preguntas/{pregunta_id}")
def borrar_pregunta(pregunta_id: int, usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    pregunta = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    verificar_acceso_curso(usuario, _curso_id_de_tema(db, pregunta.tema_id))
    _borrar_rastro_de_preguntas(db, [pregunta.id])
    db.delete(pregunta)
    db.commit()
    return {"mensaje": "Pregunta eliminada"}


# ==========================================
# IMPORTACIÓN MASIVA (CSV / XLSX)
# ==========================================
@router.get("/preguntas/plantilla")
def plantilla_importar_preguntas(usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    """Excel de ejemplo para importar preguntas: hoja «Preguntas» (la que se rellena),
    hoja «Temas» con los ID de los temas a los que tienes acceso e «Instrucciones»."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    permitidos = _temas_permitidos_ids(db, usuario)
    q = db.query(Tema)
    if permitidos is not None:
        q = q.filter(Tema.id.in_(permitidos or [-1]))
    temas = q.order_by(Tema.curso_id, Tema.bloque, Tema.id).all()
    cursos = {c.id: c.nombre for c in db.query(Curso).all()}

    negrita = Font(bold=True, color="FFFFFF")
    naranja = PatternFill("solid", fgColor="F97316")

    def cabecera(ws, columnas, anchos):
        ws.append(columnas)
        for celda in ws[1]:
            celda.font, celda.fill = negrita, naranja
        for letra, ancho in zip("ABCDEFGHI", anchos):
            ws.column_dimensions[letra].width = ancho
        ws.freeze_panes = "A2"

    wb = Workbook()
    ws = wb.active
    ws.title = HOJA_PREGUNTAS
    cabecera(ws, ENCABEZADOS, [9, 14, 50, 26, 26, 26, 26, 19, 40])
    ejemplo = temas[0].id if temas else 1
    ws.append([ejemplo, "001", "¿Cuál es la norma suprema del ordenamiento jurídico español?",
               "La Constitución", "Las leyes orgánicas", "Los reglamentos", "Los tratados",
               "A", "Art. 9.1 CE: los ciudadanos y los poderes públicos están sujetos a la Constitución."])
    ws.append([ejemplo, "001", "¿Qué dos poderes del Estado se citan en esta pregunta de ejemplo con varias correctas?",
               "El legislativo", "El municipal", "El judicial", "", "AC",
               "Ejemplo de pregunta con varias respuestas correctas (se escriben juntas: AC)."])

    wt = wb.create_sheet("Temas")
    cabecera(wt, ["tema_id", "Tema", "Bloque", "Curso"], [9, 45, 30, 30])
    for t in temas:
        wt.append([t.id, t.nombre, t.bloque or "", cursos.get(t.curso_id, "")])

    wi = wb.create_sheet("Instrucciones")
    wi.column_dimensions["A"].width = 110
    for linea in [
        "Cómo importar preguntas",
        "1. Rellena la hoja «Preguntas»: una fila por pregunta (puedes borrar las dos filas de ejemplo).",
        "2. tema_id: el número de la hoja «Temas». numero_test: el nombre del test (si no existe, se crea).",
        "3. opcion_a y opcion_b son obligatorias; opcion_c y opcion_d, opcionales.",
        "4. respuesta_correcta: A, B, C o D. Si hay varias correctas, escríbelas juntas (p. ej. AC).",
        "5. explicacion: opcional; se muestra al corregir y en el repaso.",
        "6. Las filas con algún error no se importan y se indica el número de fila y el motivo.",
        "7. Si una pregunta ya existe en ese test (mismo enunciado), se omite: puedes reimportar el archivo sin duplicar.",
        "8. Guarda como Excel (.xlsx) o como CSV (con «,» o «;»).",
    ]:
        wi.append([linea])
    wi["A1"].font = Font(bold=True, size=13)

    salida = io.BytesIO()
    wb.save(salida)
    salida.seek(0)
    return StreamingResponse(
        salida,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plantilla_preguntas.xlsx"'},
    )


@router.post("/preguntas/importar")
async def importar_preguntas(
    archivo: UploadFile = File(...),
    usuario: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db),
):
    """Importa preguntas desde Excel o CSV (ver `services/importar_preguntas.py`).
    - Las filas con errores (p. ej. sin respuesta correcta válida) NO se importan y
      se devuelven con su número de fila y el motivo.
    - Las preguntas que ya existen en ese test (mismo enunciado) se omiten, así que
      reimportar el mismo archivo no duplica nada.
    Solo se aceptan filas de temas a los que tengas acceso."""
    contenido = await archivo.read()
    try:
        filas = leer_filas(archivo.filename, contenido)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo. Comprueba que es un Excel (.xlsx) o un CSV válido.")
    filas = [f for f in filas if any(_texto(v) for v in f.values())]
    if not filas:
        raise HTTPException(status_code=400, detail="El archivo no tiene preguntas.")
    try:
        columnas = detectar_columnas(filas[0].keys())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    creadas, omitidas, errores = 0, 0, []
    enunciados_por_test = {}   # test -> enunciados ya existentes (para no duplicar)
    for i, fila in enumerate(filas, start=2):  # fila 1 = cabecera
        try:
            datos = interpretar_fila(fila, columnas)
            tema = db.query(Tema).filter(Tema.id == datos["tema_id"]).first()
            if not tema:
                raise ValueError(f"el tema {datos['tema_id']} no existe (mira la hoja «Temas» de la plantilla)")
            verificar_acceso_curso(usuario, tema.curso_id)

            # El nombre del test admite cualquier texto ("001", "Simulacro 2"...)
            numero_test = normalizar_nombre_test(datos["numero_test"])
            plantilla = db.query(TestPlantilla).filter(TestPlantilla.numero_test == numero_test).first()
            if not plantilla:
                plantilla = TestPlantilla(tema_id=tema.id, numero_test=numero_test, total_preguntas=10)
                plantilla.temas = [tema]
                db.add(plantilla)
                db.commit()
                db.refresh(plantilla)
            elif tema.id not in plantilla.tema_ids:
                # Mismo test en otro tema: se asigna también a este tema (test multi-tema),
                # siempre que el test ya sea visible para quien importa.
                if not _puede_ver_test(db, usuario, plantilla):
                    raise ValueError(f"ya existe un test llamado «{numero_test}» en otro curso")
                plantilla.temas.append(tema)
                db.commit()

            if plantilla.id not in enunciados_por_test:
                enunciados_por_test[plantilla.id] = {
                    clave_enunciado(e) for (e,) in
                    db.query(Pregunta.enunciado).filter(Pregunta.test_plantilla_id == plantilla.id).all()
                }
            clave = clave_enunciado(datos["enunciado"])
            if clave in enunciados_por_test[plantilla.id]:
                omitidas += 1
                continue

            db.add(Pregunta(
                tema_id=tema.id,
                test_plantilla_id=plantilla.id,
                enunciado=datos["enunciado"],
                opcion_a=datos["opcion_a"],
                opcion_b=datos["opcion_b"],
                opcion_c=datos["opcion_c"],
                opcion_d=datos["opcion_d"],
                respuesta_correcta=datos["respuesta_correcta"],
                explicacion=datos["explicacion"],
            ))
            db.commit()
            enunciados_por_test[plantilla.id].add(clave)
            creadas += 1
        except HTTPException as e:
            db.rollback()
            errores.append(f"Fila {i}: {e.detail}")
        except ValueError as e:
            db.rollback()
            errores.append(f"Fila {i}: {e}")
        except Exception as e:  # error inesperado: se informa y se sigue con el resto
            db.rollback()
            print(f"Error importando la fila {i}: {e!r}")
            errores.append(f"Fila {i}: no se pudo guardar")

    return {"creadas": creadas, "omitidas": omitidas, "errores": errores, "filas": len(filas)}


# ==========================================
# MÉTRICAS (limitadas a los cursos accesibles)
# ==========================================
@router.get("/metricas")
def obtener_metricas(usuario: Usuario = Depends(require_gestor), db: Session = Depends(get_db)):
    hace_7d = datetime.utcnow() - timedelta(days=7)
    hoy = datetime.utcnow().date()

    temas_ok = _temas_permitidos_ids(db, usuario)
    tests_ok = _tests_permitidos_ids(db, usuario)
    cursos_ok = cursos_permitidos_ids(usuario)

    # --- Usuarios ---
    if es_superadmin(usuario):
        usuarios_total = db.query(func.count(Usuario.id)).scalar() or 0
        alumnos_total = db.query(func.count(Usuario.id)).filter(Usuario.rol == "estudiante").scalar() or 0
    else:
        # Solo los estudiantes matriculados en los cursos del profesor
        alumnos_total = (
            db.query(func.count(func.distinct(Usuario.id)))
            .join(Usuario.cursos)
            .filter(Curso.id.in_(cursos_ok or [-1]), Usuario.rol == "estudiante")
            .scalar() or 0
        )
        usuarios_total = alumnos_total

    # --- Alumnos activos (7d) ---
    q_activos = db.query(func.count(func.distinct(TestIntento.alumno_id))).filter(TestIntento.fecha_intento >= hace_7d)
    if tests_ok is not None:
        q_activos = q_activos.filter(TestIntento.test_plantilla_id.in_(tests_ok or [-1]))
    alumnos_activos_7d = q_activos.scalar() or 0

    # --- Progreso medio por tema ---
    q_prog = (
        db.query(
            Tema.id,
            Tema.nombre,
            func.count(RespuestaAlumno.id),
            func.sum(cast(RespuestaAlumno.es_correcta, Integer)),
        )
        .join(Pregunta, Pregunta.tema_id == Tema.id)
        .join(RespuestaAlumno, RespuestaAlumno.pregunta_id == Pregunta.id)
    )
    if temas_ok is not None:
        q_prog = q_prog.filter(Tema.id.in_(temas_ok or [-1]))
    progreso_por_tema = []
    for tema_id, nombre, total, correctas in q_prog.group_by(Tema.id, Tema.nombre).all():
        total = total or 0
        correctas = correctas or 0
        progreso_por_tema.append({
            "tema_id": tema_id,
            "nombre": nombre,
            "respuestas": total,
            "porcentaje": round((correctas / total) * 100) if total else 0,
        })

    # --- Preguntas más falladas ---
    q_fallos = db.query(RegistroFallo.pregunta_id, func.count(RegistroFallo.id).label("veces"))
    if temas_ok is not None:
        preguntas_ok = [p[0] for p in db.query(Pregunta.id).filter(Pregunta.tema_id.in_(temas_ok or [-1])).all()]
        q_fallos = q_fallos.filter(RegistroFallo.pregunta_id.in_(preguntas_ok or [-1]))
    preguntas_mas_falladas = []
    for pregunta_id, veces in q_fallos.group_by(RegistroFallo.pregunta_id).order_by(func.count(RegistroFallo.id).desc()).limit(10).all():
        p = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
        preguntas_mas_falladas.append({
            "pregunta_id": pregunta_id,
            "enunciado": p.enunciado if p else "(pregunta eliminada)",
            "veces_fallada": veces,
        })

    # --- Uso de IA (solo lo ve el superadmin: es un coste global) ---
    if es_superadmin(usuario):
        ia = {
            "total": db.query(func.count(IALlamada.id)).scalar() or 0,
            "ultimos_7d": db.query(func.count(IALlamada.id)).filter(IALlamada.fecha >= hace_7d).scalar() or 0,
            "hoy": db.query(func.count(IALlamada.id)).filter(func.date(IALlamada.fecha) == hoy).scalar() or 0,
            "tokens_totales": db.query(func.coalesce(func.sum(IALlamada.tokens_totales), 0)).scalar() or 0,
        }
    else:
        ia = None

    return {
        "usuarios_total": usuarios_total,
        "alumnos_total": alumnos_total,
        "alumnos_activos_7d": alumnos_activos_7d,
        "progreso_por_tema": progreso_por_tema,
        "preguntas_mas_falladas": preguntas_mas_falladas,
        "ia": ia,
    }


# (El ranking ya no se guarda aparte: se calcula a partir de los intentos de los
#  tests del banco, ver routers/ranking.py. Por eso no hay herramientas de limpieza.)


# ==========================================
# USUARIOS, ROLES Y CURSOS (solo superadmin)
# ==========================================
@router.get("/usuarios")
def listar_usuarios(_: Usuario = Depends(require_superadmin), db: Session = Depends(get_db)):
    return [
        {
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "rol": u.rol,
            "gestionado_access": bool(u.gestionado_access),
            "cursos": [{"id": c.id, "nombre": c.nombre} for c in u.cursos],
        }
        for u in db.query(Usuario).order_by(Usuario.id).all()
    ]

@router.put("/usuarios/{usuario_id}/rol")
def cambiar_rol(
    usuario_id: int,
    datos: RolUpdate,
    admin: Usuario = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    if datos.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Rol no válido. Usa uno de: {', '.join(ROLES_VALIDOS)}")
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.id == admin.id and datos.rol != "superadmin":
        raise HTTPException(status_code=400, detail="No puedes quitarte a ti mismo el rol de superadministrador.")
    usuario.rol = datos.rol
    db.commit()
    return {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol}

@router.put("/usuarios/{usuario_id}/cursos")
def asignar_cursos(
    usuario_id: int,
    datos: CursosUsuarioUpdate,
    _: Usuario = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Asigna los cursos de un usuario: los que gestiona (admin) o en los que
    está matriculado (estudiante)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    cursos = db.query(Curso).filter(Curso.id.in_(datos.curso_ids or [-1])).all()
    if len(cursos) != len(set(datos.curso_ids or [])):
        raise HTTPException(status_code=400, detail="Algún curso indicado no existe.")
    usuario.cursos = cursos
    db.commit()
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "cursos": [{"id": c.id, "nombre": c.nombre} for c in usuario.cursos],
    }
