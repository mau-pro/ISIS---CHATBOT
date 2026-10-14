"""
services/username_service.py
------------------------------
Reglas del nombre de usuario (lo que se escribe en el login en vez del
correo) y utilidades para generarlo a partir de un correo, usadas al migrar
las cuentas que se crearon antes de que existiera el campo.

Reglas: entre 3 y 30 caracteres; letras, números, punto, guion y guion bajo;
se guarda siempre en minúsculas (el login no distingue mayúsculas).
"""

import re

USERNAME_MIN = 3
USERNAME_MAX = 30
_PERMITIDO = re.compile(r"^[a-z0-9._-]+$")

MENSAJE_USERNAME_INVALIDO = (
    f"El nombre de usuario debe tener entre {USERNAME_MIN} y {USERNAME_MAX} caracteres "
    "y solo puede usar letras, números, punto, guion y guion bajo."
)


def normalizar_username(valor: str) -> str:
    return (valor or "").strip().lower()


def username_valido(valor: str) -> bool:
    return USERNAME_MIN <= len(valor) <= USERNAME_MAX and bool(_PERMITIDO.match(valor))


def username_desde_email(email: str, usados: set[str]) -> str:
    """Toma la parte del correo antes de la @, la limpia y, si ya está en uso,
    le agrega un número hasta que sea único. Agrega el resultado a `usados`."""
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower())[:USERNAME_MAX] or "usuario"
    base = base.ljust(USERNAME_MIN, "0")
    candidato, n = base, 1
    while candidato in usados:
        n += 1
        sufijo = str(n)
        candidato = base[: USERNAME_MAX - len(sufijo)] + sufijo
    usados.add(candidato)
    return candidato
