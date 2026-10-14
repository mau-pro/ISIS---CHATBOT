"""
services/respuesta_directa.py
--------------------------------
Responde SIN llamar a la IA las preguntas cuya respuesta es una lista sacada
tal cual de los datos: "¿qué materias hay en primer semestre?", "¿quién dicta
SIS415?", "¿horario del semestre 3 grupo 1?". Cuestan 0 tokens, tardan
milisegundos y no pueden equivocarse ni inventar: los datos vienen del Excel.

Solo se usa cuando la pregunta es CLARAMENTE de ese tipo (hay un filtro exacto
de semestre/grupo/sigla, no sobran palabras que indiquen otra intención y las
filas traen las columnas necesarias). En cualquier duda devuelve None y la
pregunta sigue su camino normal (caché y luego Groq).
"""

import re

from services.query_parser import detectar_filtro, extraer_terminos, _ORDINALES_A_NUMERO

_ORDINAL_TEXTO = {
    "1": "primer", "2": "segundo", "3": "tercer", "4": "cuarto", "5": "quinto",
    "6": "sexto", "7": "séptimo", "8": "octavo", "9": "noveno",
}
_ORDEN_DIAS = {d: i for i, d in enumerate(["lunes", "martes", "miercoles", "miércoles", "jueves", "viernes", "sabado", "sábado"])}

_PIDE_HORARIO = re.compile(r"\b(horarios?|horas?|d[ií]as?|ambientes?|aulas?|cu[aá]ndo|d[oó]nde|laboratorios?)\b", re.I)
_PIDE_DOCENTE = re.compile(r"\b(docentes?|profesor(es|as?)?|qui[eé]n(es)?|dicta[n]?|imparte[n]?)\b", re.I)
_ES_LISTADO = re.compile(r"\b(materias?|asignaturas?|docentes?|profesor(es|as?)?|qui[eé]n(es)?|dicta[n]?|imparte[n]?|horarios?|ambientes?|aulas?|clases?)\b", re.I)
# Preguntas que piden algo distinto a listar datos (contar, comparar, opinar...)
_NO_ES_LISTADO_SIMPLE = re.compile(
    r"cu[aá]nt|cantidad|total|compar|diferenc|mejor|recomend|f[aá]cil|dif[ií]cil|requisit|cr[eé]dito|carga|ordena|"
    r"por qu[eé]|para qu[eé]|c[oó]mo|explic|adem[aá]s|tambi[eé]n|y si|pero",
    re.I,
)


def terminos_residuales(pregunta: str) -> list[str]:
    """Palabras clave de la pregunta que NO son solo el número de semestre en palabras."""
    return [t for t in extraer_terminos(pregunta) if t not in _ORDINALES_A_NUMERO]


def _unir_grupos(grupos: list[str]) -> str:
    grupos = sorted(set(grupos), key=lambda g: (len(g), g))
    if len(grupos) == 1:
        return f"Grupo {grupos[0]}"
    return "Grupos " + ", ".join(grupos[:-1]) + " y " + grupos[-1]


def responder_directo(pregunta: str, filtro: dict, filas: list[dict]) -> str | None:
    """
    Arma la respuesta desde las filas que cumplen el filtro, o devuelve None si
    la pregunta no es del tipo "listado simple" o faltan datos para contestarla.
    """
    if not filas or not _ES_LISTADO.search(pregunta) or _NO_ES_LISTADO_SIMPLE.search(pregunta):
        return None

    pide_horario = bool(_PIDE_HORARIO.search(pregunta))
    pide_docente = bool(_PIDE_DOCENTE.search(pregunta))
    solo_materia = "sigla" in filtro  # una materia puntual: siempre se pide algo de ella
    if solo_materia and not (pide_docente or pide_horario):
        return None

    if not all(f.get("sigla") for f in filas):
        return None

    # Los datos vienen de varios Excel (docentes, horarios) y cada uno trae columnas
    # distintas: una fila de horario puede no traer el nombre de la materia o el
    # docente, que sí están en otra fila de la misma sigla/grupo. Se juntan antes.
    nombres = {f["sigla"]: f["materia"] for f in filas if f.get("materia")}
    docentes: dict[tuple, list[str]] = {}
    horarios: dict[tuple, list[tuple]] = {}
    pares = []
    for f in filas:
        par = (f["sigla"], str(f.get("grupo", "")))
        if par not in pares:
            pares.append(par)
        if f.get("docente") and f["docente"] not in docentes.setdefault(par, []):
            docentes[par].append(f["docente"])
        if f.get("dia") and f.get("horario"):
            h = (f["dia"], f["horario"], f.get("ambiente", ""))
            if h not in horarios.setdefault(par, []):
                horarios[par].append(h)

    # Se agrupa por todo excepto el grupo, para escribir "Grupos 1 y 2" en una sola línea
    lineas: dict[tuple, list[str]] = {}
    orden: dict[tuple, tuple] = {}
    for sigla, grupo in pares:
        materia = nombres.get(sigla, "Materia sin nombre registrado")
        docs = (docentes.get((sigla, grupo)) or ["Docente no registrado"]) if pide_docente else [""]
        hors = (horarios.get((sigla, grupo)) or [("Sin horario registrado", "", "")]) if pide_horario else [("", "", "")]
        for docente in docs:
            for dia, horario, ambiente in hors:
                clave = (sigla, materia, docente, dia, horario, ambiente)
                lineas.setdefault(clave, []).append(grupo)
                orden.setdefault(clave, (sigla, _ORDEN_DIAS.get(dia.lower(), 99), horario))

    items = []
    for clave in sorted(lineas, key=lambda k: orden[k]):
        sigla, materia, docente, dia, horario, ambiente = clave
        texto = f"{materia} ({sigla})"
        if pide_docente:
            texto += f" - {docente}"
        if pide_horario:
            texto += f" - {dia} {horario}".rstrip() + (f" - {ambiente}" if ambiente else "")
        grupos = [g for g in lineas[clave] if g]
        if (pide_docente or pide_horario) and grupos and "grupo" not in filtro:
            texto += f" ({_unir_grupos(grupos)})"
        items.append(texto)

    if "sigla" in filtro:
        nombre = nombres.get(filtro["sigla"], filtro["sigla"])
        intro = f"Sobre {nombre} ({filtro['sigla']}):"
        if "grupo" in filtro:
            intro = f"Sobre {nombre} ({filtro['sigla']}), grupo {filtro['grupo']}:"
    else:
        semestre = _ORDINAL_TEXTO.get(filtro.get("semestre", ""), f"{filtro.get('semestre')}º")
        intro = f"En {semestre} semestre"
        if "grupo" in filtro:
            intro += f", grupo {filtro['grupo']},"
        intro += " se imparten:"

    return intro + "\n\n" + "\n".join(f"- {i}" for i in items)


def intentar_respuesta_directa(pregunta: str, buscar_filas) -> str | None:
    """`buscar_filas(filtro)` debe devolver las filas (dict) que cumplen el filtro exacto."""
    filtro = detectar_filtro(pregunta)
    if not filtro or terminos_residuales(pregunta):
        return None
    return responder_directo(pregunta, filtro, buscar_filas(filtro))
