/**
 * components/EdificioFondo.jsx
 * ------------------------------
 * Fondo con el edificio de la universidad. Si existe una foto real en
 * frontend/public/edificio-uatf.jpg se usa esa (con degradados por encima para
 * que el texto siga legible); si no existe, se dibuja una silueta propia en SVG.
 * Para usar la foto real, copiá el archivo con ese nombre a frontend/public/.
 */

import { useState } from "react";

const VENTANAS_ALA = [0, 1, 2].flatMap((fila) => [0, 1, 2, 3].map((col) => ({ fila, col })));

function Ventana({ x, y }) {
  return <path d={`M${x} ${y} v-15 a6 6 0 0 1 12 0 v15 z`} />;
}

export default function EdificioFondo() {
  const [fotoCargada, setFotoCargada] = useState(false);

  return (
    <div className={`edificio ${fotoCargada ? "edificio--foto" : ""}`} aria-hidden="true">
      <img
        src="/edificio-uatf.jpg"
        alt=""
        className={`edificio__foto ${fotoCargada ? "edificio__foto--visible" : ""}`}
        onLoad={() => setFotoCargada(true)}
        onError={() => setFotoCargada(false)}
      />
      {!fotoCargada && (
        <svg className="edificio__silueta" viewBox="0 0 420 300" preserveAspectRatio="xMidYMax slice">
          <defs>
            <linearGradient id="ed-fachada" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#7dd3fc" stopOpacity="0.32" />
              <stop offset="1" stopColor="#3b82f6" stopOpacity="0.1" />
            </linearGradient>
          </defs>
          <g fill="url(#ed-fachada)" stroke="#7dd3fc" strokeOpacity="0.4" strokeWidth="1.2">
            {/* alas */}
            <rect x="10" y="120" width="140" height="180" />
            <rect x="270" y="120" width="140" height="180" />
            {/* cuerpo central */}
            <rect x="140" y="70" width="140" height="230" />
            {/* torre y cúpula */}
            <rect x="182" y="20" width="56" height="60" />
            <path d="M176 22 L210 -6 L244 22 Z" />
            <path d="M200 -6 L210 -22 L220 -6 Z" />
            {/* cornisas */}
            <rect x="4" y="112" width="152" height="10" />
            <rect x="264" y="112" width="152" height="10" />
            <rect x="134" y="62" width="152" height="10" />
          </g>
          <circle cx="210" cy="50" r="14" fill="none" stroke="#a5f3fc" strokeOpacity="0.6" strokeWidth="2" />
          <path d="M210 50 v-8 M210 50 l6 4" stroke="#a5f3fc" strokeOpacity="0.7" strokeWidth="2" />
          {/* ventanas en arco */}
          <g fill="#bae6fd" fillOpacity="0.28" stroke="none">
            {VENTANAS_ALA.map(({ fila, col }) => (
              <Ventana key={`i${fila}${col}`} x={26 + col * 34} y={158 + fila * 44} />
            ))}
            {VENTANAS_ALA.map(({ fila, col }) => (
              <Ventana key={`d${fila}${col}`} x={286 + col * 34} y={158 + fila * 44} />
            ))}
            {[0, 1, 2].flatMap((fila) =>
              [0, 1, 2].map((col) => <Ventana key={`c${fila}${col}`} x={166 + col * 34} y={108 + fila * 46} />)
            )}
            <path d="M196 300 v-46 a14 14 0 0 1 28 0 v46 z" fillOpacity="0.4" />
          </g>
        </svg>
      )}
    </div>
  );
}
