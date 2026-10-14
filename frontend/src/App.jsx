import { Routes, Route } from "react-router-dom";

import Home from "./pages/Home.jsx";
import Register from "./pages/Register.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import DocumentosSeccion from "./pages/DocumentosSeccion.jsx";
import EstudianteDashboard from "./pages/EstudianteDashboard.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import RutaProtegida from "./components/RutaProtegida.jsx";

export default function App() {
  return (
    <Routes>
      {/* Página de inicio: presenta el sistema y lleva al login */}
      <Route path="/" element={<Home />} />

      {/* El login vive en la portada (tarjeta de inicio de sesión) */}
      <Route path="/login" element={<Home />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Secciones públicas de documentos (comunicados, horarios, docentes) */}
      <Route path="/documentos/:seccion" element={<DocumentosSeccion />} />

      {/* Dashboard del estudiante: Inicio (chat) + Historial */}
      <Route
        path="/chat"
        element={
          <RutaProtegida>
            <EstudianteDashboard />
          </RutaProtegida>
        }
      />

      {/* Dashboard del administrador: Documentos, Estadísticas, Roles */}
      <Route
        path="/admin"
        element={
          <RutaProtegida soloAdmin>
            <AdminDashboard />
          </RutaProtegida>
        }
      />
    </Routes>
  );
}
