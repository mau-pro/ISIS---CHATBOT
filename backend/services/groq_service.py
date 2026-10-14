"""
services/groq_service.py
--------------------------
Se encarga de la llamada al modelo de Groq: toma la pregunta del usuario,
el contexto recuperado de ChromaDB (RAG), arma el prompt y devuelve la respuesta.

La respuesta pasa por limpiar_formato() antes de devolverse: el SYSTEM_PROMPT
le pide al modelo no usar Markdown, pero ninguna instrucción de prompt
garantiza cumplimiento al 100% —limpiar_formato() es la garantía real,
determinística, de que nunca llegan asteriscos ni tablas crudas al frontend.

Antes de llamar a Groq, preparar_contexto() recorta los fragmentos a un
presupuesto de tokens (estimado, sin depender de ninguna librería externa de
tokenización): así una pregunta que dispara una búsqueda muy amplia no le
manda al modelo un contexto gigante e innecesariamente caro en tokens.
"""

import os
import re
import time
from groq import Groq, APIStatusError
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Modelos gratuitos de Groq que sirven para responder, en orden de preferencia. Cada uno
# tiene su PROPIO cupo (8.000 tokens/min, 200.000 tokens/día, 1.000 consultas/día en
# el plan gratuito), así que al agotarse uno el pedido sigue con el siguiente y los
# cupos se suman. Se puede cambiar el orden o quitar modelos con MODELOS_IA en .env
# (ids separados por coma).
MODELOS_CONOCIDOS = {
    "openai/gpt-oss-120b": {"max_tokens": 1200, "extra_body": {"reasoning_effort": "low"}},
    "qwen/qwen3.8-27b": {"max_tokens": 800, "extra_body": None},  # tope de 1000 tokens de SALIDA por minuto
    "openai/gpt-oss-20b": {"max_tokens": 1200, "extra_body": {"reasoning_effort": "low"}},
}
_AJUSTES_POR_DEFECTO = {"max_tokens": 800, "extra_body": None}
MODELOS = [m.strip() for m in os.getenv("MODELOS_IA", ",".join(MODELOS_CONOCIDOS)).split(",") if m.strip()]
MODELO = MODELOS[0]  # el preferido

# Presupuesto de tokens para el CONTEXTO (no cuenta el system prompt ni la
# pregunta). Se estima sin librería de tokenización: en la práctica el texto de
# este proyecto (español con mayúsculas, tildes y JSON) rinde ~2.8 caracteres
# por token, no 4, así que se usa 3 para no quedarse corto. El plan gratuito de
# Groq limita a 8000 tokens por minuto POR PEDIDO (prompt + respuesta), por eso
# el default es conservador: 3500 de contexto + ~700 del prompt + 1200 de salida.
PRESUPUESTO_TOKENS_CONTEXTO = int(os.getenv("PRESUPUESTO_TOKENS_CONTEXTO", "3500"))
CARACTERES_POR_TOKEN = 3
ESPERA_MAXIMA_SEGUNDOS = 20  # si Groq pide esperar más que esto, se avisa al estudiante en vez de dejarlo colgado

SYSTEM_PROMPT = (
    "Eres I-SIS, el asistente virtual educativo de la carrera de Ingeniería de Sistemas de la universidad (si te preguntan tu nombre, decí que sos I-SIS). Respondes preguntas "
    "de estudiantes sobre horarios, docentes, convocatorias y avisos, usando "
    "únicamente la información de contexto proporcionada. Si la información "
    "no está en el contexto, dilo claramente en vez de inventar datos.\n\n"
    "MUY IMPORTANTE — revisá TODO el contexto antes de responder: el contexto "
    "puede traer varios fragmentos relacionados a la pregunta, y algunos no son "
    "relevantes (mencionan a otra persona o materia por coincidencia parcial). "
    "Tu trabajo es: 1) identificar CADA fragmento que realmente corresponde "
    "exacto a lo que se pregunta (mismo nombre completo, misma sigla, etc.), "
    "2) incluir TODAS esas coincidencias en tu respuesta, sin quedarte solo "
    "con la primera que encontrás. Por ejemplo, si un docente dicta 2 materias "
    "distintas y el contexto trae ambas, tu respuesta debe mencionar las 2, no 1. "
    "Si el contexto trae un bloque de datos en formato JSON (una lista de "
    "objetos), tratá cada objeto como un registro completo e independiente, "
    "pero NUNCA menciones en tu respuesta palabras como \"contexto\", "
    "\"JSON\", \"registro\", \"fragmento\" o \"documento\": esas son cosas "
    "internas del sistema, no de la respuesta. Respondé directo, como si ya "
    "supieras el dato de memoria.\n\n"
    "Si te paso una \"Pregunta anterior\" y \"Respuesta anterior\": es una "
    "conversación en curso, y la pregunta actual es una continuación (ej. "
    "\"¿y en qué horario?\" después de preguntar por un docente puntual). "
    "En ese caso, el contexto puede traer datos de VARIAS personas o "
    "grupos que coinciden por palabra suelta (ej. varios profesores dictan "
    "\"Base de Datos\"), pero tu respuesta debe quedarse enfocada en la "
    "persona/materia/grupo que ya se había establecido en la respuesta "
    "anterior, no mezclar ahí datos de otras personas o grupos que no "
    "vienen al caso. Solo salís de ese foco si la pregunta actual menciona "
    "explícitamente algo distinto.\n\n"
    "Tono didáctico: explicá como si hablaras con un estudiante que recién "
    "empieza la carrera. Antes de dar el dato puntual, ubicá brevemente de qué "
    "se trata (ej. \"Sobre la convocatoria de becas: ...\"), usá oraciones "
    "cortas y palabras simples, y evitá tecnicismos innecesarios o siglas sin "
    "explicar la primera vez que aparecen.\n\n"
    "Formato de respuesta: escribí SIEMPRE en texto plano y natural, como si "
    "chatearas por WhatsApp. Está PROHIBIDO usar cualquier símbolo de "
    "formato: nada de asteriscos (**negrita** o *cursiva*), guiones bajos "
    "(_cursiva_), comillas invertidas (`código`), numerales para títulos (# "
    "Título), tablas con barras verticales (| columna |), ni viñetas raras "
    "como •, ▪, ‣ o ➤. Tampoco uses emojis. Si hay varios elementos que "
    "listar (varios docentes de una materia, o varias materias de un "
    "docente), usá una lista simple con guiones normales, un elemento por "
    "línea, así:\n"
    "- Estructura de Datos (SIS312), Grupo 2\n"
    "- Análisis Discreto (SIS342), Grupos 1 y 2\n"
    "Mantené las respuestas claras, breves y directas, como si se lo "
    "explicaras a alguien en una conversación de texto normal.\n\n"
    "RESPUESTAS CORTAS: máximo 1 oración de introducción y luego la lista. "
    "Sin despedidas, sin repetir la pregunta, sin aclaraciones innecesarias. "
    "Cada elemento de la lista en UNA línea, con el formato "
    "\"Materia (SIGLA) - Docente - Día hora - Ambiente\", incluyendo solo "
    "los datos que la pregunta pide. Si hay muchos grupos de la misma "
    "materia, agrupalos en una sola línea (ej. \"grupos 1 y 2\"). Si la "
    "pregunta es solo por QUÉ materias hay, listá únicamente \"Materia "
    "(SIGLA)\", sin docentes ni horarios; si pregunta por docentes, sumá el "
    "docente; los horarios/ambientes solo si los piden.\n\n"
    "TEXTO DE IMÁGENES: parte del contexto viene de fotos de carteles y "
    "comunicados leídas con OCR, así que puede tener errores de lectura "
    "(letras cambiadas, palabras cortadas, símbolos sueltos) y una lista final "
    "de \"otras palabras detectadas\" sin orden. Interpretá esos errores con "
    "sentido común (ej. \"FLAMPAGO\" es \"relámpago\", \"tecnoldgico\" es "
    "\"tecnológico\") y armá la respuesta con los datos que sí se entienden "
    "(fechas, horas, lugares, precios, requisitos). Si preguntan cuánto cuesta "
    "inscribirse o participar y el texto trae un monto en Bs. (ej. \"Bs. 30 por "
    "equipo\", \"Bs. 150 por equipo\"), ese monto es el costo: respondelo. Solo decí que no tenés la "
    "información si de verdad no hay ningún dato relacionado con la pregunta.\n\n"
    "MENSAJES QUE NO SON CONSULTAS: si el estudiante cuenta algo de su situación "
    "personal (ej. \"reprobé una materia\", \"estoy cansado\"), hace un comentario o "
    "pide algo ajeno a la carrera (tareas, temas generales, opiniones), NO respondas "
    "con listas de materias ni otros datos que nadie pidió. Contestá en una o dos "
    "oraciones: con empatía si corresponde, aclarando que no tenés acceso a sus notas "
    "ni a su kárdex, y ofreciendo ayuda con lo que sí sabés (materias, docentes, "
    "horarios, becas, convocatorias y avisos de Ingeniería de Sistemas UATF)."
)


# Emojis y pictogramas comunes (rangos Unicode donde viven la mayoría).
_PATRON_EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # símbolos, pictogramas, emoticones, transporte, etc.
    "\U00002600-\U000027BF"  # símbolos varios y dingbats (☀ ✅ ➤ ✂ etc.)
    "\U0001F1E6-\U0001F1FF"  # banderas
    "]+",
    flags=re.UNICODE,
)

# Viñetas "raras" que el modelo a veces usa en vez de un guion normal.
_PATRON_VINETAS_RARAS = re.compile(r"^[•▪◦‣➤→»]\s*", flags=re.MULTILINE)


def limpiar_formato(texto: str) -> str:
    """
    Quita cualquier resto de sintaxis Markdown o símbolos raros que el
    modelo haya usado a pesar de la instrucción del SYSTEM_PROMPT. Es la
    red de seguridad determinística: no depende de que el modelo "obedezca"
    bien, así la respuesta que llega al frontend siempre es texto plano y
    legible para un estudiante.
    """
    # Negrita/cursiva: **texto** o *texto* -> texto
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"(?<!\*)\*([^\*\n]+?)\*(?!\*)", r"\1", texto)

    # Cursiva con guion bajo: _texto_ -> texto (solo si rodea palabras, para
    # no tocar guiones bajos legítimos dentro de correos o códigos).
    texto = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"\1", texto)

    # Código en línea o en bloque: `texto` o ```texto``` -> texto
    texto = re.sub(r"```(.*?)```", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"`([^`\n]+?)`", r"\1", texto)

    # Encabezados: "# Título" -> "Título"
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)

    # Líneas separadoras tipo "---", "___", "***" -> se descartan
    texto = re.sub(r"^\s*([-_*])\1{2,}\s*$", "", texto, flags=re.MULTILINE)

    # Tablas markdown ("| a | b |") -> líneas simples ("a - b")
    lineas_nuevas = []
    for linea in texto.split("\n"):
        cruda = linea.strip()
        if cruda.startswith("|") and cruda.endswith("|"):
            celdas = [c.strip() for c in cruda.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", c) for c in celdas):
                continue  # fila separadora (---|---|---), se descarta
            lineas_nuevas.append(" - ".join(celdas))
        else:
            lineas_nuevas.append(linea)
    texto = "\n".join(lineas_nuevas)

    # Viñetas con asterisco o símbolos raros (•, ▪, ➤, →...) -> guion normal
    texto = re.sub(r"^\*\s+", "- ", texto, flags=re.MULTILINE)
    texto = _PATRON_VINETAS_RARAS.sub("- ", texto)

    # Comillas "inteligentes" y emojis -> versión simple / se eliminan
    texto = texto.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    texto = _PATRON_EMOJI.sub("", texto)

    # Colapsar espacios dobles que puedan haber quedado tras las limpiezas
    texto = re.sub(r"[ \t]{2,}", " ", texto)

    return texto.strip()


def preparar_contexto(fragmentos_contexto: list[str], presupuesto_tokens: int = PRESUPUESTO_TOKENS_CONTEXTO) -> str:
    """
    Une los fragmentos de contexto respetando un presupuesto de tokens
    (estimado), en vez de mandarle a Groq TODO lo que encontró la búsqueda
    sin control. Los fragmentos ya vienen ordenados por prioridad (filtro
    exacto / JSON estructurado primero, luego texto, luego semántico), así
    que si hay que recortar, se recorta desde el final —lo menos relevante—
    y nunca desde el principio.

    Esto es lo que evita mandarle "toda la carga pesada" a Groq en cada
    pregunta: la búsqueda puede encontrar decenas de fragmentos, pero acá se
    decide cuántos realmente vale la pena pagar en tokens.
    """
    if not fragmentos_contexto:
        return "No se encontró información relevante para esta pregunta."

    presupuesto_caracteres = presupuesto_tokens * CARACTERES_POR_TOKEN
    incluidos = []
    caracteres_usados = 0

    for fragmento in fragmentos_contexto:
        if caracteres_usados + len(fragmento) > presupuesto_caracteres and incluidos:
            break
        incluidos.append(fragmento)
        caracteres_usados += len(fragmento)

    return "\n---\n".join(incluidos)


class LimiteIAError(Exception):
    """Todos los modelos disponibles alcanzaron su límite de uso (o el pedido no entra en ninguno)."""

    def __init__(self, diario: bool = False):
        super().__init__("límite de uso de la IA alcanzado")
        self.diario = diario


# modelo -> (instante hasta el que no se usa, si el bloqueo fue por límite DIARIO)
_bloqueados: dict[str, tuple[float, bool]] = {}
_BLOQUEO_DIARIO_SEGUNDOS = 30 * 60  # se vuelve a probar cada 30 min: el cupo diario se libera de a poco
_BLOQUEO_MAXIMO_POR_MINUTO = 120


def _libre(modelo: str) -> bool:
    return _bloqueados.get(modelo, (0.0, False))[0] <= time.time()


def _bloquear(modelo: str, error: APIStatusError) -> None:
    """Un modelo devolvió 429: se deja de usar un rato y los pedidos siguen por los demás."""
    diario = "per day" in str(error).lower()
    if diario:
        segundos = _BLOQUEO_DIARIO_SEGUNDOS
    else:
        try:
            segundos = min(float(error.response.headers.get("retry-after")) + 0.5, _BLOQUEO_MAXIMO_POR_MINUTO)
        except (TypeError, ValueError, AttributeError):
            segundos = 60.0
    _bloqueados[modelo] = (time.time() + segundos, diario)


def estado_modelos() -> dict[str, str]:
    """Para diagnóstico: 'libre' o 'bloqueado (N s)' por modelo."""
    ahora = time.time()
    return {
        m: "libre" if _libre(m) else f"bloqueado ({int(_bloqueados[m][0] - ahora)} s)"
        for m in MODELOS
    }


def generar_respuesta(
    pregunta: str,
    fragmentos_contexto: list[str],
    pregunta_anterior: str | None = None,
    respuesta_anterior: str | None = None,
) -> tuple[str, int, str]:
    """
    Arma el prompt con el contexto recuperado de ChromaDB y consulta a Groq.
    Devuelve (respuesta, tokens usados, modelo que respondió).

    Se prueba cada modelo de MODELOS en orden: si uno alcanza su límite (429) se
    bloquea un rato y el pedido sigue con el siguiente, así los cupos de todos
    se suman. Si todos están agotados se espera unos segundos (límite por
    minuto) o se lanza LimiteIAError (límite diario).
    """
    if pregunta_anterior:
        # Para preguntas de seguimiento ("¿y quién la dicta?"): sin esto,
        # Groq no tiene forma de saber a qué se refiere "la" o "esos". Y sin
        # la RESPUESTA anterior, tampoco sabe a cuál de varias coincidencias
        # posibles (ej. varios docentes de "Base de Datos") se refería la
        # respuesta previa —ver la instrucción de "quedate enfocado" en
        # SYSTEM_PROMPT.
        bloque_respuesta_anterior = (
            f"Respuesta anterior del asistente: {respuesta_anterior}\n" if respuesta_anterior else ""
        )
        cola = (
            f"Pregunta anterior del estudiante: {pregunta_anterior}\n"
            f"{bloque_respuesta_anterior}"
            f"Pregunta actual del estudiante: {pregunta}"
        )
    else:
        cola = f"Pregunta del estudiante: {pregunta}"

    presupuesto = PRESUPUESTO_TOKENS_CONTEXTO
    reducciones = esperas = 0
    while True:
        contexto = preparar_contexto(fragmentos_contexto, presupuesto)
        mensajes = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Contexto disponible:\n{contexto}\n\n{cola}"},
        ]

        candidatos = [m for m in MODELOS if _libre(m)]
        if not candidatos:
            # Todos agotados: si el que se libera antes lo hace en pocos segundos se espera
            # (el estudiante ve una respuesta lenta, no un error); si no, se avisa.
            libera_en = min(_bloqueados[m][0] for m in MODELOS) - time.time()
            if libera_en <= ESPERA_MAXIMA_SEGUNDOS and esperas < 2:
                esperas += 1
                time.sleep(max(libera_en, 0) + 0.5)
                continue
            raise LimiteIAError(diario=all(_bloqueados[m][1] for m in MODELOS))

        demasiado_grande = False
        for modelo in candidatos:
            ajustes = MODELOS_CONOCIDOS.get(modelo, _AJUSTES_POR_DEFECTO)
            try:
                respuesta = _client.chat.completions.create(
                    model=modelo,
                    messages=mensajes,
                    temperature=0.1,
                    max_tokens=ajustes["max_tokens"],
                    **({"extra_body": ajustes["extra_body"]} if ajustes["extra_body"] else {}),
                )
            except APIStatusError as e:
                if e.status_code == 413:
                    demasiado_grande = True  # el contexto no entra: se achica y se reintenta
                    break
                if e.status_code == 429:
                    _bloquear(modelo, e)
                    continue
                raise
            tokens = getattr(respuesta.usage, "total_tokens", 0) or 0
            return limpiar_formato(respuesta.choices[0].message.content or ""), tokens, modelo

        if demasiado_grande:
            if reducciones == 2:
                raise LimiteIAError(diario=False)
            reducciones += 1
            presupuesto //= 2
