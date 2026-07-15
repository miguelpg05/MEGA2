import os
import secrets
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

_NIVEL_ROL = {"alumno": 0, "profesor": 1, "admin": 2}

def _rol_por_entorno(email: str) -> str:
    e = email.lower()
    if e in ADMIN_EMAILS:
        return "admin"
    if e in PROFESOR_EMAILS:
        return "profesor"
    return "alumno"

def _aplicar_promocion_rol(db_user: Usuario) -> None:
    """Promociona el rol del usuario según ADMIN_EMAILS/PROFESOR_EMAILS.
    Nunca degrada un rol asignado manualmente desde el panel."""
    rol_entorno = _rol_por_entorno(db_user.email)
    if _NIVEL_ROL.get(rol_entorno, 0) > _NIVEL_ROL.get(db_user.rol or "alumno", 0):
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

def require_staff(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Permite el paso solo a profesores y administradores (gestión de contenido y métricas)."""
    if usuario.rol not in ("profesor", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de profesor o administrador.")
    return usuario

def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """Permite el paso solo a administradores (gestión de usuarios/roles)."""
    if usuario.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador.")
    return usuario

def _validar_dominio_academia(email: str):
    if not email.lower().endswith(f"@{DOMINIO_PERMITIDO}"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo se admiten cuentas del correo de la academia (@{DOMINIO_PERMITIDO}).",
        )

# El acceso admite DOS vías, ambas restringidas al dominio @academiamega.net:
#   1) Email + contraseña (registro/login).
#   2) Google Identity Services.
# El rol (alumno/profesor/admin) se asigna/promociona según ADMIN_EMAILS/PROFESOR_EMAILS.

# ENDPOINT 1: REGISTRO con email + contraseña (solo dominio de la academia)
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

# ENDPOINT 2: LOGIN con email + contraseña
@router.post("/login", response_model=Token)
def iniciar_sesion(usuario: UsuarioLogin, db: Session = Depends(get_db)):
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if not db_user or not db_user.hashed_password:
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")

    if not verify_password(usuario.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")

    _aplicar_promocion_rol(db_user)  # por si el email entró en ADMIN_EMAILS después de registrarse
    sesion_id = _crear_sesion(db, db_user)
    access_token = create_access_token(db_user.id, sesion_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario_id": db_user.id,
        "nombre": db_user.nombre,
    }

# ENDPOINT 3: LOGIN con Google (restringido al dominio de la academia)
@router.post("/google", response_model=Token)
def iniciar_sesion_google(datos: GoogleLogin, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="El login con Google no está configurado en el servidor.")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            datos.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido o caducado.")

    if not idinfo.get("email_verified"):
        raise HTTPException(status_code=401, detail="El email de Google no está verificado.")

    email = idinfo["email"]
    if idinfo.get("hd") != DOMINIO_PERMITIDO:
        _validar_dominio_academia(email)  # comprobación de respaldo por si 'hd' no viene

    rol_entorno = _rol_por_entorno(email)

    db_user = db.query(Usuario).filter(Usuario.email == email).first()
    if not db_user:
        db_user = Usuario(
            nombre=idinfo.get("name") or email.split("@")[0],
            email=email,
            hashed_password=None,
            google_sub=idinfo["sub"],
            rol=rol_entorno,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    else:
        if not db_user.google_sub:
            db_user.google_sub = idinfo["sub"]
        _aplicar_promocion_rol(db_user)  # nunca degrada un rol asignado desde el panel
        db.commit()

    sesion_id = _crear_sesion(db, db_user)
    access_token = create_access_token(db_user.id, sesion_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario_id": db_user.id,
        "nombre": db_user.nombre,
    }

# ENDPOINT 4: Quién soy (para que el frontend valide la sesión al cargar)
@router.get("/me", response_model=UsuarioActual)
def usuario_actual(usuario: Usuario = Depends(get_current_user)):
    return {"usuario_id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol}

# ENDPOINT 5: LOGOUT (invalida la sesión en el servidor, no solo en el navegador)
@router.post("/logout")
def cerrar_sesion(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    usuario.sesion_id = None
    db.commit()
    return {"mensaje": "Sesión cerrada"}