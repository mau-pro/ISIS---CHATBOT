"""
models/user.py
---------------
Define la tabla `users`. Cada usuario tiene un rol:
- "admin": puede subir/eliminar documentos, sin límite de consultas.
- "student": se registra libremente, tiene límite de consultas por hora.
"""

import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean
from sqlalchemy.sql import func

from database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    student = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # Nombre con el que se inicia sesión (el correo se usa solo para verificar y recuperar la contraseña)
    username = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
