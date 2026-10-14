"""
routes/auth_routes.py
-----------------------
Endpoints públicos de autenticación:
- POST /auth/register          -> crea la cuenta de estudiante (inactiva) y envía correo de verificación
- GET  /auth/verify              -> confirma el correo a partir del token del link recibido
- POST /auth/login               -> valida usuario y contraseña, exige is_verified=True, devuelve un JWT
- POST /auth/forgot-password    -> manda un correo con link para restablecer la contraseña
- POST /auth/reset-password     -> aplica la nueva contraseña a partir del token del link
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, UserRole
from schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_verification_token,
    verificar_token_de_verificacion,
    create_password_reset_token,
    verificar_token_de_reset,
)
from services.username_service import normalizar_username, username_valido, MENSAJE_USERNAME_INVALIDO
from services.email_service import enviar_correo_verificacion, enviar_correo_recuperacion

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAJE_GENERICO_FORGOT_PASSWORD = (
    "Si ese correo tiene una cuenta registrada, te enviamos un enlace para "
    "restablecer la contraseña."
)


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Registro público: crea la cuenta inactiva y envía el correo de verificación."""
    username = normalizar_username(data.username)
    if not username_valido(username):
        raise HTTPException(status_code=400, detail=MENSAJE_USERNAME_INVALIDO)
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Ese nombre de usuario ya está en uso")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    nuevo_usuario = User(
        username=username,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.student,
        is_verified=False,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    token_verificacion = create_verification_token(nuevo_usuario.email)

    try:
        enviar_correo_verificacion(nuevo_usuario.email, token_verificacion)
    except Exception:
        # Si falla el envío (ej. SMTP mal configurado), no rompemos el registro:
        # la cuenta queda creada pero sin verificar. Se podría reintentar el envío.
        pass

    return {
        "detail": "Cuenta creada. Revisá tu correo para activar tu cuenta antes de iniciar sesión."
    }


@router.get("/verify", response_class=HTMLResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    El estudiante llega acá al hacer clic en el link del correo.
    Devuelve una página HTML simple de confirmación (no requiere frontend).
    """
    email = verificar_token_de_verificacion(token)
    if email is None:
        return HTMLResponse(
            "<h2>Enlace inválido o vencido</h2><p>Pedí un nuevo enlace de verificación.</p>",
            status_code=400,
        )

    usuario = db.query(User).filter(User.email == email).first()
    if usuario is None:
        return HTMLResponse("<h2>Cuenta no encontrada</h2>", status_code=404)

    usuario.is_verified = True
    db.commit()

    return HTMLResponse(
        "<h2>¡Cuenta verificada correctamente!</h2>"
        "<p>Ya podés cerrar esta pestaña e iniciar sesión en el asistente.</p>"
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(User).filter(User.username == normalizar_username(data.username)).first()

    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    if not usuario.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta todavía no fue verificada. Revisá tu correo.",
        )

    token = create_access_token({"sub": usuario.email, "role": usuario.role.value})
    return TokenResponse(access_token=token, role=usuario.role.value)


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Pide el correo y, si existe una cuenta con ese correo, manda el enlace de
    recuperación. Devuelve SIEMPRE el mismo mensaje genérico (exista o no la
    cuenta) para no revelar qué correos están registrados.
    """
    usuario = db.query(User).filter(User.email == data.email).first()
    if usuario:
        token = create_password_reset_token(usuario.email)
        try:
            enviar_correo_recuperacion(usuario.email, token)
        except Exception:
            # Si falla el envío (ej. SMTP mal configurado), no lo reflejamos
            # en la respuesta: igual devolvemos el mensaje genérico.
            pass

    return {"detail": MENSAJE_GENERICO_FORGOT_PASSWORD}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Valida el token del link de recuperación y aplica la nueva contraseña."""
    email = verificar_token_de_reset(data.token)
    if email is None:
        raise HTTPException(
            status_code=400,
            detail="El enlace es inválido o venció. Pedí uno nuevo desde '¿Olvidaste tu contraseña?'.",
        )

    if len(data.nueva_password) < 6:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres."
        )

    usuario = db.query(User).filter(User.email == email).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    usuario.password_hash = hash_password(data.nueva_password)
    db.commit()

    return {"detail": "Contraseña actualizada. Ya podés iniciar sesión con la nueva."}
