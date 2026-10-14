/**
 * components/Paginacion.jsx
 * ----------------------------
 * Controles de paginación reutilizables (tablas del admin, historial del
 * estudiante). Muestra "1-10 de 253", botones anterior/siguiente y números
 * de página con "..." cuando hay muchas.
 */

function paginasVisibles(actual, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const set = new Set([1, total, actual, actual - 1, actual + 1]);
  const ordenadas = [...set].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b);
  const resultado = [];
  ordenadas.forEach((n, i) => {
    if (i > 0 && n - ordenadas[i - 1] > 1) resultado.push("…");
    resultado.push(n);
  });
  return resultado;
}

export default function Paginacion({ pagina, tamano, total, onCambiar }) {
  const totalPaginas = Math.max(1, Math.ceil(total / tamano));
  if (total === 0) return null;

  const desde = (pagina - 1) * tamano + 1;
  const hasta = Math.min(pagina * tamano, total);

  return (
    <div className="paginacion">
      <span className="paginacion__info">
        {desde}-{hasta} de {total}
      </span>
      <div className="paginacion__botones">
        <button disabled={pagina <= 1} onClick={() => onCambiar(pagina - 1)} aria-label="Página anterior">
          <span className="material-symbols-outlined">chevron_left</span>
        </button>
        {paginasVisibles(pagina, totalPaginas).map((n, i) =>
          n === "…" ? (
            <span key={`p${i}`} className="paginacion__puntos">…</span>
          ) : (
            <button
              key={n}
              className={n === pagina ? "paginacion__activa" : ""}
              onClick={() => onCambiar(n)}
            >
              {n}
            </button>
          )
        )}
        <button disabled={pagina >= totalPaginas} onClick={() => onCambiar(pagina + 1)} aria-label="Página siguiente">
          <span className="material-symbols-outlined">chevron_right</span>
        </button>
      </div>
    </div>
  );
}
