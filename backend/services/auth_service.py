"""
services/auth_service.py
-------------------------
Toda la lógica de autenticación vive acá:
- hash_password / verify_password: manejo seguro de contraseñas (bcrypt).
- create_access_token: genera un JWT.
- get_current_user: dependencia que valida el JWT y devuelve el User autenticado.
- get_current_admin: igual, pero además exige rol admin.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models.user import User

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cambia-esto-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # el token de sesión dura 1 hora
VERIFICATION_TOKEN_EXPIRE_MINUTES = 60 * 24  # el link de verificación dura 1 día
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30  # el link de recuperación dura poco, por seguridad

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl apunta al endpoint de login; auto_error=False deja que get_current_user
# devuelva su propio 401 con el mismo formato de error.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def create_verification_token(email: str) -> str:
    """
    Genera un JWT de corta duración con purpose='email_verification', para
    diferenciarlo de un token de sesión normal (así uno no sirve como el otro).
    """
    expire = datetime.utcnow() + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "purpose": "email_verification", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token_de_verificacion(token: str) -> Optional[str]:
    """Decodifica el token del link de verificación. Devuelve el email, o None si es inválido/expiró."""
    payload = _decode_token(token)
    if payload is None or payload.get("purpose") != "email_verification":
        return None
    return payload.get("sub")


def create_password_reset_token(email: str) -> str:
    """
    Genera un JWT de vida corta (30 min) con purpose='password_reset', para
    el link de "olvidé mi contraseña". La vida corta limita la ventana en la
    que un correo interceptado podría usarse para cambiar la contraseña.
    """
    expire = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "purpose": "password_reset", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token_de_reset(token: str) -> Optional[str]:
    """Decodifica el token del link de recuperación. Devuelve el email, o None si es inválido/expiró."""
    payload = _decode_token(token)
    if payload is None or payload.get("purpose") != "password_reset":
        return None
    return payload.get("sub")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Exige un JWT válido. Usar en rutas que requieren cuenta (estudiante o admin)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    payload = _decode_token(token)
    if payload is None:
        raise credentials_exception

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Exige que el usuario autenticado sea admin. Usar en rutas de /admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return user
