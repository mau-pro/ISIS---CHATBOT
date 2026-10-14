/**
 * pages/Home.jsx
 * ----------------
 * Portada del sistema (rutas / y /login): barra superior, presentación con
 * accesos, mascota del asistente sobre el edificio de la universidad y la
 * tarjeta de inicio de sesión. Todo entra en una pantalla; los estilos están
 * en home.css (prefijo "inicio").
 */

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { LOGO_UATF } from "../components/Logos.jsx";
import LoginCard from "../components/LoginCard.jsx";
import RobotMascota from "../components/RobotMascota.jsx";
import EdificioFondo from "../components/EdificioFondo.jsx";
import "../styles/home.css";

const TARJETAS = [
  {
    color: "cian",
    icono: "forum",
    titulo: "Consultas académicas",
    texto: "Materias, planes, horarios y más.",
    login: true,
  },
  {
    color: "violeta",
    icono: "article",
    titulo: "Información institucional",
    texto: "Noticias, comunicados y trámites.",
    to: "/documentos/comunicados",
  },
  {
    color: "ambar",
    icono: "calendar_month",
    titulo: "Horarios y eventos",
    texto: "Mantente al día con fechas importantes.",
    to: "/documentos/horarios",
  },
  {
    color: "rosa",
    icono: "co_present",
    titulo: "Docentes",
    texto: "Lista de docentes y materias asignadas.",
    to: "/documentos/docentes",
  },
];

const VENTAJAS = [
  { icono: "school", titulo: "Para Estudiantes", texto: "Accede a información académica cuando la necesites." },
  { icono: "verified_user", titulo: "Seguro y confiable", texto: "Información oficial de la UATF." },
  { icono: "schedule", titulo: "Disponible 24/7", texto: "Consulta en cualquier momento." },
];

function enfocarLogin() {
  const campo = document.getElementById("login-usuario");
  campo?.scrollIntoView({ behavior: "smooth", block: "center" });
  campo?.focus({ preventScroll: true });
}

export default function Home() {
  const [ayudaAbierta, setAyudaAbierta] = useState(false);

  // La ayuda se cierra con Escape
  useEffect(() => {
    if (!ayudaAbierta) return;
    const alTeclear = (e) => e.key === "Escape" && setAyudaAbierta(false);
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [ayudaAbierta]);

  return (
    <div className="inicio">
      <div className="inicio__fondo">
        <EdificioFondo />
      </div>

      <header className="inicio__barra">
        <div className="inicio__marca">
          <img src={LOGO_UATF} alt="Logo UATF" className="inicio__sello" />
          <div className="inicio__marca-texto">
            <strong>UATF</strong>
            <small>Universidad Autónoma Tomás Frías</small>
          </div>
          <span className="inicio__separador" />
          <span className="material-symbols-outlined inicio__marca-icono">psychology</span>
          <div className="inicio__marca-texto inicio__marca-texto--asistente">
            <strong>I-SIS</strong>
            <small>Asistente Virtual · Ing. de Sistemas</small>
          </div>
        </div>

        <nav className="inicio__nav">
          <Link to="/" className="inicio__nav-item inicio__nav-item--activo">
            <span className="material-symbols-outlined">home</span>
            Inicio
          </Link>
          <div className="inicio__ayuda-wrap">
            <button type="button" className="inicio__nav-item" onClick={() => setAyudaAbierta((v) => !v)}>
              <span className="material-symbols-outlined">help</span>
              Ayuda
            </button>
            {ayudaAbierta && (
              <div className="inicio__ayuda" role="dialog" aria-label="Ayuda">
                <button type="button" className="inicio__ayuda-cerrar" onClick={() => setAyudaAbierta(false)} title="Cerrar">
                  <span className="material-symbols-outlined">close</span>
                </button>
                <h3>¿Necesitás ayuda?</h3>
                <ul>
                  <li>Ingresá con tu <b>nombre de usuario</b> (no con el correo).</li>
                  <li>
                    ¿Olvidaste tu contraseña? <Link to="/forgot-password">Recupérala acá</Link>.
                  </li>
                  <li>
                    ¿Todavía no tienes cuenta? <Link to="/register">Regístrate gratis</Link>.
                  </li>
                  <li>Para otras consultas, comunicate con la administración de la carrera de Ingeniería de Sistemas.</li>
                </ul>
              </div>
            )}
          </div>
          <button type="button" className="inicio__btn-login" onClick={enfocarLogin}>
            <span className="material-symbols-outlined">person</span>
            Iniciar sesión
          </button>
        </nav>
      </header>

      <main className="inicio__main">
        <section className="inicio__hero">
          <div className="inicio__badge">
            <span className="inicio__badge-punto" />
            Sistema online activo
          </div>
          <h1 className="inicio__titulo">
            Conoce a I-SIS, tu asistente virtual en <span>Ingeniería de Sistemas</span>
          </h1>
          <p className="inicio__texto">
            Resuelve tus dudas, consulta información académica y accede a recursos de manera rápida y sencilla.
          </p>

          <div className="inicio__tarjetas">
            {TARJETAS.map((t) => {
              const contenido = (
                <>
                  <span className={`inicio__tarjeta-icono inicio__tarjeta-icono--${t.color}`}>
                    <span className="material-symbols-outlined">{t.icono}</span>
                  </span>
                  <h3>{t.titulo}</h3>
                  <p>{t.texto}</p>
                  <span className={`inicio__tarjeta-flecha inicio__tarjeta-flecha--${t.color}`}>
                    <span className="material-symbols-outlined">arrow_forward</span>
                  </span>
                </>
              );
              const clase = `inicio__tarjeta inicio__tarjeta--${t.color}`;
              if (t.to) {
                return (
                  <Link key={t.titulo} to={t.to} className={clase}>
                    {contenido}
                  </Link>
                );
              }
              return (
                <button
                  key={t.titulo}
                  type="button"
                  className={clase}
                  onClick={enfocarLogin}
                >
                  {contenido}
                </button>
              );
            })}
          </div>

          <div className="inicio__ventajas">
            {VENTAJAS.map((v) => (
              <div key={v.titulo} className="inicio__ventaja">
                <span className="material-symbols-outlined">{v.icono}</span>
                <div>
                  <strong>{v.titulo}</strong>
                  <p>{v.texto}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="inicio__mascota">
          <div className="inicio__mascota-caja">
          <div className="inicio__burbuja">
            <span className="material-symbols-outlined">chat</span>
            <div>
              <strong>¡Hola!</strong>
              <p>
                Soy <b>I-SIS</b>, tu asistente virtual de la UATF. ¿En qué puedo ayudarte hoy?
              </p>
            </div>
          </div>
          <RobotMascota />
          </div>
        </section>

        <aside className="inicio__login">
          <LoginCard />
        </aside>
      </main>

      <footer className="inicio__pie">
        <div>
          <strong>Universidad Autónoma Tomás Frías</strong>
          <span className="inicio__pie-sep" />
          <span>Ingeniería de Sistemas</span>
        </div>
        <div className="inicio__pie-lugar">
          <span className="material-symbols-outlined">location_on</span>
          Potosí - Bolivia
        </div>
        <div>© {new Date().getFullYear()} UATF. Todos los derechos reservados.</div>
      </footer>
    </div>
  );
}
