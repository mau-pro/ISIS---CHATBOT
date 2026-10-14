/**
 * components/RespuestaFormateada.jsx
 * -------------------------------------
 * Muestra la respuesta del asistente de forma ordenada. El backend devuelve
 * texto plano (sin Markdown); acá las líneas "- Materia (SIGLA) - Docente -
 * Día hora - Ambiente" se dibujan como tarjetas: la primera parte en negrita
 * y el resto como etiquetas, mucho más fácil de leer que un párrafo largo.
 */

function partirLineas(texto) {
  const bloques = [];
  let lista = null;
  texto.split("\n").forEach((linea) => {
    const limpia = linea.trim();
    if (/^-\s+/.test(limpia)) {
      if (!lista) {
        lista = { tipo: "lista", items: [] };
        bloques.push(lista);
      }
      lista.items.push(limpia.replace(/^-\s+/, ""));
    } else if (limpia) {
      lista = null;
      bloques.push({ tipo: "texto", texto: limpia });
    }
  });
  return bloques;
}

export default function RespuestaFormateada({ texto }) {
  return (
    <div className="respuesta">
      {partirLineas(texto).map((b, i) =>
        b.tipo === "texto" ? (
          <p key={i} className="respuesta__texto">{b.texto}</p>
        ) : (
          <ul key={i} className="respuesta__lista">
            {b.items.map((item, j) => {
              const [principal, ...detalles] = item.split(/\s+-\s+/);
              return (
                <li key={j} className="respuesta__item">
                  <span className="respuesta__principal">{principal}</span>
                  {detalles.map((d, k) => (
                    <span key={k} className="respuesta__etiqueta">{d}</span>
                  ))}
                </li>
              );
            })}
          </ul>
        )
      )}
    </div>
  );
}
