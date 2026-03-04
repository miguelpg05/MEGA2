from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from models import get_db, Usuario
from schemas import UsuarioRegistro, UsuarioLogin, Token

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

# Configuración de Seguridad
SECRET_KEY = "mi_clave_super_secreta_para_el_mvp" # Es la firma de tus tokens
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # El token durará 1 semana entera

# Herramienta para encriptar contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ENDPOINT 1: REGISTRO
@router.post("/registro")
def registrar_usuario(usuario: UsuarioRegistro, db: Session = Depends(get_db)):
    # 1. Comprobar si el email ya existe
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")
    
    # 2. Encriptar la contraseña y guardar en base de datos
    hashed_password = get_password_hash(usuario.password)
    nuevo_usuario = Usuario(nombre=usuario.nombre, email=usuario.email, hashed_password=hashed_password)
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return {"mensaje": "Usuario creado con éxito. ¡Ya puedes iniciar sesión!"}

# ENDPOINT 2: LOGIN
@router.post("/login", response_model=Token)
def iniciar_sesion(usuario: UsuarioLogin, db: Session = Depends(get_db)):
    # 1. Buscar al usuario por email
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")
    
    # 2. Comprobar que la contraseña coincide
    if not verify_password(usuario.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")
    
    # 3. Crear el Token (la "pulsera virtual")
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    # 4. Devolver el token y los datos básicos al frontend
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario_id": db_user.id,
        "nombre": db_user.nombre
    }