from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func # <-- AÑADIDO: 'func' para poder hacer order_by(func.random())
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from collections import defaultdict

# <-- AÑADIDO: Importamos el modelo 'Pregunta'
from models import SessionLocal, TestPlantilla, TestIntento, Pregunta 

router = APIRouter(prefix="/api/test", tags=["Progreso de Tests"])

class IntentoRequest(BaseModel):
    alumno_id: int
    test_plantilla_id: int
    fallos: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- NUEVA RUTA: GENERADOR DE TESTS ÚNICOS ---
# --- NUEVA RUTA: GENERADOR DE TESTS EXACTOS DESDE EXCEL ---
# --- NUEVA RUTA: GENERADOR DE TESTS EXACTOS DESDE EXCEL ---
@router.get("/generar")
def generar_test_exacto(test_plantilla_id: int, db: Session = Depends(get_db)):
    """
    Busca SOLAMENTE las preguntas vinculadas a este test específico en el Excel.
    Las desordena para que el alumno no memorice el orden, pero las preguntas son fijas.
    """
    preguntas_db = db.query(Pregunta)\
                     .filter(Pregunta.test_plantilla_id == test_plantilla_id)\
                     .order_by(func.random())\
                     .all()
    
    test_formateado = []
    for p in preguntas_db:
        texto_pregunta = p.pregunta if hasattr(p, 'pregunta') else p.enunciado
        
        # Limpiamos la respuesta del Excel por si has puesto "A.", " a " o el texto entero
        letra_limpia = str(p.respuesta_correcta).strip().lower()[0] # Coge solo la primera letra: "b"
        
        # Nos aseguramos de que sea a, b, c o d
        if letra_limpia not in ['a', 'b', 'c', 'd']:
            letra_limpia = 'a' # Por defecto si hay un error grave en el Excel
            
        texto_respuesta = getattr(p, f"opcion_{letra_limpia}")
        opciones_lista = [p.opcion_a, p.opcion_b, p.opcion_c, p.opcion_d]

        test_formateado.append({
            "id": p.id,
            "pregunta": texto_pregunta,
            "opciones": opciones_lista, 
            "respuestaCorrecta": texto_respuesta, 
            "explicacion": getattr(p, 'explicacion', "Consulta el temario para más detalle.")
        })
        
    return test_formateado
# --- RUTAS DE PROGRESO Y REGISTRO ---
@router.get("/listado-progreso")
def obtener_listado_tests_con_progreso(alumno_id: int, tema_id: Optional[int] = None, db: Session = Depends(get_db)):
    # 1. PRIMER VIAJE: Obtenemos los tests correspondientes
    query_tests = db.query(TestPlantilla)
    if tema_id:
        query_tests = query_tests.filter(TestPlantilla.tema_id == tema_id)
    tests = query_tests.order_by(TestPlantilla.numero_test).all()
    
    # Si no hay tests, cortamos rápido
    if not tests:
        return []

    # 2. SEGUNDO VIAJE: Pedimos de GOLPE todos los intentos del alumno para estos tests
    test_ids = [t.id for t in tests]
    intentos_totales = db.query(TestIntento).filter(
        TestIntento.alumno_id == alumno_id,
        TestIntento.test_plantilla_id.in_(test_ids)
    ).all()
    
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
            "numero_test": test.numero_test,
            "fallos_ultimo": fallos,
            "realizado_veces": total_realizado,
            "ultimo_fecha": fecha
        })
        
    return listado_final

@router.post("/registrar-intento")
def registrar_intento_test(datos: IntentoRequest, db: Session = Depends(get_db)):
    nuevo_intento = TestIntento(
        alumno_id=datos.alumno_id,
        test_plantilla_id=datos.test_plantilla_id,
        fallos_ultimo=datos.fallos,
        fecha_intento=datetime.utcnow()
    )
    db.add(nuevo_intento)
    db.commit()
    return {"mensaje": "Intento registrado correctamente en el historial"}