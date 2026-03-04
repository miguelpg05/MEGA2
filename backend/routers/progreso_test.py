from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from models import SessionLocal, TestPlantilla, TestIntento

router = APIRouter(prefix="/api/test", tags=["Progreso de Tests"])

# Esquema para recibir los datos desde React
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

@router.get("/listado-progreso")
def obtener_listado_tests_con_progreso(alumno_id: int, tema_id: Optional[int] = None, db: Session = Depends(get_db)):
    query_tests = db.query(TestPlantilla)
    if tema_id:
        query_tests = query_tests.filter(TestPlantilla.tema_id == tema_id)
        
    tests = query_tests.order_by(TestPlantilla.numero_test).all()
    
    listado_final = []
    for test in tests:
        query_intentos = db.query(TestIntento).filter(
            TestIntento.alumno_id == alumno_id,
            TestIntento.test_plantilla_id == test.id
        )
        
        total_realizado = query_intentos.count()
        ultimo_intento = query_intentos.order_by(desc(TestIntento.fecha_intento)).first()
        
        listado_final.append({
            "test_id": test.id,
            "numero_test": test.numero_test,
            "fallos_ultimo": ultimo_intento.fallos_ultimo if ultimo_intento else None,
            "realizado_veces": total_realizado,
            "ultimo_fecha": ultimo_intento.fecha_intento if ultimo_intento else None
        })
        
    return listado_final

# --- NUEVA RUTA: PARA GUARDAR EL INTENTO AL TERMINAR EL TEST ---
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