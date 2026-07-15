/**
 * Sinergia de composição (item 4 do PDF) — gráficos circulares Engage / Poke / Disengage.
 */
import { useMemo } from 'react';
import { ChampionImage } from './ChampionImage';

export type SynergyScores = {
  engage: number; // 0–100
  poke: number;
  disengage: number;
  team: number;
};

/** Heurística leve a partir dos nomes de campeões (sem DB de classes no FE). */
const ENGAGE_HINTS =
  /malphite|ornn|nautilus|leona|alistar|rell|amumu|sejuani|jarvan|wukong|vi|elise|lee sin|camille|renekton|rakan|thresh|pyke|pantheon|nocturne|hecate|maokai|sion|zac|poppy|braum/i;
const POKE_HINTS =
  /azir|viktor|xerath|ziggs|varus|jayce|nidalee|karma|lux|vel.?koz|zyra|caitlyn|ezreal|corki|syndra|orianna|zoe|twisted fate|ahri/i;
const DISENGAGE_HINTS =
  /janna|lulu|nami|soraka|yuumi|gragas|anivia|azir|orianna|taric|tahm|braum|lissandra|viktor|cassiopeia/i;

export function estimateSynergy(champions: string[]): SynergyScores {
  if (!champions.length) {
    return { engage: 28, poke: 28, disengage: 28, team: 30 };
  }
  let engage = 20;
  let poke = 20;
  let disengage = 20;
  for (const c of champions) {
    if (ENGAGE_HINTS.test(c)) engage += 14;
    if (POKE_HINTS.test(c)) poke += 14;
    if (DISENGAGE_HINTS.test(c)) disengage += 14;
  }
  engage = Math.min(96, engage + champions.length * 2);
  poke = Math.min(96, poke + champions.length * 2);
  disengage = Math.min(96, disengage + champions.length * 2);
  const team = Math.round((engage + poke + disengage) / 3);
  return { engage, poke, disengage, team };
}

function RingChart({
  scores,
  side,
  size = 120,
}: {
  scores: SynergyScores;
  side: 'blue' | 'red';
  size?: number;
}) {
  const accent = side === 'blue' ? '#38bdf8' : '#fb7185';
  const accent2 = side === 'blue' ? '#22d3ee' : '#f97316';
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.34;

  // Three arcs for engage/poke/disengage as overlapping rings
  const arcs = [
    { key: 'engage', value: scores.engage, color: accent, rOff: 0 },
    { key: 'poke', value: scores.poke, color: accent2, rOff: 8 },
    { key: 'disengage', value: scores.disengage, color: '#a78bfa', rOff: 16 },
  ];

  const describeArc = (radius: number, pct: number) => {
    const angle = Math.max(0.05, Math.min(0.999, pct / 100)) * 2 * Math.PI;
    const start = -Math.PI / 2;
    const end = start + angle;
    const x1 = cx + radius * Math.cos(start);
    const y1 = cy + radius * Math.sin(start);
    const x2 = cx + radius * Math.cos(end);
    const y2 = cy + radius * Math.sin(end);
    const large = angle > Math.PI ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`;
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {arcs.map((a) => (
          <g key={a.key}>
            <circle
              cx={cx}
              cy={cy}
              r={r - a.rOff}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={5}
            />
            <path
              d={describeArc(r - a.rOff, a.value)}
              fill="none"
              stroke={a.color}
              strokeWidth={5}
              strokeLinecap="round"
              opacity={0.9}
            />
          </g>
        ))}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fill="rgba(255,255,255,0.85)"
          fontSize={16}
          fontFamily="ui-monospace, monospace"
          fontWeight={700}
        >
          {scores.team}
        </text>
        <text
          x={cx}
          y={cy + 12}
          textAnchor="middle"
          fill="rgba(255,255,255,0.35)"
          fontSize={8}
          fontFamily="ui-monospace, monospace"
          letterSpacing="0.12em"
        >
          TEAM
        </text>
      </svg>
      <div className="grid grid-cols-3 gap-x-2 text-[8px] font-mono uppercase tracking-wide text-white/45">
        <span style={{ color: accent }}>Engage {scores.engage}</span>
        <span style={{ color: accent2 }}>Poke {scores.poke}</span>
        <span className="text-violet-300">Diseng. {scores.disengage}</span>
      </div>
    </div>
  );
}

interface CompositionSynergyProps {
  blueChamps: string[];
  redChamps: string[];
  /** Counter-picks recomendados (scout ou heurística) */
  counterPicks?: { style: string; champions: string[]; tone?: string }[];
  className?: string;
}

export function CompositionSynergy({
  blueChamps,
  redChamps,
  counterPicks,
  className = '',
}: CompositionSynergyProps) {
  const blue = useMemo(() => estimateSynergy(blueChamps), [blueChamps]);
  const red = useMemo(() => estimateSynergy(redChamps), [redChamps]);

  const defaultCounters = useMemo(() => {
    const styles: { style: string; champions: string[]; tone: string }[] = [];
    if (red.engage > red.poke) {
      styles.push({
        style: 'DISENGAGE',
        champions: ['Janna', 'Gragas', 'Anivia'].filter((c) => !blueChamps.includes(c)),
        tone: 'text-violet-300',
      });
    }
    if (red.poke >= red.engage) {
      styles.push({
        style: 'ENGAGE',
        champions: ['Malphite', 'Nautilus', 'Sejuani'].filter((c) => !blueChamps.includes(c)),
        tone: 'text-sky-300',
      });
    }
    styles.push({
      style: 'POKE',
      champions: ['Azir', 'Varus', 'Jayce'].filter((c) => !blueChamps.includes(c)),
      tone: 'text-lol-hq-orange',
    });
    return styles.slice(0, 3);
  }, [blueChamps, red.engage, red.poke]);

  const counters = counterPicks?.length ? counterPicks : defaultCounters;

  return (
    <div className={`hq-manager-analytics hq-frame ${className}`}>
      <div className="hq-panel-header">
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-lol-hq-cyan font-mono">
          Manager Analytics
        </span>
        <span className="text-[9px] font-mono text-white/35 tracking-wider">
          Composition Synergy · Engage / Poke / Disengage
        </span>
      </div>
      <div className="p-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Counter picks */}
        <div className="hq-glass-inset space-y-2">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-semibold font-mono">
            Recommended Counter-Picks
          </div>
          {counters.map((row) => (
            <div key={row.style} className="flex items-center gap-2">
              <span
                className={`text-[9px] font-mono font-bold w-16 shrink-0 ${row.tone || 'text-white/60'}`}
              >
                {row.style}
              </span>
              <div className="flex gap-1 flex-wrap">
                {row.champions.slice(0, 4).map((c) => (
                  <ChampionImage key={c} name={c} variant="ban" className="!w-7 !h-7" />
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="hq-glass-inset flex flex-col items-center justify-center">
          <div className="text-[9px] uppercase tracking-wider text-sky-400/80 font-semibold mb-1">
            Blue · Synergy
          </div>
          <RingChart scores={blue} side="blue" />
        </div>

        <div className="hq-glass-inset flex flex-col items-center justify-center">
          <div className="text-[9px] uppercase tracking-wider text-rose-400/80 font-semibold mb-1">
            Red · Synergy
          </div>
          <RingChart scores={red} side="red" />
        </div>
      </div>
    </div>
  );
}
