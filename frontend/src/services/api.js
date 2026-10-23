/**
 * services/api.js
 * -----------------
 * Cliente axios único para toda la app. Agrega automáticamente el JWT
 * (si existe en localStorage) a cada petición, así los componentes no
 * tienen que preocuparse por eso.
 */

import axios from "axios";
import { leerSesion, borrarSesionDelAlmacen } from "../utils/sesion.js";

// En desarrollo la API está en el puerto 8000. En Docker se compila con VITE_API_URL=/api y nginx
// reenvía /api al backend (mismo dominio: sin problemas de CORS).
export const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = leerSesion("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si el servidor responde 401 estando con sesión, es que el token venció (dura 1 hora):
// se cierra la sesión y se vuelve al inicio con un aviso, en vez de mostrar errores genéricos.
api.interceptors.response.use(
  (respuesta) => respuesta,
  (error) => {
    const url = error.config?.url || "";
    if (error.response?.status === 401 && leerSesion("token") && !url.includes("/auth/")) {
      borrarSesionDelAlmacen();
      window.location.href = "/login?expirada=1";
    }
    return Promise.reject(error);
  }
);

// ---------- Auth ----------
export const login = (username, password) =>
  api.post("/auth/login", { username, password });

export const register = (username, email, password) =>
  api.post("/auth/register", { username, email, password });

export const solicitarRecuperacion = (email) =>
  api.post("/auth/forgot-password", { email });

export const restablecerPassword = (token, nuevaPassword) =>
  api.post("/auth/reset-password", { token, nueva_password: nuevaPassword });

// ---------- Chat ----------
// editarId (opcional): si se manda, el backend reemplaza esa pregunta ya
// enviada en vez de crear una consulta nueva (edición, no duplica historial).
// preguntaAnterior/respuestaAnterior (opcionales): el intercambio previo del
// mismo chat, para que el backend pueda resolver seguimientos como "¿y
// quién la dicta?" sin mezclar datos de otras personas/grupos parecidos.
export const enviarPregunta = (pregunta, editarId, preguntaAnterior, respuestaAnterior) =>
  api.post("/chat", {
    pregunta,
    ...(editarId ? { editar_id: editarId } : {}),
    ...(preguntaAnterior ? { pregunta_anterior: preguntaAnterior } : {}),
    ...(respuestaAnterior ? { respuesta_anterior: respuestaAnterior } : {}),
  });
export const obtenerHistorial = (page = 1, pageSize = 8) =>
  api.get("/chat/history", { params: { page, page_size: pageSize } });
export const eliminarHistorial = () => api.delete("/chat/history");

// ---------- Admin: documentos ----------
export const listarDocumentos = (page = 1, pageSize = 6, q = "") =>
  api.get("/admin/documents", { params: { page, page_size: pageSize, q } });

export const subirDocumento = (file, category) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category", category);
  return api.post("/admin/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const eliminarDocumento = (id) => api.delete(`/admin/documents/${id}`);

// ---------- Admin: estadísticas ----------
export const obtenerEstadisticas = () => api.get("/admin/stats");
export const listarModelosIA = () => api.get("/admin/modelos-ia");
export const configurarModelosIA = (activos, principal) => api.put("/admin/modelos-ia", { activos, principal });

// ---------- Admin: usuarios y roles ----------
export const listarUsuarios = (page = 1, pageSize = 10, q = "", rol = "") =>
  api.get("/admin/users", { params: { page, page_size: pageSize, q, rol } });
export const cambiarRolUsuario = (id, role) =>
  api.patch(`/admin/users/${id}/role`, { role });
export const eliminarUsuario = (id) => api.delete(`/admin/users/${id}`);

// ---------- Preguntas aprendidas (caché) ----------
export const listarPreguntasAprendidas = () => api.get("/admin/cache");
export const olvidarPregunta = (id) => api.delete(`/admin/cache/${id}`);
export const olvidarTodas = () => api.delete("/admin/cache");

// ---------- Documentos públicos (inicio, sin cuenta) ----------
export const listarDocumentosPublicos = (seccion) =>
  api.get("/documentos", { params: { seccion } });

export const urlDescargaDocumento = (id) => `${BASE_URL}/documentos/${id}/descargar`;

export default api;