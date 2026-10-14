/**
 * context/AuthContext.jsx
 * -------------------------
 * Guarda el estado de sesión (token + rol) en memoria y en el navegador
 * (ver utils/sesion.js), para que sobreviva a un refresh de página. Expone helpers de login/logout
 * y un flag isAdmin para proteger rutas del panel de administración.
 */

import { createContext, useContext, useState } from "react";
import { leerSesion, guardarSesionEnAlmacen, borrarSesionDelAlmacen } from "../utils/sesion.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(leerSesion("token"));
  const [role, setRole] = useState(leerSesion("role"));

  // recordar=false -> la sesión vive solo mientras la pestaña esté abierta
  const guardarSesion = (nuevoToken, nuevoRole, recordar = true) => {
    guardarSesionEnAlmacen(nuevoToken, nuevoRole, recordar);
    setToken(nuevoToken);
    setRole(nuevoRole);
  };

  const cerrarSesion = () => {
    borrarSesionDelAlmacen();
    setToken(null);
    setRole(null);
  };

  const value = {
    token,
    role,
    isAuthenticated: !!token,
    isAdmin: role === "admin",
    guardarSesion,
    cerrarSesion,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
