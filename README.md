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
