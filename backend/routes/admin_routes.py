"""
routes/admin_routes.py
------------------------
Endpoints protegidos (solo admin, vía get_current_admin):
- POST   /admin/documents         -> sube un archivo (PDF/Word/Excel/Imagen), lo procesa e indexa
- GET    /admin/documents         -> lista paginada (?page&page_size&q) de los documentos subidos
- POST   /admin/documents/reindexar-imagenes -> vuelve a leer con OCR las imágenes ya subidas
- DELETE /admin/documents/{id}    -> elimina un documento y sus chunks en ChromaDB
- GET    /admin/stats             -> estadísticas generales del sistema
- GET    /admin/users             -> lista todos los usuarios (para gestionar roles)
- PATCH  /admin/users/{id}/role   -> cambia el rol de un usuario (estudiante <-> admin)
- DELETE /admin/users/{id}        -> elimina la cuenta de un usuario
- GET/DELETE /admin/cache[/{id}]  -> ver / olvidar las preguntas aprendidas (caché)
"""

import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pytesseract import TesseractNotFoundError

from database import get_db
from models.user import User, UserRole
from models.document import Document, DocumentCategory
from models.chat_log import ChatLog
from schemas import (
    DocumentResponse,
    DocumentosPaginados,
    StatsResponse,
    UserAdminResponse,
    RoleUpdateRequest,
    UsuariosPaginados,
)
from services.auth_service import get_current_admin
from services.file_ingest_service import extract_text, chunk_text, filas_con_metadata, EXTENSIONES_IMAGEN
from services.groq_service import MODELOS
from services.vector_service import index_chunks, delete_document_chunks, obtener_chunks_de_documento
from services.cache_service import (
    vaciar_cache,
    cantidad_en_cache,
    listar_cache,
    borrar_de_cache,
    invalidar_por_documento,
)

router = APIRouter(prefix="/admin", tags=["admin"])

EXTENSIONES_PERMITIDAS = {"pdf", "docx", "xlsx", "xlsm"} | EXTENSIONES_IMAGEN
TAMANO_MAXIMO_MB = 15
UPLOADS_DIR = "uploads"


@router.post("/documents", response_model=DocumentResponse)
async def subir_documento(
    file: UploadFile = File(...),
    category: DocumentCategory = Form(DocumentCategory.otro),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    extension = file.filename.lower().rsplit(".", 1)[-1]
    if extension not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Usa: {', '.join(EXTENSIONES_PERMITIDAS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"El archivo supera los {TAMANO_MAXIMO_MB}MB")

    # 1. Extraer texto según el tipo de archivo
    try:
        if extension in ("xlsx", "xlsm"):
            # Los Excel se trocean por fila (cada registro es una unidad
            # completa), no por cantidad de caracteres — y cada fila trae
            # su metadata estructurada (semestre, grupo, sigla, etc.) para
            # poder filtrar exacto en preguntas tipo "todas las materias
            # del semestre 1" — ver services/query_parser.py.
            filas = filas_con_metadata(file_bytes)
            chunks = [texto for texto, _ in filas]
            metadatas_extra = [metadata for _, metadata in filas]
            texto = "\n".join(chunks)  # solo para la validación de abajo
        else:
            texto = extract_text(file.filename, file_bytes)
            chunks = None  # se calcula más abajo con chunk_text()
            metadatas_extra = None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TesseractNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=(
                "El servidor no tiene instalado el programa Tesseract-OCR "
                "(necesario para leer texto de imágenes). Instalalo en la "
                "máquina donde corre el backend y, si no queda en el PATH, "
                "definí la variable de entorno TESSERACT_CMD con la ruta al "
                "ejecutable (ej. C:\\Program Files\\Tesseract-OCR\\tesseract.exe)."
            ),
        )

    if not texto.strip():
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del archivo")

    # 2. Registrar el documento en la base de datos
    nuevo_doc = Document(
        filename=file.filename,
        original_type=extension,
        category=category,
        chunk_count=0,
        uploaded_by=admin.id,
    )
    db.add(nuevo_doc)
    db.commit()
    db.refresh(nuevo_doc)

    # 2.5. Guardar una copia del archivo original en disco (uploads/), para
    # que los estudiantes puedan descargarlo tal cual desde las secciones
    # públicas del inicio. El nombre en disco usa el id (no el filename que
    # mandó el usuario) para no pisar archivos ni depender de caracteres
    # raros en el nombre original.
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    stored_filename = f"{nuevo_doc.id}.{extension}"
    with open(os.path.join(UPLOADS_DIR, stored_filename), "wb") as destino:
        destino.write(file_bytes)
    nuevo_doc.stored_filename = stored_filename

    # 3. Trocear (si no se hizo ya arriba) e indexar en ChromaDB
    if chunks is None:
        chunks = chunk_text(texto)
    cantidad = index_chunks(
        nuevo_doc.id, nuevo_doc.filename, category.value, chunks, metadatas_extra
    )

    nuevo_doc.chunk_count = cantidad
    # Solo se olvidan las respuestas que este documento puede haber cambiado
    invalidar_por_documento(chunks, metadatas_extra)
    db.commit()
    db.refresh(nuevo_doc)

    return nuevo_doc


@router.post("/documents/reindexar-imagenes")
def reindexar_imagenes(
    ids: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Vuelve a leer con OCR las imágenes ya subidas (usando la copia original
    guardada en uploads/) y reemplaza su texto indexado. Sirve cuando se
    mejora el OCR: las imágenes viejas conservan la lectura anterior hasta
    que se reindexan. `ids` (opcional) limita a esos documentos.
    """
    consulta = db.query(Document).filter(
        Document.original_type.in_(sorted(EXTENSIONES_IMAGEN)), Document.stored_filename.isnot(None)
    )
    if ids:
        consulta = consulta.filter(Document.id.in_(ids))

    resultado = []
    for doc in consulta.order_by(Document.id).all():
        ruta = os.path.join(UPLOADS_DIR, doc.stored_filename)
        if not os.path.exists(ruta):
            resultado.append({"id": doc.id, "filename": doc.filename, "estado": "sin archivo original"})
            continue
        with open(ruta, "rb") as f:
            texto = extract_text(doc.filename, f.read())
        if not texto.strip():
            resultado.append({"id": doc.id, "filename": doc.filename, "estado": "el OCR no encontró texto (se conserva el anterior)"})
            continue
        viejos, metas_viejas = obtener_chunks_de_documento(doc.id)
        delete_document_chunks(doc.id)
        nuevos = chunk_text(texto)
        doc.chunk_count = index_chunks(doc.id, doc.filename, doc.category.value, nuevos)
        invalidar_por_documento(viejos + nuevos, metas_viejas)
        db.commit()
        resultado.append({"id": doc.id, "filename": doc.filename, "estado": "reindexada", "fragmentos": doc.chunk_count})

    return {"reindexadas": resultado}


@router.get("/documents", response_model=DocumentosPaginados)
def listar_documentos(
    page: int = 1,
    page_size: int = 6,
    q: str = "",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Documentos paginados en el servidor: solo se envían los de la página pedida
    (con cientos de documentos no tiene sentido traerlos todos de golpe). `q` filtra por nombre."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    consulta = db.query(Document)
    if q.strip():
        consulta = consulta.filter(Document.filename.ilike(f"%{q.strip()}%"))
    total = consulta.count()
    items = (
        consulta.order_by(Document.uploaded_at.desc(), Document.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return DocumentosPaginados(items=items, total=total, page=page, page_size=page_size)


@router.delete("/documents/{document_id}")
def eliminar_documento(
    document_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    documento = db.query(Document).filter(Document.id == document_id).first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    textos, metas = obtener_chunks_de_documento(document_id)
    delete_document_chunks(document_id)
    if documento.stored_filename:
        ruta = os.path.join(UPLOADS_DIR, documento.stored_filename)
        if os.path.exists(ruta):
            os.remove(ruta)
    db.delete(documento)
    db.commit()
    invalidar_por_documento(textos, metas)

    return {"detail": "Documento eliminado correctamente"}


@router.get("/stats", response_model=StatsResponse)
def obtener_estadisticas(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    total_estudiantes = db.query(User).filter(User.role == UserRole.student).count()
    total_documentos = db.query(Document).count()
    total_fragmentos = db.query(func.sum(Document.chunk_count)).scalar() or 0
    # Las consultas de prueba del admin (panel "Probar Chatbot") no cuentan
    # acá: son pruebas del propio admin, no consultas reales de estudiantes.
    total_consultas = db.query(ChatLog).filter(ChatLog.es_prueba == False).count()  # noqa: E712

    inicio_hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    consultas_hoy = (
        db.query(ChatLog)
        .filter(ChatLog.created_at >= inicio_hoy, ChatLog.es_prueba == False)  # noqa: E712
        .count()
    )

    tokens_hoy = (
        db.query(func.coalesce(func.sum(ChatLog.tokens), 0)).filter(ChatLog.created_at >= inicio_hoy).scalar() or 0
    )

    # Tokens gastados hoy por modelo (los registros anteriores al encadenado eran del preferido)
    tokens_por_modelo = {m: 0 for m in MODELOS}
    filas_modelo = (
        db.query(ChatLog.modelo, func.sum(ChatLog.tokens))
        .filter(ChatLog.created_at >= inicio_hoy, ChatLog.tokens > 0)
        .group_by(ChatLog.modelo)
        .all()
    )
    for modelo, total in filas_modelo:
        tokens_por_modelo[modelo or MODELOS[0]] = tokens_por_modelo.get(modelo or MODELOS[0], 0) + int(total or 0)

    filas_categoria = (
        db.query(Document.category, func.count(Document.id))
        .group_by(Document.category)
        .all()
    )
    consultas_por_categoria = {categoria.value: cantidad for categoria, cantidad in filas_categoria}

    return StatsResponse(
        total_estudiantes=total_estudiantes,
        total_documentos=total_documentos,
        total_fragmentos=total_fragmentos,
        total_consultas=total_consultas,
        respuestas_desde_cache=db.query(ChatLog).filter(ChatLog.desde_cache == True, ChatLog.es_prueba == False).count(),  # noqa: E712
        preguntas_aprendidas=cantidad_en_cache(),
        tokens_hoy=int(tokens_hoy),
        tokens_por_modelo=tokens_por_modelo,
        consultas_hoy=consultas_hoy,
        consultas_por_categoria=consultas_por_categoria,
    )


@router.get("/cache")
def ver_preguntas_aprendidas(admin: User = Depends(get_current_admin)):
    """Preguntas que el sistema aprendió (caché), las más reutilizadas primero."""
    return listar_cache()


@router.delete("/cache/{id_pregunta}")
def borrar_pregunta_aprendida(id_pregunta: str, admin: User = Depends(get_current_admin)):
    """Olvida UNA pregunta aprendida (por ejemplo si su respuesta guardada estaba mal)."""
    borrar_de_cache(id_pregunta)
    return {"detail": "Pregunta olvidada"}


@router.delete("/cache")
def vaciar_preguntas_aprendidas(admin: User = Depends(get_current_admin)):
    """Olvida TODAS las preguntas aprendidas."""
    vaciar_cache()
    return {"detail": "Se olvidaron todas las preguntas aprendidas"}


@router.get("/users", response_model=UsuariosPaginados)
def listar_usuarios(
    page: int = 1,
    page_size: int = 10,
    q: str = "",
    rol: str = "",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Usuarios paginados (con 250+ cuentas no tiene sentido traerlas todas de golpe).
    `rol` ("admin" | "student") filtra por rol; los totales por rol son globales."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    consulta = db.query(User)
    if q.strip():
        patron = f"%{q.strip()}%"
        consulta = consulta.filter(or_(User.email.ilike(patron), User.username.ilike(patron)))
    if rol in ("admin", "student"):
        consulta = consulta.filter(User.role == UserRole(rol))
    total = consulta.count()
    items = (
        consulta.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_admins = db.query(User).filter(User.role == UserRole.admin).count()
    return UsuariosPaginados(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_admins=total_admins,
        total_estudiantes=db.query(User).count() - total_admins,
    )


@router.patch("/users/{user_id}/role", response_model=UserAdminResponse)
def cambiar_rol(
    user_id: int,
    data: RoleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=400, detail="No podés cambiar tu propio rol"
        )

    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.role = data.role
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/users/{user_id}")
def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=400, detail="No podés eliminar tu propia cuenta"
        )

    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Borrar primero su historial de chat, para no dejar registros huérfanos
    db.query(ChatLog).filter(ChatLog.user_id == user_id).delete()
    db.delete(usuario)
    db.commit()

    return {"detail": "Usuario eliminado correctamente"}