import os
import json
import secrets
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from datetime import datetime, timedelta

from models import get_db, Usuario
from schemas import UsuarioRegistro, UsuarioLogin, GoogleLogin, Token, UsuarioActual

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

# Configuración de Seguridad
SECRET_KEY = os.getenv("SECRET_KEY", "mi_clave_super_secreta_para_el_mvp")  # En producción, define SECRET_KEY en el entorno
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # El token durará 1 semana entera

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
DOMINIO_PERMITIDO = os.getenv("GOOGLE_HOSTED_DOMAIN", "academiamega.net")

# Bootstrap de roles por variables de entorno (listas de emails separados por comas).
# Al iniciar sesión, estos emails se promocionan automáticamente al rol indicado.
def _parse_emails(valor):
    return {e.strip().lower() for e in (valor or "").split(",") if e.strip()}

ADMIN_EMAILS = _parse_emails(os.getenv("ADMIN_EMAILS"))
PROFESOR_EMAILS = _parse_emails(os.getenv("PROFESOR_EMAILS"))

# Roles por alcance:
#   estudiante  -> solo los cursos en los que está matriculado
#   admin       -> profesor: gestiona SOLO los cursos que tiene asignados
#   superadmin  -> jefe de la academia: acceso total a todos los cursos
ROL_ESTUDIANTE = "estudiante"
ROL_ADMIN = "admin"
ROL_SUPERADMIN = "superadmin"
ROLES_VALIDOS = (ROL_ESTUDIANTE, ROL_ADMIN, ROL_SUPERADMIN)

_NIVEL_ROL = {ROL_ESTUDIANTE: 0, ROL_ADMIN: 1, ROL_SUPERADMIN: 2}

def _rol_por_entorno(email: str) -> str:
    e = email.lower()
    if e in ADMIN_EMAILS:        # jefes de la academia
        return ROL_SUPERADMIN
    if e in PROFESOR_EMAILS:     # profesores
        return ROL_ADMIN
    return ROL_ESTUDIANTE

def _aplicar_promocion_rol(db_user: Usuario) -> None:
    """Promociona el rol del usuario según ADMIN_EMAILS/PROFESOR_EMAILS.
    Nunca degrada un rol asignado manualmente desde el panel."""
    rol_entorno = _rol_por_entorno(db_user.email)
    if _NIVEL_ROL.get(rol_entorno, 0) > _NIVEL_ROL.get(db_user.rol or ROL_ESTUDIANTE, 0):
        db_user.rol = rol_entorno

# Encriptado de contraseñas (para el acceso por email + contraseña)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

bearer_scheme = HTTPBearer(auto_error=False)

def _crear_sesion(db: Session, usuario: Usuario) -> str:
    """Genera una nueva sesión y la guarda como la ÚNICA sesión válida del usuario,
    invalidando automáticamente cualquier token emitido antes (otro dispositivo)."""
    usuario.sesion_id = secrets.token_hex(16)
    db.commit()
    return usuario.sesion_id

def create_access_token(usuario_id: int, sesion_id: str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(usuario_id), "sid": sesion_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credenciales: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    error_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión no válida. Inicia sesión de nuevo.",
    )
    if not credenciales:
        raise error_auth
    try:
        payload = jwt.decode(credenciales.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = int(payload.get("sub"))
        sesion_id = payload.get("sid")
    except (JWTError, TypeError, ValueError):
        raise error_auth

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario or not sesion_id or usuario.sesion_id != sesion_id:
        # El sesion_id no coincide: se ha iniciado sesión en otro dispositivo
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tu sesión se ha cerrado porque se ha iniciado sesión en otro dispositivo.",
        )
    return usuario

def es_superadmin(usuario: Usuario) -> bool:
    return usuario.rol == ROL_SUPERADMIN

def require_gestor(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Gestión de contenido: administradores (profesores) y superadministradores.
    El alcance por curso se comprueba después con `verificar_acceso_curso`."""
    if usuario.rol not in (ROL_ADMIN, ROL_SUPERADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador.")
    return usuario

def require_superadmin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Solo superadministradores: gestión de cursos, usuarios y roles."""
    if usuario.rol != ROL_SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de superadministrador.")
    return usuario

def cursos_permitidos_ids(usuario: Usuario):
    """IDs de los cursos a los que el usuario tiene acceso.
    Devuelve None si es superadmin (acceso a TODOS los cursos)."""
    if es_superadmin(usuario):
        return None
    return [c.id for c in usuario.cursos]

def verificar_acceso_curso(usuario: Usuario, curso_id) -> None:
    """Lanza 403 si el usuario no puede gestionar ese curso."""
    if es_superadmin(usuario):
        return
    if curso_id is None or curso_id not in [c.id for c in usuario.cursos]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este curso.",
        )

def _validar_dominio_academia(email: str):
    if not email.lower().endswith(f"@{DOMINIO_PERMITIDO}"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo se admiten cuentas del correo de la academia (@{DOMINIO_PERMITIDO}).",
        )

# El acceso admite DOS vías, ambas restringidas al dominio @academiamega.net:
#   1) Email + contraseña (registro/login).
#   2) Google (OAuth2 con selector de cuenta forzado; el backend valida el access_token).
# El rol (alumno/profesor/admin) se asigna/promociona según ADMIN_EMAILS/PROFESOR_EMAILS.

# ENDPOINT: REGISTRO con email + contraseña (solo dominio de la academia)
@router.post("/registro")
def registrar_usuario(usuario: UsuarioRegistro, db: Session = Depends(get_db)):
    _validar_dominio_academia(usuario.email)

    if len(usuario.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    nuevo_usuario = Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        hashed_password=get_password_hash(usuario.password),
        rol=_rol_por_entorno(usuario.email),
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return {"mensaje": "Usuario creado con éxito. ¡Ya puedes iniciar sesión!"}

# ENDPOINT: LOGIN con email + contraseña
@router.post("/login", response_model=Token)
def iniciar_sesion(usuario: UsuarioLogin, db: Session = Depends(get_db)):
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if not db_user or not db_user.hashed_password:
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")

    if not verify_password(usuario.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")

    _aplicar_promocion_rol(db_user)  # por si el email entró en ADMIN_EMAILS tras registrarse
    sesion_id = _crear_sesion(db, db_user)
    token_sesion = create_access_token(db_user.id, sesion_id)

    return {
        "access_token": token_sesion,
        "token_type": "bearer",
        "usuario_id": db_user.id,
        "nombre": db_user.nombre,
    }

def _verificar_access_token_google(access_token: str) -> dict:
    """Valida un access token de Google (endpoint tokeninfo) y devuelve su info.
    Comprueba que el token fue emitido para NUESTRO client_id, evitando ataques de
    sustitución de token (que alguien use un token válido de otra aplicación)."""
    url = "https://oauth2.googleapis.com/tokeninfo?" + urlencode({"access_token": access_token})
    try:
        with urlopen(url, timeout=10) as resp:
            info = json.loads(resp.read().decode())
    except URLError:
        raise HTTPException(status_code=401, detail="Token de Google inválido o caducado.")

    if info.get("aud") != GOOGLE_CLIENT_ID and info.get("azp") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token de Google no emitido para esta aplicación.")
    return info

# ENDPOINT 1: LOGIN con Google (restringido al dominio de la academia)
@router.post("/google", response_model=Token)
def iniciar_sesion_google(datos: GoogleLogin, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="El login con Google no está configurado en el servidor.")

    if datos.access_token:
        # Flujo nuevo (OAuth2 con selector de cuenta)
        info = _verificar_access_token_google(datos.access_token)
        email = info.get("email")
        email_verificado = str(info.get("email_verified")).lower() == "true"
        google_sub = info.get("sub")
        nombre = (email or "").split("@")[0]
    elif datos.credential:
        # Compatibilidad: flujo antiguo con id_token
        try:
            idinfo = google_id_token.verify_oauth2_token(
                datos.credential, google_requests.Request(), GOOGLE_CLIENT_ID
            )
        except ValueError:
            raise HTTPException(status_code=401, detail="Token de Google inválido o caducado.")
        email = idinfo.get("email")
        email_verificado = bool(idinfo.get("email_verified"))
        google_sub = idinfo.get("sub")
        nombre = idinfo.get("name") or (email or "").split("@")[0]
    else:
        raise HTTPException(status_code=400, detail="Falta el token de Google.")

    if not email:
        raise HTTPException(status_code=401, detail="No se pudo obtener el email de Google.")
    if not email_verificado:
        raise HTTPException(status_code=401, detail="El email de Google no está verificado.")
    _validar_dominio_academia(email)

    db_user = db.query(Usuario).filter(Usuario.email == email).first()
    if not db_user:
        db_user = Usuario(
            nombre=nombre,
            email=email,
            hashed_password=None,
            google_sub=google_sub,
            rol=_rol_por_entorno(email),
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    else:
        if not db_user.google_sub and google_sub:
            db_user.google_sub = google_sub
        _aplicar_promocion_rol(db_user)  # nunca degrada un rol asignado desde el panel
        db.commit()

    sesion_id = _crear_sesion(db, db_user)
    token_sesion = create_access_token(db_user.id, sesion_id)

    return {
        "access_token": token_sesion,
        "token_type": "bearer",
        "usuario_id": db_user.id,
        "nombre": db_user.nombre,
    }

# ENDPOINT 4: Quién soy (para que el frontend valide la sesión al cargar)
@router.get("/me", response_model=UsuarioActual)
def usuario_actual(usuario: Usuario = Depends(get_current_user)):
    return {
        "usuario_id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "cursos": [{"id": c.id, "nombre": c.nombre} for c in usuario.cursos],
    }

# ENDPOINT 5: LOGOUT (invalida la sesión en el servidor, no solo en el navegador)
@router.post("/logout")
def cerrar_sesion(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    usuario.sesion_id = None
    db.commit()
    return {"mensaje": "Sesión cerrada"}