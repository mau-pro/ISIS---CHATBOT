"""
crear_cuentas_beta.py
-----------------------
Crea cuentas de estudiante para la prueba BETA (ya verificadas, sin necesidad de correo),
cada una con una contraseña distinta, y las deja en cuentas_beta.csv para repartir.
Es seguro repetirlo: no duplica ni cambia las cuentas que ya existen.

    python crear_cuentas_beta.py [cantidad]            (por defecto 10)
    docker compose exec backend python crear_cuentas_beta.py 10
"""

import csv
import secrets
import sys

from database import Base, engine, SessionLocal
from models.user import User, UserRole
import models.document, models.chat_log  # noqa: F401  (registra todas las tablas)
from services.auth_service import hash_password

DOMINIO = "beta.example.com"  # dominio de ejemplo reservado: no envía ni recibe correos
# Sin letras ni números que se confunden al dictarlos o copiarlos (0/O, 1/l/I)
ALFABETO = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def clave() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(10))


def main(cantidad: int) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    nuevas = []
    try:
        for n in range(1, cantidad + 1):
            usuario = f"beta{n:02d}"
            if db.query(User).filter(User.username == usuario).first():
                print(f"{usuario}: ya existía, no se modificó")
                continue
            contrasena = clave()
            db.add(User(
                username=usuario,
                email=f"{usuario}@{DOMINIO}",
                password_hash=hash_password(contrasena),
                role=UserRole.student,
                is_verified=True,
            ))
            nuevas.append((usuario, contrasena))
        db.commit()
    finally:
        db.close()

    if nuevas:
        with open("cuentas_beta.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if f.tell() == 0:
                w.writerow(["usuario", "contrasena"])
            w.writerows(nuevas)
    print(f"Cuentas beta creadas: {len(nuevas)} (lista en cuentas_beta.csv)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
