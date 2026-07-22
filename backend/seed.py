"""Carga de datos de demostración (temas, preguntas y plantillas de test).

Antes esto vivía dentro de `@app.on_event("startup")` en `main.py` y se ejecutaba
en CADA arranque del servidor. Ahora es un script independiente e IDEMPOTENTE que
se lanza a mano una sola vez sobre una base de datos ya migrada:

    # 1) Crea el esquema con Alembic
    alembic upgrade head
    # 2) Siembra los datos demo
    python seed.py

Notas:
- `respuesta_correcta` se guarda en el FORMATO CANÓNICO (letra "A"–"D") usando
  `services.preguntas.letra_de_texto`, coherente con la importación desde Excel.
- Ya NO se insertan usuarios ficticios en el ranking (contaminaban el ranking real).
"""

from models import SessionLocal, Curso, Tema, Pregunta, TestPlantilla
from services.preguntas import letra_de_texto


# (enunciado, a, b, c, d, texto_correcto, explicacion)
PREGUNTAS_TEMA_1 = [
    ("Según la Constitución Española, ¿quién sanciona y promulga las leyes?", "El Presidente del Gobierno", "El Rey", "El Presidente del Congreso", "El Tribunal Constitucional", "El Rey", "Artículo 62.a de la CE: Corresponde al Rey sancionar y promulgar las leyes."),
    ("¿Cuál es el valor fundamental del ordenamiento jurídico español según el Art. 1.1 CE?", "La libertad, la justicia, la igualdad y el pluralismo político", "La paz, la justicia y la libertad", "La democracia, la ley y la monarquía", "El estado social, democrático y de derecho", "La libertad, la justicia, la igualdad y el pluralismo político", "Artículo 1.1 CE: España se constituye en un Estado social y democrático de Derecho, que propugna como valores superiores..."),
    ("La soberanía nacional reside en:", "Las Cortes Generales", "El Rey", "El pueblo español", "El Gobierno", "El pueblo español", "Artículo 1.2 CE: La soberanía nacional reside en el pueblo español, del que emanan los poderes del Estado."),
    ("La forma política del Estado español es:", "La República federal", "La Monarquía parlamentaria", "La Monarquía constitucional", "El Estado unitario", "La Monarquía parlamentaria", "Artículo 1.3 CE: La forma política del Estado español es la Monarquía parlamentaria."),
    ("La capital del Estado es:", "La ciudad de Madrid", "La villa de Madrid", "Madrid y sus provincias", "El territorio nacional", "La villa de Madrid", "Artículo 5 CE: La capital del Estado es la villa de Madrid."),
    ("Los españoles son mayores de edad a los:", "16 años", "18 años", "21 años", "19 años", "18 años", "Artículo 12 CE: Los españoles son mayores de edad a los dieciocho años."),
    ("¿Qué idioma es el oficial del Estado?", "El español", "El castellano", "Las lenguas cooficiales", "El castellano y el catalán", "El castellano", "Artículo 3.1 CE: El castellano es la lengua española oficial del Estado."),
    ("La bandera de España está formada por tres franjas horizontales, roja, amarilla y roja, siendo la amarilla:", "De igual anchura que cada una de las rojas", "De doble anchura que cada una de las rojas", "Del triple de anchura que las rojas", "Proporcional al escudo", "De doble anchura que cada una de las rojas", "Artículo 4.1 CE sobre las proporciones de la bandera nacional."),
    ("Los partidos políticos expresan el pluralismo político, concurren a la formación de la voluntad popular y son instrumento fundamental para:", "La participación política", "La defensa del Estado", "El control del Gobierno", "El reparto de escaños", "La participación política", "Artículo 6 CE que define la función de los partidos políticos."),
    ("La misión de las Fuerzas Armadas es:", "Garantizar la soberanía, defender su integridad territorial y el ordenamiento constitucional", "Proteger al Rey y a su familia", "Mantener el orden público interior", "Dirigir la política de defensa", "Garantizar la soberanía, defender su integridad territorial y el ordenamiento constitucional", "Artículo 8.1 CE define la misión exacta de las Fuerzas Armadas."),
    ("¿Qué título de la CE está dedicado a los Derechos y Deberes fundamentales?", "Título Preliminar", "Título I", "Título II", "Título III", "Título I", "La estructura de la CE reserva el Título I para los derechos y deberes fundamentales."),
]

PREGUNTAS_TEMA_2 = [
    ("¿Quién dirige la política interior y exterior, la Administración civil y militar y la defensa del Estado?", "El Rey", "El Congreso de los Diputados", "El Gobierno", "El Presidente del Gobierno", "El Gobierno", "Artículo 97 de la CE: El Gobierno dirige la política interior y exterior..."),
    ("¿Ante quién responde solidariamente el Gobierno en su gestión política?", "Ante el Rey", "Ante el Congreso de los Diputados", "Ante las Cortes Generales", "Ante el Tribunal Supremo", "Ante el Congreso de los Diputados", "Artículo 108 de la CE establece la responsabilidad ante el Congreso."),
    ("El Gobierno se compone de:", "El Presidente, el Rey y los Ministros", "El Presidente, Vicepresidentes (en su caso) y Ministros", "Solo de Ministros y Secretarios de Estado", "Presidente y Tribunal Supremo", "El Presidente, Vicepresidentes (en su caso) y Ministros", "Artículo 98.1 CE detalla la composición del Gobierno."),
    ("¿Quién propone al Rey el nombramiento de los demás miembros del Gobierno?", "El Congreso", "El Senado", "El Presidente del Gobierno", "El Tribunal Constitucional", "El Presidente del Gobierno", "Artículo 100 CE: Los demás miembros del Gobierno serán nombrados y separados por el Rey, a propuesta de su Presidente."),
    ("¿Por qué sala se exigirá la responsabilidad criminal del Presidente y los demás miembros del Gobierno?", "Sala de lo Penal del Tribunal Supremo", "Sala de lo Contencioso del Tribunal Supremo", "Tribunal Constitucional", "Audiencia Nacional", "Sala de lo Penal del Tribunal Supremo", "Artículo 102.1 CE especifica la jurisdicción para el Gobierno."),
    ("El Gobierno cesa tras la celebración de elecciones generales, pérdida de confianza, dimisión o:", "Decisión del Rey", "Fallecimiento de su Presidente", "Acuerdo del Consejo de Ministros", "Enfermedad grave de un Ministro", "Fallecimiento de su Presidente", "Artículo 101.1 CE marca las causas del cese del Gobierno."),
    ("La moción de censura deberá ser adoptada por:", "Mayoría simple del Senado", "Mayoría absoluta del Congreso", "Mayoría simple del Congreso", "Mayoría absoluta de las Cortes", "Mayoría absoluta del Congreso", "Artículo 113.1 CE exige mayoría absoluta para la moción de censura."),
    ("La cuestión de confianza se entenderá otorgada cuando vote a favor de la misma la mayoría:", "Absoluta del Congreso", "Simple de las Cortes", "Simple de los Diputados", "Absoluta del Senado", "Simple de los Diputados", "Artículo 112 CE: La confianza se entenderá otorgada cuando vote a favor la mayoría simple de los Diputados."),
    ("Las disposiciones del Gobierno que contengan legislación delegada recibirán el título de:", "Decretos-leyes", "Decretos Legislativos", "Leyes Orgánicas", "Reglamentos", "Decretos Legislativos", "Artículo 85 CE sobre la delegación legislativa."),
    ("¿En qué casos puede el Gobierno dictar Decretos-leyes?", "En casos de extraordinaria y urgente necesidad", "Cuando se lo ordene el Rey", "Para aprobar Presupuestos", "Para reformar la Constitución", "En casos de extraordinaria y urgente necesidad", "Artículo 86.1 CE habilita el uso de Decretos-leyes solo en esta situación de urgencia."),
]


def _crear_preguntas(db, filas, tema_id):
    for enunciado, a, b, c, d, correcta, exp in filas:
        letra = letra_de_texto(correcta, [a, b, c, d])
        db.add(Pregunta(
            enunciado=enunciado,
            opcion_a=a, opcion_b=b, opcion_c=c, opcion_d=d,
            respuesta_correcta=letra,
            explicacion=exp,
            tema_id=tema_id,
        ))


def sembrar_datos_demo():
    db = SessionLocal()
    try:
        # --- Curso de demostración (el temario cuelga de un curso) ---
        curso = db.query(Curso).filter(Curso.nombre == "Curso de demostración").first()
        if not curso:
            curso = Curso(nombre="Curso de demostración", descripcion="Datos de ejemplo para probar la plataforma")
            db.add(curso)
            db.commit()
            db.refresh(curso)
            print(f"✅ Curso de demostración creado (id={curso.id}).")

        # --- Temas + preguntas (solo si aún no hay temas) ---
        if not db.query(Tema).first():
            print("Inyectando temas y preguntas de demostración...")
            tema1 = Tema(nombre="Tema 1: La Constitución Española", bloque="Derecho Constitucional", curso_id=curso.id)
            tema2 = Tema(nombre="Tema 2: El Gobierno y la Administración", bloque="Derecho Constitucional", curso_id=curso.id)
            db.add_all([tema1, tema2])
            db.commit()
            db.refresh(tema1)
            db.refresh(tema2)

            _crear_preguntas(db, PREGUNTAS_TEMA_1, tema1.id)
            _crear_preguntas(db, PREGUNTAS_TEMA_2, tema2.id)
            db.commit()
            print("✅ Temas y preguntas listos.")
        else:
            print("Ya existen temas; no se re-inyectan preguntas demo.")

        # --- Plantillas de test 001-100 (solo si no hay ninguna) ---
        if not db.query(TestPlantilla).first():
            print("💉 Inyectando plantillas de test (001-100)...")
            plantillas = [
                TestPlantilla(numero_test=str(i).zfill(3), tema_id=1 if i <= 50 else 2, total_preguntas=10)
                for i in range(1, 101)
            ]
            db.add_all(plantillas)
            db.commit()
            print("✅ 100 tests listos en la base de datos.")
        else:
            print("Ya existen plantillas de test; no se re-inyectan.")

    except Exception as e:
        print(f"⚠️ Error en la siembra de datos: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    sembrar_datos_demo()
