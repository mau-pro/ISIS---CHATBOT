/**
 * components/LoginCard.jsx
 * --------------------------
 * Tarjeta de inicio de sesión integrada en la portada (/ y /login).
 * - Un solo formulario para todos: el backend devuelve el rol de la cuenta y de ahí se
 *   decide el destino (admin -> /admin, estudiante -> /chat).
 * - Se inicia sesión con NOMBRE DE USUARIO (no con el correo).
 * - "Recuérdame": si está apagado, la sesión se guarda solo en sessionStorage.
 */

import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { login as loginRequest } from "../services/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { mensajeDeError } from "../utils/errores.js";
import Logos from "./Logos.jsx";

export default function LoginCard() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [verPassword, setVerPassword] = useState(false);
  const [recordar, setRecordar] = useState(true);
  // Si se llegó por una sesión vencida (ver services/api.js) se avisa desde el principio
  const [params] = useSearchParams();
  const [error, setError] = useState(
    params.get("expirada") ? "Tu sesión venció (dura 1 hora). Inicia sesión de nuevo para seguir consultando." : ""
  );
  const [cargando, setCargando] = useState(false);
  const { guardarSesion } = useAuth();
  const navigate = useNavigate();

  const manejarSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setCargando(true);
    try {
      const { data } = await loginRequest(username.trim(), password);
      // El servidor dice qué rol tiene la cuenta: los administradores van al panel
      // de administración y los estudiantes al chat, sin tener que elegirlo acá.
      guardarSesion(data.access_token, data.role, recordar);
      navigate(data.role === "admin" ? "/admin" : "/chat");
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo iniciar sesión. Intenta de nuevo."));
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="login-tarjeta" id="login">
      <Logos tamano="md" />
      <h2 className="login-tarjeta__titulo">
        Iniciar <span>sesión</span>
      </h2>
      <p className="login-tarjeta__sub">
        Accede a I-SIS, el asistente virtual de Ingeniería de Sistemas UATF.
      </p>

      {error && <p className="login-tarjeta__error">{error}</p>}

      <form onSubmit={manejarSubmit}>
        <div className="login-campo">
          <span className="material-symbols-outlined">person</span>
          <input
            id="login-usuario"
            type="text"
            placeholder="Nombre de usuario"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
          />
        </div>

        <div className="login-campo">
          <span className="material-symbols-outlined">lock</span>
          <input
            type={verPassword ? "text" : "password"}
            placeholder="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <button
            type="button"
            className="login-campo__ojo"
            onClick={() => setVerPassword((v) => !v)}
            title={verPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
          >
            <span className="material-symbols-outlined">{verPassword ? "visibility" : "visibility_off"}</span>
          </button>
        </div>

        <div className="login-fila">
          <label className="login-recordar">
            <input type="checkbox" checked={recordar} onChange={(e) => setRecordar(e.target.checked)} />
            Recuérdame
          </label>
          <Link to="/forgot-password">¿Olvidaste tu contraseña?</Link>
        </div>

        <button type="submit" className="login-boton" disabled={cargando}>
          {cargando ? "Ingresando..." : "Ingresar"}
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </form>

      <p className="login-tarjeta__pie">
        ¿No tienes una cuenta? <Link to="/register">Regístrate gratis</Link>
      </p>
    </div>
  );
}
