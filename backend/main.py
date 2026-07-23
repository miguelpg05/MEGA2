import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from google import genai

# Modelos, routers y utilidades
from models import get_db, Pregunta, Puntuacion, RegistroFallo, Usuario, IALlamada, Tema, MaterialTema
from routers import progreso, auth, progreso_test, admin, temas
from routers.auth import get_current_user, es_superadmin
from schemas import (
    FalloRequest,
    ResumenRequest,
    PuntosRequest,
    RepasoCompletado,
    EsquemaRequest,
)
from services.preguntas import texto_opcion_correcta, textos_correctos
from services.esquema import construir_mindmap, extraer_json, extraer_texto_pdf

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

def _tema_accesible_para(usuario: Usuario, tema: Tema) -> bool:
    if es_superadmin(usuario):
        return True
    if tema is None:
        return False
    return tema.curso_id is None or tema.curso_id in [c.id for c in usuario.cursos]


def _contenido_para_esquema(datos: EsquemaRequest, usuario: Usuario, db: Session):
    """Devuelve (texto_fuente, descripcion_fuente) según lo que el usuario haya
    elegido: texto libre, un PDF del tema, o solo el nombre del tema."""
    if datos.texto and datos.texto.strip():
        return datos.texto.strip()[:18000], "el texto proporcionado"

    if datos.material_id:
        material = db.query(MaterialTema).filter(MaterialTema.id == datos.material_id).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material no encontrado.")
        tema = db.query(Tema).filter(Tema.id == material.tema_id).first()
        if not _tema_accesible_para(usuario, tema):
            raise HTTPException(status_code=403, detail="No tienes acceso a este material.")
        texto = extraer_texto_pdf(material.contenido)
        if not texto:
            raise HTTPException(status_code=400, detail="No se pudo extraer texto de ese PDF (puede ser escaneado/imagen).")
        return texto, f"el documento «{material.nombre_archivo}»"

    return "", "el tema (solo el título)"


@app.post("/api/ia/esquema")
def generar_esquema_ia(datos: EsquemaRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="La IA no está configurada en el servidor (falta GEMINI_API_KEY).")

    contenido, fuente = _contenido_para_esquema(datos, usuario, db)

    base = (
        f'Basándote en {fuente}, sobre el tema "{datos.tema_nombre}",'
        if contenido == "" else
        f'A partir del siguiente CONTENIDO (de {fuente}) sobre el tema "{datos.tema_nombre}",'
    )
    prompt = f"""Eres un experto en síntesis pedagógica para oposiciones.
{base} crea un mapa mental jerárquico para memorizar lo esencial.

Devuelve EXCLUSIVAMENTE un JSON válido (sin explicaciones, sin markdown, sin ```),
con esta forma exacta:
{{"titulo": "Título corto del tema",
  "ramas": [
    {{"titulo": "Bloque principal", "hijos": ["Detalle", "Detalle"]}}
  ]}}

Reglas: máximo 6 ramas; máximo 8 hijos por rama; cada texto de 5 palabras como
máximo; en español; sin comillas ni paréntesis dentro de los textos.
{("CONTENIDO:\\n" + contenido) if contenido else ""}
"""
    modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # 1) Llamada al modelo
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model=modelo, contents=prompt)
    except Exception as e:
        print(f"❌ Esquema: fallo al llamar a Gemini (modelo={modelo}): {e!r}")
        raise HTTPException(status_code=502, detail=f"La IA no respondió (modelo {modelo}): {str(e)[:300]}")

    _registrar_uso_ia(db, usuario.id, "esquema", response)

    # 2) Procesado de la respuesta a un mindmap válido
    try:
        texto_ia = response.text or ""
    except Exception as e:
        print(f"❌ Esquema: no se pudo leer response.text: {e!r}")
        raise HTTPException(status_code=502, detail=f"La IA no devolvió texto: {str(e)[:200]}")

    try:
        data = extraer_json(texto_ia)
        codigo = construir_mindmap(data)
        return {"esquema_codigo": codigo, "fuente": fuente}
    except Exception as e:
        print(f"❌ Esquema: respuesta no parseable: {e!r} | texto={texto_ia[:300]!r}")
        raise HTTPException(status_code=502, detail=f"Formato inesperado de la IA: {str(e)[:150]} · respuesta: {texto_ia[:150]}")
