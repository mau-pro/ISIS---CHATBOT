"""
routes/chat_routes.py
-----------------------
- POST /chat          -> responde la pregunta (exige cuenta; rate limit según
                          rol) y guarda un registro en chat_logs con el user_id.
                          Si data.editar_id viene con valor, en vez de crear
                          un registro nuevo se actualiza ese (edición de una
                          pregunta ya enviada, no cuenta como consulta extra).
- GET    /chat/history -> historial de preguntas del estudiante logueado
                          (requiere cuenta; cada estudiante ve solo lo suyo).
- DELETE /chat/history -> borra TODO el historial del estudiante logueado.

Estrategia de búsqueda, en orden de prioridad:
1. Filtro exacto (semestre/grupo/sigla detectado por query_parser) —trae
   TODAS las filas que cumplen, ideal para "materias del semestre 1". Estas
   filas se arman como UN bloque JSON compacto (services/vector_service ya
   devuelve la metadata estructurada de cada fila), en vez de mandarle a
   Groq cada fila como texto suelto repetido.
2. Materias optativas (sigla "OPT...") si la pregunta las menciona —no hay
   columna "tipo" en los datos, así que se busca por el prefijo de sigla.
3. Búsqueda por texto (palabras clave de la pregunta, ej. nombre de un
   docente) —trae filas que contienen esas palabras exactas, ideal para
   "qué materias dicta Juan Pérez". Exige que TODAS las palabras estén
   presentes (no cualquiera de ellas), para no traer, por ejemplo, los 6
   docentes distintos que tienen el apellido "Mamani".
4. Búsqueda semántica (similitud) —respaldo general para preguntas
   abiertas donde no aplica ningún filtro ni coincidencia de texto.
Estas se combinan sin duplicar, priorizando 1-3 sobre la semántica, y
groq_service.preparar_contexto() recorta el total a un presupuesto de
tokens antes de mandarlo —así una búsqueda amplia no dispara un gasto de
tokens innecesario en cada pregunta.

Preguntas de seguimiento (ej. primero "¿qué materias hay en sexto
semestre?" y después "¿qué docentes las dictan?"): el /chat no manda
historial de conversación a Groq, así que si la pregunta actual sola no
encuentra ningún filtro/término (es decir, probablemente depende de la
pregunta anterior), se reintenta la detección sobre la pregunta anterior +
la actual combinadas —así "las" hereda el semestre/grupo/sigla que ya se
había mencionado, en vez de buscar en todo el sistema sin ningún filtro.
"""

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from schemas import ChatRequest, ChatResponse, HistorialPaginado
from services.auth_service import get_current_user
from services.rate_limit_service import check_rate_limit
from services.vector_service import search, search_por_filtro_estructurado, search_por_texto, buscar_en_imagenes
from services.query_parser import detectar_filtro, extraer_terminos, es_pregunta_de_electivas
from services.groq_service import generar_respuesta, LimiteIAError
from services.cache_service import buscar_en_cache, guardar_en_cache
from services.respuesta_directa import intentar_respuesta_directa
from services.intencion import respuesta_por_intencion
from models.chat_log import ChatLog

router = APIRouter(tags=["chat"])


_ES_SIN_INFORMACION = re.compile(
    r"\bno (tengo|dispongo|cuento|poseo|hay)\b[^.\n]{0,40}\binformaci|no se encontr|no dispongo", re.I
)
_PIDE_HORARIO = re.compile(r"\b(horarios?|horas?|d[ií]as?|ambientes?|aulas?|cu[aá]ndo|d[oó]nde|laboratorios?|lab)\b", re.I)
_PIDE_DOCENTE = re.compile(r"\b(docentes?|profesor(es|as?)?|qui[eé]n(es)?|dicta[n]?|imparte[n]?)\b", re.I)


def _podar_metadatas(texto_pregunta: str, metadatas: list[dict]) -> list[dict]:
    """
    Le manda a Groq solo las columnas que la pregunta necesita y sin filas
    repetidas. Para "¿qué materias hay en primer semestre?" no hacen falta
    docentes ni horarios: 72 filas con 8 columnas pasan a 6 filas con 3.
    Es lo que más baja el tiempo de respuesta y los tokens gastados.
    """
    pide_horario = bool(_PIDE_HORARIO.search(texto_pregunta))
    pide_docente = bool(_PIDE_DOCENTE.search(texto_pregunta))

    claves = ["semestre", "sigla", "materia"]
    if pide_docente or pide_horario:
        claves.append("grupo")
    if pide_docente:
        claves.append("docente")
    if pide_horario:
        claves += ["dia", "horario", "ambiente"]

    vistas, podadas = set(), []
    for fila in metadatas:
        recortada = {k: fila[k] for k in claves if k in fila}
        firma = json.dumps(recortada, sort_keys=True, ensure_ascii=False)
        if firma not in vistas:
            vistas.add(firma)
            podadas.append(recortada)
    return podadas


def _armar_fragmentos(pregunta: str, pregunta_anterior: str | None = None) -> list[str]:
    """Junta las fuentes de contexto (filtro/JSON, electivas, texto,
    semántica), en orden de prioridad y sin duplicados, listas para
    preparar_contexto()."""
    filtro = detectar_filtro(pregunta)
    terminos = extraer_terminos(pregunta)

    # Pregunta de seguimiento sin filtro ni términos propios ("¿y quién la
    # dicta?") -> se prueba de nuevo combinando con la pregunta anterior,
    # que es la que probablemente tenía el semestre/grupo/sigla real.
    if not filtro and not terminos and pregunta_anterior:
        combinada = f"{pregunta_anterior} {pregunta}"
        filtro = detectar_filtro(combinada)
        terminos = extraer_terminos(combinada)

    documentos_filtro, metadatas_filtro = (
        search_por_filtro_estructurado(filtro) if filtro else ([], [])
    )

    fragmentos_filtro = []
    if metadatas_filtro:
        # Un único bloque JSON con todas las filas que cumplen el filtro,
        # en vez de N fragmentos de texto con los mismos nombres de columna
        # repetidos una y otra vez — mismo dato, muchos menos tokens.
        fragmentos_filtro.append(
            "Filas que cumplen el filtro (JSON):\n"
            + json.dumps(
                _podar_metadatas(
                    f"{pregunta_anterior or ''} {pregunta}", metadatas_filtro
                ),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    elif documentos_filtro:
        fragmentos_filtro.extend(documentos_filtro)

    pregunta_completa = f"{pregunta_anterior} {pregunta}" if pregunta_anterior else pregunta
    fragmentos_electivas = (
        search_por_texto(["OPT"]) if es_pregunta_de_electivas(pregunta_completa) else []
    )
    if fragmentos_electivas:
        # Los datos no dicen la palabra "optativa": solo tienen siglas OPT###.
        # Se aclara acá para que el modelo no tenga que adivinarlo.
        fragmentos_electivas.insert(
            0,
            "IMPORTANTE: las materias OPTATIVAS (electivas) son las que tienen "
            "sigla que empieza con OPT. Estas son las filas de optativas:",
        )

    fragmentos_texto = search_por_texto(terminos) if terminos else []

    # Imágenes: el OCR comete errores de lectura, así que se busca aparte con
    # tolerancia (sin tildes ni mayúsculas, palabras parecidas).
    fragmentos_imagen, imagen_fuerte = buscar_en_imagenes(terminos) if terminos else ([], False)
    if imagen_fuerte:
        # La pregunta trata claramente de esa imagen: los fragmentos de otros
        # documentos que coinciden por palabras comunes (ej. otras becas)
        # solo mezclarían datos ajenos en la respuesta.
        fragmentos_texto = []

    # La búsqueda semántica es el respaldo: si el filtro exacto ya trajo las
    # filas, se salta (ahorra un embedding + decenas de fragmentos de ruido
    # que hacían más lenta y más cara cada respuesta).
    # Con resultados más precisos (imagen/texto), la similitud solo aporta contexto
    # de apoyo: 3 fragmentos bastan y evitan que datos de otros documentos parecidos
    # (ej. otras becas) se mezclen en la respuesta.
    fragmentos_semanticos = (
        [] if fragmentos_filtro or imagen_fuerte
        else search(pregunta, n_results=3 if (fragmentos_imagen or fragmentos_texto) else 10)
    )

    fragmentos = []
    vistos = set()
    for grupo in (fragmentos_filtro, fragmentos_electivas, fragmentos_imagen, fragmentos_texto, fragmentos_semanticos):
        for f in grupo:
            if f not in vistos:
                fragmentos.append(f)
                vistos.add(f)

    return fragmentos


def _mensaje_limite_ia(diario: bool) -> str:
    """Todos los modelos alcanzaron su límite de uso: se explica en vez de mostrar un error genérico."""
    if diario:
        return (
            "Se alcanzó el límite diario de consultas a la IA. Las preguntas frecuentes "
            "(materias, docentes y horarios) siguen funcionando; para el resto, intenta mañana."
        )
    return "El asistente está recibiendo muchas consultas en este momento. Intenta de nuevo en un minuto."


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: Request,
    data: ChatRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    check_rate_limit(request)

    # Tres caminos, de más barato a más caro. Las preguntas de seguimiento
    # ("¿y quién la dicta?") no usan los dos primeros: su significado depende de
    # la conversación anterior.
    respuesta = None
    desde_cache = False  # True = no se gastaron tokens (datos directos o caché)
    tokens = 0
    modelo_usado = None

    # 0) Mensajes que no son consultas (situaciones personales como "reprobé todo el
    # quinto semestre", saludos, gracias...): respuesta adecuada sin IA. Si no, el
    # asistente contestaba con listas de materias que nadie pidió.
    respuesta = respuesta_por_intencion(data.pregunta)
    desde_cache = respuesta is not None

    if respuesta is None and not data.pregunta_anterior:
        # 1) Datos exactos: si la respuesta es una lista sacada tal cual del Excel
        # ("materias del semestre 4", "quién dicta SIS415"), se arma con código:
        # 0 tokens, milisegundos y siempre al día.
        respuesta = intentar_respuesta_directa(
            data.pregunta, lambda filtro: search_por_filtro_estructurado(filtro)[1]
        )
        # 2) Caché que aprende: si ya se respondió una pregunta equivalente.
        if respuesta is None:
            respuesta = buscar_en_cache(data.pregunta)
        desde_cache = respuesta is not None

    if respuesta is None:
        # 3) Groq, con el contexto recuperado.
        fragmentos = _armar_fragmentos(data.pregunta, data.pregunta_anterior)
        try:
            respuesta, tokens, modelo_usado = generar_respuesta(
                data.pregunta, fragmentos, data.pregunta_anterior, data.respuesta_anterior
            )
        except LimiteIAError as e:
            raise HTTPException(status_code=503, detail=_mensaje_limite_ia(e.diario))
        # Las respuestas "no sé" no se guardan: si fueron por una búsqueda floja, el
        # caché las repetiría para siempre aunque después se arregle o se suba el dato.
        if fragmentos and not data.pregunta_anterior and not _ES_SIN_INFORMACION.search(respuesta):
            guardar_en_cache(data.pregunta, respuesta)

    registro = None
    if data.editar_id:
        registro = (
            db.query(ChatLog)
            .filter(ChatLog.id == data.editar_id, ChatLog.user_id == usuario.id)
            .first()
        )

    if registro:
        registro.pregunta = data.pregunta
        registro.respuesta = respuesta
        registro.tokens = (registro.tokens or 0) + tokens
        registro.modelo = modelo_usado or registro.modelo
    else:
        registro = ChatLog(
            user_id=usuario.id,
            pregunta=data.pregunta,
            respuesta=respuesta,
            es_prueba=usuario.role == "admin",
            desde_cache=desde_cache,
            tokens=tokens,
            modelo=modelo_usado,
        )
        db.add(registro)

    db.commit()
    db.refresh(registro)

    return ChatResponse(id=registro.id, respuesta=respuesta, desde_cache=desde_cache)


@router.get("/chat/history", response_model=HistorialPaginado)
def historial(
    page: int = 1,
    page_size: int = 8,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    consulta = db.query(ChatLog).filter(ChatLog.user_id == usuario.id)
    total = consulta.count()
    items = (
        consulta.order_by(ChatLog.created_at.desc(), ChatLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return HistorialPaginado(items=items, total=total, page=page, page_size=page_size)


@router.delete("/chat/history")
def borrar_historial(db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    """Borra TODO el historial de consultas del estudiante logueado (el suyo, no el de otros)."""
    db.query(ChatLog).filter(ChatLog.user_id == usuario.id).delete()
    db.commit()
    return {"detail": "Historial eliminado correctamente"}
