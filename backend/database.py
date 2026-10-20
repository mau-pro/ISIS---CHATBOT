"""
database.py
-----------
Configura la conexión a la base de datos y expone:
- `engine`: motor de conexión SQLAlchemy
- `SessionLocal`: fábrica de sesiones para cada request
- `Base`: clase base de la que heredan todos los modelos
- `get_db`: dependencia de FastAPI que entrega una sesión y la cierra al terminar
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Por defecto SQLite (un archivo, ideal para desarrollo). Para producción se
# define DATABASE_URL en el .env apuntando a PostgreSQL, por ejemplo:
#   DATABASE_URL=postgresql+psycopg2://postgres:CLAVE@localhost:5432/asistente
# El resto del código no cambia: SQLAlchemy abstrae el motor.
load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Supabase, Neon y Heroku entregan la URL como "postgresql://..." o "postgres://...",
# pero SQLAlchemy necesita indicar el driver: se acepta tal cual la dan.
for _prefijo in ("postgresql://", "postgres://"):
    if SQLALCHEMY_DATABASE_URL.startswith(_prefijo):
        SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://" + SQLALCHEMY_DATABASE_URL[len(_prefijo):]

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},  # necesario solo para SQLite
    )
else:
    # pool_pre_ping revalida conexiones caídas; pool_size permite atender
    # varias consultas de estudiantes en paralelo (lo que SQLite no hace bien).
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: abre una sesión de BD y garantiza que se cierre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
