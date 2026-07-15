/**
 * Gráfico de radar (spider chart) — perfil do jogador.
 * Eixos: Mecânica, Visão, Pool, Liderança, Consistência, Resil. (0–20)
 * Estética: holograma tech-noir com glow cyan.
 */

export type RadarAxis = {
  key: string;
  label: string;
  value: number; // 0–20
};

interface AttributeRadarProps {
  axes: RadarAxis[];
  size?: number;
  className?: string;
  accent?: string;
  fill?: string;
}

function polar(cx: number, cy: number, r: number, angleRad: number) {
  return {
    x: cx + r * Math.cos(angleRad),
    y: cy + r * Math.sin(angleRad),
  };
}

export function AttributeRadar({
  axes,
  size = 180,
  className = '',
  accent = '#22d3ee',
  fill = 'rgba(34, 211, 238, 0.2)',
}: AttributeRadarProps) {
  const n = Math.max(3, axes.length);
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.36;
  const start = -Math.PI / 2;
  const uid = `radar-${size}-${n}`;

  const rings = [0.25, 0.5, 0.75, 1];

  const ringPoints = (t: number) =>
    Array.from({ length: n }, (_, i) => {
      const a = start + (i * 2 * Math.PI) / n;
      const p = polar(cx, cy, maxR * t, a);
      return `${p.x},${p.y}`;
    }).join(' ');

  const valuePoints = axes
    .map((ax, i) => {
      const a = start + (i * 2 * Math.PI) / n;
      const t = Math.max(0, Math.min(1, (ax.value || 0) / 20));
      const p = polar(cx, cy, maxR * t, a);
      return `${p.x},${p.y}`;
    })
    .join(' ');

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      role="img"
      aria-label="Atributos de performance"
    >
      <defs>
        <filter id={`${uid}-glow`} x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="2.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <radialGradient id={`${uid}-core`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={accent} stopOpacity="0.12" />
          <stop offset="100%" stopColor={accent} stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* soft core */}
      <circle cx={cx} cy={cy} r={maxR} fill={`url(#${uid}-core)`} />

      {/* grid rings */}
      {rings.map((t) => (
        <polygon
          key={t}
          points={ringPoints(t)}
          fill="none"
          stroke={t === 1 ? 'rgba(34,211,238,0.22)' : 'rgba(255,255,255,0.07)'}
          strokeWidth={t === 1 ? 1.2 : 1}
        />
      ))}

      {/* axes */}
      {axes.map((_, i) => {
        const a = start + (i * 2 * Math.PI) / n;
        const p = polar(cx, cy, maxR, a);
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={p.x}
            y2={p.y}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
          />
        );
      })}

      {/* value polygon glow + fill */}
      <polygon
        points={valuePoints}
        fill={fill}
        stroke={accent}
        strokeWidth={1.8}
        strokeLinejoin="round"
        filter={`url(#${uid}-glow)`}
      />

      {/* dots */}
      {axes.map((ax, i) => {
        const a = start + (i * 2 * Math.PI) / n;
        const t = Math.max(0, Math.min(1, (ax.value || 0) / 20));
        const p = polar(cx, cy, maxR * t, a);
        return (
          <g key={ax.key}>
            <circle cx={p.x} cy={p.y} r={4} fill={accent} opacity={0.25} />
            <circle cx={p.x} cy={p.y} r={2.2} fill={accent} />
          </g>
        );
      })}

      {/* labels */}
      {axes.map((ax, i) => {
        const a = start + (i * 2 * Math.PI) / n;
        const p = polar(cx, cy, maxR + size * 0.1, a);
        return (
          <text
            key={`l-${ax.key}`}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="rgba(226,232,240,0.72)"
            fontSize={size * 0.048}
            fontFamily="ui-monospace, monospace"
            style={{ textTransform: 'uppercase', letterSpacing: '0.06em' }}
          >
            {ax.label}
          </text>
        );
      })}
    </svg>
  );
}

/** Helper: monta eixos a partir de um Player do store */
export function playerToRadarAxes(p: {
  mechanics?: number;
  focus?: number;
  teamwork?: number;
  resilience?: number;
  consistency?: number | null;
  consistencyKnown?: boolean;
  championPool?: unknown[];
}): RadarAxis[] {
  const poolSize = Array.isArray(p.championPool) ? p.championPool.length : 0;
  const poolScore = Math.min(20, 6 + poolSize * 2.2);
  const consistency =
    p.consistencyKnown && p.consistency != null ? Number(p.consistency) : 10;

  return [
    { key: 'mechanics', label: 'Mecânica', value: Number(p.mechanics) || 10 },
    { key: 'vision', label: 'Visão', value: Number(p.focus) || 10 },
    { key: 'pool', label: 'Pool', value: poolScore },
    { key: 'leadership', label: 'Liderança', value: Number(p.teamwork) || 10 },
    { key: 'consistency', label: 'Consist.', value: consistency },
    { key: 'resilience', label: 'Resil.', value: Number(p.resilience) || 10 },
  ];
}
