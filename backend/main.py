"""
main.py
-------
Punto de entrada de la aplicación. Se encarga de:
1. Crear las tablas de la base de datos si no existen.
2. Configurar CORS para que el frontend (Vite, puerto 5173) pueda consultar la API.
3. Registrar las rutas de cada módulo (auth, admin, chat).

Ejecutar con: uvicorn main:app --reload
"""

import os

from sqlalchemy import inspect, text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routes import auth_routes, admin_routes, chat_routes, documentos_routes
from services.username_service import username_desde_email
from models import chat_log, ajuste  # noqa: F401 — registra las tablas chat_logs y ajustes en Base.metadata

# Crea las tablas (users, documents) si el archivo app.db no existe todavía.
Base.metadata.create_all(bind=engine)


def _migrar_columnas_faltantes() -> None:
    """
    create_all() solo crea tablas que no existen; no agrega columnas nuevas
    a una tabla que ya existía (ej. app.db de una versión anterior). Este
    proyecto no usa Alembic, así que acá se agregan a mano, con ALTER TABLE,
    las columnas que se sumaron después del primer despliegue.
    """
    inspector = inspect(engine)
    columnas_chat_logs = {c["name"] for c in inspector.get_columns("chat_logs")}
    if "es_prueba" not in columnas_chat_logs:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE chat_logs ADD COLUMN es_prueba BOOLEAN NOT NULL DEFAULT FALSE"))

    if "desde_cache" not in columnas_chat_logs:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE chat_logs ADD COLUMN desde_cache BOOLEAN NOT NULL DEFAULT FALSE"))

    if "tokens" not in columnas_chat_logs:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE chat_logs ADD COLUMN tokens INTEGER NOT NULL DEFAULT 0"))

    if "tamano_bytes" not in {c["name"] for c in inspector.get_columns("documents")}:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN tamano_bytes INTEGER"))

    if "modelo" not in columnas_chat_logs:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE chat_logs ADD COLUMN modelo VARCHAR"))

    columnas_documents = {c["name"] for c in inspector.get_columns("documents")}
    if "stored_filename" not in columnas_documents:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN stored_filename VARCHAR"))

    # Nombre de usuario para el login: las cuentas existentes lo reciben a partir
    # de su correo (parte antes de la @). SQLite no permite agregar una columna
    # UNIQUE con ALTER TABLE, así que la unicidad se da con un índice único.
    columnas_users = {c["name"] for c in inspector.get_columns("users")}
    if "username" not in columnas_users:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR"))
    with engine.begin() as conn:
        sin_username = conn.execute(text("SELECT id, email FROM users WHERE username IS NULL")).fetchall()
        if sin_username:
            usados = {r[0] for r in conn.execute(text("SELECT username FROM users WHERE username IS NOT NULL"))}
            for user_id, email in sin_username:
                conn.execute(
                    text("UPDATE users SET username = :u WHERE id = :i"),
                    {"u": username_desde_email(email, usados), "i": user_id},
                )
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))

    # La categoría "convocatoria" se fusionó con "aviso" (quedan 4 categorías:
    # horario, docentes, aviso, otro). Si no se convierten las filas viejas,
    # leerlas fallaría porque ya no existe ese valor en el Enum.
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE documents SET category = 'aviso' WHERE category = 'convocatoria'"))
    except Exception:
        # En una base nueva (PostgreSQL) el tipo enum ya no tiene "convocatoria": no hay nada que convertir
        pass


_migrar_columnas_faltantes()

# Orígenes del frontend autorizados a llamar a la API. En desarrollo es Vite (5173); en Docker
# el frontend y la API comparten dominio (nginx), pero se puede ampliar con CORS_ORIGINS
# (lista separada por comas, ej. "https://isis.midominio.edu.bo").
_ORIGENES_PERMITIDOS = ["http://localhost:5173"] + [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]

app = FastAPI(title="Asistente Virtual Universitario")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGENES_PERMITIDOS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(chat_routes.router)
app.include_router(documentos_routes.router)


@app.on_event("startup")
def _cargar_modelos_ia():
    """Recupera qué modelos de IA dejó activos el admin (panel Estadísticas)."""
    from database import SessionLocal
    from services.ajustes_service import aplicar_modelos_guardados

    with SessionLocal() as db:
        aplicar_modelos_guardados(db)


@app.on_event("startup")
def _precalentar_embeddings():
    """La primera búsqueda carga el modelo de embeddings (segundos). Se hace
    al arrancar para que ningún estudiante pague esa espera."""
    try:
        from services.vector_service import search
        search("precalentamiento", n_results=1)
    except Exception:
        pass


@app.get("/")
def root():
    return {"status": "ok", "servicio": "Asistente Virtual Universitario"}
