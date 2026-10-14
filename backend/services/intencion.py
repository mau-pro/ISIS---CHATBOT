"""
services/intencion.py
------------------------
Filtro de INTENCIÓN: detecta mensajes que no son una consulta de información y
les da una respuesta adecuada SIN llamar a la IA (0 tokens, y sin riesgo de que
el asistente responda cualquier cosa).

El caso que motivó esto: un estudiante escribió "reprobé todo el quinto semestre"
y, como el mensaje nombraba un semestre, el asistente contestó con la lista de
materias de ese semestre. Era una situación personal, no una pregunta.

Se reconocen:
- situaciones personales sobre notas ("reprobé", "aprobé", "me aplazaron"...):
  se responde con empatía o felicitación, se aclara que el sistema no ve
  el kárdex ni las notas, se deriva a quien aplica el reglamento y se ofrece
  la pregunta concreta que sí puede responder;
- saludos, agradecimientos y despedidas;
- "¿qué podés hacer?" / "ayuda".

Todo lo demás devuelve None y sigue su camino normal (datos directos, caché, IA).
Solo se activa con mensajes CLAROS: ante la duda no actúa.
"""

import re

from services.query_parser import detectar_filtro, sin_acentos

_ORDINAL_TEXTO = {
    "1": "primer", "2": "segundo", "3": "tercer", "4": "cuarto", "5": "quinto",
    "6": "sexto", "7": "séptimo", "8": "octavo", "9": "noveno",
}

# Primera persona, pasado: cuenta lo que le pasó al estudiante (no pregunta nada).
_NEGATIVA = re.compile(
    r"\b(reprob(e|amos)|aplaz(e|amos)|me (aplazaron|reprobaron|quede|retire|llevaron a)|"
    r"perdi (la|el|una|un|mi|mis|todas|todos|todo|toda)|no (pase|aprobe|logre pasar)|"
    r"me (fue|salio) (mal|pesimo)|abandone|suspendi|arrastro|estoy arrastrando|deje (la|el|de|todas|todo))\b"
)
_POSITIVA = re.compile(
    r"\b(aprobe|aprobamos|promocione|me fue (bien|excelente|genial)|pase (todo|todas|la|el|el semestre)|termine (el|la|mi))\b"
)

# Mensajes formados SOLO por estas palabras (sin ninguna consulta mezclada)
_SALUDO = {
    "hola", "holi", "holis", "buenas", "buenos", "buen", "dia", "dias", "tarde", "tardes", "noche", "noches",
    "que", "tal", "como", "estas", "esta", "estan", "todos", "asistente", "bot", "amigo", "hey", "hi", "saludos",
    "ola", "por", "favor", "is", "uatf",
}
_SALUDO_CLAVE = {"hola", "holi", "holis", "buenas", "buenos", "buen", "hey", "hi", "saludos", "ola", "tal", "estas"}

_GRACIAS = {
    "gracias", "muchas", "mil", "ok", "okay", "vale", "listo", "perfecto", "genial", "excelente", "bien", "bueno",
    "entendido", "entiendo", "dale", "super", "claro", "asistente", "por", "la", "el", "ayuda", "respuesta",
    "informacion", "muy", "amable", "te", "lo", "agradezco", "gracia", "buenisimo", "chevere", "todo",
}
_GRACIAS_CLAVE = {"gracias", "agradezco", "ok", "okay", "vale", "listo", "perfecto", "genial", "excelente", "entendido", "dale", "chevere", "buenisimo", "gracia"}

_DESPEDIDA = {
    "chau", "chao", "adios", "hasta", "luego", "pronto", "nos", "vemos", "bye", "cuidate", "saludos", "buenas",
    "noches", "que", "te", "vaya", "bien", "manana", "gracias", "muchas", "mañana", "tardes", "dias",
}
_DESPEDIDA_CLAVE = {"chau", "chao", "adios", "bye", "cuidate", "luego", "pronto", "vemos"}

_AYUDA = re.compile(
    r"^(ayuda|ayudame|help|menu|que (eres|sos|haces|puedes hacer|podes hacer|sabes hacer|sabes)|"
    r"quien (eres|sos)|en que (me )?(puedes|podes) ayudar(me)?|como (funcionas|te uso|se usa)|para que sirves)$"
)

TEXTO_SALUDO = (
    "¡Hola! Soy I-SIS, el asistente virtual de Ingeniería de Sistemas UATF. Puedo ayudarte con materias, docentes, horarios, "
    "becas, convocatorias y avisos de la carrera. Por ejemplo: ¿Qué materias hay en primer semestre?"
)
TEXTO_GRACIAS = "¡De nada! Si tenés otra consulta sobre la carrera, acá estoy."
TEXTO_DESPEDIDA = "¡Hasta luego! Éxitos en tus estudios."
TEXTO_AYUDA = (
    "Soy I-SIS, el asistente virtual de Ingeniería de Sistemas UATF. Puedo contarte qué materias hay en cada semestre, "
    "quién dicta cada materia, en qué horario y ambiente, y darte información de becas, convocatorias, comunicados "
    "y eventos de la carrera. No tengo acceso a tus notas ni a tu kárdex. Probá con: ¿Quién dicta SIS415?"
)


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", sin_acentos(texto))


def _solo_de(palabras: list[str], permitidas: set[str], clave: set[str]) -> bool:
    return 0 < len(palabras) <= 8 and all(p in permitidas for p in palabras) and any(p in clave for p in palabras)


def _oferta(pregunta: str, siguiente: bool = False) -> str:
    """La pregunta concreta que el estudiante puede hacer a continuación."""
    semestre = detectar_filtro(pregunta).get("semestre")
    if semestre in _ORDINAL_TEXTO:
        if siguiente and semestre != "9":
            semestre = str(int(semestre) + 1)
        return (
            f"Si querés planificar, preguntame «¿Qué materias hay en {_ORDINAL_TEXTO[semestre]} semestre?» "
            "y te muestro las materias; también podés pedirme los docentes y los horarios."
        )
    return "Si querés, preguntame por las materias, los docentes o los horarios de cualquier semestre."


def respuesta_por_intencion(pregunta: str) -> str | None:
    """Respuesta lista si el mensaje no es una consulta de información; None si hay que procesarlo normal."""
    limpio = " ".join(_palabras(pregunta))
    palabras = limpio.split()
    if not palabras:
        return None

    if _NEGATIVA.search(limpio):
        return (
            "Lamento que te haya pasado eso, ¡ánimo! Yo no tengo acceso a tu kárdex ni a tus notas, así que no puedo "
            "saber cómo te afecta. Para saber qué pasa con las materias reprobadas (repetición, arrastre, cuántas veces "
            "podés cursarlas) consultá en Dirección de Carrera o en Kárdex, que son quienes aplican el reglamento. "
            + _oferta(pregunta)
        )
    if _POSITIVA.search(limpio):
        return "¡Felicitaciones, buen trabajo! " + _oferta(pregunta, siguiente=True)

    if _solo_de(palabras, _SALUDO, _SALUDO_CLAVE):
        return TEXTO_SALUDO
    if _solo_de(palabras, _GRACIAS, _GRACIAS_CLAVE):
        return TEXTO_GRACIAS
    if _solo_de(palabras, _DESPEDIDA, _DESPEDIDA_CLAVE):
        return TEXTO_DESPEDIDA
    if _AYUDA.match(limpio):
        return TEXTO_AYUDA
    return None
