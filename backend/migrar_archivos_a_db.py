"""
migrar_archivos_a_db.py
-------------------------
Mete dentro de la base de datos (tabla document_files) los archivos originales que estaban
sueltos en la carpeta uploads/, y guarda el tamaño de cada uno en documents.tamano_bytes.
Es seguro repetirlo: solo copia los que todavía no están en la base.

Uso (desde backend/, con la base configurada en DATABASE_URL o la SQLite por defecto):
    python migrar_archivos_a_db.py [carpeta]      # carpeta por defecto: uploads
Dentro de Docker:
    docker compose exec backend python migrar_archivos_a_db.py /app/uploads
"""

import os
import sys

from database import Base, engine, SessionLocal
from models.document import Document, DocumentFile
import models.user, models.chat_log  # noqa: F401  (registra todas las tablas)


def main(carpeta: str) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    copiados = ya_estaban = sin_archivo = 0
    try:
        for doc in db.query(Document).filter(Document.stored_filename.isnot(None)).order_by(Document.id).all():
            if db.get(DocumentFile, doc.id) is not None:
                ya_estaban += 1
                if doc.tamano_bytes is None:  # por si faltaba el tamaño
                    doc.tamano_bytes = len(db.get(DocumentFile, doc.id).contenido)
                continue
            ruta = os.path.join(carpeta, doc.stored_filename)
            if not os.path.exists(ruta):
                sin_archivo += 1
                print(f"  sin archivo en {carpeta}: id {doc.id} ({doc.filename})")
                continue
            with open(ruta, "rb") as f:
                datos = f.read()
            db.add(DocumentFile(document_id=doc.id, contenido=datos))
            doc.tamano_bytes = len(datos)
            copiados += 1
            if copiados % 100 == 0:
                db.commit()
                print(f"  {copiados} archivos copiados...", flush=True)
        db.commit()
    finally:
        db.close()
    print(f"Listo: {copiados} archivos copiados a la base | {ya_estaban} ya estaban | {sin_archivo} sin archivo.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "uploads")
