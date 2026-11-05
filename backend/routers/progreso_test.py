from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from collections import defaultdict

from models import get_db, TestPlantilla, TestIntento, Pregunta, Usuario, Tema, RespuestaAlumno, RegistroFallo, Puntuacion
from routers.auth import get_current_user, es_superadmin
from routers.temas import _tema_accesible
from services.preguntas import texto_opcion_correcta, textos_correctos, letras_correctas, LETRAS_OPCION as LETRAS
from services.tests_util import clave_orden_natural

router = APIRouter(prefix="/api/test", tags=["Progreso de Tests"])

MODOS_VALIDOS = ("practica", "examen")
MAX_PREGUNTAS_PERSONALIZADO = 200
MAX_RESPUESTAS_ENTREGA = 1000   # tope de seguridad por entrega

class PersonalizadoRequest(BaseModel):
    tema_ids: List[int] = Field(..., min_length=1)
    num_preguntas: int = Field(..., ge=1, le=MAX_PREGUNTAS_PERSONALIZADO)


def _formatear_pregunta(p: Pregunta) -> dict:
    """Formato común de una pregunta para el test del alumno."""
    correctas = textos_correctos(p)  # lista (una o varias)
    return {
        "id": p.id,
        "tema_id": p.tema_id,
        "pregunta": p.enunciado,
        "opciones": [p.opcion_a, p.opcion_b, p.opcion_c, p.opcion_d],
        "respuestaCorrecta": texto_opcion_correcta(p),   # compatibilidad (la primera)
        "respuestasCorrectas": correctas,                 # todas las correctas
        "multiple": len(correctas) > 1,
        "explicacion": p.explicacion or "Consulta el temario para más detalle.",
    }

# --- RUTA: GENERADOR DE TESTS EXACTOS DESDE EXCEL ---
@router.get("/generar")
def generar_test_exacto(test_plantilla_id: int, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Busca SOLAMENTE las preguntas vinculadas a este test específico en el Excel.
    Las desordena para que el alumno no memorice el orden, pero las preguntas son fijas.
    """
    preguntas_db = db.query(Pregunta)\
                     .filter(Pregunta.test_plantilla_id == test_plantilla_id)\
                     .order_by(func.random())\
                     .all()
    
    return [_formatear_pregunta(p) for p in preguntas_db]


# --- RUTA: "PERSONALIZA TU TEST" ---
@router.post("/personalizado")
def generar_test_personalizado(datos: PersonalizadoRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Test configurado por el alumno: N preguntas al azar de los temas elegidos.
    Solo se aceptan temas a los que el alumno tiene acceso."""
    tema_ids = list(dict.fromkeys(datos.tema_ids))
    for tid in tema_ids:
        _tema_accesible(db, usuario, tid)  # 404/403 si no existe o no es suyo

    base = db.query(Pregunta).filter(Pregunta.tema_id.in_(tema_ids))
    disponibles = base.count()
    if disponibles == 0:
        raise HTTPException(status_code=400, detail="Los temas elegidos todavía no tienen preguntas.")
    preguntas_db = base.order_by(func.random()).limit(datos.num_preguntas).all()
    return {
        "disponibles": disponibles,
        "preguntas": [_formatear_pregunta(p) for p in preguntas_db],
    }


# --- RUTAS DE PROGRESO Y REGISTRO ---
@router.get("/listado-progreso")
def obtener_listado_tests_con_progreso(tema_id: Optional[int] = None, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. PRIMER VIAJE: Obtenemos los tests correspondientes. Un test puede estar
    # asignado a VARIOS temas: aparece en el banco de cada uno de ellos.
    query_tests = db.query(TestPlantilla)
    if tema_id:
        _tema_accesible(db, usuario, tema_id)
        query_tests = query_tests.filter(or_(
            TestPlantilla.tema_id == tema_id,
            TestPlantilla.temas.any(Tema.id == tema_id),
        ))
    tests = sorted(query_tests.all(), key=lambda t: clave_orden_natural(t.numero_test))

    # Si no hay tests, cortamos rápido
    if not tests:
        return []

    # 2. SEGUNDO VIAJE: Pedimos de GOLPE todos los intentos del alumno para estos tests
    test_ids = [t.id for t in tests]
    intentos_totales = db.query(TestIntento).filter(
        TestIntento.alumno_id == usuario.id,
        TestIntento.test_plantilla_id.in_(test_ids)
    ).all()
    
    conteo_preguntas = dict(
        db.query(Pregunta.test_plantilla_id, func.count(Pregunta.id))
        .filter(Pregunta.test_plantilla_id.in_(test_ids))
        .group_by(Pregunta.test_plantilla_id)
        .all()
    )

    # 3. PROCESAMIENTO EN MEMORIA (Tarda 0.001 segundos)
    # Agrupamos los intentos en un diccionario usando el ID del test como llave
    diccionario_intentos = defaultdict(list)
    for intento in intentos_totales:
        diccionario_intentos[intento.test_plantilla_id].append(intento)
        
    # Construimos la lista final cruzando los datos
    listado_final = []
    for test in tests:
        mis_intentos = diccionario_intentos[test.id]
        total_realizado = len(mis_intentos)
        
        if total_realizado > 0:
            # Ordenamos la lista en memoria de más reciente a más antiguo
            mis_intentos.sort(key=lambda x: x.fecha_intento, reverse=True)
            ultimo = mis_intentos[0]
            
            fallos = ultimo.fallos_ultimo
            fecha = ultimo.fecha_intento
        else:
            fallos = None
            fecha = None
            
        listado_final.append({
            "test_id": test.id,
            "numero_test": test.numero_test,   # nombre del test (cualquier texto)
            "num_preguntas": conteo_preguntas.get(test.id, 0),
            "fallos_ultimo": fallos,
            "realizado_veces": total_realizado,
            "ultimo_fecha": fecha
        })
        
    return listado_final

@router.get("/evolucion")
def evolucion_intentos(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Evolución de resultados del alumno, un punto por intento (en orden cronológico).
    Cada punto lleva el % de aciertos, para pintar una gráfica dinámica en el Dashboard."""
    intentos = (
        db.query(TestIntento)
        .filter(TestIntento.alumno_id == usuario.id)
        .order_by(TestIntento.fecha_intento)
        .all()
    )
    if not intentos:
        return []

    # Total de preguntas por plantilla (para convertir fallos -> % de aciertos)
    ids = list({i.test_plantilla_id for i in intentos if i.test_plantilla_id is not None})
    plantillas = {
        p.id: p for p in db.query(TestPlantilla).filter(TestPlantilla.id.in_(ids)).all()
    }

    resultado = []
    for n, i in enumerate(intentos, start=1):
        plantilla = plantillas.get(i.test_plantilla_id)
        # Preferimos el nº real de preguntas del intento (tests nuevos y personalizados)
        total = i.total_preguntas or (plantilla.total_preguntas if plantilla and plantilla.total_preguntas else 10)
        fallos = i.fallos_ultimo if i.fallos_ultimo is not None else 0
        aciertos = max(0, total - fallos)
        resultado.append({
            "intento": n,
            "fecha": i.fecha_intento,
            "numero_test": plantilla.numero_test if plantilla else ("Personalizado" if i.personalizado else None),
            "modo": i.modo,
            "aciertos": aciertos,
            "total": total,
            "porcentaje": round(aciertos / total * 100) if total else 0,
        })
    return resultado


# --- RUTA: ENTREGA DE UN TEST (corrección en el servidor) ---
class RespuestaEntrega(BaseModel):
    pregunta_id: int
    seleccion: List[str] = []   # letras marcadas ("A".."D"); vacía = en blanco


class EntregaRequest(BaseModel):
    test_plantilla_id: Optional[int] = None   # None en tests personalizados
    personalizado: bool = False
    modo: Optional[str] = None                # "practica" | "examen"
    respuestas: List[RespuestaEntrega] = Field(..., min_length=1, max_length=MAX_RESPUESTAS_ENTREGA)


def _puede_ver_tema(usuario: Usuario, tema: Optional[Tema]) -> bool:
    if es_superadmin(usuario):
        return True
    if tema is None:
        return False
    return tema.curso_id is None or tema.curso_id in [c.id for c in usuario.cursos]


def _preguntas_de_la_entrega(datos: EntregaRequest, usuario: Usuario, db: Session) -> List[Pregunta]:
    """Preguntas que se corrigen, comprobando que el alumno tiene acceso a ellas."""
    if datos.test_plantilla_id is not None:
        plantilla = db.query(TestPlantilla).filter(TestPlantilla.id == datos.test_plantilla_id).first()
        if not plantilla:
            raise HTTPException(status_code=404, detail="Este test ya no existe.")
        temas = db.query(Tema).filter(Tema.id.in_(plantilla.tema_ids or [-1])).all()
        if not any(_puede_ver_tema(usuario, t) for t in temas) and not es_superadmin(usuario):
            raise HTTPException(status_code=403, detail="No tienes acceso a este test.")
        # Se corrigen TODAS las preguntas del test: las que no lleguen cuentan en blanco
        preguntas = db.query(Pregunta).filter(Pregunta.test_plantilla_id == plantilla.id).all()
        ids_test = {p.id for p in preguntas}
        if any(r.pregunta_id not in ids_test for r in datos.respuestas):
            raise HTTPException(status_code=400, detail="Hay respuestas que no pertenecen a este test.")
        return preguntas

    if not datos.personalizado:
        raise HTTPException(status_code=400, detail="Falta el test que se entrega.")
    ids = list(dict.fromkeys(r.pregunta_id for r in datos.respuestas))
    preguntas = db.query(Pregunta).filter(Pregunta.id.in_(ids)).all()
    if len(preguntas) != len(ids):
        raise HTTPException(status_code=400, detail="Alguna pregunta del test ya no existe. Genera un test nuevo.")
    temas = {t.id: t for t in db.query(Tema).filter(Tema.id.in_({p.tema_id for p in preguntas})).all()}
    if not all(_puede_ver_tema(usuario, temas.get(p.tema_id)) for p in preguntas):
        raise HTTPException(status_code=403, detail="No tienes acceso a alguna de las preguntas.")
    return preguntas


@router.post("/entregar")
def entregar_test(datos: EntregaRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Corrige el test EN EL SERVIDOR a partir de las opciones marcadas y guarda, en
    una sola transacción: el intento, las respuestas (progreso por tema), los
    fallos (mazo de repaso, sin duplicar los pendientes) y los puntos del ranking.
    Si algo falla no se guarda nada, y el alumno puede reintentar."""
    preguntas = _preguntas_de_la_entrega(datos, usuario, db)
    if not preguntas:
        raise HTTPException(status_code=400, detail="Este test no tiene preguntas.")

    marcadas = {r.pregunta_id: r.seleccion for r in datos.respuestas}
    pendientes = {
        f.pregunta_id for f in db.query(RegistroFallo).filter(
            RegistroFallo.alumno_id == usuario.id,
            RegistroFallo.repasada == False,  # noqa: E712
            RegistroFallo.pregunta_id.in_([p.id for p in preguntas]),
        ).all()
    }

    aciertos = incorrectas = en_blanco = 0
    correccion = {}
    try:
        for p in preguntas:
            seleccion = {str(l).strip().upper() for l in marcadas.get(p.id, []) if str(l).strip().upper() in LETRAS}
            if not seleccion:
                en_blanco += 1
                ok = False
            else:
                ok = seleccion == set(letras_correctas(p))
                if ok:
                    aciertos += 1
                else:
                    incorrectas += 1
            correccion[p.id] = ok
            db.add(RespuestaAlumno(alumno_id=usuario.id, pregunta_id=p.id, es_correcta=ok))
            if not ok and p.id not in pendientes:
                db.add(RegistroFallo(alumno_id=usuario.id, pregunta_id=p.id, repasada=False))
                pendientes.add(p.id)

        total = len(preguntas)
        db.add(TestIntento(
            alumno_id=usuario.id,
            test_plantilla_id=datos.test_plantilla_id,
            fallos_ultimo=incorrectas + en_blanco,
            total_preguntas=total,
            modo=datos.modo if datos.modo in MODOS_VALIDOS else None,
            personalizado=datos.test_plantilla_id is None,
            fecha_intento=datetime.utcnow(),
        ))

        hoy = datetime.now().strftime("%Y-%m-%d")
        fila = db.query(Puntuacion).filter(Puntuacion.usuario_id == usuario.id).first()
        if fila:
            fila.puntos = (fila.puntos or 0) + aciertos
            fila.alumno_nombre = usuario.nombre
            fila.fecha = hoy
        else:
            db.add(Puntuacion(usuario_id=usuario.id, alumno_nombre=usuario.nombre, puntos=aciertos, fecha=hoy))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "aciertos": aciertos,
        "fallos": incorrectas,
        "en_blanco": en_blanco,
        "total": total,
        "porcentaje": round(aciertos / total * 100) if total else 0,
        "nota": round(aciertos / total * 100) / 10 if total else 0,
        "correccion": correccion,
    }
