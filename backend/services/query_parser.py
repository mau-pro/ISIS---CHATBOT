"""
services/query_parser.py
---------------------------
Detecta si la pregunta del estudiante menciona un filtro exacto sobre datos
tabulares: semestre, grupo, o sigla de materia (ej. "SIS110").

Por qué existe: la búsqueda semántica de ChromaDB trae los fragmentos "más
parecidos" a la pregunta, pero preguntas tipo "¿qué materias hay en el
semestre 1?" necesitan TODAS las filas que cumplen esa condición (pueden ser
20+), no solo las más similares. Cuando detectamos un filtro claro acá, lo
usamos para hacer una búsqueda exacta en vez de depender de similitud.
"""

import re
import unicodedata

# Palabras que se ignoran al extraer términos de búsqueda: no aportan como
# palabra clave (son parte de la pregunta, no del dato que se busca).
PALABRAS_VACIAS = {
    "que", "qué", "quien", "quién", "cual", "cuál", "cuales", "cuáles",
    "materia", "materias", "docente", "docentes", "profesor", "profesora",
    "dicta", "dictan", "imparte", "imparten", "hay", "son", "tiene", "tienen",
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "con",
    "para", "por", "sobre", "es", "esta", "está",
    # Palabras de la pregunta que no identifican nada: "dia" aparece en TODAS las
    # filas de horarios y disparaba una búsqueda enorme (y un pedido demasiado
    # grande para Groq) en preguntas como "¿qué día es el torneo?".
    "dia", "día", "dias", "días", "fecha", "fechas", "cuando", "cuándo", "hora", "horas",
    "semestre", "grupo", "sigla",  # ya los maneja detectar_filtro por separado
    "horario", "horarios", "hora", "horas", "cuando", "cuándo",
    "cursa", "cursan", "llevan", "lleva", "carrera", "clases", "clase",
    "pasa", "pasan", "toma", "toman", "dan", "ambiente", "ambientes",
    "aula", "aulas",
    # Palabras de relleno de una pregunta ("¿cómo es la beca...?", "quiero saber
    # dónde..."): sin esto, una sola como "como" —que nunca está en los datos—
    # hacía fallar la búsqueda de "todos los términos".
    "como", "cómo", "donde", "dónde", "cuanto", "cuánto", "cuantos", "cuántos",
    "cuanta", "cuánta", "cuantas", "cuántas", "porque", "puedo", "puede", "pueden",
    "quiero", "quisiera", "saber", "informacion", "información", "acerca", "dime",
    "decime", "dame", "explica", "explicame", "cuentame", "sera", "será", "fue",
    "ser", "hacer", "hago", "tengo", "tener", "esto", "ese", "esa", "esos", "esas",
    "algun", "algún", "alguna", "algunos", "algunas", "muy", "mas", "más", "todo",
    "todos", "todas", "nos", "les", "sus", "mis", "tus",
}


def sin_acentos(texto: str) -> str:
    """Minúsculas y sin tildes: para comparar la pregunta con texto de OCR, donde
    las tildes y las mayúsculas salen distintas (o se pierden) según la imagen."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def extraer_terminos(pregunta: str, maximo: int = 5) -> list[str]:
    """
    Extrae palabras clave de la pregunta (largo >= 3, sin palabras vacías),
    para usarlas en una búsqueda de texto exacto —ej. "materias dicta juan
    jose choque" -> ["juan", "jose", "choque"]— cuando no se detectó un
    filtro estructurado (semestre/grupo/sigla). Útil para nombres propios:
    coincidencia de texto es más confiable que similitud semántica para
    encontrar TODAS las filas de un docente específico.
    """
    palabras = re.findall(r"\b[a-zA-ZÁÉÍÓÚÑáéíóúñ]{3,}\b", pregunta)
    terminos = []
    for palabra in palabras:
        if palabra.lower() not in PALABRAS_VACIAS and palabra.lower() not in terminos:
            terminos.append(palabra.lower())
        if len(terminos) >= maximo:
            break
    return terminos


# "primer semestre", "segundo grupo", etc. — la gente rara vez dice
# "semestre 1", dice "primer semestre". Sin esto, detectar_filtro() no
# encontraba ningún filtro y la pregunta caía a búsqueda semántica, que no
# garantiza traer TODAS las filas de ese semestre/grupo.
_ORDINALES_A_NUMERO = {
    "primer": "1", "primero": "1", "primera": "1", "uno": "1",
    "segundo": "2", "segunda": "2", "dos": "2",
    "tercer": "3", "tercero": "3", "tercera": "3", "tres": "3",
    "cuarto": "4", "cuarta": "4", "cuatro": "4",
    "quinto": "5", "quinta": "5", "cinco": "5",
    "sexto": "6", "sexta": "6", "seis": "6",
    "septimo": "7", "séptimo": "7", "sétimo": "7", "septima": "7", "séptima": "7", "siete": "7",
    "octavo": "8", "octava": "8", "ocho": "8",
    "noveno": "9", "novena": "9", "nueve": "9",
}
_PATRON_ORDINAL = "|".join(_ORDINALES_A_NUMERO.keys())


def _extraer_numero(texto: str, palabra_clave: str) -> str | None:
    """
    Busca un número (dígito u ordinal en palabras) asociado a palabra_clave,
    en cualquier orden: "semestre 1" / "semestre número 1" / "primer
    semestre" / "semestre primero".
    """
    match = re.search(rf"{palabra_clave}\s*(?:n[uú]mero\s*)?(\d+)", texto)
    if match:
        return match.group(1)

    match = re.search(rf"\b({_PATRON_ORDINAL})\b\s+{palabra_clave}", texto)
    if match:
        return _ORDINALES_A_NUMERO[match.group(1)]

    match = re.search(rf"{palabra_clave}\s+\b({_PATRON_ORDINAL})\b", texto)
    if match:
        return _ORDINALES_A_NUMERO[match.group(1)]

    return None


def detectar_filtro(pregunta: str) -> dict:
    """
    Devuelve un diccionario de filtros detectados (ej. {"semestre": "1"}),
    o un diccionario vacío si no se detectó ningún patrón reconocible.
    Las claves coinciden con los encabezados de columna en minúscula, así
    que funciona automáticamente con cualquier Excel que tenga columnas
    "Semestre", "Grupo" o "Sigla" (no hace falta configurar nada más).
    """
    filtro = {}
    texto = pregunta.lower()

    numero_semestre = _extraer_numero(texto, "semestre")
    if numero_semestre:
        filtro["semestre"] = numero_semestre

    # Siglas típicas de materia: 2-4 letras seguidas de 2-4 números (SIS110, MAT100, LIN140)
    match_sigla = re.search(r"\b([A-Za-zÁÉÍÓÚñÑ]{2,4}\d{2,4})\b", pregunta)
    if match_sigla:
        filtro["sigla"] = match_sigla.group(1).upper()

    numero_grupo = _extraer_numero(texto, "grupo")
    if numero_grupo and (numero_semestre or match_sigla):
        # "grupo" solo (sin semestre ni sigla) es un filtro demasiado amplio:
        # el grupo 1 existe en los 9 semestres, así que "materias del grupo
        # 1" solo, traería TODAS esas filas mezcladas. Se exige que venga
        # acompañado de semestre o sigla para que el filtro sea preciso.
        filtro["grupo"] = numero_grupo

    return filtro


def es_pregunta_de_electivas(pregunta: str) -> bool:
    """
    Detecta preguntas sobre materias optativas/electivas (ej. "¿cuáles son
    las materias optativas?"). No hay una columna "tipo" en los datos, pero
    todas las siglas de electivas empiezan con "OPT" (OPT001, OPT004...),
    así que alcanza con buscar ese prefijo como texto —ver _armar_fragmentos
    en chat_routes.py.
    """
    return bool(re.search(r"\b(optativ|electiv)\w*", pregunta.lower()))
