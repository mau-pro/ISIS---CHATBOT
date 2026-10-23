"""
comparar_ia_local.py
----------------------
Compara, con las MISMAS preguntas, instrucciones y contexto que usa I-SIS, la IA en la nube
(Groq, el encadenado de modelos gratuitos) contra un modelo LOCAL corriendo en esta PC con
Ollama. Mide tiempo total, tiempo leyendo el contexto, velocidad de escritura, memoria usada
y guarda las respuestas para comparar su calidad.

Uso (desde backend/, con Ollama encendido y el modelo descargado):
    python comparar_ia_local.py qwen2.5:1.5b
Resultado: comparacion_ia_local.json (y un resumen en pantalla)
"""

import json
import sys
import time

import requests

from routes.chat_routes import _armar_fragmentos
import services.groq_service as g

OLLAMA = "http://localhost:11434"
MODELO_LOCAL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:1.5b"

PREGUNTAS = [
    ("imagen (OCR)", "cuando es el torneo de billar"),
    ("texto / docente", "que materias dicta el docente wilfredo terrazas"),
    ("documento PDF", "que requisitos piden para la beca de alimentacion"),
    ("imagen (OCR)", "hasta cuando puedo postular a la beca google"),
]


def memoria_ollama_mb() -> int:
    """RAM usada por los procesos de Ollama (Windows). El modelo corre en 'llama-server', aparte de 'ollama'."""
    try:
        import subprocess
        salida = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process | Where-Object { $_.Name -match 'ollama|llama-server' } | Measure-Object WorkingSet64 -Sum).Sum"],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
        return int(int(salida or 0) / 1024 / 1024)
    except Exception:
        return -1


def preguntar_local(mensajes: list[dict]) -> dict:
    t = time.time()
    r = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": MODELO_LOCAL,
            "messages": mensajes,
            "stream": False,
            # num_ctx: el contexto de I-SIS ronda 1.400-2.100 tokens; con el valor por defecto
            # (2048) Ollama recortaría el principio del mensaje.
            "options": {"temperature": 0.1, "num_ctx": 4096, "num_predict": 400},
        },
        timeout=900,
    ).json()
    total = time.time() - t
    ns = 1e9
    return {
        "segundos_total": round(total, 1),
        "segundos_leyendo_contexto": round(r.get("prompt_eval_duration", 0) / ns, 1),
        "tokens_contexto": r.get("prompt_eval_count"),
        "segundos_escribiendo": round(r.get("eval_duration", 0) / ns, 1),
        "tokens_respuesta": r.get("eval_count"),
        "tokens_por_segundo_escritura": round(r.get("eval_count", 0) / max(r.get("eval_duration", 1) / ns, 1e-9), 1),
        "segundos_cargando_modelo": round(r.get("load_duration", 0) / ns, 1),
        "respuesta": g.limpiar_formato(r.get("message", {}).get("content", "")),
    }


def preguntar_groq(pregunta: str, fragmentos: list[str]) -> dict:
    t = time.time()
    texto, tokens, modelo = g.generar_respuesta(pregunta, fragmentos)
    return {"segundos_total": round(time.time() - t, 1), "tokens": tokens, "modelo": modelo, "respuesta": texto}


def main() -> None:
    print(f"Modelo local: {MODELO_LOCAL}\n")
    # Calentamiento: la primera llamada carga el modelo en memoria (no es representativa)
    requests.post(f"{OLLAMA}/api/chat", json={"model": MODELO_LOCAL, "messages": [{"role": "user", "content": "hola"}],
                                               "stream": False, "options": {"num_predict": 5}}, timeout=900)
    resultados = []
    for tipo, pregunta in PREGUNTAS:
        fragmentos = _armar_fragmentos(pregunta)
        contexto = g.preparar_contexto(fragmentos)
        mensajes = [
            {"role": "system", "content": g.SYSTEM_PROMPT},
            {"role": "user", "content": f"Contexto disponible:\n{contexto}\n\nPregunta del estudiante: {pregunta}"},
        ]
        nube = preguntar_groq(pregunta, fragmentos)
        local = preguntar_local(mensajes)
        local["ram_ollama_mb"] = memoria_ollama_mb()
        resultados.append({"tipo": tipo, "pregunta": pregunta, "groq": nube, "local": local})
        print(f"[{tipo}] {pregunta}")
        print(f"   Groq  : {nube['segundos_total']:>6} s  -> {nube['respuesta'][:110]!r}")
        print(f"   Local : {local['segundos_total']:>6} s  (leer contexto {local['segundos_leyendo_contexto']} s de "
              f"{local['tokens_contexto']} tokens; escribir {local['segundos_escribiendo']} s a "
              f"{local['tokens_por_segundo_escritura']} tok/s; RAM {local['ram_ollama_mb']} MB)")
        print(f"           -> {local['respuesta'][:110]!r}\n")
        time.sleep(5)

    with open("comparacion_ia_local.json", "w", encoding="utf-8") as f:
        json.dump({"modelo_local": MODELO_LOCAL, "resultados": resultados}, f, ensure_ascii=False, indent=1)
    prom = lambda k, lado: round(sum(r[lado][k] for r in resultados) / len(resultados), 1)
    print(f"PROMEDIO  Groq: {prom('segundos_total', 'groq')} s  |  Local ({MODELO_LOCAL}): {prom('segundos_total', 'local')} s")


if __name__ == "__main__":
    main()
