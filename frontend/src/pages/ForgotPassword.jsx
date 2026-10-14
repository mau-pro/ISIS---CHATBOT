import { useState } from "react";
import { Link } from "react-router-dom";
import { solicitarRecuperacion } from "../services/api.js";
import { mensajeDeError } from "../utils/errores.js";
import AuthFoto from "../components/AuthFoto.jsx";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  const manejarSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setCargando(true);
    try {
      await solicitarRecuperacion(email);
      setEnviado(true);
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo procesar la solicitud. Intenta de nuevo."));
    } finally {
      setCargando(false);
    }
  };

  if (enviado) {
    return (
      <AuthFoto icono="mark_email_read" titulo="Revisá tu correo">
        <p className="login-exito">
          Si <strong>{email}</strong> tiene una cuenta registrada, te enviamos un enlace para restablecer la
          contraseña. Revisá tu bandeja de entrada (y spam); el enlace vence en 30 minutos.
        </p>
        <Link to="/login" className="login-boton">
          Volver a iniciar sesión
        </Link>
      </AuthFoto>
    );
  }

  return (
    <AuthFoto
      icono="lock_reset"
      titulo="¿Olvidaste tu contraseña?"
      subtitulo="Escribe tu correo y te mandamos un enlace para restablecerla."
    >
      {error && <p className="login-tarjeta__error">{error}</p>}

      <form onSubmit={manejarSubmit}>
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

        <button type="submit" className="login-boton" disabled={cargando}>
          {cargando ? "Enviando..." : "Enviar enlace"}
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </form>

      <p className="login-tarjeta__pie">
        ¿Ya la recordaste? <Link to="/login">Inicia sesión</Link>
      </p>
      <Link to="/" className="login-boton login-boton--secundario">
        Volver al inicio
      </Link>
    </AuthFoto>
  );
}
