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

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models.document import Document, DocumentCategory
from schemas import DocumentoPublicoResponse

router = APIRouter(prefix="/documentos", tags=["documentos públicos"])

UPLOADS_DIR = "uploads"

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

    ruta = os.path.join(UPLOADS_DIR, documento.stored_filename)
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible")

    return FileResponse(ruta, filename=documento.filename)
