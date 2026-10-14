"""
services/vector_service.py
----------------------------
Encapsula todo el uso de ChromaDB:
- index_chunks: guarda los fragmentos de un documento nuevo (con metadata
  opcional por fila, para poder filtrar exacto más adelante).
- delete_document_chunks: borra los fragmentos de un documento eliminado.
- search: busca los fragmentos más parecidos a una pregunta (similitud).
- search_por_filtro: busca fragmentos que cumplen EXACTO un filtro
  (ej. semestre=1) — usado cuando query_parser detecta un filtro claro,
  porque la similitud semántica no garantiza traer todas las filas.
- search_por_filtro_estructurado: igual que search_por_filtro, pero además
  devuelve la metadata de cada fila (dict) para que el llamador arme un
  bloque JSON compacto en vez de mandar texto repetitivo por cada fila.

ChromaDB genera los embeddings automáticamente con su función de embedding
por defecto (no depende de la API de Groq, así que indexar documentos no
consume tokens de Groq).
"""

import functools
import re

import chromadb

from services.query_parser import sin_acentos

_client = chromadb.PersistentClient(path="./chroma_data")
_collection = _client.get_or_create_collection(name="documentos_universidad")


def index_chunks(
    document_id: int,
    filename: str,
    category: str,
    chunks: list[str],
    metadatas_extra: list[dict] | None = None,
) -> int:
    """
    Guarda los chunks de un documento en ChromaDB. metadatas_extra (opcional,
    misma longitud que chunks) agrega columnas estructuradas por fila —ej.
    {"semestre": "1", "grupo": "1", "sigla": "SIS110"}— que luego permiten
    filtrar exacto con search_por_filtro(). Devuelve cuántos se indexaron.
    """
    if not chunks:
        return 0

    ids = [f"doc{document_id}_chunk{i}" for i in range(len(chunks))]
    metadatas = []
    for i in range(len(chunks)):
        base = {"document_id": document_id, "filename": filename, "category": category}
        if metadatas_extra and i < len(metadatas_extra):
            base.update(metadatas_extra[i])
        metadatas.append(base)

    _collection.add(ids=ids, documents=chunks, metadatas=metadatas)
    _invalidar_indice_imagenes()
    return len(chunks)


def delete_document_chunks(document_id: int) -> None:
    """Elimina todos los chunks asociados a un documento (cuando el admin lo borra)."""
    _collection.delete(where={"document_id": document_id})
    _invalidar_indice_imagenes()


def obtener_chunks_de_documento(document_id: int) -> tuple[list[str], list[dict]]:
    """Textos y metadatos de los fragmentos de un documento (antes de borrarlo o releerlo)."""
    r = _collection.get(where={"document_id": document_id}, include=["documents", "metadatas"])
    return r["documents"], r["metadatas"]


def search(query: str, n_results: int = 10) -> list[str]:
    """
    Devuelve los fragmentos más parecidos semánticamente a la pregunta.
    Útil para preguntas abiertas o de una sola coincidencia (ej. "¿cuándo
    es la convocatoria de becas?"), pero NO garantiza traer todas las filas
    que cumplen una condición — para eso usar search_por_filtro().

    n_results se bajó de 12 a 10: es la fuente de más bajo valor (similitud,
    no coincidencia exacta), así que se recorta primero para no inflar el
    contexto —y los tokens— que se le manda a Groq en cada consulta.
    """
    resultados = _collection.query(query_texts=[query], n_results=n_results)
    documentos = resultados.get("documents", [[]])
    return documentos[0] if documentos else []


def _limpiar_metadata_interna(metadata: dict) -> dict:
    """Quita las claves internas (document_id, filename, category) que no
    aportan a la IA y solo agregan tokens; deja solo las columnas del Excel."""
    return {
        clave: valor
        for clave, valor in metadata.items()
        if clave not in ("document_id", "filename", "category")
    }


def search_por_filtro(filtro: dict, limite: int = 100) -> list[str]:
    """
    Devuelve TODOS los fragmentos que cumplen exactamente el filtro dado
    (ej. {"semestre": "1"} trae las 24 filas de semestre 1, no solo las más
    "parecidas"). Si el filtro no coincide con ninguna metadata indexada
    (ej. el Excel no tiene esa columna), devuelve una lista vacía —el
    llamador debe entonces recurrir a search() como respaldo.
    """
    documentos, _ = search_por_filtro_estructurado(filtro, limite)
    return documentos


def search_por_filtro_estructurado(filtro: dict, limite: int = 100) -> tuple[list[str], list[dict]]:
    """
    Igual que search_por_filtro(), pero además devuelve la metadata limpia
    (sin document_id/filename/category) de cada fila que cumple el filtro.
    El llamador (chat_routes) arma con esos diccionarios un único bloque
    JSON en vez de mandarle a Groq una fila de texto repetitivo por
    fragmento —mismo dato, muchos menos tokens repetidos ("Campo: valor,
    Campo2: valor2" en cada una de las N filas).
    """
    if not filtro:
        return [], []

    if len(filtro) == 1:
        clave, valor = next(iter(filtro.items()))
        where = {clave: valor}
    else:
        where = {"$and": [{clave: valor} for clave, valor in filtro.items()]}

    try:
        resultados = _collection.get(where=where, limit=limite, include=["documents", "metadatas"])
    except Exception:
        return [], []

    documentos = resultados.get("documents", []) or []
    metadatas = [_limpiar_metadata_interna(m) for m in (resultados.get("metadatas", []) or [])]
    return documentos, metadatas


_MAX_FRAGMENTOS_TERMINO_RARO = 5


def search_por_texto(terminos: list[str], limite: int = 100) -> list[str]:
    """
    Devuelve fragmentos cuyo texto CONTIENE alguna de las palabras dadas
    (coincidencia exacta de texto, no similitud semántica). Se usa como
    respaldo cuando la pregunta menciona algo específico que no encaja en
    un filtro estructurado —típicamente un nombre propio, ej. "juan jose
    choque"— y donde la búsqueda semántica podría no traer todas las filas.

    IMPORTANTE: $contains de ChromaDB distingue mayúsculas de minúsculas.
    Como los datos de Excel suelen estar en MAYÚSCULAS pero la pregunta del
    usuario viene en minúsculas normales, probamos 3 variantes por término
    (minúscula, MAYÚSCULA, Capitalizada) para cubrir cualquier formato.

    El límite se subió de 25 a 100: con varios documentos que repiten los
    mismos apellidos (ej. "Mamani" aparece en 6 docentes distintos, entre
    docentes.xlsx y los horarios), un apellido común por sí solo ya supera
    25 coincidencias en TODA la colección, y ChromaDB no las devuelve
    ordenadas por relevancia sino por orden interno —así que con el límite
    bajo, todas las 25 podían salir de un solo documento y las filas
    relevantes de otro documento (ej. el horario) quedaban afuera antes de
    llegar a Groq. El presupuesto de tokens de preparar_contexto() sigue
    siendo el que controla el gasto real, no este límite.

    Cuando hay MÁS DE UN término, primero se exige que la fila contenga
    TODOS (no "cualquiera de ellos"): un solo apellido como "Mamani" da
    falsos positivos con 6 docentes distintos, pero "jose" + "david" +
    "mamani" juntos casi siempre identifican a una sola persona. Esto de
    paso reduce los fragmentos irrelevantes que se le mandan a Groq —menos
    ruido y menos tokens gastados en filas que no tienen nada que ver.

    Si esa búsqueda "todos los términos" no encuentra nada, se reintenta
    con "cualquiera de ellos" (el comportamiento anterior). Esto es
    necesario porque extraer_terminos() no corrige errores de tipeo: una
    sola palabra mal escrita en la pregunta (ej. "docnte" en vez de
    "docente", "claces" en vez de "clases") nunca va a aparecer en los
    datos, y exigirla igual que a las demás anularía toda la búsqueda por
    una palabra que ni siquiera es la relevante.
    """
    if not terminos:
        return []

    def _clausula_por_termino(t: str) -> dict:
        variantes = [{"$contains": v} for v in {t.lower(), t.upper(), t.capitalize()}]
        return variantes[0] if len(variantes) == 1 else {"$or": variantes}

    clausulas_por_termino = [_clausula_por_termino(t) for t in terminos]

    if len(clausulas_por_termino) == 1:
        where_document = clausulas_por_termino[0]
    else:
        where_document = {"$and": clausulas_por_termino}

    try:
        resultados = _collection.get(where_document=where_document, limit=limite)
        documentos = resultados.get("documents", []) or []
    except Exception:
        documentos = []

    if not documentos and len(clausulas_por_termino) > 1:
        # "Cualquiera de los términos": se consulta cada término por separado y se
        # ordena por cuántos términos contiene cada fragmento. Sin esto, un término
        # común ("beca": decenas de fragmentos) llenaba el límite con resultados en
        # orden arbitrario y el fragmento que tenía además "google" y "launchpad"
        # podía quedar fuera —o al final, recortado por el presupuesto de tokens.
        #
        # Además cada término pesa según lo RARO que es (1 / cuántos fragmentos lo
        # contienen): "google" (3 fragmentos) vale mucho más que "beca" (decenas),
        # así una pregunta sobre la beca Google no la ganan los PDF de otras becas
        # que repiten "beca" y "postular" más veces.
        encontrados: dict[str, None] = {}
        peso: dict[str, float] = {}
        for termino, clausula in zip(terminos, clausulas_por_termino):
            try:
                resultados = _collection.get(where_document=clausula, limit=limite)
            except Exception:
                continue
            docs_termino = resultados.get("documents", []) or []
            if not docs_termino:
                continue  # palabra que no está en ningún dato (típicamente un error de tipeo)
            peso[termino.lower()] = 1 / len(docs_termino)
            for doc in docs_termino:
                encontrados.setdefault(doc, None)
        # Si algún término es MUY raro (está en 5 fragmentos o menos, ej. "google"),
        # identifica de qué habla la pregunta: se descartan los fragmentos que solo
        # coinciden por palabras comunes ("beca", "postular") y mezclarían datos
        # de otras becas en la respuesta.
        raros = [t for t, w in peso.items() if w >= 1 / _MAX_FRAGMENTOS_TERMINO_RARO]
        if raros:
            encontrados = {d: None for d in encontrados if any(t in d.lower() for t in raros)}
        documentos = sorted(
            encontrados,
            key=lambda d: -sum(w for t, w in peso.items() if t in d.lower()),
        )[:limite]

    return documentos


# ---------------------------------------------------------------------------
# Búsqueda tolerante a errores de OCR, solo sobre el texto de las imágenes.
#
# El OCR de un cartel casi nunca sale perfecto ("FLAMPAGO" por "relámpago",
# "tecnoldgico"), y $contains de ChromaDB exige la palabra EXACTA (y distingue
# tildes). Como las imágenes son pocas, se guarda en memoria el texto de todas
# y se compara palabra por palabra sin tildes ni mayúsculas, aceptando parecidos.
# ---------------------------------------------------------------------------

_EXTENSIONES_IMAGEN = ("jpg", "jpeg", "png", "webp", "bmp", "tiff")
# {document_id: ([textos de sus fragmentos en orden], palabras de TODA la imagen)}
_indice_imagenes: dict[int, tuple[list[str], frozenset[str]]] | None = None

# Puntaje (suma de coincidencias por palabra) desde el cual una imagen se considera
# "la respuesta" de la pregunta: ver buscar_en_imagenes().
PUNTAJE_IMAGEN_FUERTE = 3.0


def _invalidar_indice_imagenes() -> None:
    """Se llama al indexar o borrar cualquier documento: el índice se rearma solo."""
    global _indice_imagenes
    _indice_imagenes = None


def _tokens(texto: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]{3,}", sin_acentos(texto)))


def _cargar_indice_imagenes() -> dict[int, tuple[list[str], frozenset[str]]]:
    global _indice_imagenes
    if _indice_imagenes is None:
        from database import SessionLocal  # import tardío: evita ciclos al arrancar
        from models.document import Document

        db = SessionLocal()
        try:
            ids = [d.id for d in db.query(Document.id).filter(Document.original_type.in_(_EXTENSIONES_IMAGEN))]
        finally:
            db.close()
        indice: dict[int, tuple[list[str], frozenset[str]]] = {}
        if ids:
            r = _collection.get(where={"document_id": {"$in": ids}}, include=["documents", "metadatas"])
            por_doc: dict[int, list[tuple[int, str]]] = {}
            for chunk_id, texto, meta in zip(r["ids"], r["documents"], r["metadatas"]):
                orden = int(chunk_id.rsplit("_chunk", 1)[-1])
                por_doc.setdefault(meta["document_id"], []).append((orden, texto))
            for doc_id, partes in por_doc.items():
                textos = [t for _, t in sorted(partes)]
                indice[doc_id] = (textos, frozenset().union(*(_tokens(t) for t in textos)))
        _indice_imagenes = indice
    return _indice_imagenes


@functools.lru_cache(maxsize=50000)
def _bigramas(palabra: str) -> frozenset[str]:
    return frozenset(palabra[i:i + 2] for i in range(len(palabra) - 1))


def _similitud(termino: str, tokens: frozenset[str]) -> float:
    """1.0 si la palabra está exacta; ~0.9 si está contenida en otra; si no, el
    parecido (coeficiente de Dice sobre pares de letras) de la palabra más
    parecida, solo si supera 0.72. Palabras de menos de 5 letras: solo exactas."""
    if termino in tokens:
        return 1.0
    if len(termino) < 5:
        return 0.0
    mejor = 0.0
    bt = _bigramas(termino)
    for tk in tokens:
        if len(tk) >= 5 and (termino in tk or tk in termino):
            return 0.9
        if abs(len(tk) - len(termino)) > 2:
            continue
        b2 = _bigramas(tk)
        dice = 2 * len(bt & b2) / (len(bt) + len(b2))
        if dice > mejor:
            mejor = dice
    return mejor if mejor >= 0.72 else 0.0


def buscar_en_imagenes(terminos: list[str], limite: int = 2) -> tuple[list[str], bool]:
    """
    Devuelve (fragmentos, fuerte). Se puntúa cada IMAGEN completa (las palabras de
    todos sus fragmentos juntas: el dato que se pregunta puede estar en otro
    fragmento que el nombre del evento) y se devuelven TODOS los fragmentos de
    las `limite` mejores. Con una sola palabra en la pregunta alcanza una
    coincidencia; con varias se piden ~2. `fuerte` es True si la mejor imagen
    coincide con 3 o más palabras: en ese caso la pregunta trata de esa imagen
    y conviene no mezclar datos de otros documentos parecidos.
    """
    terminos = [sin_acentos(t) for t in terminos if len(t) >= 3]
    if not terminos:
        return [], False
    umbral = 0.85 if len(terminos) == 1 else 1.7
    puntuadas = []
    for textos, tokens in _cargar_indice_imagenes().values():
        puntaje = sum(_similitud(t, tokens) for t in terminos)
        if puntaje >= umbral:
            puntuadas.append((puntaje, textos))
    puntuadas.sort(key=lambda x: -x[0])
    fragmentos = [t for _, textos in puntuadas[:limite] for t in textos]
    return fragmentos, bool(puntuadas) and puntuadas[0][0] >= PUNTAJE_IMAGEN_FUERTE
