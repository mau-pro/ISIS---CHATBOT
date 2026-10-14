"""
seed_estudiantes.py
-------------------
Crea 250 cuentas de estudiante de prueba (ya verificadas, no hace falta
confirmar correo) para poder probar el sistema con volumen real: paginación
del panel de usuarios, rate limit por cuenta, carga concurrente, etc.

Los correos son ficticios (dominio de ejemplo reservado: no reciben ni envían nada) y todas
comparten la misma contraseña de prueba, así se puede iniciar sesión con
cualquiera. Es idempotente: si se corre dos veces no duplica cuentas.

Ejecutar desde backend/:
    python seed_estudiantes.py
"""

import csv
import random

from database import Base, engine, SessionLocal
from models.user import User, UserRole
from services.auth_service import hash_password

CANTIDAD = 250
PASSWORD_PRUEBA = "Estudiante2026"
DOMINIO = "estudiantes.example.com"

NOMBRES = [
    "juan", "maria", "carlos", "ana", "luis", "rosa", "jorge", "lucia", "pedro", "sofia",
    "miguel", "carla", "diego", "valeria", "andres", "daniela", "marco", "paola", "ivan",
    "elena", "raul", "camila", "oscar", "fernanda", "victor", "gabriela", "david", "nayra",
    "kevin", "brenda", "alex", "mariela", "ronald", "yesica", "franz", "noemi", "edson", "lidia",
]
APELLIDOS = [
    "mamani", "quispe", "choque", "flores", "condori", "gutierrez", "huanca", "vargas",
    "rojas", "mendoza", "copa", "colque", "torrez", "cruz", "apaza", "ticona", "villca",
    "callapa", "limachi", "lopez", "nina", "poma", "salazar", "yujra", "zeballos", "ramos",
    "ortega", "paco", "sanchez", "veliz",
]

Base.metadata.create_all(bind=engine)


def main():
    random.seed(2026)  # mismo resultado cada vez que se corre
    db = SessionLocal()
    hash_comun = hash_password(PASSWORD_PRUEBA)  # un solo hash: bcrypt es lento a propósito
    creadas, saltadas, filas = 0, 0, []
    try:
        for n in range(1, CANTIDAD + 1):
            email = f"{random.choice(NOMBRES)}.{random.choice(APELLIDOS)}{n:03d}@{DOMINIO}"
            if db.query(User).filter(User.email == email).first():
                saltadas += 1
                continue
            username = email.split("@")[0]  # ej. lucia.copa001
            db.add(User(username=username, email=email, password_hash=hash_comun, role=UserRole.student, is_verified=True))
            filas.append((username, email))
            creadas += 1
        db.commit()
    finally:
        db.close()

    with open("cuentas_estudiantes_prueba.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["usuario", "email", "password"])
        for username, email in filas:
            w.writerow([username, email, PASSWORD_PRUEBA])

    print(f"Cuentas creadas: {creadas} | ya existían: {saltadas}")
    print(f"Contraseña de todas: {PASSWORD_PRUEBA}  (lista en cuentas_estudiantes_prueba.csv)")


if __name__ == "__main__":
    main()
