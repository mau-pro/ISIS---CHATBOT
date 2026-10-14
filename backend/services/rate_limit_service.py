"""
services/rate_limit_service.py
-------------------------------
Rate limiting explícito por rol, usando la librería `limits` (la misma que
usa slowapi por debajo) directamente. /chat exige cuenta, así que hay 2 casos:

- Estudiante (con token)   -> límite por email, ej. 30/hora
- Admin (con token)        -> sin límite

`check_rate_limit(request)` decide qué caso aplica y lanza HTTPException 429
si se superó el límite. Se llama explícitamente al inicio de /chat.
"""

import os
from fastapi import Request, HTTPException, status
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from services.auth_service import _decode_token

RATE_LIMIT_ESTUDIANTE = os.getenv("RATE_LIMIT_ESTUDIANTE", "30/hour")

# MemoryStorage alcanza para un solo proceso/servidor. Si el proyecto crece a
# múltiples instancias, cambiar a RedisStorage sin tocar el resto del código.
_storage = MemoryStorage()
_strategy = MovingWindowRateLimiter(_storage)

_limite_estudiante = parse(RATE_LIMIT_ESTUDIANTE)


def _usuario_desde_request(request: Request) -> dict | None:
    """Decodifica el JWT del header Authorization, si existe. Devuelve el payload o None."""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    return _decode_token(token)


def check_rate_limit(request: Request) -> None:
    """
    Aplica el límite correspondiente según quién hace la petición (siempre
    logueado, porque /chat usa get_current_user). Lanza HTTPException 429 si
    se supera el límite permitido.
    """
    payload = _usuario_desde_request(request) or {}

    if payload.get("role") == "admin":
        return  # admin sin límite

    permitido = _strategy.hit(_limite_estudiante, f"user:{payload.get('sub')}")
    if not permitido:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Superaste el límite de consultas por hora. Intenta más tarde.",
        )
