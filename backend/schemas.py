"""
schemas.py
----------
Modelos Pydantic usados para validar los datos de entrada/salida de la API.
Mantenerlos separados de los modelos de SQLAlchemy (models/) es una buena
práctica: schemas.py define la "forma" de la API, models/ define la base de datos.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from models.document import DocumentCategory
from models.user import UserRole


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    nueva_password: str


# ---------- Chat ----------

class ChatRequest(BaseModel):
    pregunta: str
    # Si se manda, en vez de crear una consulta nueva se reemplaza la
    # pregunta/respuesta de ese registro existente (edición de una pregunta
    # ya enviada) — así una corrección no cuenta como una consulta aparte
    # en el historial ni en las estadísticas.
    editar_id: int | None = None
    # La pregunta y respuesta inmediatamente anteriores del mismo chat (si
    # las hay). El backend no guarda historial de conversación entre
    # requests, así que el frontend manda esto para que preguntas de
    # seguimiento como "¿y quién la dicta?" o "¿y en qué horario da esa
    # materia?" puedan heredar el semestre/grupo/sigla/docente ya
    # establecido en vez de perder ese contexto y traer datos de todos los
    # grupos/docentes que coincidan con la palabra suelta.
    pregunta_anterior: str | None = None
    respuesta_anterior: str | None = None


class ChatResponse(BaseModel):
    id: int
    respuesta: str
    desde_cache: bool = False


# ---------- Documentos (admin) ----------

class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_type: str
    category: DocumentCategory
    chunk_count: int
    uploaded_at: datetime
    size_bytes: int | None = None

    class Config:
        from_attributes = True


class DocumentosPaginados(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


# ---------- Documentos públicos (inicio, sin cuenta) ----------

class DocumentoPublicoResponse(BaseModel):
    id: int
    filename: str
    original_type: str
    uploaded_at: datetime
    size_bytes: int | None = None

    class Config:
        from_attributes = True


# ---------- Historial de chat (estudiante) ----------

class ChatLogResponse(BaseModel):
    id: int
    pregunta: str
    respuesta: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Estadísticas (admin) ----------

class StatsResponse(BaseModel):
    total_estudiantes: int
    total_documentos: int
    total_fragmentos: int
    total_consultas: int
    consultas_hoy: int
    consultas_por_categoria: dict[str, int]
    respuestas_desde_cache: int = 0
    preguntas_aprendidas: int = 0
    tokens_hoy: int = 0
    tokens_por_modelo: dict[str, int] = {}  # hoy, un cupo diario de 200.000 por modelo
    limite_tokens_dia: int = 200000  # plan gratuito de Groq para openai/gpt-oss-120b


class ModelosIAUpdate(BaseModel):
    """Qué modelos de IA quedan encendidos y cuál responde primero (panel Estadísticas)."""
    activos: list[str]
    principal: str


# ---------- Gestión de usuarios y roles (admin) ----------

class UserAdminResponse(BaseModel):
    id: int
    username: str | None = None
    email: str
    role: UserRole
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RoleUpdateRequest(BaseModel):
    role: UserRole


# ---------- Paginación ----------

class UsuariosPaginados(BaseModel):
    items: list[UserAdminResponse]
    total: int
    page: int
    page_size: int
    total_admins: int = 0
    total_estudiantes: int = 0


class HistorialPaginado(BaseModel):
    items: list[ChatLogResponse]
    total: int
    page: int
    page_size: int
