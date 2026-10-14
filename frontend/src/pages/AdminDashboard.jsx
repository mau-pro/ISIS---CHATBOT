import { mensajeDeError } from "../utils/errores.js";
import { useState, useEffect, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  listarDocumentos,
  subirDocumento,
  eliminarDocumento,
  obtenerEstadisticas,
  listarUsuarios,
  cambiarRolUsuario,
  eliminarUsuario,
  listarPreguntasAprendidas,
  olvidarPregunta,
  olvidarTodas,
  urlDescargaDocumento,
} from "../services/api.js";
import { infoIconoArchivo, formatearTamano } from "../utils/archivos.js";
import { CATEGORIAS, infoCategoria } from "../utils/categorias.js";
import Sidebar from "../components/Sidebar.jsx";
import ChatWidget from "../components/ChatWidget.jsx";
import Footer from "../components/Footer.jsx";
import Paginacion from "../components/Paginacion.jsx";
import BotonCerrarSesion from "../components/BotonCerrarSesion.jsx";
import "../styles/app.css";
import "../styles/rediseno.css";
import "../styles/documentos.css";
import "../styles/admin.css";

const SECCIONES = [
  { id: "documentos", etiqueta: "Documentos", icono: "description" },
  { id: "chatbot", etiqueta: "Probar Chatbot", icono: "forum" },
  { id: "estadisticas", etiqueta: "Estadísticas", icono: "monitoring" },
  { id: "roles", etiqueta: "Roles y permisos", icono: "admin_panel_settings" },
];

function formatearFecha(iso) {
  return new Date(iso).toLocaleDateString("es-BO", { day: "2-digit", month: "short", year: "numeric" });
}

/* ---------- Sección: Documentos ---------- */

const TAMANO_DOCS = 6;

function SeccionDocumentos() {
  // Los documentos se piden al servidor de a una página (TAMANO_DOCS por vez), no todos juntos
  const [datosDocs, setDatosDocs] = useState({ items: [], total: 0 });
  const [cargandoDocs, setCargandoDocs] = useState(true);
  const [categoria, setCategoria] = useState("otro");
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState("");
  const [busquedaDocs, setBusquedaDocs] = useState("");
  const [consultaDocs, setConsultaDocs] = useState("");
  const [paginaDocs, setPaginaDocs] = useState(1);

  const visibles = datosDocs.items;

  // La búsqueda espera 350 ms después de la última tecla antes de consultar al servidor
  useEffect(() => {
    const t = setTimeout(() => {
      setConsultaDocs(busquedaDocs.trim());
      setPaginaDocs(1);
    }, 350);
    return () => clearTimeout(t);
  }, [busquedaDocs]);

  const cargarDocumentos = async (pagina = paginaDocs) => {
    const { data } = await listarDocumentos(pagina, TAMANO_DOCS, consultaDocs);
    // Si se borró el último de la última página, se retrocede a la anterior
    const ultima = Math.max(1, Math.ceil(data.total / TAMANO_DOCS));
    if (pagina > ultima) {
      setPaginaDocs(ultima);
      return;
    }
    setDatosDocs(data);
    setCargandoDocs(false);
  };

  useEffect(() => {
    cargarDocumentos();
  }, [paginaDocs, consultaDocs]);

  const onDrop = useCallback(
    async (archivosAceptados) => {
      setError("");
      setSubiendo(true);
      try {
        for (const archivo of archivosAceptados) {
          await subirDocumento(archivo, categoria);
        }
        // Lo último subido aparece primero: se vuelve a la página 1
        setPaginaDocs(1);
        await cargarDocumentos(1);
      } catch (err) {
        setError(mensajeDeError(err, "Error al subir el archivo."));
      } finally {
        setSubiendo(false);
      }
    },
    [categoria]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/webp": [".webp"],
      "image/bmp": [".bmp"],
      "image/tiff": [".tiff"],
    },
  });

  const manejarEliminar = async (id) => {
    await eliminarDocumento(id);
    await cargarDocumentos();
  };

  return (
    <>
      <div className="panel__card">
        <div className="panel__selector">
          <label id="categoria-label">Categoría del documento a subir</label>
          <div className="cat-selector" role="radiogroup" aria-labelledby="categoria-label">
            {CATEGORIAS.map((c) => (
              <button
                key={c.value}
                type="button"
                role="radio"
                aria-checked={categoria === c.value}
                className={`cat-opcion cat-${c.value} ${categoria === c.value ? "cat-opcion--activa" : ""}`}
                onClick={() => setCategoria(c.value)}
              >
                <span className="cat-opcion__icono">
                  <span className="material-symbols-outlined">{c.icono}</span>
                </span>
                <span className="cat-opcion__texto">
                  <strong>{c.label}</strong>
                  <small>{c.ayuda}</small>
                </span>
                {categoria === c.value && (
                  <span className="material-symbols-outlined cat-opcion__check">check_circle</span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div
          {...getRootProps()}
          className={`panel__dropzone ${isDragActive ? "panel__dropzone--activa" : ""}`}
        >
          <input {...getInputProps()} />
          <span className="material-symbols-outlined">cloud_upload</span>
          {subiendo ? (
            <p className="panel__dropzone-titulo">Subiendo y procesando…</p>
          ) : (
            <>
              <p className="panel__dropzone-titulo">Arrastrá archivos acá</p>
              <p>PDF, Word, Excel o Imagen — o hacé clic para elegirlos</p>
            </>
          )}
        </div>
      </div>

      {error && <p className="panel__aviso-error">{error}</p>}

      <div className="panel__buscador">
        <span className="material-symbols-outlined">search</span>
        <input
          type="text"
          placeholder="Buscar documento por nombre…"
          value={busquedaDocs}
          onChange={(e) => {
            setBusquedaDocs(e.target.value);
            setPaginaDocs(1);
          }}
        />
      </div>

      <div className="docs-tabla-card">
        <table className="docs-tabla">
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Tipo</th>
              <th>Categoría</th>
              <th>Tamaño</th>
              <th>Fragmentos</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((doc) => {
              const { icono, clase, claseTipo } = infoIconoArchivo(doc.original_type);
              const cat = infoCategoria(doc.category);
              return (
                <tr key={doc.id}>
                  <td>
                    <div className="docs-archivo">
                      <div className={`docs-archivo__icono ${clase}`}>
                        <span className="material-symbols-outlined">{icono}</span>
                      </div>
                      <span className="docs-archivo__nombre">{doc.filename}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`docs-tipo-badge ${claseTipo}`}>{doc.original_type.toUpperCase()}</span>
                  </td>
                  <td>
                    <span className={`cat-badge cat-${cat.value}`}>
                      <span className="material-symbols-outlined">{cat.icono}</span>
                      {cat.label}
                    </span>
                  </td>
                  <td>{formatearTamano(doc.size_bytes) || "—"}</td>
                  <td>{doc.chunk_count}</td>
                  <td>
                    <div className="panel__acciones-fila">
                      {doc.size_bytes != null && (
                        <a
                          href={urlDescargaDocumento(doc.id)}
                          className="panel__boton-rol"
                          title="Descargar archivo original"
                        >
                          <span className="material-symbols-outlined">download</span>
                          Descargar
                        </a>
                      )}
                      <button
                        className="panel__boton-icono-eliminar"
                        onClick={() => manejarEliminar(doc.id)}
                        title="Eliminar documento"
                      >
                        <span className="material-symbols-outlined">delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {!cargandoDocs && datosDocs.total === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--panel-ink-soft)" }}>
                  {consultaDocs ? "Ningún documento coincide con la búsqueda." : "Todavía no subiste ningún documento."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <Paginacion pagina={paginaDocs} tamano={TAMANO_DOCS} total={datosDocs.total} onCambiar={setPaginaDocs} />
      </div>
    </>
  );
}

/* ---------- Sección: Probar Chatbot ---------- */

function SeccionProbarChatbot() {
  return (
    <>
      <ChatWidget
        mensajeBienvenida="Panel de prueba: hacé preguntas como lo haría un estudiante para revisar qué responde el asistente con los documentos que subiste."
        placeholder="Probá una pregunta, ej: ¿Qué materias hay en el semestre 1?"
      />
      <p className="panel__chat-disclaimer">
        Estas consultas de prueba no se cuentan en las estadísticas de "Consultas totales".
      </p>
    </>
  );
}

/* ---------- Sección: Estadísticas ---------- */

const ICONOS_STATS = ["groups", "description", "grid_view", "search", "calendar_today", "bolt", "psychology"];

function SeccionEstadisticas() {
  const [stats, setStats] = useState(null);

  const cargarStats = () => obtenerEstadisticas().then(({ data }) => setStats(data));

  useEffect(() => {
    cargarStats();
  }, []);

  if (!stats) return <p className="panel__estado-vacio">Cargando…</p>;

  const tarjetas = [
    { valor: stats.total_estudiantes, etiqueta: "Estudiantes registrados" },
    { valor: stats.total_documentos, etiqueta: "Documentos cargados" },
    { valor: stats.total_fragmentos, etiqueta: "Fragmentos indexados" },
    { valor: stats.total_consultas, etiqueta: "Consultas totales" },
    { valor: stats.consultas_hoy, etiqueta: "Consultas hoy" },
    { valor: stats.respuestas_desde_cache, etiqueta: "Respuestas sin gastar tokens (datos directos y caché)" },
    { valor: stats.preguntas_aprendidas, etiqueta: "Preguntas aprendidas por el sistema" },
  ];

  return (
    <>
      <div className="panel__stats-grid">
        {tarjetas.map((t, i) => (
          <div key={t.etiqueta} className="panel__stat-card">
            <span className="panel__stat-card__valor">{t.valor}</span>
            <span className="panel__stat-card__etiqueta">{t.etiqueta}</span>
            <div className={`panel__stat-card__icono panel__stat-card__icono--${i}`}>
              <span className="material-symbols-outlined">{ICONOS_STATS[i]}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="tokens-dia">
        <div className="tokens-dia__texto">
          <strong>Tokens de IA gastados hoy: {stats.tokens_hoy.toLocaleString("es-BO")}</strong>
          <span>
            Cada modelo gratuito tiene su propio límite diario de {stats.limite_tokens_dia.toLocaleString("es-BO")} tokens:
            cuando uno se agota, el asistente sigue con el siguiente.
          </span>
        </div>
        {Object.entries(stats.tokens_por_modelo).map(([modelo, tokens]) => {
          const uso = tokens / stats.limite_tokens_dia;
          return (
            <div key={modelo} className="tokens-dia__fila">
              <span className="tokens-dia__modelo" title={modelo}>{modelo.split("/").pop()}</span>
              <div className="tokens-dia__barra">
                <div
                  className={`tokens-dia__relleno ${uso > 0.8 ? "tokens-dia__relleno--alto" : ""}`}
                  style={{ width: `${Math.min(100, uso * 100)}%` }}
                />
              </div>
              <span className="tokens-dia__num">
                {tokens.toLocaleString("es-BO")} / {stats.limite_tokens_dia.toLocaleString("es-BO")}
              </span>
            </div>
          );
        })}
      </div>

      <PreguntasAprendidas onCambio={cargarStats} />
    </>
  );
}

/* ---------- Preguntas aprendidas (caché) ---------- */

const TAMANO_APRENDIDAS = 5;

function PreguntasAprendidas({ onCambio }) {
  const [filas, setFilas] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [confirmando, setConfirmando] = useState(null); // id de la fila, o "todas"

  const cargar = async () => {
    const { data } = await listarPreguntasAprendidas();
    setFilas(data);
  };

  useEffect(() => {
    cargar();
  }, []);

  const olvidar = async () => {
    if (confirmando === "todas") await olvidarTodas();
    else await olvidarPregunta(confirmando);
    setConfirmando(null);
    setPagina(1);
    await cargar();
    onCambio?.();
  };

  if (filas === null) return <p className="panel__estado-vacio">Cargando…</p>;

  const visibles = filas.slice((pagina - 1) * TAMANO_APRENDIDAS, pagina * TAMANO_APRENDIDAS);

  return (
    <div className="panel__card panel__card--tabla aprendidas">
      <div className="aprendidas__cabecera">
        <div>
          <h3>Preguntas aprendidas</h3>
          <p>
            El sistema guarda las respuestas de la IA y las reutiliza sin gastar tokens. Si una respuesta guardada
            está mal, olvidala y se generará de nuevo.
          </p>
        </div>
        {filas.length > 0 &&
          (confirmando === "todas" ? (
            <div className="roles-confirmar">
              <span>¿Olvidar todas?</span>
              <button className="roles-btn roles-btn--peligro" onClick={olvidar}>Sí</button>
              <button className="roles-btn roles-btn--neutro" onClick={() => setConfirmando(null)}>No</button>
            </div>
          ) : (
            <button className="roles-btn roles-btn--peligro-suave" onClick={() => setConfirmando("todas")}>
              <span className="material-symbols-outlined">delete_sweep</span>
              Olvidar todas
            </button>
          ))}
      </div>

      {filas.length === 0 ? (
        <p className="panel__estado-vacio">Todavía no aprendió ninguna pregunta.</p>
      ) : (
        <>
          <ul className="aprendidas__lista">
            {visibles.map((f) => (
              <li key={f.id} className="aprendidas__item">
                <div className="aprendidas__texto">
                  <strong>{f.pregunta}</strong>
                  <span>{f.respuesta.replace(/\s+/g, " ")}</span>
                </div>
                <span className="aprendidas__usos" title="Veces que se reutilizó sin gastar tokens">
                  <span className="material-symbols-outlined">bolt</span>
                  {f.usos}
                </span>
                {confirmando === f.id ? (
                  <div className="roles-confirmar">
                    <span>¿Olvidar?</span>
                    <button className="roles-btn roles-btn--peligro" onClick={olvidar}>Sí</button>
                    <button className="roles-btn roles-btn--neutro" onClick={() => setConfirmando(null)}>No</button>
                  </div>
                ) : (
                  <button
                    className="roles-btn roles-btn--icono roles-btn--peligro-suave"
                    title="Olvidar esta pregunta"
                    onClick={() => setConfirmando(f.id)}
                  >
                    <span className="material-symbols-outlined">delete</span>
                  </button>
                )}
              </li>
            ))}
          </ul>
          <Paginacion pagina={pagina} tamano={TAMANO_APRENDIDAS} total={filas.length} onCambiar={setPagina} />
        </>
      )}
    </div>
  );
}

/* ---------- Sección: Roles y permisos ---------- */

const TAMANO_USUARIOS = 10;

const FILTROS_ROL = [
  { valor: "", etiqueta: "Todos", icono: "groups", total: "total_todos" },
  { valor: "admin", etiqueta: "Administradores", icono: "shield_person", total: "total_admins" },
  { valor: "student", etiqueta: "Estudiantes", icono: "school", total: "total_estudiantes" },
];

function iniciales(nombre) {
  const partes = nombre.split("@")[0].split(/[._-]+/).filter(Boolean);
  return ((partes[0]?.[0] || "?") + (partes[1]?.[0] || "")).toUpperCase();
}

function SeccionRoles() {
  const [datos, setDatos] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [busqueda, setBusqueda] = useState("");
  const [consulta, setConsulta] = useState("");
  const [rol, setRol] = useState("");
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");
  // Acción esperando confirmación en una fila: { id, tipo: "rol" | "eliminar" }
  const [pendiente, setPendiente] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  // La búsqueda espera 350 ms después de la última tecla, así no se hace
  // una consulta al servidor por cada letra que se escribe.
  useEffect(() => {
    const t = setTimeout(() => {
      setConsulta(busqueda);
      setPagina(1);
    }, 350);
    return () => clearTimeout(t);
  }, [busqueda]);

  const cargarUsuarios = async () => {
    const { data } = await listarUsuarios(pagina, TAMANO_USUARIOS, consulta, rol);
    setDatos(data);
  };

  useEffect(() => {
    cargarUsuarios();
  }, [pagina, consulta, rol]);

  // El mensaje de éxito se apaga solo a los 4 s
  useEffect(() => {
    if (!exito) return;
    const t = setTimeout(() => setExito(""), 4000);
    return () => clearTimeout(t);
  }, [exito]);

  const cambiarFiltro = (valor) => {
    setRol(valor);
    setPagina(1);
    setPendiente(null);
  };

  const ejecutar = async (usuario) => {
    setError("");
    setExito("");
    setTrabajando(true);
    try {
      if (pendiente.tipo === "rol") {
        const nuevoRol = usuario.role === "admin" ? "student" : "admin";
        await cambiarRolUsuario(usuario.id, nuevoRol);
        setExito(
          nuevoRol === "admin"
            ? `${usuario.username || usuario.email} ahora es administrador.`
            : `${usuario.username || usuario.email} volvió a ser estudiante.`
        );
      } else {
        await eliminarUsuario(usuario.id);
        setExito(`Se eliminó la cuenta ${usuario.username || usuario.email}.`);
      }
      setPendiente(null);
      await cargarUsuarios();
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo completar la acción."));
      setPendiente(null);
    } finally {
      setTrabajando(false);
    }
  };

  const conteos = datos && { ...datos, total_todos: datos.total_admins + datos.total_estudiantes };

  return (
    <>
      {error && <p className="panel__aviso-error">{error}</p>}
      {exito && (
        <p className="panel__aviso-exito">
          <span className="material-symbols-outlined">check_circle</span>
          {exito}
        </p>
      )}

      <div className="roles-barra">
        <div className="panel__buscador roles-barra__buscador">
          <span className="material-symbols-outlined">search</span>
          <input
            type="text"
            placeholder="Buscar por usuario o correo…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
          {busqueda && (
            <button className="roles-barra__limpiar" onClick={() => setBusqueda("")} title="Limpiar búsqueda">
              <span className="material-symbols-outlined">close</span>
            </button>
          )}
        </div>

        <div className="roles-filtros" role="tablist">
          {FILTROS_ROL.map((f) => (
            <button
              key={f.valor}
              role="tab"
              aria-selected={rol === f.valor}
              className={`roles-filtro roles-filtro--${f.valor || "todos"} ${rol === f.valor ? "roles-filtro--activo" : ""}`}
              onClick={() => cambiarFiltro(f.valor)}
            >
              <span className="material-symbols-outlined">{f.icono}</span>
              {f.etiqueta}
              {conteos && <span className="roles-filtro__conteo">{conteos[f.total]}</span>}
            </button>
          ))}
        </div>
      </div>

      {datos === null && <p className="panel__estado-vacio">Cargando…</p>}

      {datos && (
        <div className="panel__card panel__card--tabla">
          <div className="roles-tabla-scroll">
            <table className="roles-tabla">
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Rol</th>
                  <th>Cuenta</th>
                  <th>Registro</th>
                  <th className="roles-tabla__acciones">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {datos.items.map((u) => {
                  const esAdmin = u.role === "admin";
                  const enConfirmacion = pendiente?.id === u.id;
                  return (
                    <tr
                      key={u.id}
                      className={`${esAdmin ? "roles-fila--admin" : ""} ${enConfirmacion ? "roles-fila--confirmar" : ""}`}
                    >
                      <td>
                        <div className="roles-usuario">
                          <span className={`roles-avatar ${esAdmin ? "roles-avatar--admin" : ""}`}>
                            {iniciales(u.username || u.email)}
                          </span>
                          <span className="roles-usuario__datos">
                            <span className="roles-usuario__correo">{u.username || u.email}</span>
                            {u.username && <span className="roles-usuario__email">{u.email}</span>}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className={`roles-rol ${esAdmin ? "roles-rol--admin" : "roles-rol--estudiante"}`}>
                          <span className="material-symbols-outlined">{esAdmin ? "shield_person" : "school"}</span>
                          {esAdmin ? "Administrador" : "Estudiante"}
                        </span>
                      </td>
                      <td>
                        {u.is_verified ? (
                          <span className="roles-estado roles-estado--ok">
                            <span className="material-symbols-outlined">verified</span>Verificada
                          </span>
                        ) : (
                          <span className="roles-estado roles-estado--pendiente">
                            <span className="material-symbols-outlined">schedule</span>Pendiente
                          </span>
                        )}
                      </td>
                      <td className="roles-fecha">{formatearFecha(u.created_at)}</td>
                      <td className="roles-tabla__acciones">
                        {enConfirmacion ? (
                          <div className="roles-confirmar">
                            <span>
                              {pendiente.tipo === "eliminar"
                                ? "¿Eliminar cuenta?"
                                : esAdmin
                                ? "¿Quitar permisos de admin?"
                                : "¿Dar permisos de admin?"}
                            </span>
                            <button
                              className={`roles-btn ${pendiente.tipo === "eliminar" ? "roles-btn--peligro" : "roles-btn--ok"}`}
                              disabled={trabajando}
                              onClick={() => ejecutar(u)}
                            >
                              {trabajando ? "…" : "Sí"}
                            </button>
                            <button
                              className="roles-btn roles-btn--neutro"
                              disabled={trabajando}
                              onClick={() => setPendiente(null)}
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <div className="roles-acciones">
                            <button
                              className={`roles-btn ${esAdmin ? "roles-btn--quitar" : "roles-btn--dar"}`}
                              onClick={() => setPendiente({ id: u.id, tipo: "rol" })}
                            >
                              <span className="material-symbols-outlined">
                                {esAdmin ? "remove_moderator" : "add_moderator"}
                              </span>
                              {esAdmin ? "Quitar admin" : "Hacer admin"}
                            </button>
                            <button
                              className="roles-btn roles-btn--icono roles-btn--peligro-suave"
                              onClick={() => setPendiente({ id: u.id, tipo: "eliminar" })}
                              title="Eliminar usuario"
                            >
                              <span className="material-symbols-outlined">delete</span>
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {datos.items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="roles-vacio">
                      <span className="material-symbols-outlined">person_search</span>
                      No se encontraron usuarios con ese filtro.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <Paginacion pagina={pagina} tamano={TAMANO_USUARIOS} total={datos.total} onCambiar={setPagina} />
        </div>
      )}
    </>
  );
}

/* ---------- Dashboard principal ---------- */

const TITULOS = {
  documentos: { titulo: "Documentos", subtitulo: "Subí horarios, listas de docentes, avisos y comunicados." },
  chatbot: { titulo: "Probar Chatbot", subtitulo: "Probá el asistente antes de que lo usen los estudiantes." },
  estadisticas: { titulo: "Estadísticas", subtitulo: "Panorama general del sistema." },
  roles: { titulo: "Roles y permisos", subtitulo: "Gestioná qué cuentas tienen acceso de administrador." },
};

export default function AdminDashboard() {
  const [seccion, setSeccion] = useState("documentos");
  const { titulo, subtitulo } = TITULOS[seccion];

  return (
    <div className="panel">
      <Sidebar
        titulo="Ingeniería de Sistemas U.A.T.F"
        subtitulo="Administración Central"
        variante="admin"
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
            <button className="panel__topbar-icono">
              <span className="material-symbols-outlined">help</span>
            </button>
            <BotonCerrarSesion className="panel__topbar-icono" title="Cerrar sesión">
              <span className="material-symbols-outlined">logout</span>
            </BotonCerrarSesion>
          </div>
        </div>

        <div className="panel__contenido">
          {seccion === "documentos" && <SeccionDocumentos />}
          {seccion === "chatbot" && <SeccionProbarChatbot />}
          {seccion === "estadisticas" && <SeccionEstadisticas />}
          {seccion === "roles" && <SeccionRoles />}
        </div>

        <Footer />
      </main>
    </div>
  );
}