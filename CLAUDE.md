# CLAUDE.md — Plataforma Academia MEGA

Guía de trabajo para Claude Code sobre esta plataforma SaaS educativa (preparación de oposiciones) de Academia MEGA.

---

## 1. Qué es este proyecto

SaaS didáctico para una academia. Los alumnos hacen tests por temas, reciben repaso automático de sus fallos (flashcards), esquemas visuales generados por IA, y compiten en un ranking. Uso previsto: **~200 alumnos concurrentes** de una única academia.

- **Frontend**: React 19 + Vite 7 + Tailwind 4 + React Router 7 → desplegado en **Vercel**.
- **Backend**: FastAPI + SQLAlchemy → desplegado en **Render**.
- **Base de datos**: PostgreSQL en **Neon**.
- **IA**: capa intercambiable (`services/ia.py`, `generar_texto()`), seleccionable con `IA_PROVIDER`: **Groq** (Llama 3.3, por defecto) o **Gemini**. Genera resúmenes y esquemas (mapa mental Mermaid construido desde un JSON).
- **Auth**: dos vías, ambas restringidas a `@academiamega.net`: **email+contraseña** (registro/login) y **Google** (OAuth2 con selector de cuenta forzado `prompt=select_account`; el backend valida el `access_token` contra `tokeninfo` comprobando `aud`/`azp` = nuestro client_id). La sesión se gestiona con un JWT propio + `sesion_id` (sesión única por usuario). En el front, la sesión se valida contra `/api/auth/me` vía `AuthContext`. El rol se promociona según `ADMIN_EMAILS`/`PROFESOR_EMAILS`.
- **Repo**: `https://github.com/miguelpg05/WebMEGA.git` (rama principal `main`).

---

## 2. Estructura del repositorio

```
backend/
  main.py                 # App FastAPI, CORS, seed de arranque, endpoints IA/ranking/repaso
  models.py               # Modelos SQLAlchemy + engine + create_all
  schemas.py              # Esquemas Pydantic
  routers/
    auth.py               # Login Google, /me, logout, sesión única, roles (require_staff/require_admin)
    progreso.py           # Progreso por tema y guardado de resultados
    progreso_test.py      # Generación de tests desde plantillas + histórico de intentos
    admin.py              # Panel admin: CRUD temas/tests/preguntas, importación, métricas, roles, ranking
  seed.py                 # Datos demo (idempotente); se ejecuta a mano, no en el arranque
  alembic/                # Migraciones (0001 esquema inicial, 0002 rol + ia_llamadas)
  inyectar_preguntas.py   # Script para cargar preguntas desde preguntas.xlsx
  services/               # (auxiliares)
  requirements.txt
frontend/
  src/
    config.js             # API_BASE_URL y GOOGLE_CLIENT_ID (leen de import.meta.env)
    api.js                # apiFetch: añade Bearer y gestiona 401 (sesión en otro dispositivo)
    pages/                # Auth, Dashboard, Test, TestListado, Repaso, Esquema, Admin, PanelAlumno
    components/           # IndicadorProgreso, RankingClase, ResumenIA, MermaidDiagram, Estado
    auth/AuthContext.jsx  # Valida la sesión con /me y expone el usuario+rol
  index.html              # Incluye el script de Google Identity Services
```

---

## 3. Comandos

**Backend** (desde `backend/`, con el venv activo):
```bash
pip install -r requirements.txt
alembic upgrade head             # crea/actualiza el esquema (BD nueva)
# alembic stamp head             # BD YA existente (prod): márcala como migrada, NO crees tablas
python seed.py                   # carga datos demo (temas, preguntas, tests 001-100) — idempotente
uvicorn main:app --reload        # desarrollo local (http://127.0.0.1:8000)
python -m pytest -q              # tests

# Al cambiar models.py, genera una migración nueva:
alembic revision --autogenerate -m "descripcion del cambio"
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
- `IA_PROVIDER` — `groq` (por defecto) o `gemini`. Groq es gratis y con límites más altos.
- `GROQ_API_KEY` / `GROQ_MODEL` — clave de Groq (console.groq.com) y modelo (`llama-3.3-70b-versatile`).
- `GEMINI_API_KEY` / `GEMINI_MODEL` — solo si `IA_PROVIDER=gemini`.
- `GOOGLE_CLIENT_ID` — client ID de Google OAuth.
- `GOOGLE_HOSTED_DOMAIN` — `academiamega.net`.
- `ADMIN_EMAILS` — emails (separados por comas) que se promocionan a **`superadmin`** al iniciar sesión. **Bootstrap del primer jefe**: pon tu email aquí.
- `PROFESOR_EMAILS` — emails que se promocionan a **`admin`** (profesor: solo sus cursos asignados).
- `SENTRY_DSN` — opcional; si se define, activa la monitorización de errores con Sentry.

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
| **Login Google solo @academiamega.net** | 🟢 Implementado (+ email/contraseña) | Google: OAuth2 con `prompt=select_account` (sin auto-login) + `hosted_domain`; backend valida el `access_token` con `tokeninfo`. Coexiste con email+contraseña (también restringido al dominio). Requiere `GOOGLE_CLIENT_ID` en ambos lados. |
| **Soportar 200 concurrentes** | 🔴 Pendiente | Requiere: Neon pooled connection, pool de SQLAlchemy, workers de uvicorn/gunicorn, plan de pago en Render (el free hiberna), quitar el seed/ALTER de cada arranque. |

---

## 5b. Roles y alcance por curso

Todo el temario cuelga de un **`Curso`**. La tabla intermedia `usuario_cursos` (muchos a muchos) vincula usuarios y cursos.

| Rol | Pensado para | Alcance |
|---|---|---|
| `superadmin` | Jefes de la academia | **Todos** los cursos. Único que gestiona cursos, usuarios y roles |
| `admin` | Profesores | Solo los cursos **asignados**: puede añadir/editar/borrar temario y tests de esos cursos |
| `estudiante` | Alumnos | Solo los cursos en los que está **matriculado** |

- Dependencias en `routers/auth.py`: `require_gestor` (admin+superadmin) y `require_superadmin`.
- El alcance se comprueba con `verificar_acceso_curso(usuario, curso_id)` y `cursos_permitidos_ids(usuario)` (devuelve `None` = todos).
- **Al añadir un endpoint de gestión**, valida SIEMPRE el curso implicado (para tests/preguntas, resuélvelo a través de su `tema.curso_id`).

## 6. Convenciones de código

- **Idioma**: dominio y nombres de negocio en español (`Usuario`, `Pregunta`, `sesion_id`). Mantén la coherencia.
- **Auth en el backend**: toda ruta protegida usa `Depends(get_current_user)` (en `routers/auth.py`). El `alumno_id` **nunca** viaja desde el cliente: se deriva del token. Respeta esto en endpoints nuevos.
- **Auth en el frontend**: usa siempre `apiFetch` (de `src/api.js`), nunca `fetch` directo, para que se añada el Bearer y se gestione el 401.
- **Config del frontend**: URLs y client IDs salen de `src/config.js` (leen `import.meta.env`). No hardcodear URLs de producción en componentes.
- **Migraciones**: el esquema lo gestiona **Alembic** (`backend/alembic/`). Al tocar `models.py`, genera una migración con `alembic revision --autogenerate -m "..."` y revísala antes de aplicar. No reintroducir `create_all` ni `ALTER TABLE` en el arranque.
- **Datos demo**: en `seed.py` (script idempotente), nunca en el arranque de la app.

---

## 7. Deuda técnica y trampas conocidas (leer antes de tocar)

**✅ Ya resueltos:**
- **Gestión / panel de administración**: roles `alumno`/`profesor`/`admin` (`usuarios.rol`), panel en `/admin` (solo staff) con CRUD de temas/tests/preguntas, importación CSV/XLSX, gestión de roles (solo admin) y limpieza del ranking demo. Métricas: alumnos activos (7d), progreso por tema, preguntas más falladas y uso de IA. Sentry opcional (`SENTRY_DSN`) y registro de uso de Gemini (`ia_llamadas`).
- **Acceso email+contraseña y Google** (OAuth2 con selector de cuenta forzado): ambas vías restringidas a `@academiamega.net`. El email+contraseña permite crear un admin (vía `ADMIN_EMAILS`) sin depender de una cuenta de Google real — útil porque el 2FA obligatorio del Workspace bloqueaba la cuenta de admin. El registro por contraseña no verifica el buzón (deuda de seguridad conocida).
- **`respuesta_correcta`**: guarda las letras correctas ordenadas y sin separador (`"A"` o, con varias correctas, `"AC"`). La traducción letras↔texto vive en un único sitio, `services/preguntas.py` (`letras_correctas`/`textos_correctos`/`normalizar_respuesta`), usado por el panel, `main.py` (repaso) y `routers/progreso_test.py`. Tolera datos antiguos (una letra o el texto completo). Cubierto por tests. En el test del alumno una pregunta con varias correctas se acierta solo si el conjunto marcado coincide exactamente.
- **`main.py` sobrecargado**: el seed se movió a `seed.py` (script idempotente, sin usuarios de ranking falsos), los modelos Pydantic a `schemas.py`, y `@app.on_event` → `lifespan`.
- **Esquema con Alembic**: `Base.metadata.create_all` y los `ALTER TABLE` de arranque se retiraron. Ver carpeta `alembic/`.
- **Tests + CI**: `backend/tests/` con pytest y `.github/workflows/ci.yml` (pytest + lint/build del front).
- **Artefactos versionados**: `venv/`, `*.db`, `__pycache__/`, `.env` ya en `.gitignore` (no estaban trackeados).

**⚠️ Trampas aprendidas (leer si algo "no conecta"):**
- **`alembic stamp head` NO aplica las migraciones**, solo las marca como aplicadas. Sobre una BD ya existente hay que hacer `alembic stamp 0001` y luego `alembic upgrade head`. Si te saltas esto, faltan columnas (nos pasó con `usuarios.rol`) y **toda consulta a esa tabla peta**. Verifica con:
  `SELECT column_name FROM information_schema.columns WHERE table_name='usuarios';`
- **Un "Failed to fetch" en el navegador casi nunca es CORS ni red**: puede ser un 500 del backend. Ya está mitigado (los 500 llevan cabeceras CORS), pero para diagnosticar: prueba un endpoint **sin BD** (`/api/test-cors`), otro **con BD** (`/api/ranking/clase`) y otro de la tabla sospechosa. El que falle te señala la causa.
- **Ojo con los servicios duplicados**: existieron a la vez un Render/Vercel antiguos (`backend-academia-kxx5`, `web-mega-flax`) y los buenos (`mega2-mi1o`, `mega-2-rho`). Confirma siempre a qué URL apunta el bundle desplegado.

**⏳ Pendientes (prioridad para siguientes fases):**
1. **`SECRET_KEY` con default inseguro** (`routers/auth.py`). Si en producción no se define la env var, los JWT son falsificables. Debe fallar al arrancar si falta.
2. **Sin rate limiting**: los endpoints de IA (`/api/ia/*`) son abusables (coste de Gemini). Añadir límites (p. ej. `slowapi`).
3. **JWT en `localStorage`**: expuesto a XSS. Aceptable para MVP; tenerlo presente.
4. **Pool de conexiones sin configurar**: `create_engine(URL)` usa el pool por defecto (5). Con Neon + 200 usuarios hace falta pooled connection y ajustar `pool_size`/`max_overflow`/`pool_pre_ping`.
5. **Dashboard hardcodea Tema 1 y Tema 2**: no lista los temas dinámicamente desde la BD.
6. **`inyectar_preguntas.py`** usa `pandas`/`openpyxl`, que no están en `requirements.txt` (script local).

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

**Fase 4 — Gestión (panel de administración): ✅ hecha**
- Roles, panel `/admin`, CRUD e importación de contenido, métricas, Sentry y uso de Gemini. Pendiente opcional: rediseñar el ranking (hoy inserta una fila por intento con el nombre; considerar agregación por usuario).

**Al desplegar esta fase** (BD de Neon ya existente): ejecutar `alembic upgrade head` para aplicar la migración `0002` (columna `rol` + tabla `ia_llamadas`), y definir `ADMIN_EMAILS` con tu correo para tener el primer administrador.

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
