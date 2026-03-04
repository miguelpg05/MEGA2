# 1. IMPORTS ESTÁNDAR
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import random # Lo necesitamos para mezclar las preguntas
from google import genai

# 2. TUS MODELOS Y RUTAS LOCALES
from models import SessionLocal, engine, Base, Tema, Pregunta, RegistroFallo, Puntuacion
from routers import progreso

# 3. INICIALIZACIÓN DE LA APP
app = FastAPI(title="API Academia Oposiciones")
# --- AÑADIMOS ESTE BLOQUE NUEVO ---
# Le decimos al backend que acepte conexiones desde cualquier web
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web-mega-flax.vercel.app", # Tu web real en Vercel
        "http://localhost:5173"             # Tu web local para cuando programes
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------
# 4. CONFIGURACIÓN DE CORS (Una sola vez)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*" # Asterisco para evitar cualquier bloqueo en desarrollo
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Importamos los routers
from routers import progreso, auth # <-- Añade 'auth' aquí

# 5. INCLUSIÓN DE RUTAS EXTERNAS
app.include_router(progreso.router)
app.include_router(auth.router) # <-- ¡La puerta de entrada!
# Si creaste el router 'tests.py' descomenta la siguiente línea:
# app.include_router(tests.router)

# 6. FUNCIÓN DE BASE DE DATOS
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 7. MODELOS PYDANTIC (Para validar datos entrantes)
class FalloRequest(BaseModel):
    pregunta_id: int

class ResumenRequest(BaseModel):
    tiempo: int
    nivel: str
    tema: str

class PuntosRequest(BaseModel):
    nombre: str
    puntos: int

# NUEVO MODELO: Para cuando el alumno acierta la flashcard
class RepasoCompletado(BaseModel):
    fallo_id: int

# 8. INYECCIÓN DE DATOS DE PRUEBA AL ARRANCAR
@app.on_event("startup")
def inicializar_datos():
    db = SessionLocal()
    # Solo inyectamos si la base de datos está vacía
    if not db.query(Tema).first():
        print("Inyectando datos de demostración para el MVP...")
        
        # --- 1. CREAMOS LOS TEMAS ---
        tema1 = Tema(nombre="Tema 1: La Constitución Española", bloque="Derecho Constitucional")
        tema2 = Tema(nombre="Tema 2: El Gobierno y la Administración", bloque="Derecho Constitucional")
        db.add_all([tema1, tema2])
        db.commit()
        db.refresh(tema1)
        db.refresh(tema2)

        preguntas_demo = []

        # --- 2. PREGUNTAS TEMA 1 (CONSTITUCIÓN) ---
        preguntas_t1 = [
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
            ("¿Qué título de la CE está dedicado a los Derechos y Deberes fundamentales?", "Título Preliminar", "Título I", "Título II", "Título III", "Título I", "La estructura de la CE reserva el Título I para los derechos y deberes fundamentales.")
        ]

        for en, a, b, c, d, correcta, exp in preguntas_t1:
            preguntas_demo.append(Pregunta(enunciado=en, opcion_a=a, opcion_b=b, opcion_c=c, opcion_d=d, respuesta_correcta=correcta, explicacion=exp, tema_id=tema1.id))

        # --- 3. PREGUNTAS TEMA 2 (GOBIERNO) ---
        preguntas_t2 = [
            ("¿Quién dirige la política interior y exterior, la Administración civil y militar y la defensa del Estado?", "El Rey", "El Congreso de los Diputados", "El Gobierno", "El Presidente del Gobierno", "El Gobierno", "Artículo 97 de la CE: El Gobierno dirige la política interior y exterior..."),
            ("¿Ante quién responde solidariamente el Gobierno en su gestión política?", "Ante el Rey", "Ante el Congreso de los Diputados", "Ante las Cortes Generales", "Ante el Tribunal Supremo", "Ante el Congreso de los Diputados", "Artículo 108 de la CE establece la responsabilidad ante el Congreso."),
            ("El Gobierno se compone de:", "El Presidente, el Rey y los Ministros", "El Presidente, Vicepresidentes (en su caso) y Ministros", "Solo de Ministros y Secretarios de Estado", "Presidente y Tribunal Supremo", "El Presidente, Vicepresidentes (en su caso) y Ministros", "Artículo 98.1 CE detalla la composición del Gobierno."),
            ("¿Quién propone al Rey el nombramiento de los demás miembros del Gobierno?", "El Congreso", "El Senado", "El Presidente del Gobierno", "El Tribunal Constitucional", "El Presidente del Gobierno", "Artículo 100 CE: Los demás miembros del Gobierno serán nombrados y separados por el Rey, a propuesta de su Presidente."),
            ("¿Por qué sala se exigirá la responsabilidad criminal del Presidente y los demás miembros del Gobierno?", "Sala de lo Penal del Tribunal Supremo", "Sala de lo Contencioso del Tribunal Supremo", "Tribunal Constitucional", "Audiencia Nacional", "Sala de lo Penal del Tribunal Supremo", "Artículo 102.1 CE especifica la jurisdicción para el Gobierno."),
            ("El Gobierno cesa tras la celebración de elecciones generales, pérdida de confianza, dimisión o:", "Decisión del Rey", "Fallecimiento de su Presidente", "Acuerdo del Consejo de Ministros", "Enfermedad grave de un Ministro", "Fallecimiento de su Presidente", "Artículo 101.1 CE marca las causas del cese del Gobierno."),
            ("La moción de censura deberá ser adoptada por:", "Mayoría simple del Senado", "Mayoría absoluta del Congreso", "Mayoría simple del Congreso", "Mayoría absoluta de las Cortes", "Mayoría absoluta del Congreso", "Artículo 113.1 CE exige mayoría absoluta para la moción de censura."),
            ("La cuestión de confianza se entenderá otorgada cuando vote a favor de la misma la mayoría:", "Absoluta del Congreso", "Simple de las Cortes", "Simple de los Diputados", "Absoluta del Senado", "Simple de los Diputados", "Artículo 112 CE: La confianza se entenderá otorgada cuando vote a favor la mayoría simple de los Diputados."),
            ("Las disposiciones del Gobierno que contengan legislación delegada recibirán el título de:", "Decretos-leyes", "Decretos Legislativos", "Leyes Orgánicas", "Reglamentos", "Decretos Legislativos", "Artículo 85 CE sobre la delegación legislativa."),
            ("¿En qué casos puede el Gobierno dictar Decretos-leyes?", "En casos de extraordinaria y urgente necesidad", "Cuando se lo ordene el Rey", "Para aprobar Presupuestos", "Para reformar la Constitución", "En casos de extraordinaria y urgente necesidad", "Artículo 86.1 CE habilita el uso de Decretos-leyes solo en esta situación de urgencia.")
        ]

        for en, a, b, c, d, correcta, exp in preguntas_t2:
            preguntas_demo.append(Pregunta(enunciado=en, opcion_a=a, opcion_b=b, opcion_c=c, opcion_d=d, respuesta_correcta=correcta, explicacion=exp, tema_id=tema2.id))

        db.add_all(preguntas_demo)

        # --- 4. POBLAR EL RANKING DE LA CLASE ---
        usuarios_demo = [
            Puntuacion(alumno_nombre="Marta V.", puntos=1250, fecha="2024-03-01"),
            Puntuacion(alumno_nombre="Carlos M.", puntos=980, fecha="2024-03-02"),
            Puntuacion(alumno_nombre="Lucía Gómez", puntos=850, fecha="2024-03-03"),
            Puntuacion(alumno_nombre="Javier R.", puntos=720, fecha="2024-03-03"),
            Puntuacion(alumno_nombre="Ana Ruiz", puntos=610, fecha="2024-03-03")
        ]
        db.add_all(usuarios_demo)

        db.commit()
        print("¡Datos de demostración cargados con éxito!")
    db.close()

# ==========================================
# RUTAS DE LA API
# ==========================================

@app.get("/api/test-cors")
def test_cors():
    return {
        "mensaje": "¡Conexión exitosa! CORS está funcionando.",
        "tema_actual": "Configuración inicial",
        "progreso": 100
    }

# RUTA MODIFICADA: Generar test filtrando por tema
@app.get("/api/test/generar")
def generar_test(tema_id: int = 1, db: Session = Depends(get_db)):
    preguntas_db = db.query(Pregunta).filter(Pregunta.tema_id == tema_id).all()
    
    if len(preguntas_db) > 10:
        preguntas_db = random.sample(preguntas_db, 10)

    test_formateado = []
    for p in preguntas_db:
        test_formateado.append({
            "id": p.id,
            "pregunta": p.enunciado,
            "opciones": [p.opcion_a, p.opcion_b, p.opcion_c, p.opcion_d],
            "respuestaCorrecta": p.respuesta_correcta,
            "explicacion": p.explicacion
        })
    return test_formateado

# RUTA: Recibir fallo desde React
@app.post("/api/test/fallo")
def registrar_fallo(datos: FalloRequest, db: Session = Depends(get_db)):
    nuevo_fallo = RegistroFallo(alumno_id=1, pregunta_id=datos.pregunta_id)
    db.add(nuevo_fallo)
    db.commit()
    return {"mensaje": "Fallo guardado en el historial para el repaso automático"}

# RUTA: Generar resumen con Inteligencia Artificial (Gemini)
@app.post("/api/ia/resumir")
def generar_resumen_ia(datos: ResumenRequest):
    client = genai.Client(api_key="AIzaSyBIxgqxYJCANFKdltP7w3uS8FfcxInCBcY")
    
    prompt = f"""
    Actúa como un preparador de oposiciones experto. 
    Tu alumno tiene un nivel {datos.nivel} y dispone de solo {datos.tiempo} minutos.
    Genera un resumen ejecutivo, claro y con puntos clave sobre: {datos.tema}.
    Usa un lenguaje motivador y directo. Formatea con puntos y negritas.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return {"resumen": response.text}
    except Exception as e:
        print(f"Error detallado de Gemini: {e}")
        return {"resumen": "Error en la conexión con la IA. Revisa la consola."}

# RUTA: Guardar puntuaciones en el Ranking
@app.post("/api/ranking/guardar")
def guardar_puntos(datos: PuntosRequest, db: Session = Depends(get_db)):
    nueva_puntuacion = Puntuacion(
        alumno_nombre=datos.nombre, 
        puntos=datos.puntos,
        fecha=datetime.now().strftime("%Y-%m-%d")
    )
    db.add(nueva_puntuacion)
    db.commit()
    return {"mensaje": "Puntuación registrada"}

# RUTA: Obtener Ranking de la clase
@app.get("/api/ranking/clase")
def obtener_ranking(db: Session = Depends(get_db)):
    return db.query(Puntuacion).order_by(Puntuacion.puntos.desc()).limit(5).all()

# ==========================================
# NUEVAS RUTAS: MODO REPASO AUTOMÁTICO
# ==========================================

@app.get("/api/repaso/pendientes")
def obtener_repasos(alumno_id: int = 1, db: Session = Depends(get_db)):
    # 1. Buscamos los fallos pendientes de este alumno
    fallos = db.query(RegistroFallo).filter(
        RegistroFallo.alumno_id == alumno_id,
        RegistroFallo.repasada == False
    ).all()

    preguntas_repaso = []
    
    # 2. Por cada fallo, buscamos la pregunta real y montamos el JSON
    for fallo in fallos:
        p = db.query(Pregunta).filter(Pregunta.id == fallo.pregunta_id).first()
        if p:
            opciones = [opt for opt in [p.opcion_a, p.opcion_b, p.opcion_c, p.opcion_d] if opt]
            
            # Determinamos cuál es el texto de la respuesta correcta
            texto_correcta = ""
            if p.respuesta_correcta == "A": texto_correcta = p.opcion_a
            elif p.respuesta_correcta == "B": texto_correcta = p.opcion_b
            elif p.respuesta_correcta == "C": texto_correcta = p.opcion_c
            elif p.respuesta_correcta == "D": texto_correcta = p.opcion_d
            else: texto_correcta = p.respuesta_correcta # Por si guardaste el texto directamente

            preguntas_repaso.append({
                "fallo_id": fallo.id, # IMPORTANTE: Enviamos el ID del fallo
                "pregunta": p.enunciado,
                "opciones": opciones,
                "respuestaCorrecta": texto_correcta,
                "explicacion": p.explicacion or "Sin explicación."
            })
            
    return preguntas_repaso

@app.post("/api/repaso/completar")
def completar_repaso(datos: RepasoCompletado, db: Session = Depends(get_db)):
    # Buscamos ese fallo concreto y lo marcamos como repasado (superado)
    fallo = db.query(RegistroFallo).filter(RegistroFallo.id == datos.fallo_id).first()
    if fallo:
        fallo.repasada = True
        db.commit()
        return {"mensaje": "¡Pregunta superada y eliminada del mazo!"}
    return {"error": "No se encontró el fallo."}

# --- Asegúrate de tener este modelo arriba junto a los otros ---
class EsquemaRequest(BaseModel):
    tema_nombre: str

# --- Busca o añade este endpoint al final de main.py ---
@app.post("/api/ia/esquema")
def generar_esquema_ia(datos: EsquemaRequest):
    client = genai.Client(api_key="AIzaSyBIxgqxYJCANFKdltP7w3uS8FfcxInCBcY")
    
    # PROMPT MODIFICADO PARA GENERAR DIAGRAMAS VISUALES
    prompt = f"""
    Actúa como un experto en visualización de datos y profesor de oposiciones.
    Crea un diagrama de MAPA MENTAL (mindmap) usando exclusivamente la sintaxis de Mermaid.js sobre el tema: "{datos.tema_nombre}".
    
    REGLAS:
    1. Empieza el código con la palabra clave 'mindmap'.
    2. Usa una estructura jerárquica clara con nodos principales y secundarios.
    3. Sé conciso en los textos de los nodos para que el diagrama sea limpio.
    4. NO añadas explicaciones adicionales ni texto fuera del bloque de código de Mermaid. Solo el código.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        # Limpiamos la respuesta por si Gemini incluye los ```mermaid al principio y final
        codigo_limpio = response.text.replace("```mermaid", "").replace("```", "").strip()
        
        return {"esquema_codigo": codigo_limpio}
    except Exception as e:
        print(f"Error detallado de Gemini: {e}")
        # Devolvemos un diagrama de error simple en caso de fallo
        error_diagram = "mindmap\nroot((Error al generar))\n   Inténtalo de nuevo\n   Revisa la conexión"
        return {"esquema_codigo": error_diagram}