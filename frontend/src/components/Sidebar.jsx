/**
 * components/Sidebar.jsx
 * -------------------------
 * Barra lateral de navegación para los dashboards. Recibe la lista de
 * secciones (id, etiqueta, icono) y cuál está activa; el dashboard que lo
 * usa controla qué contenido se muestra según la sección seleccionada.
 */

import Logos from "./Logos.jsx";
import BotonCerrarSesion from "./BotonCerrarSesion.jsx";

export default function Sidebar({
  titulo,
  subtitulo,
  variante = "admin", // "admin" (subtítulo dorado) | "estudiante" (subtítulo gris)
  secciones,
  seccionActiva,
  onCambiarSeccion,
}) {
  return (
    <aside className="panel__sidebar">
      <div className="panel__sidebar-marca">
        <Logos tamano="sm" />
        <div>
          <div className="panel__sidebar-titulo">{titulo}</div>
          {subtitulo && (
            <span
              className={`panel__sidebar-subtitulo panel__sidebar-subtitulo--${variante}`}
            >
              {subtitulo}
            </span>
          )}
        </div>
      </div>

      <nav className="panel__nav">
        {secciones.map((seccion) => (
          <button
            key={seccion.id}
            className={`panel__nav-item ${
              seccionActiva === seccion.id ? "panel__nav-item--activo" : ""
            }`}
            onClick={() => onCambiarSeccion(seccion.id)}
          >
            <span className="material-symbols-outlined">{seccion.icono}</span>
            {seccion.etiqueta}
          </button>
        ))}

        <div className="panel__sidebar-pie">
          <BotonCerrarSesion className="panel__nav-item">
            <span className="material-symbols-outlined">logout</span>
            Cerrar sesión
          </BotonCerrarSesion>
        </div>
      </nav>
    </aside>
  );
}