/**
 * components/ChatWidget.jsx
 * ----------------------------
 * Chat reutilizable: lo usan tanto el dashboard del estudiante (Inicio)
 * como el panel "Probar Chatbot" del administrador. Cada intercambio
 * (pregunta + respuesta) guarda el id que devuelve el backend, para poder
 * editar la pregunta y reenviarla: el backend reemplaza ese mismo registro
 * en vez de crear una consulta nueva, así una corrección no cuenta como
 * dos preguntas en el historial ni en las estadísticas.
 */

import { useState, useRef, useEffect } from "react";
import { enviarPregunta } from "../services/api.js";
import RespuestaFormateada from "./RespuestaFormateada.jsx";
import RobotAvatar from "./RobotAvatar.jsx";
import RobotMascota from "./RobotMascota.jsx";

const SUGERENCIAS = [
  "¿Qué materias hay en primer semestre?",
  "¿Cuáles son las materias optativas?",
  "¿Qué materias dicta el docente Wilfredo Terrazas?",
  "¿Cuándo son las convocatorias vigentes?",
];

export default function ChatWidget({
  mensajeBienvenida,
  placeholder = "Escribe tu consulta aquí...",
  permitirEditar = true,
}) {
  const [intercambios, setIntercambios] = useState([]);
  const [pregunta, setPregunta] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [editandoIndex, setEditandoIndex] = useState(null);
  const listaRef = useRef(null);

  // La conversación se desplaza sola hasta el último mensaje
  useEffect(() => {
    if (intercambios.length === 0) return; // sin mensajes se ve el saludo completo desde arriba
    listaRef.current?.scrollTo({ top: listaRef.current.scrollHeight, behavior: "smooth" });
  }, [intercambios]);

  const manejarEnvio = async (e, textoDirecto) => {
    e?.preventDefault();
    const textoAEnviar = textoDirecto ?? pregunta;
    if (!textoAEnviar.trim() || cargando) return;

    setError("");
    setCargando(true);
    const preguntaActual = textoAEnviar;
    const indiceEditado = editandoIndex;
    const original = indiceEditado !== null ? intercambios[indiceEditado] : null;
    const indiceActual = indiceEditado !== null ? indiceEditado : intercambios.length;
    setPregunta("");
    setEditandoIndex(null);

    // Se muestra la pregunta de inmediato, con la respuesta en "cargando"
    // (respuesta: null), en vez de esperar a tener la respuesta completa
    // para recién ahí mostrar el intercambio entero.
    setIntercambios((prev) => {
      const pendiente = { id: original?.id ?? null, pregunta: preguntaActual, respuesta: null };
      if (indiceEditado !== null) {
        const copia = [...prev];
        copia[indiceEditado] = pendiente;
        return copia;
      }
      return [...prev, pendiente];
    });

    try {
      const idAEditar = original?.id;
      // Solo se manda "intercambio anterior" para preguntas nuevas de
      // seguimiento, no al editar (ahí no aplica el mismo sentido).
      const anterior = indiceEditado === null && intercambios.length > 0
        ? intercambios[intercambios.length - 1]
        : null;
      const { data } = await enviarPregunta(
        preguntaActual,
        idAEditar,
        anterior?.pregunta,
        anterior?.respuesta
      );

      setIntercambios((prev) => {
        const copia = [...prev];
        copia[indiceActual] = { id: data.id, pregunta: preguntaActual, respuesta: data.respuesta, desdeCache: data.desde_cache };
        return copia;
      });
    } catch (err) {
      if (err.response?.status === 429 || err.response?.status === 503) {
        setError(err.response.data.detail || "Alcanzaste tu límite de consultas por hora.");
      } else if (!err.response) {
        setError("No se pudo conectar con el servidor. Verifica que esté encendido e intenta de nuevo.");
      } else {
        setError("Ocurrió un error al consultar. Intenta de nuevo.");
      }
      // Si falló, se revierte: una edición vuelve a su respuesta anterior,
      // una pregunta nueva se quita (no queda una burbuja sin respuesta).
      setIntercambios((prev) => {
        if (original) {
          const copia = [...prev];
          copia[indiceActual] = original;
          return copia;
        }
        return prev.filter((_, i) => i !== indiceActual);
      });
    } finally {
      setCargando(false);
    }
  };

  const manejarEditar = (index) => {
    setPregunta(intercambios[index].pregunta);
    setEditandoIndex(index);
  };

  const cancelarEdicion = () => {
    setPregunta("");
    setEditandoIndex(null);
  };

  return (
    <div className="chat-caja">
      <div className="panel__chat" ref={listaRef}>
        {intercambios.length === 0 ? (
          <div className="chat-bienvenida">
            <RobotMascota />
            {mensajeBienvenida && <p className="chat-bienvenida__burbuja">{mensajeBienvenida}</p>}
          </div>
        ) : (
          mensajeBienvenida && (
            <div className="panel__msg panel__msg--asistente">
              <RobotAvatar />
              <div className="panel__msg-col">
                <span className="panel__msg-nombre">I-SIS</span>
                <div className="panel__msg-burbuja">{mensajeBienvenida}</div>
              </div>
            </div>
          )
        )}

        {intercambios.map((item, i) => (
          <div key={item.id ?? i} className="chat-par">
            <div className="panel__msg panel__msg--usuario">
              <div className="panel__msg-avatar panel__msg-avatar--usuario">
                <span className="material-symbols-outlined">person</span>
              </div>
              <div className="panel__msg-col">
                <span className="panel__msg-nombre">Tú</span>
                <div className="panel__msg-burbuja">{item.pregunta}</div>
              </div>
              {permitirEditar && item.respuesta !== null && (
                <button
                  type="button"
                  className="panel__msg-editar"
                  onClick={() => manejarEditar(i)}
                  disabled={cargando}
                  title="Editar esta pregunta"
                >
                  <span className="material-symbols-outlined">edit</span>
                </button>
              )}
            </div>
            <div className="panel__msg panel__msg--asistente">
              <RobotAvatar pensando={item.respuesta === null} />
              <div className="panel__msg-col">
                <span className="panel__msg-nombre">I-SIS</span>
                {item.respuesta === null ? (
                  <div className="panel__msg-burbuja panel__msg-burbuja--cargando">
                    <span className="panel__msg-punto" />
                    <span className="panel__msg-punto" />
                    <span className="panel__msg-punto" />
                  </div>
                ) : (
                  <div className="panel__msg-burbuja panel__msg-burbuja--respuesta">
                    <RespuestaFormateada texto={item.respuesta} />
                    {item.desdeCache && (
                      <span className="respuesta__rapida" title="Respondida desde la memoria del sistema, sin gastar tokens de la IA">
                        <span className="material-symbols-outlined">bolt</span>
                        Respuesta instantánea
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="chat-caja__pie">
        {intercambios.length === 0 && (
          <div className="panel__sugerencias">
            {SUGERENCIAS.map((s) => (
              <button key={s} type="button" className="panel__sugerencia" onClick={() => manejarEnvio(null, s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        {error && <p className="panel__aviso-error">{error}</p>}

        {editandoIndex !== null && (
          <p className="panel__chat-editando">
            Editando tu pregunta anterior —
            <button type="button" onClick={cancelarEdicion}>cancelar</button>
          </p>
        )}

        <form onSubmit={manejarEnvio} className="panel__chat-input-row">
          <span className="material-symbols-outlined">{editandoIndex !== null ? "edit" : "chat"}</span>
          <input
            type="text"
            value={pregunta}
            onChange={(e) => setPregunta(e.target.value)}
            placeholder={placeholder}
            className="panel__chat-input"
          />
          <button type="submit" className="panel__chat-enviar" disabled={cargando}>
            {cargando ? "..." : editandoIndex !== null ? "Reenviar" : "Enviar"}
            <span className="material-symbols-outlined">send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
