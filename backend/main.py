import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from google import genai

# Modelos, routers y utilidades
from models import get_db, Pregunta, Puntuacion, RegistroFallo, Usuario, IALlamada
from routers import progreso, auth, progreso_test, admin, temas
from routers.auth import get_current_user
from schemas import (
    FalloRequest,
    ResumenRequest,
    PuntosRequest,
    RepasoCompletado,
    EsquemaRequest,
)
from services.preguntas import texto_opcion_correcta, textos_correctos

# Monitorización de errores con Sentry (opcional: solo si se define SENTRY_DSN)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1, send_default_pii=False)
        print("✅ Sentry inicializado.")
    except Exception as e:
        print(f"⚠️ No se pudo inicializar Sentry: {e}")


def _registrar_uso_ia(db: Session, usuario_id: int, tipo: str, response) -> None:
    """Guarda un registro de la llamada a Gemini para dar visibilidad de uso/coste."""
    try:
        tokens = None
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            tokens = getattr(meta, "total_token_count", None)
        db.add(IALlamada(usuario_id=usuario_id, tipo=tipo, tokens_totales=tokens, fecha=datetime.utcnow()))
        db.commit()
    except Exception as e:
        print(f"No se pudo registrar el uso de IA: {e}")
        db.rollback()

# ==========================================
# 1. CICLO DE VIDA DE LA APP
# ==========================================
# El esquema de la base de datos se gestiona con Alembic (`alembic upgrade head`).
# Los datos de demostración se cargan aparte con `python seed.py` (ver README/CLAUDE.md).
# Por eso ya NO inyectamos datos ni ejecutamos ALTER TABLE en el arranque.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranque
    yield
    # Cierre


# ==========================================
# 2. INICIALIZACIÓN DE LA APP Y CORS
# ==========================================
app = FastAPI(title="API Academia Oposiciones", lifespan=lifespan)


# IMPORTANTE: este middleware se añade ANTES que el de CORS para que quede por
# DENTRO de él. Así, cuando una excepción no controlada revienta (p. ej. una
# columna que falta en la base de datos), la respuesta 500 sale por el
# CORSMiddleware y LLEVA sus cabeceras. Sin esto, el navegador no puede leer el
# error y lo muestra como un engañoso "Failed to fetch", ocultando la causa real.
@app.middleware("http")
async def capturar_errores_no_controlados(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        print(f"❌ Error no controlado en {request.method} {request.url.path}: {exc!r}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor. Revisa los logs del backend."},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mega-2-rho.vercel.app",     # Frontend de MEGA2 (producción)
        "https://web-mega-flax.vercel.app",  # Proyecto Vercel antiguo (por compatibilidad)
        "http://localhost:5173",             # Desarrollo local
        "http://127.0.0.1:5173",
    ],
    # Permite también las URLs de "preview" de Vercel del proyecto MEGA2
    # (p. ej. mega-2-git-rama-usuario.vercel.app) sin tener que listarlas una a una.
    allow_origin_regex=r"https://mega-2[-a-z0-9]*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==========================================
# 3. INCLUSIÓN DE RUTAS EXTERNAS
# ==========================================
app.include_router(progreso.router)
app.include_router(auth.router)
app.include_router(progreso_test.router)
app.include_router(admin.router)
app.include_router(temas.router)

# ==========================================
# 4. RUTAS DE LA API
# ==========================================

@app.get("/api/test-cors")
def test_cors():
    return {
        "mensaje": "¡Conexión exitosa! CORS está funcionando.",
        "tema_actual": "Configuración inicial",
        "progreso": 100
    }

@app.post("/api/test/fallo")
def registrar_fallo(datos: FalloRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    nuevo_fallo = RegistroFallo(alumno_id=usuario.id, pregunta_id=datos.pregunta_id)
    db.add(nuevo_fallo)
    db.commit()
    return {"mensaje": "Fallo guardado en el historial para el repaso automático"}

@app.post("/api/ia/resumir")
def generar_resumen_ia(datos: ResumenRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    client = genai.Client(api_key=GEMINI_API_KEY)
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
        _registrar_uso_ia(db, usuario.id, "resumen", response)
        return {"resumen": response.text}
    except Exception as e:
        print(f"Error detallado de Gemini: {e}")
        return {"resumen": "Error en la conexión con la IA. Revisa la consola."}

@app.post("/api/ranking/guardar")
def guardar_puntos(datos: PuntosRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    nueva_puntuacion = Puntuacion(
        alumno_nombre=usuario.nombre,
        puntos=datos.puntos,
        fecha=datetime.now().strftime("%Y-%m-%d")
    )
    db.add(nueva_puntuacion)
    db.commit()
    return {"mensaje": "Puntuación registrada"}

@app.get("/api/ranking/clase")
def obtener_ranking(db: Session = Depends(get_db)):
    return db.query(Puntuacion).order_by(Puntuacion.puntos.desc()).limit(5).all()

@app.get("/api/repaso/pendientes")
def obtener_repasos(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    fallos = db.query(RegistroFallo).filter(
        RegistroFallo.alumno_id == usuario.id,
        RegistroFallo.repasada == False
    ).all()

    preguntas_repaso = []
    for fallo in fallos:
        p = db.query(Pregunta).filter(Pregunta.id == fallo.pregunta_id).first()
        if p:
            opciones = [opt for opt in [p.opcion_a, p.opcion_b, p.opcion_c, p.opcion_d] if opt]
            correctas = textos_correctos(p)
            preguntas_repaso.append({
                "fallo_id": fallo.id,
                "pregunta": p.enunciado,
                "opciones": opciones,
                "respuestaCorrecta": texto_opcion_correcta(p),   # compatibilidad
                "respuestasCorrectas": correctas,
                "multiple": len(correctas) > 1,
                "explicacion": p.explicacion or "Sin explicación."
            })
    return preguntas_repaso

@app.post("/api/repaso/completar")
def completar_repaso(datos: RepasoCompletado, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    fallo = db.query(RegistroFallo).filter(RegistroFallo.id == datos.fallo_id).first()
    if not fallo or fallo.alumno_id != usuario.id:
        raise HTTPException(status_code=404, detail="No se encontró el fallo.")
    fallo.repasada = True
    db.commit()
    return {"mensaje": "¡Pregunta superada y eliminada del mazo!"}

@app.post("/api/ia/esquema")
def generar_esquema_ia(datos: EsquemaRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Actúa como un experto en diseño instruccional y síntesis pedagógica para oposiciones.
    Tu objetivo es transformar el tema "{datos.tema_nombre}" en un mapa mental de Mermaid.js que facilite la memoria visual.

    REGLAS ESTRUCTURALES:
    1. Usa exclusivamente la sintaxis `mindmap`.
    2. Jerarquía Estricta:
    - Raíz: Usa la forma de bordes dobles `((Nombre del Tema))`
    - Nivel 1 (Bloques principales): Usa la forma redondeada `(Concepto)`
    - Nivel 2 (Detalles): Usa la forma de nubes `)Detalle(` o rectángulos `[Detalle]`
    3. Regla de Oro: Máximo 3 palabras por nodo. Si es más largo, sintetiza.
    4. Densidad: No generes más de 5 ramas principales para evitar el desorden visual.
    5. Iconografía: Incluye un emoji relevante al principio de cada nodo de Nivel 1 para mejorar la asociación mental.

    CONFIGURACIÓN VISUAL:
    - Empieza el bloque con:
    ---
    config:
    look: handDrawn
    theme: neutral
    ---
    mindmap
    (( {datos.tema_nombre} ))
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        _registrar_uso_ia(db, usuario.id, "esquema", response)
        codigo_limpio = response.text.replace("```mermaid", "").replace("```", "").strip()
        return {"esquema_codigo": codigo_limpio}
    except Exception as e:
        print(f"Error detallado de Gemini: {e}")
        error_diagram = "mindmap\nroot((Error al generar))\n   Inténtalo de nuevo\n   Revisa la conexión"
        return {"esquema_codigo": error_diagram}
