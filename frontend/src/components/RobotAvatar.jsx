/**
 * components/RobotAvatar.jsx
 * ----------------------------
 * Cara del robot "IS" (la misma mascota de la portada) en tamaño de avatar:
 * es quien responde en los chats del estudiante y del administrador. Con
 * `pensando` los ojos titilan mientras llega la respuesta. Colores planos (sin
 * gradientes con id) para poder repetirlo muchas veces en la misma pantalla.
 */

export default function RobotAvatar({ pensando = false, className = "" }) {
  return (
    <span className={`robot-avatar ${pensando ? "robot-avatar--pensando" : ""} ${className}`} aria-hidden="true">
      <svg viewBox="0 0 100 100">
        {/* diadema y auriculares */}
        <path d="M17 50 Q50 -2 83 50" stroke="#22d3ee" strokeWidth="6" strokeLinecap="round" fill="none" />
        <circle cx="13" cy="58" r="9" fill="#22d3ee" stroke="#0b1b45" strokeWidth="2.5" />
        <circle cx="87" cy="58" r="9" fill="#22d3ee" stroke="#0b1b45" strokeWidth="2.5" />
        <path d="M9 66 Q8 84 30 84" stroke="#0b1b45" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <circle cx="32" cy="84" r="3.6" fill="#67e8f9" />
        {/* cabeza */}
        <rect x="19" y="24" width="62" height="60" rx="26" fill="#f1f6ff" stroke="#b7d0ff" strokeWidth="1.5" />
        <ellipse cx="36" cy="32" rx="9" ry="4" fill="#fff" />
        {/* pantalla de la cara */}
        <rect x="26" y="36" width="48" height="40" rx="19" fill="#0b1b45" stroke="#22d3ee" strokeOpacity="0.55" strokeWidth="1.5" />
        <g className="robot-avatar__ojos">
          <ellipse cx="40" cy="55" rx="5.5" ry="7.5" fill="#67e8f9" />
          <ellipse cx="60" cy="55" rx="5.5" ry="7.5" fill="#67e8f9" />
        </g>
        <path d="M42 66 Q50 72 58 66" stroke="#67e8f9" strokeWidth="3" strokeLinecap="round" fill="none" />
      </svg>
    </span>
  );
}
