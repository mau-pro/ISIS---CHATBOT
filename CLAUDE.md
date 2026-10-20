# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

Sistema RAG (FastAPI + React) para una universidad. Un admin sube documentos (PDF/Word/Excel/Imagen), el sistema los indexa en ChromaDB, y los estudiantes (con cuenta; no hay chat anónimo) consultan por chat sobre horarios, docentes, avisos y comunicados. Las respuestas las genera Groq (modelo `openai/gpt-oss-120b`) usando solo el contexto recuperado.

No hay tests ni linters configurados en el repo.

## Comandos

Backend (desde `backend/`):
```bash
venv\Scripts\activate                    # Windows; activar el venv existente
uvicorn main:app --reload                # http://127.0.0.1:8000/docs
python seed_admin.py                     # crea/actualiza la cuenta admin desde .env
```

Frontend (desde `frontend/`):
```bash
npm run dev       # http://localhost:5173
npm run build
npm run preview
```

**Docker**: `docker compose up -d --build` levanta db (PostgreSQL), backend y frontend (nginx en el puerto 80, `/api` -> backend); ver la sección "Despliegue con Docker" del README. Datos en volúmenes (`pgdata` = cuentas, historial y archivos originales; `chroma` = índice de búsqueda). El frontend usa `VITE_API_URL` (`/api` en Docker, `http://localhost:8000` en desarrollo) y el backend acepta orígenes extra con `CORS_ORIGINS`.

En desarrollo, el backend espera el frontend en `http://localhost:5173` (CORS en [backend/main.py](backend/main.py)). Variables de entorno en `backend/.env` (ver `.env.example`): `JWT_SECRET_KEY`, `GROQ_API_KEY`, `ADMIN_EMAIL`/`ADMIN_PASSWORD`, `RATE_LIMIT_ESTUDIANTE`, SMTP para verificación de correo, `PRESUPUESTO_TOKENS_CONTEXTO`.

## Arquitectura

**Ahorro de tokens (orden de intentos en `/chat`)**: 0) `services/intencion.py` detecta mensajes que NO son consultas (situaciones personales como "reprobé todo el quinto semestre", saludos, gracias, despedidas, "¿qué podés hacer?") y responde con un texto fijo, sin IA; 1) `services/respuesta_directa.py` arma con código (0 tokens) las listas exactas de materias/docentes/horarios cuando la pregunta trae un filtro semestre/grupo/sigla y ninguna palabra extra; 2) `cache_service` reutiliza respuestas ya generadas (misma firma + similitud >= 88%); 3) recién ahí Groq, con un ENCADENADO de modelos gratuitos (`groq_service.MODELOS`: `gpt-oss-120b` → `qwen/qwen3.8-27b` → `gpt-oss-20b`; cada uno tiene su propio cupo, si uno devuelve 429 se bloquea un rato y el pedido sigue con el siguiente; orden configurable con `MODELOS_IA` en `.env`; qwen exige `max_tokens` <= 1000). El caché NO se vacía entero al subir/borrar/releer un documento: `invalidar_por_documento` borra solo lo que ese documento puede haber cambiado. El admin ve y borra preguntas aprendidas en Estadísticas (`/admin/cache`). Cada consulta guarda los tokens gastados (`chat_logs.tokens`); límites del plan gratuito de Groq POR MODELO: 30 consultas/min, 1.000/día, 8.000 tokens/min y 200.000 tokens/día (si todos los modelos están agotados por minuto se espera el `retry-after` y se reintenta; si no hay remedio, `/chat` devuelve 503 con un mensaje claro).

**Flujo de una pregunta de chat** ([backend/routes/chat_routes.py](backend/routes/chat_routes.py)): combina 4 fuentes de contexto en orden de prioridad y sin duplicar:
1. **Filtro exacto** — `query_parser.detectar_filtro()` detecta semestre/grupo/sigla en la pregunta; si hay match, `vector_service.search_por_filtro_estructurado()` trae TODAS las filas que cumplen (no solo las "parecidas") y se arman como un único bloque JSON compacto.
2. **Búsqueda por texto** — `query_parser.extraer_terminos()` saca palabras clave (ej. nombre de un docente) y `vector_service.search_por_texto()` busca coincidencia exacta de texto (case-insensitive, probando 3 variantes de capitalización).
3. **Búsqueda en imágenes** — `vector_service.buscar_en_imagenes()` compara las palabras de la pregunta con el texto OCR de cada imagen completa, sin tildes ni mayúsculas y aceptando palabras parecidas (el OCR se equivoca); devuelve todos los fragmentos de las mejores imágenes y, si una coincide con 3+ palabras, se descartan los fragmentos de otros documentos. En `search_por_texto`, las palabras raras pesan más que las comunes y, si hay alguna muy rara, se descartan los fragmentos que solo coinciden por palabras comunes.
4. **Búsqueda semántica** — `vector_service.search()`, respaldo general por similitud vía ChromaDB.

Luego `groq_service.preparar_contexto()` recorta los fragmentos combinados a un presupuesto de tokens (recortando desde el final, lo menos prioritario) antes de llamar a Groq, y `groq_service.limpiar_formato()` post-procesa la respuesta con regex para garantizar texto plano (sin Markdown/emojis) sin depender de que el modelo obedezca el system prompt.

**Ingesta de documentos** ([backend/services/file_ingest_service.py](backend/services/file_ingest_service.py)): PDF/Word se trocean por caracteres (`chunk_text`, con overlap). Excel es distinto: cada fila se indexa como su propio chunk indivisible (`filas_con_metadata`), y cada columna del Excel se guarda como metadata estructurada en ChromaDB — eso es lo que permite el filtro exacto del punto 1. Imágenes pasan por OCR local (Tesseract) antes de indexarse, nunca se manda la imagen a un modelo de IA. El OCR (`extract_text_from_image`) prueba varias versiones de la imagen y se queda con la de mayor confianza; si queda poco texto corrido (carteles), agrega pasadas en modo "texto disperso" y suma las palabras nuevas al final ("Otras palabras detectadas…"). Usa `spa+eng` solo si el Tesseract instalado tiene el idioma `spa` (hoy solo tiene `eng`). Las imágenes ya subidas se releen con `POST /admin/documents/reindexar-imagenes` (opcional `?ids=`).

**Embeddings**: los genera ChromaDB con su función por defecto al indexar (`vector_service.py`), no dependen de la API de Groq — indexar documentos no consume tokens de Groq.

**Auth** ([backend/services/auth_service.py](backend/services/auth_service.py)): JWT propio (no OAuth externo). Un mismo mecanismo de token con campo `purpose` distingue sesión normal, verificación de email y reset de contraseña, para que un token no sirva para otro fin. `/chat` exige sesión (`get_current_user`). El login usa **nombre de usuario** (`users.username`, único, minúsculas, sin distinguir mayúsculas; reglas en `services/username_service.py`), no el correo; el correo queda para verificar la cuenta y recuperar la contraseña, y el `sub` del JWT sigue siendo el email. Las cuentas anteriores recibieron su usuario automáticamente (parte del correo antes de la @) en la migración de `main.py`.

**Rate limiting** ([backend/services/rate_limit_service.py](backend/services/rate_limit_service.py)): explícito por rol dentro del endpoint `/chat`, no un middleware global — estudiante por email, admin sin límite. Usa `MemoryStorage` (un solo proceso); si el proyecto escala a múltiples instancias hay que pasar a `RedisStorage`.

**Migraciones**: no hay Alembic. `main.py` corre `Base.metadata.create_all()` (crea tablas nuevas) y además `_migrar_columnas_faltantes()`, que agrega a mano con `ALTER TABLE` las columnas que se sumaron después del primer despliegue de `app.db`. Si se agrega una columna a un modelo existente, hay que sumar su ALTER TABLE ahí también.

**Listados del admin**: usuarios y documentos se paginan en el servidor (`GET /admin/users` y `GET /admin/documents` con `page`, `page_size`, `q`; responden `{items, total, page, page_size}`); el frontend pide una página por clic.

**Documentos públicos** ([backend/routes/documentos_routes.py](backend/routes/documentos_routes.py)): 3 secciones visibles sin cuenta (comunicados, horarios, docentes) mapeadas a las 4 categorías de `DocumentCategory` (horario, docentes, aviso, otro; "comunicados" = `aviso`; la antigua `convocatoria` se migra a `aviso` al arrancar). El archivo ORIGINAL se guarda dentro de la base (tabla `document_files`, columna binaria; el tamaño en `documents.tamano_bytes`) para poder descargarlo tal cual y para que un solo respaldo de la base lo incluya todo; el texto extraído solo vive en ChromaDB (reconstruible desde los archivos). `uploads/` ya no se usa salvo para migrar archivos viejos con `migrar_archivos_a_db.py`.

**Frontend**: rutas definidas en [frontend/src/App.jsx](frontend/src/App.jsx). El asistente se llama **I-SIS** (nombre en chat, portada, mensajes fijos y prompt de Groq). La portada (`pages/Home.jsx`, rutas `/` y `/login`) integra la tarjeta de login (`components/LoginCard.jsx`: un solo formulario, el rol lo devuelve el backend y decide el destino /admin o /chat; "Recuérdame" = localStorage vs sessionStorage, ver `utils/sesion.js`), la mascota SVG y el fondo del edificio; si existe `frontend/public/edificio-uatf.jpg` se usa como foto de fondo, si no se dibuja una silueta. `RutaProtegida` (con prop `soloAdmin`) protege `/chat` (estudiante) y `/admin`. Tema visual único "neón" (oscuro, vidrio, cian/violeta/rosa, fuente Outfit): los tokens y overrides viven en [frontend/src/styles/moderno.css](frontend/src/styles/moderno.css), importado al final de `main.jsx`; los logos de la UATF y de la carrera están centralizados en `components/Logos.jsx`. Estado de auth en `context/AuthContext.jsx`, llamadas HTTP centralizadas en `services/api.js`.
