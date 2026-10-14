"""
models/chat_log.py
--------------------
Guarda cada pregunta/respuesta del chat. Sirve para dos cosas:
1. Historial temporal de preguntas del estudiante (endpoint /chat/history).
2. Base para las estadísticas del admin (cuántas consultas, cuándo, de quién).

user_id puede quedar NULL solo en registros viejos de cuando existía la pregunta libre sin cuenta.
es_prueba queda en True cuando la pregunta la hizo un admin desde el panel
"Probar Chatbot": permite excluir esas pruebas de las estadísticas reales
(ver GET /admin/stats) sin dejar de registrar el intercambio.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pregunta = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    es_prueba = Column(Boolean, nullable=False, default=False, server_default="0")
    desde_cache = Column(Boolean, nullable=False, default=False, server_default="0")
    tokens = Column(Integer, nullable=False, default=0, server_default="0")  # tokens de Groq gastados (0 si vino del caché o de datos directos)
    modelo = Column(String, nullable=True)  # modelo de IA que respondió (NULL = datos directos, caché o registros viejos)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
