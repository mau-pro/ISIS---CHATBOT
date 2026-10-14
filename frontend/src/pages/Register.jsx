import { useState } from "react";
import { Link } from "react-router-dom";
import { register as registerRequest } from "../services/api.js";
import { mensajeDeError } from "../utils/errores.js";
import AuthFoto from "../components/AuthFoto.jsx";

export default function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [verPassword, setVerPassword] = useState(false);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [registrado, setRegistrado] = useState(false);

  const manejarSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setCargando(true);
    try {
      await registerRequest(username.trim(), email, password);
      setRegistrado(true);
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo crear la cuenta. Intenta de nuevo."));
    } finally {
      setCargando(false);
    }
  };

  if (registrado) {
    return (
      <AuthFoto icono="mark_email_read" titulo="Ya casi">
        <p className="login-exito">
          Te enviamos un correo a <strong>{email}</strong> con un enlace para activar tu cuenta. Revisa tu bandeja de
          entrada (y spam) antes de iniciar sesión.
        </p>
        <Link to="/login" className="login-boton">
          Ir a iniciar sesión
        </Link>
      </AuthFoto>
    );
  }

  return (
    <AuthFoto icono="person_add" titulo="Crea tu cuenta" subtitulo="Regístrate para hacer consultas ilimitadas.">
      {error && <p className="login-tarjeta__error">{error}</p>}

      <form onSubmit={manejarSubmit}>
        <div className="login-campo">
          <span className="material-symbols-outlined">person</span>
          <input
            type="text"
            placeholder="Nombre de usuario"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            minLength={3}
            maxLength={30}
            title="De 3 a 30 caracteres: letras, números, punto, guion y guion bajo"
          />
        </div>
        <small className="login-ayuda">Con este nombre vas a iniciar sesión (no con el correo).</small>

        <div className="login-campo">
          <span className="material-symbols-outlined">mail</span>
          <input
            type="email"
            placeholder="Correo electrónico"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </div>

        <div className="login-campo">
          <span className="material-symbols-outlined">lock</span>
          <input
            type={verPassword ? "text" : "password"}
            placeholder="Contraseña (mínimo 6 caracteres)"
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

        <button type="submit" className="login-boton" disabled={cargando}>
          {cargando ? "Creando cuenta..." : "Registrarme"}
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </form>

      <p className="login-tarjeta__pie">
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
      <Link to="/" className="login-boton login-boton--secundario">
        Volver al inicio
      </Link>
    </AuthFoto>
  );
}
