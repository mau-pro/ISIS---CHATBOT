/**
 * utils/sesion.js
 * -----------------
 * Dónde se guarda la sesión (token + rol). Con "Recuérdame" va a localStorage
 * (sigue abierta al cerrar el navegador, hasta que venza el token); sin
 * "Recuérdame" va a sessionStorage (se pierde al cerrar la pestaña/navegador).
 * Lo comparten AuthContext (estado) y services/api.js (header Authorization).
 */

export const leerSesion = (clave) => {
  try {
    return localStorage.getItem(clave) ?? sessionStorage.getItem(clave);
  } catch {
    return null;
  }
};

export const guardarSesionEnAlmacen = (token, role, recordar = true) => {
  borrarSesionDelAlmacen();
  const almacen = recordar ? localStorage : sessionStorage;
  almacen.setItem("token", token);
  almacen.setItem("role", role);
};

export const borrarSesionDelAlmacen = () => {
  for (const almacen of [localStorage, sessionStorage]) {
    almacen.removeItem("token");
    almacen.removeItem("role");
  }
};
