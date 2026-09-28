from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from collections import defaultdict

from models import get_db, TestPlantilla, TestIntento, Pregunta, Usuario, Tema
from routers.auth import get_current_user
from routers.temas import _tema_accesible
from services.preguntas import texto_opcion_correcta, textos_correctos
from services.tests_util import clave_orden_natural

router = APIRouter(prefix="/api/test", tags=["Progreso de Tests"])

MODOS_VALIDOS = ("practica", "examen")
MAX_PREGUNTAS_PERSONALIZADO = 200

class IntentoRequest(BaseModel):
    test_plantilla_id: Optional[int] = None   # None en tests personalizados
    fallos: int
    total_preguntas: Optional[int] = None
    modo: Optional[str] = None                # "practica" | "examen"
    personalizado: bool = False

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


@router.post("/registrar-intento")
def registrar_intento_test(datos: IntentoRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if datos.test_plantilla_id is None and not datos.personalizado:
        raise HTTPException(status_code=400, detail="Falta el test del intento.")
    modo = datos.modo if datos.modo in MODOS_VALIDOS else None
    total = datos.total_preguntas if datos.total_preguntas and datos.total_preguntas > 0 else None
    fallos = max(0, datos.fallos)
    if total is not None:
        fallos = min(fallos, total)
    nuevo_intento = TestIntento(
        alumno_id=usuario.id,
        test_plantilla_id=datos.test_plantilla_id,
        fallos_ultimo=fallos,
        total_preguntas=total,
        modo=modo,
        personalizado=bool(datos.personalizado),
        fecha_intento=datetime.utcnow()
    )
    db.add(nuevo_intento)
    db.commit()
    return {"mensaje": "Intento registrado correctamente en el historial"}