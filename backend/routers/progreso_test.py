from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

# IMPORTANTE: Hemos quitado get_db de esta línea y añadido SessionLocal
from models import SessionLocal, TestPlantilla, TestIntento

router = APIRouter(prefix="/api/test", tags=["Progreso de Tests"])

# Creamos la conexión directamente aquí para evitar "importaciones circulares"
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/listado-progreso")
def obtener_listado_tests_con_progreso(alumno_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el listado completo de tests (plantillas) y, para el alumno indicado, 
    calcula de forma agregada el progreso según el formato solicitado.
    """
    
    # 1. Obtenemos todas las plantillas de tests disponibles
    tests = db.query(TestPlantilla).order_by(TestPlantilla.numero_test).all()
    
    listado_final = []
    
    for test in tests:
        # Consulta para este test y este alumno específico
        query_intentos = db.query(TestIntento).filter(
            TestIntento.alumno_id == alumno_id,
            TestIntento.test_plantilla_id == test.id
        )
        
        # A) Total de veces realizado
        total_realizado = query_intentos.count()
        
        # B) Datos del último intento (fecha y fallos)
        ultimo_intento = query_intentos.order_by(desc(TestIntento.fecha_intento)).first()
        
        datos_test = {
            "test_id": test.id,
            "numero_test": test.numero_test,
            # C) Fallos en el último intento (o None si nunca se ha hecho)
            "fallos_ultimo": ultimo_intento.fallos_ultimo if ultimo_intento else None,
            "realizado_veces": total_realizado,
            "ultimo_fecha": ultimo_intento.fecha_intento if ultimo_intento else None
        }
        
        listado_final.append(datos_test)
        
    return listado_final