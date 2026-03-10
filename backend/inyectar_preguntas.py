import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import SessionLocal, Pregunta

def inyectar_desde_excel(archivo_excel="preguntas.xlsx"):
    # 1. Comprobamos si el Excel existe donde debería
    if not os.path.exists(archivo_excel):
        print(f"❌ ERROR: No encuentro el archivo '{archivo_excel}'.")
        print("Asegúrate de haberlo guardado dentro de la carpeta 'backend'.")
        return

    print("📊 Leyendo tu archivo Excel...")
    try:
        # 2. Pandas lee el Excel entero de un plumazo
        df = pd.read_excel(archivo_excel)
        
        # Por si dejas alguna explicación en blanco, le ponemos un texto por defecto
        df['explicacion'] = df['explicacion'].fillna("Consulta el temario para más detalle.")
        
    except Exception as e:
        print(f"❌ Error al abrir el Excel (¿está abierto en otro programa?): {e}")
        return

    db: Session = SessionLocal()
    
    try:
        print("🧹 Haciendo limpieza total en la base de datos (TRUNCATE CASCADE)...")
        db.execute(text("TRUNCATE TABLE preguntas CASCADE"))
        db.commit()

        print(f"⏳ Fabricando {len(df)} preguntas nuevas...")
        
        preguntas_nuevas = []
        # 3. Recorremos fila a fila tu Excel
        for index, fila in df.iterrows():
            pregunta = Pregunta(
                tema_id=int(fila['tema_id']),
                enunciado=str(fila['enunciado']).strip(),
                opcion_a=str(fila['opcion_a']).strip(),
                opcion_b=str(fila['opcion_b']).strip(),
                opcion_c=str(fila['opcion_c']).strip(),
                opcion_d=str(fila['opcion_d']).strip(),
                respuesta_correcta=str(fila['respuesta_correcta']).strip().upper(),
                explicacion=str(fila['explicacion']).strip()
            )
            preguntas_nuevas.append(pregunta)

        # 4. Guardamos todo de golpe
        db.add_all(preguntas_nuevas)
        db.commit()
        print(f"✅ ¡ÉXITO! Se han guardado {len(preguntas_nuevas)} preguntas en la base de datos.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al guardar en la base de datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inyectar_desde_excel()