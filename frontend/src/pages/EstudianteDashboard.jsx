import { useState, useEffect } from "react";
import { obtenerHistorial, eliminarHistorial } from "../services/api.js";
import Sidebar from "../components/Sidebar.jsx";
import ChatWidget from "../components/ChatWidget.jsx";
import Footer from "../components/Footer.jsx";
import Paginacion from "../components/Paginacion.jsx";
import RespuestaFormateada from "../components/RespuestaFormateada.jsx";
import BotonCerrarSesion from "../components/BotonCerrarSesion.jsx";
import "../styles/app.css";
import "../styles/rediseno.css";

const SECCIONES = [
  { id: "inicio", etiqueta: "Inicio", icono: "home" },
  { id: "historial", etiqueta: "Historial de Consultas", icono: "history" },
];

const TITULOS = {
  inicio: { titulo: "Inicio", subtitulo: "Pregunta sobre horarios, docentes, trámites o avisos académicos." },
  historial: { titulo: "Historial de Consultas", subtitulo: "Tus últimas preguntas y respuestas." },
};

function formatearFecha(iso) {
  return new Date(iso).toLocaleString("es-BO", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SeccionInicio() {
  return (
    <>
      <ChatWidget
        mensajeBienvenida="¡Hola! Soy I-SIS, el asistente virtual de Ingeniería de Sistemas UATF. ¿En qué puedo ayudarte hoy? Podés preguntarme sobre trámites, horarios, docentes o fechas importantes."
        placeholder="Escribe tu consulta aquí... Ej: ¿Cuándo son las convocatorias de becas?"
      />
      <p className="panel__chat-disclaimer">
        El asistente puede cometer errores. Verifica la información importante con Kárdex.
      </p>
    </>
  );
}

const TAMANO_HISTORIAL = 6;

function SeccionHistorial() {
  const [datos, setDatos] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [borrando, setBorrando] = useState(false);

  useEffect(() => {
    obtenerHistorial(pagina, TAMANO_HISTORIAL).then(({ data }) => setDatos(data));
  }, [pagina]);

  const manejarEliminarHistorial = async () => {
    const confirmar = window.confirm(
      "¿Eliminar todo tu historial de consultas? Esta acción no se puede deshacer."
    );
    if (!confirmar) return;

    setBorrando(true);
    try {
      await eliminarHistorial();
      setPagina(1);
      setDatos({ items: [], total: 0, page: 1, page_size: TAMANO_HISTORIAL });
    } finally {
      setBorrando(false);
    }
  };

  return (
    <>
      {datos === null && <p className="panel__estado-vacio">Cargando…</p>}

      {datos?.total === 0 && (
        <p className="panel__estado-vacio">Todavía no hiciste ninguna pregunta.</p>
      )}

      {datos?.total > 0 && (
        <button className="panel__boton-peligro" onClick={manejarEliminarHistorial} disabled={borrando}>
          <span className="material-symbols-outlined">delete</span>
          {borrando ? "Eliminando..." : "Eliminar historial"}
        </button>
      )}

      <div className="panel__historial">
        {datos?.items.map((item) => (
          <div key={item.id} className="panel__historial-item">
            <p className="panel__historial-fecha">{formatearFecha(item.created_at)}</p>
            <p className="panel__historial-pregunta">{item.pregunta}</p>
            <RespuestaFormateada texto={item.respuesta} />
          </div>
        ))}
      </div>

      {datos && (
        <Paginacion pagina={pagina} tamano={TAMANO_HISTORIAL} total={datos.total} onCambiar={setPagina} />
      )}
    </>
  );
}

export default function EstudianteDashboard() {
  const [seccion, setSeccion] = useState("inicio");
  const { titulo, subtitulo } = TITULOS[seccion];

  return (
    <div className="panel">
      <Sidebar
        titulo="Panel del Estudiante"
        subtitulo="Ingeniería de Sistemas"
        variante="estudiante"
        secciones={SECCIONES}
        seccionActiva={seccion}
        onCambiarSeccion={setSeccion}
      />
      <main className="panel__main">
        <div className="panel__topbar">
          <div>
            <h1 className="panel__topbar-titulo">{titulo}</h1>
            <p className="panel__topbar-subtitulo">{subtitulo}</p>
          </div>
          <div className="panel__topbar-iconos">
            <button className="panel__topbar-icono">
              <span className="material-symbols-outlined">notifications</span>
            </button>
            <BotonCerrarSesion className="panel__topbar-icono" title="Cerrar sesión">
              <span className="material-symbols-outlined">logout</span>
            </BotonCerrarSesion>
          </div>
        </div>

        <div className="panel__contenido">
          {seccion === "inicio" && <SeccionInicio />}
          {seccion === "historial" && <SeccionHistorial />}
        </div>

        <Footer />
      </main>
    </div>
  );
}