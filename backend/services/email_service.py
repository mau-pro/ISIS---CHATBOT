"""
services/email_service.py
----------------------------
Envía correos usando smtplib (incluido en Python, no requiere instalar nada).
Configuración leída del .env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.

Para usar Gmail: activar verificación en 2 pasos en la cuenta, y generar una
"contraseña de aplicación" en https://myaccount.google.com/apppasswords
(no usar la contraseña normal de la cuenta).
"""

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def enviar_correo_verificacion(destinatario: str, token: str) -> None:
    """Envía el correo con el link de verificación de cuenta."""
    link_verificacion = f"{BACKEND_URL}/auth/verify?token={token}"

    cuerpo = (
        f"Hola,\n\n"
        f"Gracias por registrarte en el I-SIS, el Asistente Virtual de Ingeniería de Sistemas.\n"
        f"Para activar tu cuenta, hacé clic en el siguiente enlace:\n\n"
        f"{link_verificacion}\n\n"
        f"Si no creaste esta cuenta, podés ignorar este correo."
    )

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = "Verificá tu cuenta - I-SIS, el Asistente Virtual de Ingeniería de Sistemas"
    mensaje["From"] = SMTP_USER
    mensaje["To"] = destinatario

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
        servidor.starttls()
        servidor.login(SMTP_USER, SMTP_PASSWORD)
        servidor.sendmail(SMTP_USER, [destinatario], mensaje.as_string())


def enviar_correo_recuperacion(destinatario: str, token: str) -> None:
    """
    Envía el correo con el link para restablecer la contraseña. A diferencia
    del link de verificación (que apunta al backend, porque solo muestra un
    mensaje), este apunta al FRONTEND: ahí el estudiante ve un formulario
    para escribir su nueva contraseña.
    """
    link_reset = f"{FRONTEND_URL}/reset-password?token={token}"

    cuerpo = (
        f"Hola,\n\n"
        f"Pediste restablecer tu contraseña en el I-SIS, el Asistente Virtual de Ingeniería de Sistemas.\n"
        f"Hacé clic en el siguiente enlace para elegir una nueva (válido por 30 minutos):\n\n"
        f"{link_reset}\n\n"
        f"Si no pediste esto, podés ignorar este correo: tu contraseña actual sigue siendo válida."
    )

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = "Recuperar contraseña - I-SIS, el Asistente Virtual de Ingeniería de Sistemas"
    mensaje["From"] = SMTP_USER
    mensaje["To"] = destinatario

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
        servidor.starttls()
        servidor.login(SMTP_USER, SMTP_PASSWORD)
        servidor.sendmail(SMTP_USER, [destinatario], mensaje.as_string())
