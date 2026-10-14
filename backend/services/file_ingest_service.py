"""
services/file_ingest_service.py
---------------------------------
Convierte los archivos que sube el admin (PDF, Word, Excel o Imagen) en
texto plano, y luego lo trocea (chunking) para poder indexarlo en ChromaDB.

Flujo: extract_text(archivo) -> chunk_text(texto) -> (vector_service se encarga
de generar embeddings y guardar en ChromaDB)

Las imágenes se procesan con OCR (Tesseract, vía pytesseract) ACÁ, en el
servidor, antes de que la IA vea nada: así el texto de la imagen queda
indexado como cualquier otro documento y la pregunta del estudiante solo
gasta tokens de Groq para la búsqueda semántica normal —nunca se manda la
imagen en sí a un modelo de IA (eso sería mucho más caro en tokens).
"""

import io
import os
import re
import pdfplumber
from docx import Document as DocxDocument
import openpyxl
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

from services.query_parser import sin_acentos

_TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if _TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD

EXTENSIONES_IMAGEN = {"png", "jpg", "jpeg", "webp", "bmp", "tiff"}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrae todo el texto de un PDF, página por página."""
    texto = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texto.append(page_text)
    return "\n".join(texto)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extrae texto de un Word: párrafos y tablas."""
    doc = DocxDocument(io.BytesIO(file_bytes))
    partes = [p.text for p in doc.paragraphs if p.text.strip()]

    for tabla in doc.tables:
        for fila in tabla.rows:
            celdas = [celda.text.strip() for celda in fila.cells]
            partes.append(" | ".join(celdas))

    return "\n".join(partes)


def extract_text_from_xlsx(file_bytes: bytes) -> str:
    """
    Extrae texto de un Excel, usado para PDF/Word que sí necesitan trocearse
    por caracteres. Para Excel, usar filas_como_chunks() en su lugar (ver abajo),
    que preserva cada fila como una unidad completa e indivisible.
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    partes = []

    for hoja in wb.worksheets:
        filas = list(hoja.iter_rows(values_only=True))
        if not filas:
            continue

        encabezados = [str(c) if c is not None else "" for c in filas[0]]
        for fila in filas[1:]:
            pares = []
            for encabezado, valor in zip(encabezados, fila):
                if valor is not None and str(valor).strip():
                    pares.append(f"{encabezado}: {valor}")
            if pares:
                partes.append(", ".join(pares))

    return "\n".join(partes)


def filas_como_chunks(file_bytes: bytes) -> list[str]:
    """
    Convierte cada fila de un Excel en su propio chunk independiente, en vez
    de trocear por cantidad de caracteres. Esto es clave para datos tabulares:
    una fila (ej. "Docente: X, Sigla: Y, Materia: Z, Grupo: 1") nunca debe
    quedar cortada a la mitad ni mezclada con otras filas dentro del mismo
    chunk — cada registro tiene que ser una unidad completa para que la
    búsqueda semántica lo recupere entero.
    """
    return [texto for texto, _ in filas_con_metadata(file_bytes)]


def filas_con_metadata(file_bytes: bytes) -> list[tuple[str, dict]]:
    """
    Igual que filas_como_chunks(), pero además devuelve un diccionario por
    fila con cada columna en minúscula (ej. {"semestre": "1", "grupo": "1",
    "sigla": "SIS110"}). Ese diccionario se guarda como metadata en ChromaDB
    y permite hacer FILTROS EXACTOS (no solo búsqueda por similitud) — clave
    para preguntas tipo "todas las materias del semestre 1", donde hace falta
    traer TODAS las filas que cumplen la condición, no solo las "parecidas".
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    resultado = []

    for hoja in wb.worksheets:
        filas = list(hoja.iter_rows(values_only=True))
        if not filas:
            continue

        encabezados = [str(c) if c is not None else "" for c in filas[0]]
        for fila in filas[1:]:
            pares = []
            metadata_fila = {}
            for encabezado, valor in zip(encabezados, fila):
                if valor is not None and str(valor).strip():
                    pares.append(f"{encabezado}: {valor}")
                    clave = encabezado.strip().lower()
                    if clave:
                        metadata_fila[clave] = str(valor).strip()
            if pares:
                resultado.append((", ".join(pares), metadata_fila))

    return resultado


def _preparar_imagen_para_ocr(imagen: Image.Image) -> Image.Image:
    """
    Escala de grises + más contraste + agrandar 2x: Tesseract lee bastante
    mejor así fotos/capturas con poco contraste o texto chico (típico en
    carteles/avisos con fondo de color, letras chicas o fotos sacadas con
    el celular). No es magia —un cartel muy decorado (fuentes estilizadas,
    texto rotado, neón) igual puede salir mal—, pero ayuda en el caso común.
    """
    gris = ImageOps.grayscale(imagen)
    agrandada = gris.resize((gris.width * 2, gris.height * 2))
    return ImageEnhance.Contrast(agrandada).enhance(2.0)


def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Extrae el texto visible en una imagen (foto de un aviso, captura de un
    horario, etc.) usando OCR local con Tesseract. "spa+eng" reconoce texto
    en español e inglés en la misma pasada; si el idioma "spa" no está
    instalado en el Tesseract del sistema, reintenta con el idioma por
    defecto en vez de fallar la subida completa.

    IMPORTANTE: el OCR no es infalible, sobre todo con carteles muy
    diseñados (múltiples fuentes, colores, texto en ángulos raros). Para
    ese tipo de imagen, lo más confiable sigue siendo que el admin escriba
    los datos clave a mano (ej. en un Word/aviso corto) además de subir la
    imagen, en vez de depender 100% del OCR.
    """
    original = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    # Pasada principal: conserva líneas y párrafos (bien para comunicados y
    # documentos escaneados, que son texto corrido). Se prueban varias
    # versiones de la imagen (contraste, tamaño) y se queda la que Tesseract
    # lee con más confianza: no hay una sola preparación que sirva para todas.
    texto = _limpiar_texto_ocr(_mejor_lectura_principal(original))

    # Carteles (fondo oscuro, letras de neón, texto suelto por todos lados):
    # el modo por defecto de Tesseract lee muy poco. Si la pasada principal
    # devolvió poco texto corrido, se hacen pasadas extra en modo "texto
    # disperso" y se agregan SOLO las palabras nuevas (con confianza suficiente).
    palabras_vistas = set(_tokens_ocr(texto))
    if len(palabras_vistas) < _MIN_PALABRAS_TEXTO_CORRIDO:
        extra = _palabras_extra_de_cartel(original, palabras_vistas)
        if extra:
            texto += "\n\nOtras palabras detectadas en la imagen: " + " ".join(extra)
    return texto


# Con esta cantidad de palabras en la pasada principal, la imagen se considera
# "texto corrido" (documento/comunicado) y no se hacen las pasadas extra.
_MIN_PALABRAS_TEXTO_CORRIDO = 150
_CONFIANZA_MINIMA_EXTRA = 40  # % de confianza de Tesseract para aceptar una palabra extra


def _idioma_ocr() -> str:
    """'spa+eng' si el Tesseract instalado tiene el idioma español; si no, solo
    inglés (pedir 'spa' sin tenerlo hace fallar cada lectura y obliga a reintentar)."""
    try:
        instalados = set(pytesseract.get_languages(config=""))
    except Exception:
        return "eng"
    return "spa+eng" if "spa" in instalados else "eng"


_IDIOMA_OCR = _idioma_ocr()


def _tokens_ocr(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9:]{3,}", sin_acentos(texto))


def _leer_con_puntaje(imagen: Image.Image) -> tuple[float, int, str]:
    """Una pasada de OCR (modo por defecto). Devuelve (puntaje, palabras buenas,
    texto por líneas). El puntaje suma la confianza de las palabras de 3+ letras
    con confianza >= 50%: sube con más palabras bien leídas, no con basura."""
    datos = pytesseract.image_to_data(imagen, lang=_IDIOMA_OCR, output_type=pytesseract.Output.DICT)
    puntaje, buenas = 0.0, 0
    lineas: dict[tuple[int, int, int], list[str]] = {}
    for i, palabra in enumerate(datos["text"]):
        palabra = palabra.strip()
        try:
            confianza = float(datos["conf"][i])
        except ValueError:
            continue
        if not palabra or confianza < 30:  # por debajo de 30% casi siempre es ruido
            continue
        if len(palabra) >= 3 and confianza >= 50 and re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{3}", palabra):
            puntaje += confianza
            buenas += 1
        clave = (datos["block_num"][i], datos["par_num"][i], datos["line_num"][i])
        lineas.setdefault(clave, []).append(palabra)
    texto, bloque_previo = [], None
    for (bloque, par, _), palabras in lineas.items():
        if bloque_previo is not None and (bloque, par) != bloque_previo:
            texto.append("")  # línea en blanco entre párrafos
        texto.append(" ".join(palabras))
        bloque_previo = (bloque, par)
    return puntaje, buenas, "\n".join(texto)


def _mejor_lectura_principal(original: Image.Image) -> str:
    gris = ImageOps.grayscale(original)
    candidatas = [
        _preparar_imagen_para_ocr(original),  # gris + contraste + 2x
        ImageOps.autocontrast(gris.resize((gris.width * 2, gris.height * 2), Image.LANCZOS)),
    ]
    mejor = max((_leer_con_puntaje(c) for c in candidatas), key=lambda r: r[0])
    # Poco texto bien leído = cartel/foto difícil: se prueba también ampliando 3x.
    if mejor[1] < 80:
        ampliada = ImageOps.autocontrast(gris.resize((gris.width * 3, gris.height * 3), Image.LANCZOS))
        mejor = max(mejor, _leer_con_puntaje(ampliada), key=lambda r: r[0])
    return mejor[2]


def _limpiar_texto_ocr(texto: str) -> str:
    """Quita del resultado del OCR las líneas que son puro ruido (símbolos y
    letras sueltas de logos, íconos y fondos), que solo ensucian el contexto."""
    lineas = []
    for linea in texto.replace("�", " ").splitlines():
        linea = re.sub(r"\s+", " ", linea).strip()
        sin_espacios = linea.replace(" ", "")
        if sum(c.isalnum() for c in sin_espacios) < 3:
            continue
        if sum(c.isalnum() for c in sin_espacios) / len(sin_espacios) < 0.6:
            continue
        lineas.append(linea)
    return "\n".join(lineas)


def _palabras_extra_de_cartel(original: Image.Image, ya_vistas: set[str]) -> list[str]:
    gris = ImageOps.grayscale(original)
    variantes = [
        (ImageOps.autocontrast(gris.resize((gris.width * 3, gris.height * 3), Image.LANCZOS)), 11),
        (ImageOps.invert(ImageOps.autocontrast(
            original.split()[0].resize((original.width * 2, original.height * 2), Image.LANCZOS))), 11),
        (ImageEnhance.Contrast(gris.resize((gris.width * 2, gris.height * 2))).enhance(2.0), 11),
        (ImageOps.autocontrast(gris.resize((gris.width * 3, gris.height * 3), Image.LANCZOS)), 6),
    ]
    nuevas: list[str] = []
    for imagen, psm in variantes:
        try:
            datos = pytesseract.image_to_data(
                imagen, lang=_IDIOMA_OCR, config=f"--psm {psm}", output_type=pytesseract.Output.DICT
            )
        except pytesseract.TesseractError:
            continue
        for palabra, confianza in zip(datos["text"], datos["conf"]):
            try:
                if float(confianza) < _CONFIANZA_MINIMA_EXTRA:
                    continue
            except ValueError:
                continue
            for token in _tokens_ocr(palabra):
                if token not in ya_vistas:
                    ya_vistas.add(token)
                    nuevas.append(token)
    return nuevas


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Detecta el tipo de archivo por su extensión y llama al extractor correcto."""
    extension = filename.lower().rsplit(".", 1)[-1]

    if extension == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif extension == "docx":
        return extract_text_from_docx(file_bytes)
    elif extension in ("xlsx", "xlsm"):
        return extract_text_from_xlsx(file_bytes)
    elif extension in EXTENSIONES_IMAGEN:
        return extract_text_from_image(file_bytes)
    else:
        raise ValueError(f"Tipo de archivo no soportado: .{extension}")


def chunk_text(texto: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """
    Trocea el texto en fragmentos de ~chunk_size caracteres, con solapamiento
    (overlap) entre fragmentos para no perder contexto en los cortes.
    """
    texto = texto.strip()
    if not texto:
        return []

    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + chunk_size
        chunks.append(texto[inicio:fin])
        inicio += chunk_size - overlap

    return chunks
