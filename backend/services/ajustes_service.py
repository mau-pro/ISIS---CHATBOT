"""
services/ajustes_service.py
-----------------------------
Lectura y escritura de la tabla `ajustes` (valores en JSON) y aplicación de la
configuración de modelos de IA elegida por el admin.
"""

import json

from sqlalchemy.orm import Session

from models.ajuste import Ajuste
from services import groq_service

CLAVE_MODELOS_IA = "modelos_ia"


def leer(db: Session, clave: str, defecto=None):
    fila = db.get(Ajuste, clave)
    if fila is None:
        return defecto
    try:
        return json.loads(fila.valor)
    except ValueError:
        return defecto


def guardar(db: Session, clave: str, valor) -> None:
    fila = db.get(Ajuste, clave)
    if fila is None:
        db.add(Ajuste(clave=clave, valor=json.dumps(valor)))
    else:
        fila.valor = json.dumps(valor)
    db.commit()


def aplicar_modelos_guardados(db: Session) -> None:
    """Al arrancar: recupera qué modelos dejó activos el admin y cuál es el principal."""
    guardado = leer(db, CLAVE_MODELOS_IA)
    if guardado:
        groq_service.configurar_modelos(guardado.get("desactivados", []), guardado.get("principal"))


def guardar_modelos(db: Session, desactivados: list[str], principal: str | None) -> None:
    groq_service.configurar_modelos(desactivados, principal)
    # Se guardan los DESACTIVADOS (no los activos): un modelo nuevo que se sume a la
    # cadena en una versión futura arranca activo sin que el admin tenga que tocar nada.
    guardar(db, CLAVE_MODELOS_IA, {"desactivados": sorted(desactivados), "principal": principal})
