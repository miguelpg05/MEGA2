import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Modelos, routers y utilidades
from models import get_db, Pregunta, RegistroFallo, Usuario, IALlamada, Tema, MaterialTema
from routers import progreso, auth, progreso_test, admin, temas, access, ranking
from routers.auth import get_current_user, es_superadmin
from schemas import (
    FalloRequest,
    ResumenRequest,
    RepasoCompletado,
)
from services.preguntas import texto_opcion_correcta, textos_correctos
from services.pdf import extraer_texto_pdf, recortar_repartido, combinar_materiales
from services.ia import generar_texto, IAError
from services.limites import limiter, respuesta_limite_superado, clave_usuario, LIMITE_IA
from slowapi.errors import RateLimitExceeded

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

# Límites de peticiones (login, registro, Google e IA): ver services/limites.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, respuesta_limite_superado)


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
app.include_router(access.router)
app.include_router(ranking.router)

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
    if not db.query(Pregunta.id).filter(Pregunta.id == datos.pregunta_id).first():
        raise HTTPException(status_code=404, detail="La pregunta ya no existe.")
    # Si ya está pendiente de repaso no se duplica la carta
    ya_pendiente = db.query(RegistroFallo).filter(
        RegistroFallo.alumno_id == usuario.id,
        RegistroFallo.pregunta_id == datos.pregunta_id,
        RegistroFallo.repasada == False,  # noqa: E712
    ).first()
    if not ya_pendiente:
        db.add(RegistroFallo(alumno_id=usuario.id, pregunta_id=datos.pregunta_id))
        db.commit()
    return {"mensaje": "Fallo guardado en el historial para el repaso automático"}

@app.post("/api/ia/resumir")
@limiter.limit(LIMITE_IA, key_func=clave_usuario)
def generar_resumen_ia(request: Request, datos: ResumenRequest, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # Solo se resume material real (PDFs de la academia o texto aportado): sin él,
    # la IA escribiría de memoria y en oposiciones eso da datos erróneos.
    contenido, fuente, documentos, recortado = _contenido_fuente(datos, usuario, db)

    base = (
        f'Elabora unos apuntes de estudio a partir del CONTENIDO que te doy '
        f'(procedente de {fuente}), sobre "{datos.tema}". Cíñete ESTRICTAMENTE a ese contenido: '
        f'no añadas artículos, leyes, fechas ni cifras que no aparezcan en él. '
        f'Desarrolla y explica todo lo que sí aparece.'
    )
    if recortado:
        base += (' El contenido es una selección de fragmentos del documento (separados por «[…]»): '
                 'organízalos con coherencia y no rellenes los huecos inventando.')
    bloque_contenido = f"\n\nCONTENIDO:\n{contenido}"

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

Formato en **Markdown** (se mostrará con estilos, respeta estas reglas):
- Empieza con UNA frase de contexto (sin título; el título ya lo pone la plataforma).
- Secciones principales numeradas con «## 1. Título», «## 2. Título»… (entre 3 y 7).
- Subsecciones con «### Título» (sin numerar).
- Párrafos cortos (2-4 frases) combinados con listas; **negrita** solo en los términos clave.
- Cuando cites un artículo o precepto literal, ponlo como cita: «> **Art. 57 CE** — texto…».
- Usa una tabla Markdown (con fila de cabecera y separador |---|) solo para comparar o clasificar.
- Cierra SIEMPRE con «## 🔑 Claves para recordar»: 5-8 viñetas breves o reglas mnemotécnicas.
Escribe en español, claro y didáctico. No añadas comentarios sobre ti mismo ni sobre el formato.{bloque_contenido}
"""
    # Escalamos también el máximo de tokens de salida según el tiempo, para que no
    # se corte un resumen largo.
    # (Acotado para no superar el límite por minuto del plan gratuito de Groq.)
    tope_tokens = {5: 1400, 15: 2200, 30: 3000}.get(datos.tiempo, 2200)
    try:
        texto, tokens = generar_texto(prompt, max_tokens=tope_tokens)
    except IAError as e:
        raise HTTPException(status_code=e.status, detail=e.mensaje)

    _registrar_uso_ia(db, usuario.id, "resumen", tokens)
    return {"resumen": texto, "fuente": fuente, "documentos": documentos, "recortado": recortado}

# Los puntos del ranking los suma el servidor al corregir (POST /api/test/entregar).

# Ranking por curso: routers/ranking.py (GET /api/ranking/clase?curso_id=…)

@app.get("/api/repaso/pendientes")
def obtener_repasos(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mazo de repaso: UNA carta por pregunta pendiente (aunque se fallara varias
    veces), en una sola consulta. `veces` = cuántos fallos pendientes tiene."""
    filas = (
        db.query(RegistroFallo.id, Pregunta)
        .join(Pregunta, Pregunta.id == RegistroFallo.pregunta_id)
        .filter(RegistroFallo.alumno_id == usuario.id, RegistroFallo.repasada == False)  # noqa: E712
        .order_by(RegistroFallo.id)
        .all()
    )
    cartas = {}
    for fallo_id, p in filas:
        if p.id in cartas:
            cartas[p.id]["veces"] += 1
            continue
        correctas = textos_correctos(p)
        cartas[p.id] = {
            "pregunta_id": p.id,
            "fallo_id": fallo_id,   # compatibilidad
            "veces": 1,
            "pregunta": p.enunciado,
            "opciones": [opt for opt in [p.opcion_a, p.opcion_b, p.opcion_c, p.opcion_d] if opt],
            "respuestaCorrecta": texto_opcion_correcta(p),   # compatibilidad
            "respuestasCorrectas": correctas,
            "multiple": len(correctas) > 1,
            "explicacion": p.explicacion or "Sin explicación.",
        }
    return list(cartas.values())

@app.post("/api/repaso/completar")
def completar_repaso(datos: RepasoCompletado, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Marca como repasados TODOS los fallos pendientes de esa pregunta."""
    pregunta_id = datos.pregunta_id
    if pregunta_id is None and datos.fallo_id is not None:
        fallo = db.query(RegistroFallo).filter(RegistroFallo.id == datos.fallo_id).first()
        if fallo and fallo.alumno_id == usuario.id:
            pregunta_id = fallo.pregunta_id
    if pregunta_id is None:
        raise HTTPException(status_code=404, detail="No se encontró el fallo.")
    marcados = db.query(RegistroFallo).filter(
        RegistroFallo.alumno_id == usuario.id,
        RegistroFallo.pregunta_id == pregunta_id,
        RegistroFallo.repasada == False,  # noqa: E712
    ).update({RegistroFallo.repasada: True}, synchronize_session=False)
    if not marcados:
        raise HTTPException(status_code=404, detail="No se encontró el fallo.")
    db.commit()
    return {"mensaje": "¡Pregunta superada y eliminada del mazo!"}

def _tema_accesible_para(usuario: Usuario, tema: Tema) -> bool:
    if es_superadmin(usuario):
        return True
    if tema is None:
        return False
    return tema.curso_id is None or tema.curso_id in [c.id for c in usuario.cursos]


# Máximo de texto de los PDFs que se envía a la IA en cada resumen. Con el plan
# gratuito de Groq (8.000 tokens/minuto) no se puede enviar mucho más: si se pasa a
# un plan de pago, se puede subir (y también tope_tokens en el resumen).
TOPE_CONTENIDO_IA = int(os.getenv("IA_TOPE_CARACTERES", "10000"))

SIN_MATERIAL = ("Los temas seleccionados no tienen PDFs con texto. El resumen solo se genera a partir "
                "del material de la academia: pide que suban el PDF del tema o pega tú el texto.")


def _contenido_fuente(datos, usuario: Usuario, db: Session):
    """Devuelve (texto, descripcion_fuente, documentos, recortado) según lo elegido:
    texto libre, un PDF concreto o los PDFs de varios temas. Si no hay material
    con texto, lanza 400 (no se resume solo con el título)."""
    if datos.texto and datos.texto.strip():
        texto, recortado = recortar_repartido(datos.texto, TOPE_CONTENIDO_IA)
        return texto, "el texto proporcionado", ["Texto aportado"], recortado

    if datos.material_id:
        material = db.query(MaterialTema).filter(MaterialTema.id == datos.material_id).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material no encontrado.")
        tema = db.query(Tema).filter(Tema.id == material.tema_id).first()
        if not _tema_accesible_para(usuario, tema):
            raise HTTPException(status_code=403, detail="No tienes acceso a este material.")
        texto = extraer_texto_pdf(material.contenido, max_chars=400000)
        if not texto:
            raise HTTPException(status_code=400, detail="No se pudo extraer texto de ese PDF (puede ser escaneado/imagen).")
        texto, recortado = recortar_repartido(texto, TOPE_CONTENIDO_IA)
        return texto, f"el documento «{material.nombre_archivo}»", [material.nombre_archivo], recortado

    # Varios temas: se reparte el cupo entre TODOS sus PDFs y, de cada uno, se toman
    # fragmentos de todo el documento (no solo las primeras páginas).
    documentos = []
    for tid in (getattr(datos, "tema_ids", None) or []):
        tema = db.query(Tema).filter(Tema.id == tid).first()
        if not tema or not _tema_accesible_para(usuario, tema):
            continue
        for material in tema.materiales:
            texto_pdf = extraer_texto_pdf(material.contenido, max_chars=400000)
            if texto_pdf:
                documentos.append((f"{tema.nombre} · {material.nombre_archivo}", texto_pdf))
    contenido, recortado = combinar_materiales(documentos, TOPE_CONTENIDO_IA)
    if not contenido:
        raise HTTPException(status_code=400, detail=SIN_MATERIAL)
    return contenido, "los PDFs de los temas seleccionados", [e.split(" · ", 1)[-1] for e, _ in documentos], recortado
