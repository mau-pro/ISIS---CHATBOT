"""
models/ajuste.py
------------------
Ajustes del sistema que el admin cambia desde el panel y deben sobrevivir a un
reinicio (clave -> valor en JSON). Hoy: qué modelos de IA están activos y cuál
es el principal (clave "modelos_ia", ver services/groq_service.configurar_modelos).
"""

from sqlalchemy import Column, String, Text

from database import Base


class Ajuste(Base):
    __tablename__ = "ajustes"

    clave = Column(String(80), primary_key=True)
    valor = Column(Text, nullable=False)  # JSON
