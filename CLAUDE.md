# CLAUDE.md — Plataforma Academia MEGA

Guía de trabajo para Claude Code sobre esta plataforma SaaS educativa (preparación de oposiciones) de Academia MEGA.

---

## 1. Qué es este proyecto

SaaS didáctico para una academia. Los alumnos hacen tests por temas, reciben repaso automático de sus fallos (flashcards), esquemas visuales generados por IA, y compiten en un ranking. Uso previsto: **~200 alumnos concurrentes** de una única academia.

- **Frontend**: React 19 + Vite 7 + Tailwind 4 + React Router 7 → desplegado en **Vercel**.
- **Backend**: FastAPI + SQLAlchemy → desplegado en **Render**.
- **Base de datos**: PostgreSQL en **Neon**.
- **IA**: Google Gemini (`gemini-2.5-flash`) para resúmenes y esquemas Mermaid.
- **Auth**: JWT propio (email+contraseña) + Google Identity Services, restringido al dominio `@academiamega.net`.
- **Repo**: `https://github.com/miguelpg05/WebMEGA.git` (rama principal `main`).

---

## 2. Estructura del repositorio

```
backend/
  main.py                 # App FastAPI, CORS, seed de arranque, endpoints IA/ranking/repaso
  models.py               # Modelos SQLAlchemy + engine + create_all
  schemas.py              # Esquemas Pydantic
  routers/
    auth.py               # Registro, login, login Google, /me, logout, sesión única
    progreso.py           # Progreso por tema y guardado de resultados
    progreso_test.py      # Generación de tests desde plantillas + histórico de intentos
  inyectar_preguntas.py   # Script para cargar preguntas desde preguntas.xlsx
  services/               # (auxiliares)
  requirements.txt
frontend/
  src/
    config.js             # API_BASE_URL y GOOGLE_CLIENT_ID (leen de import.meta.env)
    api.js                # apiFetch: añade Bearer y gestiona 401 (sesión en otro dispositivo)
    pages/                # Auth, Dashboard, Test, TestListado, Repaso, Esquema, PanelAlumno
    components/           # IndicadorProgreso, RankingClase, ResumenIA
  index.html              # Incluye el script de Google Identity Services
```

---

## 3. Comandos

**Backend** (desde `backend/`, con el venv activo):
```bash
uvicorn main:app --reload        # desarrollo local (http://127.0.0.1:8000)
pip install -r requirements.txt
```

**Frontend** (desde `frontend/`):
```bash
npm install
npm run dev                      # http://localhost:5173
npm run build                    # build de producción
npm run lint
```

> En Windows la shell principal es PowerShell. Para arrancar servidores en Claude Code usa el preview/browser, no procesos en background sin control.

---

## 4. Variables de entorno (NUNCA hardcodear secretos)

**Backend** (`backend/.env` en local; en Render como Environment):
- `DATABASE_URL` — cadena Postgres de Neon. **Usar el host con `-pooler`** (connection pooling) para soportar concurrencia.
- `SECRET_KEY` — clave larga y aleatoria para firmar JWT. **Obligatoria en producción** (ver §7, hoy tiene un default inseguro).
- `GEMINI_API_KEY`
- `GOOGLE_CLIENT_ID` — client ID de Google OAuth.
- `GOOGLE_HOSTED_DOMAIN` — `academiamega.net`.

**Frontend** (`frontend/.env`; en Vercel como Environment Variables):
- `VITE_API_URL` — URL del backend en Render.
- `VITE_GOOGLE_CLIENT_ID`

Existen `.env.example` en ambas carpetas: manténlos actualizados cuando añadas variables.

---

## 5. Los 4 objetivos y su estado actual

| Objetivo | Estado | Notas |
|---|---|---|
| **Responsive** | 🟡 Parcial | `viewport` OK y hay breakpoints `md:`/`lg:` en Dashboard. Falta auditar Test, Esquema (Mermaid), TestListado y el botón de Google (ancho fijo `336`). |
| **Sesión única por usuario** | 🟢 Implementado | Columna `usuarios.sesion_id` + claim `sid` en el JWT; cada login regenera el `sesion_id` e invalida el resto. El front detecta el 401 y redirige con aviso. |
| **Login Google solo @academiamega.net** | 🟢 Implementado | Verifica el `id_token`, comprueba `hd` + fallback por dominio del email. Requiere `GOOGLE_CLIENT_ID` configurado en ambos lados. |
| **Soportar 200 concurrentes** | 🔴 Pendiente | Requiere: Neon pooled connection, pool de SQLAlchemy, workers de uvicorn/gunicorn, plan de pago en Render (el free hiberna), quitar el seed/ALTER de cada arranque. |

---

## 6. Convenciones de código

- **Idioma**: dominio y nombres de negocio en español (`Usuario`, `Pregunta`, `sesion_id`). Mantén la coherencia.
- **Auth en el backend**: toda ruta protegida usa `Depends(get_current_user)` (en `routers/auth.py`). El `alumno_id` **nunca** viaja desde el cliente: se deriva del token. Respeta esto en endpoints nuevos.
- **Auth en el frontend**: usa siempre `apiFetch` (de `src/api.js`), nunca `fetch` directo, para que se añada el Bearer y se gestione el 401.
- **Config del frontend**: URLs y client IDs salen de `src/config.js` (leen `import.meta.env`). No hardcodear URLs de producción en componentes.
- **Migraciones**: hoy el esquema se crea con `create_all` + `ALTER TABLE IF NOT EXISTS` en el arranque. Al tocar modelos, introducir **Alembic** en vez de ampliar el bloque de arranque (ver §7).

---

## 7. Deuda técnica y trampas conocidas (leer antes de tocar)

1. **`SECRET_KEY` con default inseguro** (`routers/auth.py:18`). Si en producción no se define la env var, los JWT son falsificables. Debe fallar al arrancar si falta.
2. **Inconsistencia en `respuesta_correcta`** (bug latente): el seed de `main.py` guarda el **texto completo** ("El Rey"), pero `progreso_test.py:33` asume que es una **letra** (`A`/`B`...) y hace `str(...)[0]`. Para las preguntas del seed esto elige una respuesta incorrecta por defecto. Unificar el formato (recomendado: guardar siempre la letra `A–D`) antes de mezclar ambas fuentes de datos.
3. **Seed en cada arranque** (`main.py`, `@app.on_event("startup")`): inserta preguntas demo y **usuarios de ranking falsos** ("Marta V.", etc.) que contaminan el ranking real. Además `on_event` está deprecado → migrar a `lifespan`. Separar el seed a un script que no corra en producción.
4. **Sin rate limiting**: los endpoints de IA (`/api/ia/*`) y de login son abusables (coste de Gemini / fuerza bruta). Añadir límites (p. ej. `slowapi`).
5. **Registro email+contraseña sin verificación de buzón**: cualquiera que sepa un `@academiamega.net` puede registrarlo. La vía Google es segura; valorar deshabilitar el registro por contraseña o exigir verificación por email.
6. **JWT en `localStorage`**: expuesto a XSS. Aceptable para MVP; tenerlo presente.
7. **Pool de conexiones sin configurar**: `create_engine(URL)` usa el pool por defecto (5). Con Neon + 200 usuarios hace falta pooled connection y ajustar `pool_size`/`max_overflow`/`pool_pre_ping`.
8. **Ficheros que no deberían estar versionados**: revisar que `academia.db`, `venv/`, `__pycache__/`, `node_modules/` estén en `.gitignore`.
9. **Dashboard hardcodea Tema 1 y Tema 2**: no lista los temas dinámicamente desde la BD.
10. **Sin tests automatizados** ni CI.

---

## 8. Roadmap sugerido (orden recomendado)

**Fase 1 — Solidez y seguridad (antes de abrir a alumnos):**
- `SECRET_KEY` obligatoria; validar formato de email (`EmailStr`) y política de contraseña.
- Unificar `respuesta_correcta` a letra A–D y corregir el bug del punto 7.2.
- Rate limiting en login e IA.
- Sacar el seed del arranque; limpiar ranking de datos falsos.
- Introducir Alembic para migraciones.

**Fase 2 — Escala a 200 concurrentes:**
- Neon pooled connection + pool SQLAlchemy (`pool_pre_ping=True`).
- Render: plan que no hiberne + `gunicorn -k uvicorn.workers.UvicornWorker -w N`.
- Cachear consultas frecuentes (ranking).

**Fase 3 — Responsive y UX:**
- Auditoría móvil de Test, Esquema (Mermaid con scroll horizontal), TestListado.
- Validar sesión al cargar la app llamando a `/api/auth/me` (evitar `nombre_usuario` obsoleto de localStorage).
- Recuperación de contraseña; estados de carga/error consistentes.

**Fase 4 — Gestión (panel de administración):**
- Rol de usuario (`alumno`/`profesor`/`admin`).
- Panel para subir preguntas/tests sin ejecutar scripts locales.
- Métricas para la academia: alumnos activos, progreso por tema, tests más fallados.
- Monitorización de errores (Sentry) y visibilidad de coste de Gemini.

---

## 9. Despliegue

- **Frontend → Vercel**: build `npm run build`, variables `VITE_*` en el panel. Cada push a `main` despliega.
- **Backend → Render**: start command tipo `gunicorn main:app -k uvicorn.workers.UvicornWorker` (o `uvicorn main:app` en desarrollo), variables de entorno en el panel. Hoy no hay `Procfile`/`render.yaml` — considerar añadirlo.
- **DB → Neon**: usar la cadena **pooled** en `DATABASE_URL`.
- **CORS** (`main.py`): la lista `allow_origins` está hardcodeada con el dominio de Vercel y localhost. Al cambiar de dominio, actualizarla.

---

## 10. Reglas para Claude en este repo

- No introducir secretos en el código ni en commits. Usa variables de entorno y `.env.example`.
- No hacer `git push` ni desplegar sin que el usuario lo pida explícitamente.
- Al añadir endpoints protegidos, usar `Depends(get_current_user)` y derivar el `alumno_id` del token.
- Al añadir llamadas del frontend, usar `apiFetch`.
- Cambios en el modelo de datos → acompañarlos de migración (Alembic) cuando esté introducido; mientras tanto, documentar el `ALTER`.
- Preferir cambios pequeños y verificables; correr `npm run lint` en el frontend tras editar.
