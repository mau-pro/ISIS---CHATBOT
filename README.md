# Asistente Virtual Universitario

Sistema RAG con administrador (sube PDF/Word/Excel) y estudiantes (consultan
horarios, docentes, avisos y comunicados). Las consultas requieren cuenta de
estudiante (o de administrador).

## Estructura

```
backend/     FastAPI + SQLite + ChromaDB + Groq
frontend/    React + Vite
```

## Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt --break-system-packages

copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
# completar JWT_SECRET_KEY, GROQ_API_KEY, ADMIN_EMAIL, ADMIN_PASSWORD

python seed_admin.py         # crea la cuenta de administrador
uvicorn main:app --reload    # http://127.0.0.1:8000/docs
```

## Frontend

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

## Flujo de uso

1. El admin inicia sesión con su nombre de usuario (`ADMIN_USERNAME` en `.env`, o la parte del correo antes de la @) y la contraseña definida en `.env`.
2. Desde `/admin`, arrastra archivos PDF/Word/Excel y elige una categoría
   (horarios, docentes, avisos y comunicados, otros).
3. Los estudiantes se registran en `/register` (nombre de usuario, correo y contraseña; inician sesión solo con el usuario) y consultan en `/chat`.
4. Sin cuenta solo se pueden ver y descargar los documentos públicos desde `/`.

## Próximos pasos sugeridos last

- Ajustar los límites de `RATE_LIMIT_ESTUDIANTE` en `.env`.
- Agregar verificación de correo institucional en el registro.
- Migrar de SQLite a PostgreSQL si el proyecto se despliega en producción.
- Mejorar el diseño del frontend (por ahora es funcional, sin estilos avanzados).

## Despliegue con Docker

El proyecto corre con tres contenedores (`docker-compose.yml`): **db** (PostgreSQL 16), **backend**
(FastAPI + Tesseract en español + ChromaDB) y **frontend** (nginx, puerto 80, que reenvía `/api` al backend).

### Primera vez
1. Instalar Docker (Docker Desktop en Windows, o `docker` + `docker compose` en Linux).
2. `cp .env.docker.example .env` y completar `POSTGRES_PASSWORD` y `PUBLIC_URL`.
3. Crear `backend/.env` (ver `backend/.env.example`): `GROQ_API_KEY`, `JWT_SECRET_KEY` (larga y aleatoria),
   `ADMIN_EMAIL`, `ADMIN_PASSWORD`, SMTP. No hace falta `DATABASE_URL`: el compose la define.
4. `docker compose up -d --build`
5. Crear la cuenta de administrador: `docker compose exec backend python seed_admin.py`
6. Abrir `http://localhost` (o el dominio configurado en `PUBLIC_URL`).

### Pasar los datos que ya tenías (opcional)
```bash
# 1) En tu PC (modo desarrollo): meter los archivos de uploads/ dentro de app.db
cd backend && python migrar_archivos_a_db.py uploads && cd ..
# 2) Pasar todo a PostgreSQL: cuentas, historial, documentos y sus archivos originales
docker compose cp backend/app.db backend:/app/app.db
docker compose exec backend sh -c 'python migrar_a_postgres.py "$DATABASE_URL"'
docker compose exec backend rm -f /app/app.db
# 3) Índice de búsqueda (ChromaDB)
docker compose cp backend/chroma_data/. backend:/app/chroma_data/
docker compose restart backend
```
Si el índice copiado da errores (distinta versión de ChromaDB), borrá el volumen `chroma` y volvé a subir
los documentos, o releé las imágenes con `POST /admin/documents/reindexar-imagenes`.

### Operación
- Ver registros: `docker compose logs -f backend`
- Actualizar: `git pull && docker compose up -d --build` (los datos están en volúmenes y no se pierden).
- **Respaldo** (hacerlo a diario y guardarlo FUERA del servidor):
  `docker compose exec db pg_dump -U isis asistente > respaldo.sql`, más una copia del volumen `chroma` (el índice de búsqueda, que se puede reconstruir). Cuentas, historial **y archivos originales** viven dentro de PostgreSQL, así que `pg_dump` los incluye.
- Un solo proceso del backend a propósito: el límite de consultas por estudiante vive en memoria.
- La base de datos no se expone a internet; solo la ve el backend por la red interna de Docker.
