/**
 * components/AuthFoto.jsx
 * -------------------------
 * Plantilla de las pantallas de cuenta (crear cuenta, recuperar y restablecer
 * contraseña): foto del campus de fondo, marca UATF arriba a la izquierda, frase
 * abajo a la izquierda y una tarjeta oscura a la derecha con el formulario.
 * La foto es frontend/public/campus-uatf.webp.
 *
 * Props: icono (ícono de Material Symbols del círculo superior), titulo,
 * subtitulo (opcional) y children (el contenido de la tarjeta).
 */

import { Link } from "react-router-dom";
import { LOGO_UATF } from "./Logos.jsx";
import Footer from "./Footer.jsx";
import "../styles/auth-foto.css";

export default function AuthFoto({ icono = "person", titulo, subtitulo, children }) {
  return (
    <div className="auth-foto">
      <div className="auth-foto__fondo" />

      <header className="auth-foto__barra">
        <Link to="/" className="auth-foto__marca">
          <img src={LOGO_UATF} alt="Logo UATF" />
          <strong>UATF</strong>
          <span className="auth-foto__sep" />
          <span>I-SIS · Asistente Virtual</span>
        </Link>
      </header>

      <main className="auth-foto__centro">
        <div className="auth-foto__lema">
          <span>UATF</span>
          <blockquote>“La tecnología también es una herramienta para aprender”.</blockquote>
        </div>

        <section className="login-tarjeta auth-foto__tarjeta">
          <span className="login-tarjeta__avatar">
            <span className="material-symbols-outlined">{icono}</span>
          </span>
          <h1 className="login-tarjeta__titulo">{titulo}</h1>
          {subtitulo && <p className="login-tarjeta__sub">{subtitulo}</p>}
          {children}
        </section>
      </main>

      <Footer />
    </div>
  );
}
