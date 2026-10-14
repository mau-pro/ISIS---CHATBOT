import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { listarDocumentosPublicos, urlDescargaDocumento } from "../services/api.js";
import { infoIconoArchivo, formatearTamano } from "../utils/archivos.js";
import Footer from "../components/Footer.jsx";
import Logos from "../components/Logos.jsx";
import "../styles/documentos.css";

const SECCIONES = {
  comunicados: {
    titulo: "Comunicados y Convocatorias",
    subtitulo: "Descarga y consulta de resoluciones, convocatorias a concursos y avisos de la carrera.",
  },
  horarios: {
    titulo: "Horarios",
    subtitulo: "Programación de clases en aulas y laboratorios.",
  },
  docentes: {
    titulo: "Docentes",
    subtitulo: "Listas de docentes y materias asignadas.",
  },
};

function formatearFecha(iso) {
  return new Date(iso).toLocaleDateString("es-BO", { day: "2-digit", month: "short", year: "numeric" });
}

export default function DocumentosSeccion() {
  const { seccion } = useParams();
  const info = SECCIONES[seccion];

  const [documentos, setDocumentos] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!info) return;
    listarDocumentosPublicos(seccion)
      .then(({ data }) => setDocumentos(data))
      .catch(() => setError("No se pudo cargar la lista de documentos. Intenta de nuevo."));
  }, [seccion]);

  if (!info) {
    return (
      <div className="docs-page">
        <div className="docs-contenido">
          <h1>Sección no encontrada</h1>
          <p>
            <Link to="/">Volver al inicio</Link>
          </p>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="docs-page">
      <header className="docs-header">
        <div className="docs-header__inner">
          <div className="docs-header__marca">
            <Logos tamano="sm" />
            <div>
              <div className="docs-header__titulo">Ingeniería de Sistemas UATF</div>
              <div className="docs-header__subtitulo">Universidad Autónoma Tomás Frías</div>
            </div>
          </div>
          <Link to="/" className="docs-header__boton">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>home</span>
            Inicio
          </Link>
        </div>
      </header>

      <div className="docs-contenido">
        <nav className="docs-breadcrumb">
          <Link to="/">
            <span className="material-symbols-outlined">home</span>
            Inicio
          </Link>
          <span>›</span>
          <span className="docs-breadcrumb__actual">{info.titulo}</span>
        </nav>

        <div className="docs-titulo-fila">
          <h1 className="docs-titulo">{info.titulo}</h1>
          {documentos && (
            <span className="docs-badge-conteo">
              {documentos.length} {documentos.length === 1 ? "archivo" : "archivos"}
            </span>
          )}
        </div>
        <p className="docs-subtitulo">{info.subtitulo}</p>

        {error && <p className="aviso-error">{error}</p>}

        {documentos === null && !error && <p className="estado-vacio">Cargando…</p>}

        {documentos?.length === 0 && (
          <p className="estado-vacio">Todavía no se subió ningún documento en esta sección.</p>
        )}

        {documentos?.length > 0 && (
          <div className="docs-tabla-card">
            <table className="docs-tabla">
              <thead>
                <tr>
                  <th>Archivo</th>
                  <th>Tipo</th>
                  <th>Tamaño</th>
                  <th>Subido</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {documentos.map((doc) => {
                  const { icono, clase, claseTipo } = infoIconoArchivo(doc.original_type);
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
                      <td>{formatearTamano(doc.size_bytes) || "—"}</td>
                      <td>{formatearFecha(doc.uploaded_at)}</td>
                      <td>
                        <a href={urlDescargaDocumento(doc.id)} className="docs-boton-descargar">
                          <span className="material-symbols-outlined">download</span>
                          Descargar
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="docs-ayuda">
          <div className="docs-ayuda__icono">
            <span className="material-symbols-outlined">help</span>
          </div>
          <div>
            <p className="docs-ayuda__titulo">¿Problemas para visualizar o descargar los archivos?</p>
            <p className="docs-ayuda__texto">
              Contactate con la administración de la carrera de Ingeniería de Sistemas.
            </p>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
