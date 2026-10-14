/**
 * components/BotonCerrarSesion.jsx
 * -----------------------------------
 * Botón de "Cerrar sesión" con confirmación, reutilizado en la barra
 * lateral y en la topbar de los dashboards (y en Membrete.jsx para la
 * versión pública). Centraliza la lógica para no repetir el window.confirm
 * en cada lugar donde aparece el botón.
 */

import { useAuth } from "../context/AuthContext.jsx";

export default function BotonCerrarSesion({ className, title, children }) {
  const { cerrarSesion } = useAuth();

  const manejarClick = () => {
    if (window.confirm("¿Seguro que querés cerrar sesión?")) {
      cerrarSesion();
    }
  };

  return (
    <button className={className} onClick={manejarClick} title={title}>
      {children}
    </button>
  );
}
