/**
 * components/RobotMascota.jsx
 * -----------------------------
 * Mascota del asistente (ilustración SVG propia, sin imágenes externas):
 * un robot con auricular que flota, parpadea y saluda. Lleva "IS" en el pecho
 * por Ingeniería de Sistemas. Las animaciones están en home.css (.robot*).
 */

export default function RobotMascota() {
  return (
    <svg className="robot" viewBox="0 0 250 310" role="img" aria-label="I-SIS, asistente virtual de Ingeniería de Sistemas">
      <defs>
        <linearGradient id="rb-cuerpo" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#c9dcff" />
        </linearGradient>
        <linearGradient id="rb-cian" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#a5f3fc" />
          <stop offset="0.5" stopColor="#22d3ee" />
          <stop offset="1" stopColor="#0ea5e9" />
        </linearGradient>
        <linearGradient id="rb-visor" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0f2a66" />
          <stop offset="1" stopColor="#081638" />
        </linearGradient>
        <radialGradient id="rb-base" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#22d3ee" stopOpacity="0.75" />
          <stop offset="1" stopColor="#22d3ee" stopOpacity="0" />
        </radialGradient>
        <filter id="rb-brillo" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* luz de propulsión / sombra */}
      <ellipse className="robot__base" cx="125" cy="296" rx="72" ry="12" fill="url(#rb-base)" />

      <g className="robot__flota">
        {/* brazo izquierdo (el del lado del espectador) */}
        <path d="M78 168 Q44 186 46 232" stroke="#dbe8ff" strokeWidth="21" strokeLinecap="round" fill="none" />
        <circle cx="46" cy="236" r="13" fill="url(#rb-cian)" />

        {/* cuerpo */}
        <path
          d="M72 168 Q72 138 125 138 Q178 138 178 168 L172 244 Q166 274 125 274 Q84 274 78 244 Z"
          fill="url(#rb-cuerpo)"
          stroke="#b7d0ff"
          strokeWidth="2"
        />
        <ellipse cx="100" cy="170" rx="14" ry="22" fill="#fff" opacity="0.55" />
        <circle cx="125" cy="212" r="27" fill="#0b1b45" stroke="url(#rb-cian)" strokeWidth="4" filter="url(#rb-brillo)" />
        <text x="125" y="221" textAnchor="middle" fontSize="25" fontWeight="800" fill="#67e8f9" fontFamily="Outfit, sans-serif">
          IS
        </text>

        {/* brazo derecho saludando */}
        <g className="robot__saludo">
          <path d="M172 170 Q214 160 216 112" stroke="#dbe8ff" strokeWidth="21" strokeLinecap="round" fill="none" />
          <circle cx="216" cy="102" r="14" fill="url(#rb-cian)" />
        </g>

        {/* cabeza */}
        <rect x="52" y="34" width="146" height="108" rx="50" fill="url(#rb-cuerpo)" stroke="#b7d0ff" strokeWidth="2" />
        <ellipse cx="84" cy="52" rx="18" ry="8" fill="#fff" opacity="0.7" />

        {/* diadema y auriculares */}
        <path d="M58 70 Q125 -14 192 70" stroke="url(#rb-cian)" strokeWidth="9" strokeLinecap="round" fill="none" />
        <circle cx="50" cy="92" r="17" fill="url(#rb-cian)" stroke="#0b1b45" strokeWidth="3" />
        <circle cx="200" cy="92" r="17" fill="url(#rb-cian)" stroke="#0b1b45" strokeWidth="3" />
        <path d="M42 106 Q38 138 80 138" stroke="#0b1b45" strokeWidth="4" fill="none" strokeLinecap="round" />
        <circle cx="83" cy="138" r="6" fill="#22d3ee" />

        {/* pantalla de la cara */}
        <rect x="68" y="56" width="114" height="72" rx="32" fill="url(#rb-visor)" stroke="#22d3ee" strokeOpacity="0.5" strokeWidth="2" />
        <g className="robot__ojos" filter="url(#rb-brillo)">
          <ellipse cx="102" cy="90" rx="11" ry="15" fill="#67e8f9" />
          <ellipse cx="148" cy="90" rx="11" ry="15" fill="#67e8f9" />
        </g>
        <path d="M108 110 Q125 124 142 110" stroke="#67e8f9" strokeWidth="5" strokeLinecap="round" fill="none" filter="url(#rb-brillo)" />
      </g>
    </svg>
  );
}
