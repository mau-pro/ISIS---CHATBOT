import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { restablecerPassword } from "../services/api.js";
import { mensajeDeError } from "../utils/errores.js";
import AuthFoto from "../components/AuthFoto.jsx";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [verPassword, setVerPassword] = useState(false);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [listo, setListo] = useState(false);

  const manejarSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password.length < 6) {
      setError("La contraseña debe tener al menos 6 caracteres.");
      return;
    }
    if (password !== confirmacion) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setCargando(true);
    try {
      await restablecerPassword(token, password);
      setListo(true);
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo restablecer la contraseña."));
    } finally {
      setCargando(false);
    }
  };

  if (!token) {
    return (
      <AuthFoto icono="link_off" titulo="Enlace inválido">
        <p className="login-tarjeta__error">
          Este enlace no es válido. Pide uno nuevo desde la pantalla de inicio de sesión.
        </p>
        <Link to="/forgot-password" className="login-boton">
          Pedir un nuevo enlace
        </Link>
      </AuthFoto>
    );
  }

  if (listo) {
    return (
      <AuthFoto icono="task_alt" titulo="¡Listo!">
        <p className="login-exito">Tu contraseña se actualizó correctamente.</p>
        <Link to="/login" className="login-boton">
          Ir a iniciar sesión
        </Link>
      </AuthFoto>
    );
  }

  return (
    <AuthFoto icono="lock_reset" titulo="Elige tu nueva contraseña" subtitulo="Usa al menos 6 caracteres.">
      {error && <p className="login-tarjeta__error">{error}</p>}

      <form onSubmit={manejarSubmit}>
        <div className="login-campo">
          <span className="material-symbols-outlined">lock</span>
          <input
            type={verPassword ? "text" : "password"}
            placeholder="Nueva contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={6}
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

        <div className="login-campo">
          <span className="material-symbols-outlined">lock</span>
          <input
            type={verPassword ? "text" : "password"}
            placeholder="Confirmar contraseña"
            value={confirmacion}
            onChange={(e) => setConfirmacion(e.target.value)}
            autoComplete="new-password"
            required
            minLength={6}
          />
        </div>

        <button type="submit" className="login-boton" disabled={cargando}>
          {cargando ? "Guardando..." : "Restablecer contraseña"}
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </form>
    </AuthFoto>
  );
}
