/**
 * utils/archivos.js
 * -------------------
 * Helpers compartidos entre la tabla de documentos del admin
 * (AdminDashboard) y las páginas públicas de descarga (DocumentosSeccion),
 * para que ambas muestren el mismo ícono/color por tipo de archivo y el
 * mismo formato de tamaño.
 */

const EXTENSIONES_IMAGEN = new Set(["png", "jpg", "jpeg", "webp", "bmp", "tiff"]);

/**
 * Ícono y colores por tipo de archivo: Excel verde, PDF rojo, Word azul,
 * imagen violeta. `clase` colorea el cuadro del ícono y `claseTipo` la
 * etiqueta (PDF, XLSX...) — ambas se definen en moderno.css.
 */
export function infoIconoArchivo(tipo) {
  const t = (tipo || "").toLowerCase();
  if (t === "pdf") return { icono: "picture_as_pdf", clase: "docs-archivo__icono--pdf", claseTipo: "docs-tipo-badge--pdf" };
  if (t === "docx") return { icono: "description", clase: "docs-archivo__icono--docx", claseTipo: "docs-tipo-badge--docx" };
  if (t === "xlsx" || t === "xlsm") return { icono: "grid_on", clase: "docs-archivo__icono--xlsx", claseTipo: "docs-tipo-badge--xlsx" };
  if (EXTENSIONES_IMAGEN.has(t)) return { icono: "image", clase: "docs-archivo__icono--imagen", claseTipo: "docs-tipo-badge--imagen" };
  return { icono: "draft", clase: "docs-archivo__icono--docx", claseTipo: "docs-tipo-badge--docx" };
}

export function formatearTamano(bytes) {
  if (bytes == null) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
