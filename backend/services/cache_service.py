"""
services/cache_service.py
---------------------------
Caché semántico de respuestas: el sistema "aprende" de cada consulta.

Cada vez que Groq responde una pregunta con información real de los
documentos, se guarda (pregunta -> respuesta) en una colección de ChromaDB.
Cuando llega una pregunta parecida, se responde desde acá sin llamar a Groq:
0 tokens gastados y respuesta casi instantánea. Cuantas más consultas se
hacen, más preguntas quedan cubiertas.

Cuidado con los falsos positivos: "materias del semestre 1" y "materias del
semestre 2" son casi idénticas para un modelo de embeddings, pero la
respuesta correcta es distinta. Por eso a cada pregunta se le calcula una
"firma" (filtro semestre/grupo/sigla + palabras clave + si pregunta por
optativas) y solo se aceptan coincidencias que tengan LA MISMA firma y,
además, una similitud muy alta.

Al subir, borrar o releer un documento NO se vacía todo el caché: solo se
borran las respuestas que ese documento puede haber cambiado (ver
invalidar_por_documento). Así subir un cartel nuevo no hace olvidar todo lo
aprendido. El admin también puede ver y borrar preguntas aprendidas a mano.
"""

import hashlib
import json
import unicodedata
import re
from datetime import datetime

import chromadb

from services.query_parser import detectar_filtro, extraer_terminos, es_pregunta_de_electivas, sin_acentos

_client = chromadb.PersistentClient(path="./chroma_data")
_NOMBRE = "cache_respuestas"

# Distancia coseno máxima (0 = idéntica). 0.12 ≈ 88% de similitud.
UMBRAL_DISTANCIA = 0.12


def _coleccion():
    return _client.get_or_create_collection(name=_NOMBRE, metadata={"hnsw:space": "cosine"})


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", texto)).strip()


def _id_de(normalizada: str) -> str:
    return hashlib.sha1(normalizada.encode("utf-8")).hexdigest()[:16]


def firma_de(pregunta: str) -> str:
    """Identifica QUÉ se está preguntando (filtro + términos), no cómo está escrito."""
    return json.dumps(
        {
            "f": detectar_filtro(pregunta),
            "t": sorted(extraer_terminos(pregunta)),
            "e": es_pregunta_de_electivas(pregunta),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def buscar_en_cache(pregunta: str) -> str | None:
    """Devuelve la respuesta guardada si hay una pregunta equivalente, o None."""
    try:
        coleccion = _coleccion()
        if coleccion.count() == 0:
            return None
        resultado = coleccion.query(
            query_texts=[_normalizar(pregunta)],
            n_results=1,
            where={"firma": firma_de(pregunta)},
        )
    except Exception:
        return None

    distancias = (resultado.get("distances") or [[]])[0]
    metadatas = (resultado.get("metadatas") or [[]])[0]
    ids = (resultado.get("ids") or [[]])[0]
    if distancias and distancias[0] <= UMBRAL_DISTANCIA:
        meta = metadatas[0]
        try:  # cuenta cuántas veces se reutilizó (para ver qué preguntas rinden más)
            coleccion.update(ids=[ids[0]], metadatas=[{**meta, "usos": int(meta.get("usos", 0)) + 1}])
        except Exception:
            pass
        return meta.get("respuesta")
    return None


def guardar_en_cache(pregunta: str, respuesta: str) -> None:
    """Guarda (o reemplaza) la respuesta de una pregunta para reusarla después."""
    try:
        normalizada = _normalizar(pregunta)
        _coleccion().upsert(
            ids=[_id_de(normalizada)],
            documents=[normalizada],
            metadatas=[{
                "firma": firma_de(pregunta),
                "respuesta": respuesta,
                "usos": 0,
                "creada": datetime.utcnow().isoformat(timespec="seconds"),
            }],
        )
    except Exception:
        pass  # el caché es una optimización: si falla, no debe romper el chat


def vaciar_cache() -> None:
    """Borra TODO lo aprendido (botón del admin)."""
    try:
        _client.delete_collection(_NOMBRE)
    except Exception:
        pass


def cantidad_en_cache() -> int:
    try:
        return _coleccion().count()
    except Exception:
        return 0


def listar_cache(limite: int = 1000) -> list[dict]:
    """Preguntas aprendidas, las más usadas primero (para el panel del admin)."""
    try:
        datos = _coleccion().get(include=["documents", "metadatas"], limit=limite)
    except Exception:
        return []
    filas = [
        {
            "id": id_,
            "pregunta": pregunta,
            "respuesta": meta.get("respuesta", ""),
            "usos": int(meta.get("usos", 0)),
            "creada": meta.get("creada", ""),
        }
        for id_, pregunta, meta in zip(datos["ids"], datos["documents"], datos["metadatas"])
    ]
    return sorted(filas, key=lambda f: (-f["usos"], f["creada"]), reverse=False)


def borrar_de_cache(id_: str) -> None:
    try:
        _coleccion().delete(ids=[id_])
    except Exception:
        pass


def invalidar_por_documento(textos: list[str], metadatas: list[dict] | None = None) -> int:
    """
    Borra del caché SOLO las respuestas que un documento (subido, borrado o
    releído) puede haber cambiado, y devuelve cuántas borró. Una respuesta
    guardada está afectada si:
    - su pregunta tenía un filtro (semestre/grupo/sigla) y el documento tiene
      filas que lo cumplen;
    - o trataba de optativas y el documento tiene siglas OPT;
    - o alguna de sus palabras clave aparece (aprox., el OCR se equivoca) en el
      texto del documento;
    - o era una pregunta abierta, sin filtro ni palabras clave: ahí no se puede
      saber, así que se borra por seguridad.
    Ante cualquier error se vacía todo el caché (más lento pero nunca desactualizado).
    """
    from services.vector_service import _tokens, _similitud  # import tardío: evita ciclos

    try:
        coleccion = _coleccion()
        datos = coleccion.get(include=["metadatas"])
        if not datos["ids"]:
            return 0

        filas = metadatas or []
        tokens = _tokens(" ".join(textos))
        hay_optativas = any(str(f.get("sigla", "")).upper().startswith("OPT") for f in filas)

        def cumple_filtro(filtro: dict) -> bool:
            return any(
                all(str(fila.get(k, "")).lower() == str(v).lower() for k, v in filtro.items())
                for fila in filas
            )

        a_borrar = []
        for id_, meta in zip(datos["ids"], datos["metadatas"]):
            firma = json.loads(meta["firma"])
            filtro, terminos, electivas = firma["f"], firma["t"], firma["e"]
            afectada = (
                (not filtro and not terminos and not electivas)
                or (bool(filtro) and cumple_filtro(filtro))
                or (electivas and hay_optativas)
                or any(_similitud(sin_acentos(t), tokens) > 0 for t in terminos)
            )
            if afectada:
                a_borrar.append(id_)
        if a_borrar:
            coleccion.delete(ids=a_borrar)
        return len(a_borrar)
    except Exception:
        vaciar_cache()
        return -1
