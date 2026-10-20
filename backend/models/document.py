"""
models/document.py
-------------------
Define la tabla `documents`: guarda metadata de cada archivo que el admin
sube (PDF, Word, Excel o Imagen). El texto trozado para la búsqueda vive en
ChromaDB. El archivo ORIGINAL se guarda dentro de la propia base (tabla
document_files, ver abajo) para que los estudiantes puedan descargarlo tal
cual lo subió el admin —no el texto extraído— desde las secciones públicas
del inicio, y para que un solo respaldo de la base lo incluya todo.
"""

import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, LargeBinary
from sqlalchemy.sql import func

from database import Base


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
    stored_filename = Column(String, nullable=True)  # marca de que el archivo original está guardado (en document_files)

    # Tamaño del archivo original en bytes (se guarda al subirlo, así las listas no tocan los archivos)
    tamano_bytes = Column(Integer, nullable=True)

    @property
    def size_bytes(self) -> int | None:
        """Nombre que usa la API (DocumentResponse) para el tamaño del archivo original."""
        return self.tamano_bytes


class DocumentFile(Base):
    """
    El archivo ORIGINAL (PDF, Word, Excel, imagen) guardado dentro de PostgreSQL.
    Va en una tabla aparte para que listar documentos no cargue los archivos
    completos; solo se lee al descargar o al releer una imagen con OCR.
    """

    __tablename__ = "document_files"

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    contenido = Column(LargeBinary, nullable=False)  # bytea en PostgreSQL, BLOB en SQLite
