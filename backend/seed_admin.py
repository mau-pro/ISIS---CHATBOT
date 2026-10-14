"""
seed_admin.py
-------------
Script de un solo uso para crear la cuenta de administrador, leyendo
ADMIN_EMAIL y ADMIN_PASSWORD del archivo .env (y ADMIN_USERNAME, opcional: si no está,
el usuario es la parte del correo antes de la @). No existe un endpoint público
para crear admins: se hace así a propósito, por seguridad.

Ejecutar una sola vez, desde backend/:
    python seed_admin.py
"""

import os
from dotenv import load_dotenv

from database import Base, engine, SessionLocal
from models.user import User, UserRole
from services.auth_service import hash_password
from services.username_service import normalizar_username

load_dotenv()

Base.metadata.create_all(bind=engine)


def crear_admin():
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not email or not password:
        print("Definí ADMIN_EMAIL y ADMIN_PASSWORD en el archivo .env antes de correr esto.")
        return

    db = SessionLocal()
    try:
        username = normalizar_username(os.getenv("ADMIN_USERNAME") or email.split("@")[0])
        existente = db.query(User).filter(User.email == email).first()
        if existente:
            print(f"Ya existe una cuenta con el correo {email}. No se creó nada nuevo (usuario: {existente.username}).")
            return

        admin = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
            is_verified=True,
        )
        db.add(admin)
        db.commit()
        print(f"Cuenta admin creada correctamente: usuario {username} ({email})")
    finally:
        db.close()


if __name__ == "__main__":
    crear_admin()
