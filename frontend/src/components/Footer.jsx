/**
 * components/Footer.jsx
 * ------------------------
 * Footer institucional compartido por TODAS las páginas (inicio, login,
 * registro, chat, panel admin, recuperar contraseña, etc.). Usa clases
 * "site-footer__*" definidas en index.css (el único CSS que se carga en
 * todas las páginas), para que se vea igual sin importar qué otra hoja de
 * estilos tenga cargada la página.
 */

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div>
          <p className="site-footer__marca">Ingeniería de Sistemas UATF</p>
          <p className="site-footer__texto">
            Universidad Autónoma Tomás Frías.
            <br />
            Av. Las Banderas, Edif. Bloque 3 s/n. Potosí, Bolivia.
          </p>
        </div>

        <p className="site-footer__copy">
          © {new Date().getFullYear()} Carrera de Ingeniería de Sistemas - UATF.
        </p>
      </div>
    </footer>
  );
}
