"""
routes/documentos_routes.py
------------------------------
Endpoints PÚBLICOS (sin cuenta) para que
cualquiera que entra a la página de inicio pueda ver y descargar los
documentos que subió el admin, agrupados en las 3 secciones que se muestran
como tarjetas en el inicio:

- comunicados  -> categoría "aviso" (Avisos y comunicados)
- horarios     -> categoría "horario"
- docentes     -> categoría "docentes"

- GET /documentos                  -> lista los documentos de una sección (?seccion=...)
- GET /documentos/{id}/descargar   -> descarga el archivo original (no el texto extraído)
"""

import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models.document import Document, DocumentCategory, DocumentFile
from schemas import DocumentoPublicoResponse

router = APIRouter(prefix="/documentos", tags=["documentos públicos"])

SECCIONES_CATEGORIAS: dict[str, list[DocumentCategory]] = {
    "comunicados": [DocumentCategory.aviso],
    "horarios": [DocumentCategory.horario],
    "docentes": [DocumentCategory.docentes],
}


@router.get("", response_model=list[DocumentoPublicoResponse])
def listar_documentos_publicos(
    seccion: str = Query(..., description="comunicados | horarios | docentes"),
    db: Session = Depends(get_db),
):
    categorias = SECCIONES_CATEGORIAS.get(seccion)
    if categorias is None:
        raise HTTPException(
            status_code=400,
            detail=f"Sección inválida. Usá una de: {', '.join(SECCIONES_CATEGORIAS)}",
        )

    return (
        db.query(Document)
        .filter(Document.category.in_(categorias), Document.stored_filename.isnot(None))
        .order_by(Document.uploaded_at.desc())
        .all()
    )


@router.get("/{document_id}/descargar")
def descargar_documento(document_id: int, db: Session = Depends(get_db)):
    documento = db.query(Document).filter(Document.id == document_id).first()
    if not documento or not documento.stored_filename:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    archivo = db.get(DocumentFile, document_id)
    if archivo is None:
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible")

    tipo = mimetypes.guess_type(documento.filename)[0] or "application/octet-stream"
    nombre = quote(documento.filename)  # el nombre puede tener tildes o espacios (RFC 5987)
    return Response(
        content=bytes(archivo.contenido),
        media_type=tipo,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{nombre}"},
    )
