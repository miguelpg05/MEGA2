import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

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
from services.ia import generar_texto, IAError

# Monitorización de errores con Sentry (opcional: solo si se define SENTRY_DSN)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1, send_default_pii=False)
        print("✅ Sentry inicializado.")
    except Exception as e:
        print(f"⚠️ No se pudo inicializar Sentry: {e}")


def _registrar_uso_ia(db: Session, usuario_id: int, tipo: str, tokens=None) -> None:
    """Registra una llamada a la IA para dar visibilidad de uso/coste."""
    try:
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
    contenido, fuente = _contenido_fuente(datos, usuario, db)

    if contenido:
        base = (
            f'Elabora un material de estudio DETALLADO a partir del CONTENIDO que te doy '
            f'(procedente de {fuente}), sobre "{datos.tema}". Cíñete a ese contenido; '
            f'no inventes datos que no aparezcan, pero desarrolla y explica todo lo que sí aparece.'
        )
        bloque_contenido = f"\n\nCONTENIDO:\n{contenido}"
    else:
        base = f'Elabora un material de estudio DETALLADO y completo sobre: "{datos.tema}".'
        bloque_contenido = ""

    # La extensión y profundidad escalan con el tiempo disponible...
    guias_tiempo = {
        5: "Extensión: resumen ágil pero COMPLETO (unas 300-450 palabras). Cubre todos los puntos esenciales sin dejarte nada importante.",
        15: "Extensión: resumen DETALLADO (unas 600-900 palabras). Desarrolla cada apartado con explicaciones, no solo titulares.",
        30: "Extensión: material EXTENSO y EXHAUSTIVO (1000-1500 palabras o más). Desarrolla en profundidad cada bloque, con matices y ejemplos.",
    }
    guia_tiempo = guias_tiempo.get(datos.tiempo, guias_tiempo[15])

    # ...y con el nivel del alumno.
    guias_nivel = {
        "Principiante": "Explica desde la base: define los términos, usa ejemplos sencillos y frases claras para entenderlo por primera vez.",
        "Intermedio": "Asume los conceptos básicos y profundiza en lo importante, equilibrando explicación y síntesis.",
        "Avanzado": "Repaso de alto nivel: entra en matices, excepciones y detalles finos (artículos concretos, plazos, cifras, jurisprudencia si aplica).",
    }
    guia_nivel = guias_nivel.get(datos.nivel, guias_nivel["Intermedio"])

    prompt = f"""Actúa como un preparador de oposiciones experto que crea apuntes de estudio.
{base}

Nivel del alumno: {datos.nivel}. Tiempo para repasar: {datos.tiempo} minutos.
{guia_tiempo}
{guia_nivel}

MUY IMPORTANTE — sé DETALLADO y EXTENSO: no te limites a una lista de titulares.
Desarrolla cada punto con 2-4 frases explicativas, define los conceptos, incluye
datos concretos (artículos, plazos, cifras, nombres), ejemplos y relaciones entre ideas.

Formato en **Markdown** bien estructurado y fácil de memorizar:
- Frase de contexto inicial.
- Secciones con encabezados (## Título) y subsecciones (### ) cuando convenga.
- Párrafos explicativos combinados con listas y **negrita** en los términos clave.
- Cierra con "### 🔑 Claves para recordar": 5-8 puntos o reglas mnemotécnicas.
Escribe en español, claro y didáctico. No añadas comentarios sobre ti mismo ni sobre el formato.{bloque_contenido}
"""
    # Escalamos también el máximo de tokens de salida según el tiempo, para que no
    # se corte un resumen largo.
    tope_tokens = {5: 1500, 15: 3000, 30: 5000}.get(datos.tiempo, 3000)
    try:
        texto, tokens = generar_texto(prompt, max_tokens=tope_tokens)
    except IAError as e:
        raise HTTPException(status_code=e.status, detail=e.mensaje)

    _registrar_uso_ia(db, usuario.id, "resumen", tokens)
    return {"resumen": texto, "fuente": fuente}

@app.post("/api/ranking/guardar")
def guardar_puntos(datos: PuntosRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # UNA fila por usuario: si ya existe, acumulamos; si no, la creamos.
    fila = db.query(Puntuacion).filter(Puntuacion.usuario_id == usuario.id).first()
    hoy = datetime.now().strftime("%Y-%m-%d")
    if fila:
        fila.puntos = (fila.puntos or 0) + datos.puntos
        fila.alumno_nombre = usuario.nombre  # mantener el nombre al día
        fila.fecha = hoy
    else:
        fila = Puntuacion(usuario_id=usuario.id, alumno_nombre=usuario.nombre, puntos=datos.puntos, fecha=hoy)
        db.add(fila)
    db.commit()
    return {"mensaje": "Puntuación registrada", "puntos_totales": fila.puntos}

@app.get("/api/ranking/clase")
def obtener_ranking(db: Session = Depends(get_db)):
    # Solo el ranking acumulativo por usuario (ignora filas antiguas sin usuario_id)
    return (
        db.query(Puntuacion)
        .filter(Puntuacion.usuario_id.isnot(None))
        .order_by(Puntuacion.puntos.desc())
        .limit(5)
        .all()
    )

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


def _contenido_fuente(datos, usuario: Usuario, db: Session):
    """Devuelve (texto_fuente, descripcion_fuente) según lo que el usuario haya
    elegido: texto libre, un PDF del tema, o solo el nombre del tema.
    Compartido por el esquema y el resumen (ambos aceptan texto/material_id)."""
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

    # Varios temas: combinamos el texto de TODOS sus PDFs (con un tope global para
    # controlar tokens/coste). Si ningún tema tiene material, se resume por título.
    tema_ids = getattr(datos, "tema_ids", None)
    if tema_ids:
        TOPE_TOTAL = 26000
        partes, total = [], 0
        for tid in tema_ids:
            if total >= TOPE_TOTAL:
                break
            tema = db.query(Tema).filter(Tema.id == tid).first()
            if not tema or not _tema_accesible_para(usuario, tema):
                continue
            for material in tema.materiales:
                if total >= TOPE_TOTAL:
                    break
                texto_pdf = extraer_texto_pdf(material.contenido, max_chars=min(12000, TOPE_TOTAL - total))
                if texto_pdf:
                    partes.append(f"\n\n### {tema.nombre} · {material.nombre_archivo}\n{texto_pdf}")
                    total += len(texto_pdf)
        contenido = "".join(partes).strip()
        if contenido:
            return contenido, "los materiales de los temas seleccionados"

    return "", "el tema (solo el título)"


@app.post("/api/ia/esquema")
def generar_esquema_ia(datos: EsquemaRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    contenido, fuente = _contenido_fuente(datos, usuario, db)

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
    # 1) Llamada a la IA (JSON)
    try:
        texto_ia, tokens = generar_texto(prompt, json_mode=True)
    except IAError as e:
        raise HTTPException(status_code=e.status, detail=e.mensaje)

    _registrar_uso_ia(db, usuario.id, "esquema", tokens)

    # 2) Procesado de la respuesta a un mindmap SIEMPRE válido
    try:
        data = extraer_json(texto_ia)
        codigo = construir_mindmap(data)
        return {"esquema_codigo": codigo, "fuente": fuente}
    except Exception as e:
        print(f"❌ Esquema: respuesta no parseable: {e!r} | texto={texto_ia[:300]!r}")
        raise HTTPException(status_code=502, detail="La IA devolvió un formato inesperado. Inténtalo de nuevo.")
