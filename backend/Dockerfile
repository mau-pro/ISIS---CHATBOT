# Backend de I-SIS (FastAPI). Imagen liviana de Python con Tesseract (OCR) y su idioma español.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# tesseract-ocr-spa = español para leer mejor tildes y palabras de los carteles
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Los datos viven en volúmenes (ver docker-compose.yml): /app/uploads (archivos originales)
# y /app/chroma_data (índice de búsqueda). Nada de eso se guarda dentro de la imagen.
EXPOSE 8000

# UN solo proceso a propósito: el límite de consultas por estudiante vive en memoria.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
