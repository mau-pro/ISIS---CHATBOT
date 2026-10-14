/**
 * components/RutaProtegida.jsx
 * ------------------------------
 * Envuelve páginas que requieren sesión. Si soloAdmin=true, además exige
 * que el usuario tenga rol admin (usado para /admin).
 */

import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function RutaProtegida({ children, soloAdmin = false }) {
  const { isAuthenticated, isAdmin } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (soloAdmin && !isAdmin) {
    return <Navigate to="/chat" replace />;
  }

  return children;
}
