/**
 * utils/errores.js
 * ------------------
 * Convierte el error de una llamada a la API en un texto para mostrar.
 * FastAPI devuelve `detail` como texto en los errores propios (400/401/403...)
 * pero como LISTA de objetos en los errores de validación (422); renderizar
 * esa lista directamente rompe la pantalla, así que acá se reduce a un texto.
 */
export function mensajeDeError(err, respaldo) {
  const detalle = err?.response?.data?.detail;
  if (typeof detalle === "string" && detalle) return detalle;
  if (Array.isArray(detalle) && detalle.length > 0) {
    const campo = detalle[0]?.loc?.slice(-1)[0];
    return `Revisá los datos ingresados${campo ? ` (campo: ${campo})` : ""}.`;
  }
  return respaldo;
}
