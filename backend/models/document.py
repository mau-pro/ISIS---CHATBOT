"""
models/document.py
-------------------
Define la tabla `documents`: guarda metadata de cada archivo que el admin
sube (PDF, Word, Excel o Imagen). El texto trozado para la búsqueda vive en
ChromaDB; acá además se guarda stored_filename, el nombre con el que se
guardó una COPIA del archivo original en disco (carpeta uploads/), para que
los estudiantes puedan descargar el archivo tal cual lo subió el admin
—no el texto extraído— desde las secciones públicas del inicio.
"""

import enum
import os
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func

from database import Base

UPLOADS_DIR = "uploads"


class DocumentCategory(str, enum.Enum):
    horario = "horario"
    docentes = "docentes"
    aviso = "aviso"  # "Avisos y comunicados" (incluye las antiguas convocatorias)
    otro = "otro"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_type = Column(String, nullable=False)  # pdf | docx | xlsx | png | jpg...
    category = Column(Enum(DocumentCategory), default=DocumentCategory.otro)
    chunk_count = Column(Integer, default=0)  # cuántos chunks se indexaron en ChromaDB
    uploaded_by = Column(Integer, nullable=False)  # id del admin que lo subió
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    stored_filename = Column(String, nullable=True)  # nombre del archivo copiado en uploads/

    @property
    def size_bytes(self) -> int | None:
        """
        Tamaño del archivo original en disco, calculado al vuelo (no se
        guarda en la base). None si el documento no tiene copia guardada
        (subido antes de que existiera stored_filename) o si el archivo ya
        no está en uploads/.
        """
        if not self.stored_filename:
            return None
        try:
            return os.path.getsize(os.path.join(UPLOADS_DIR, self.stored_filename))
        except OSError:
            return None
