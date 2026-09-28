import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import SessionLocal, Pregunta, TestPlantilla, Tema
from services.tests_util import normalizar_nombre_test

def inyectar_desde_excel(archivo_excel="preguntas.xlsx"):
    if not os.path.exists(archivo_excel):
        print(f"❌ ERROR: No encuentro '{archivo_excel}'.")
        return

    print("📊 Leyendo tu archivo Excel...")
    try:
        df = pd.read_excel(archivo_excel)
        df['explicacion'] = df['explicacion'].fillna("Consulta el temario para más detalle.")
    except Exception as e:
        print(f"❌ Error al abrir el Excel: {e}")
        return

    db: Session = SessionLocal()
    
    try:
        db.execute(text("ALTER TABLE preguntas ADD COLUMN IF NOT EXISTS test_plantilla_id INTEGER REFERENCES test_plantillas(id) ON DELETE CASCADE;"))
        db.commit()

        print("🧹 Borrando SÓLO las preguntas antiguas (Mantenemos las notas de los alumnos)...")
        db.execute(text("TRUNCATE TABLE preguntas CASCADE"))
        db.commit()

        print(f"⏳ Vinculando {len(df)} preguntas a sus respectivos Tests...")
        
        for index, fila in df.iterrows():
            t_id = int(fila['tema_id'])
            
            # Nombre del test: admite cualquier texto ("Simulacro 2"); si es un número
            # puro (ej: 1) se mantiene el formato histórico con ceros ("001").
            n_test = normalizar_nombre_test(fila['numero_test'])

            # 1. Buscamos si ya existe ese Test (el nombre es único)
            plantilla = db.query(TestPlantilla).filter(TestPlantilla.numero_test == n_test).first()
            tema = db.query(Tema).filter(Tema.id == t_id).first()

            if not plantilla:
                plantilla = TestPlantilla(tema_id=t_id, numero_test=n_test)
                if tema:
                    plantilla.temas = [tema]
                db.add(plantilla)
                db.commit()
                db.refresh(plantilla)
            elif tema and t_id not in plantilla.tema_ids:
                plantilla.temas.append(tema)  # mismo test asignado a varios temas
                db.commit()

            # 2. Guardamos la pregunta
            pregunta = Pregunta(
                tema_id=t_id,
                test_plantilla_id=plantilla.id,
                enunciado=str(fila['enunciado']).strip(),
                opcion_a=str(fila['opcion_a']).strip(),
                opcion_b=str(fila['opcion_b']).strip(),
                opcion_c=str(fila['opcion_c']).strip(),
                opcion_d=str(fila['opcion_d']).strip(),
                respuesta_correcta=str(fila['respuesta_correcta']).strip().upper(),
                explicacion=str(fila['explicacion']).strip()
            )
            db.add(pregunta)

        db.commit()
        print("✅ ¡ÉXITO! Base de datos sincronizada perfectamente con tu Excel.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al guardar en la base de datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inyectar_desde_excel()