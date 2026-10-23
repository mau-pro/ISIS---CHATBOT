"""
migrar_a_postgres.py
--------------------
Copia TODOS los datos de app.db (SQLite) a PostgreSQL (users, documents,
document_files —los archivos originales—, chat_logs), conservando los ids. Los
vectores de ChromaDB no se tocan: no dependen de la base relacional.

Pasos:
  1. Instalar PostgreSQL y crear la base:   CREATE DATABASE asistente;
  2. Ejecutar:  python migrar_a_postgres.py "postgresql+psycopg2://postgres:CLAVE@localhost:5432/asistente"
  3. Poner esa misma URL en backend/.env como DATABASE_URL y reiniciar uvicorn.
Es seguro correrlo más de una vez: vacía las tablas destino antes de copiar.
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database import Base
import models.user, models.document, models.chat_log, models.ajuste  # noqa: F401  (registra las tablas)

TABLAS = ["users", "documents", "document_files", "chat_logs", "ajustes"]  # orden por claves foráneas


def main(url_destino: str):
    for prefijo in ("postgresql://", "postgres://"):  # igual que database.py
        if url_destino.startswith(prefijo):
            url_destino = "postgresql+psycopg2://" + url_destino[len(prefijo):]
    origen = create_engine("sqlite:///./app.db")
    destino = create_engine(url_destino)
    Base.metadata.create_all(bind=destino)

    with origen.connect() as src, destino.begin() as dst:
        dst.execute(text("TRUNCATE chat_logs, document_files, documents, users RESTART IDENTITY CASCADE"))
        for nombre in TABLAS:
            tabla = Base.metadata.tables[nombre]
            try:
                filas = [dict(r._mapping) for r in src.execute(tabla.select())]
            except Exception:  # la tabla puede no existir todavía en la SQLite de origen
                filas = []
            if filas:
                dst.execute(tabla.insert(), filas)
            # que el próximo id autogenerado continúe después del mayor copiado
            if filas and "id" in tabla.c and nombre != "document_files":
                dst.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{nombre}','id'), (SELECT MAX(id) FROM {nombre}))"
                ))
            print(f"{nombre}: {len(filas)} filas copiadas")
    print("Migración terminada. Definí DATABASE_URL en .env y reiniciá el backend.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
