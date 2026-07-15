/**
 * Dashboard pós-jogo — War Room data viz:
 * timeline · gold differential · heatmap (eventos reais) · efficiency
 */
import { useMemo } from 'react';
import { ChampionImage } from './ChampionImage';
import { Activity, Flame, Swords, Map } from 'lucide-react';
import { buildHeatmapPoints, type HeatmapPoint, type MapEventHint } from '../lib/riftMap';

export type GoldSample = { minute: number; diff: number };
export type TimelineEvent = {
  minute: number;
  kind: 'KILL' | 'OBJECTIVE' | 'STRUCTURE' | 'OTHER';
  side?: 'BLUE' | 'RED' | string;
  text: string;
};

interface RatingRow {
  name?: string;
  role?: string;
  side?: string;
  champion?: string;
  rating?: number;
  note?: string;
  mvp?: boolean;
}

interface PostMatchAnalysisProps {
  goldSeries: GoldSample[];
  timeline: TimelineEvent[];
  /** Eventos de mapa da live → heatmap real */
  mapEvents?: MapEventHint[] | null;
  ratings?: RatingRow[] | null;
  blueTeam?: string;
  redTeam?: string;
  winnerSide?: string | null;
  blueKills?: number;
  redKills?: number;
  finalMinute?: number;
  onClose?: () => void;
}

function GoldChart({ series, events }: { series: GoldSample[]; events: TimelineEvent[] }) {
  const w = 360;
  const h = 140;
  const padX = 10;
  const padY = 12;

  const computed = useMemo(() => {
    if (!series.length) return null;
    const diffs = series.map((s) => s.diff);
    let minD = Math.min(...diffs, -200);
    let maxD = Math.max(...diffs, 200);
    if (minD === maxD) {
      minD -= 100;
      maxD += 100;
    }
    // pad 8%
    const pad = (maxD - minD) * 0.08;
    minD -= pad;
    maxD += pad;
    const span = maxD - minD || 1;
    const maxM = Math.max(...series.map((s) => s.minute), 1);
    const toX = (m: number) => padX + (m / maxM) * (w - padX * 2);
    const toY = (d: number) => padY + ((maxD - d) / span) * (h - padY * 2);
    const zeroY = toY(0);
    const pts = series.map((s) => ({ x: toX(s.minute), y: toY(s.diff), ...s }));
    const line = pts.map((p) => `${p.x},${p.y}`).join(' L ');
    // area above/below zero
    const areaPath =
      pts.length > 0
        ? `M ${pts[0].x},${zeroY} L ${line} L ${pts[pts.length - 1].x},${zeroY} Z`
        : '';
    return { line, areaPath, zeroY, toX, toY, maxM, pts, maxD, minD };
  }, [series]);

  if (!computed) {
    return (
      <div className="h-[140px] flex items-center justify-center text-[10px] text-white/30 font-mono">
        Sem dados de ouro · GPM tracking offline
      </div>
    );
  }

  const markers = events
    .filter((e) => e.kind === 'OBJECTIVE' || e.kind === 'STRUCTURE')
    .slice(0, 8);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[140px]" preserveAspectRatio="none">
      <defs>
        <linearGradient id="goldFillBlue" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.02" />
        </linearGradient>
        <linearGradient id="goldFillRed" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="#f97316" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#f97316" stopOpacity="0.02" />
        </linearGradient>
        <filter id="goldGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        {/* clip areas above/below zero */}
        <clipPath id="clipAbove">
          <rect x={0} y={0} width={w} height={computed.zeroY} />
        </clipPath>
        <clipPath id="clipBelow">
          <rect x={0} y={computed.zeroY} width={w} height={h - computed.zeroY} />
        </clipPath>
      </defs>

      {/* grid */}
      {[0.25, 0.5, 0.75].map((t) => (
        <line
          key={t}
          x1={padX}
          x2={w - padX}
          y1={padY + t * (h - padY * 2)}
          y2={padY + t * (h - padY * 2)}
          stroke="rgba(255,255,255,0.04)"
          strokeWidth={1}
        />
      ))}

      {/* zero line */}
      <line
        x1={padX}
        x2={w - padX}
        y1={computed.zeroY}
        y2={computed.zeroY}
        stroke="rgba(255,255,255,0.18)"
        strokeDasharray="3 4"
      />

      {/* fill areas */}
      <path d={computed.areaPath} fill="url(#goldFillBlue)" clipPath="url(#clipAbove)" />
      <path d={computed.areaPath} fill="url(#goldFillRed)" clipPath="url(#clipBelow)" />

      {/* main line */}
      <path
        d={`M ${computed.line}`}
        fill="none"
        stroke="#22d3ee"
        strokeWidth={1.8}
        filter="url(#goldGlow)"
        vectorEffect="non-scaling-stroke"
      />

      {/* event markers on timeline */}
      {markers.map((ev, i) => {
        const x = computed.toX(ev.minute);
        const color =
          ev.side === 'BLUE' ? '#38bdf8' : ev.side === 'RED' ? '#fb923c' : 'rgba(255,255,255,0.4)';
        return (
          <g key={`m-${i}`}>
            <line
              x1={x}
              x2={x}
              y1={padY}
              y2={h - padY}
              stroke={color}
              strokeWidth={0.8}
              opacity={0.35}
              strokeDasharray="2 2"
            />
            <circle cx={x} cy={padY + 3} r={2.2} fill={color} />
          </g>
        );
      })}

      {/* end marker */}
      {computed.pts.length > 0 && (
        <g>
          <circle
            cx={computed.pts[computed.pts.length - 1].x}
            cy={computed.pts[computed.pts.length - 1].y}
            r={5}
            fill="#22d3ee"
            opacity={0.25}
          />
          <circle
            cx={computed.pts[computed.pts.length - 1].x}
            cy={computed.pts[computed.pts.length - 1].y}
            r={2.8}
            fill="#e2e8f0"
          />
        </g>
      )}
    </svg>
  );
}

function MiniHeatmap({ points }: { points: HeatmapPoint[] }) {
  const hasData = points.length > 0;

  return (
    <div className="relative w-full aspect-square max-w-[180px] mx-auto rounded-sm overflow-hidden border border-lol-hq-cyan/20 bg-[#050d18]">
      <svg viewBox="0 0 100 100" className="w-full h-full">
        <defs>
          <pattern id="gridRift" width="10" height="10" patternUnits="userSpaceOnUse">
            <path
              d="M 10 0 L 0 0 0 10"
              fill="none"
              stroke="rgba(34,211,238,0.06)"
              strokeWidth="0.5"
            />
          </pattern>
          <filter id="heatBlur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.8" />
          </filter>
        </defs>
        <rect x="4" y="4" width="92" height="92" rx="2" fill="#0a1628" stroke="rgba(34,211,238,0.15)" />
        <rect x="4" y="4" width="92" height="92" fill="url(#gridRift)" />
        {/* river / structure skeleton */}
        <path
          d="M14 86 L86 14"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        <path d="M18 70 L70 18" stroke="#22d3ee" strokeWidth="1.2" opacity="0.25" />
        <path d="M30 88 L88 30" stroke="#f97316" strokeWidth="1.2" opacity="0.25" />
        {/* bases */}
        <circle cx="18" cy="82" r="5" fill="#0ea5e9" opacity="0.35" />
        <circle cx="82" cy="18" r="5" fill="#f97316" opacity="0.35" />
        <circle cx="58" cy="66" r="2.5" fill="#fbbf24" opacity="0.45" />
        <circle cx="42" cy="34" r="2.5" fill="#a78bfa" opacity="0.45" />

        {/* Real heat blobs from match events */}
        <g filter="url(#heatBlur)" opacity={hasData ? 1 : 0.35}>
          {(hasData
            ? points
            : [
                { x: 50, y: 50, weight: 0.4, side: 'BLUE' },
                { x: 58, y: 66, weight: 0.3, side: 'RED' },
              ]
          ).map((p, i) => {
            const isBlue = String(p.side || '').toUpperCase() === 'BLUE';
            const isRed = String(p.side || '').toUpperCase() === 'RED';
            const color = isBlue ? '#22d3ee' : isRed ? '#f97316' : '#a78bfa';
            const r = 4 + p.weight * 14;
            return (
              <circle
                key={`${p.x}-${p.y}-${i}`}
                cx={p.x}
                cy={p.y}
                r={r}
                fill={color}
                opacity={0.18 + p.weight * 0.55}
              />
            );
          })}
        </g>
        {/* crisp cores */}
        {hasData &&
          points.slice(0, 12).map((p, i) => {
            const isBlue = String(p.side || '').toUpperCase() === 'BLUE';
            const isRed = String(p.side || '').toUpperCase() === 'RED';
            const color = isBlue ? '#67e8f9' : isRed ? '#fb923c' : '#e2e8f0';
            return (
              <circle
                key={`core-${i}`}
                cx={p.x}
                cy={p.y}
                r={1.2 + p.weight * 2}
                fill={color}
                opacity={0.55 + p.weight * 0.4}
              />
            );
          })}
      </svg>
      <div className="absolute bottom-1 left-1 right-1 text-[8px] font-mono text-center text-lol-hq-cyan/50 uppercase tracking-wider">
        {hasData
          ? `Heat · ${points.length} hotspots`
          : 'Heat Map · sem telemetria'}
      </div>
    </div>
  );
}

export function PostMatchAnalysis({
  goldSeries,
  timeline,
  mapEvents,
  ratings,
  blueTeam = 'Blue',
  redTeam = 'Red',
  winnerSide,
  blueKills = 0,
  redKills = 0,
  finalMinute = 0,
  onClose,
}: PostMatchAnalysisProps) {
  const sortedTimeline = useMemo(
    () => [...timeline].sort((a, b) => a.minute - b.minute).slice(-18),
    [timeline]
  );

  const heatPoints = useMemo(
    () => buildHeatmapPoints(mapEvents || []),
    [mapEvents]
  );

  const efficiency = useMemo(() => {
    const rows = [...(ratings || [])].sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
    return rows.slice(0, 10);
  }, [ratings]);

  return (
    <div className="hq-postmatch hq-frame panel-enter">
      <div className="hq-panel-header flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Activity className="w-3.5 h-3.5 text-lol-hq-cyan shrink-0" />
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-lol-hq-cyan truncate font-mono">
            Match Analysis · Pós-jogo
          </span>
        </div>
        <div className="text-[10px] font-mono text-white/45 shrink-0">
          <span className="text-sky-400">{blueKills}</span>
          <span className="text-white/25"> – </span>
          <span className="text-lol-hq-orange">{redKills}</span>
          <span className="text-white/30"> · </span>
          {String(finalMinute).padStart(2, '0')}:00
          {winnerSide ? (
            <span className="text-white/55">
              {' '}
              · {winnerSide === 'BLUE' ? blueTeam : redTeam}
            </span>
          ) : null}
        </div>
      </div>

      <div className="p-3 grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Timeline — secondary side panel */}
        <div className="lg:col-span-3 hq-glass-inset max-h-[300px] overflow-y-auto">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-semibold mb-2 flex items-center gap-1 font-mono">
            <Swords className="w-3 h-3 text-lol-hq-cyan" /> Match Timeline
          </div>
          <div className="space-y-1">
            {sortedTimeline.length === 0 && (
              <p className="text-[10px] text-white/30 py-4 text-center">Sem eventos registrados</p>
            )}
            {sortedTimeline.map((ev, i) => (
              <div
                key={`${ev.minute}-${i}`}
                className="flex gap-2 text-[10px] font-mono border-l-2 pl-2 py-0.5"
                style={{
                  borderColor:
                    ev.side === 'BLUE'
                      ? '#38bdf8'
                      : ev.side === 'RED'
                        ? '#fb923c'
                        : 'rgba(255,255,255,0.15)',
                }}
              >
                <span className="text-white/35 w-8 shrink-0">
                  {String(ev.minute).padStart(2, '0')}
                </span>
                <span className="text-white/70 truncate">{ev.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Gold differential — central primary viz */}
        <div className="lg:col-span-5 hq-glass-inset">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-semibold mb-1 flex items-center gap-1 font-mono">
            <Flame className="w-3 h-3 text-lol-hq-orange" /> Gold Differential
          </div>
          <div className="flex justify-between text-[9px] font-mono mb-1">
            <span className="text-sky-400">{blueTeam}</span>
            <span className="text-white/25">GPM / net worth Δ</span>
            <span className="text-lol-hq-orange">{redTeam}</span>
          </div>
          <GoldChart series={goldSeries} events={timeline} />
          <div className="flex gap-3 justify-center text-[8px] font-mono text-white/35 mt-1">
            <span className="text-sky-400">● Blue lead</span>
            <span className="text-lol-hq-orange">● Red lead</span>
            <span className="text-white/30">┊ Obj. markers</span>
          </div>
        </div>

        {/* Heatmap */}
        <div className="lg:col-span-4 hq-glass-inset flex flex-col items-center">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-semibold mb-2 self-start flex items-center gap-1 font-mono">
            <Map className="w-3 h-3 text-lol-hq-cyan" /> Heat Map
          </div>
          <MiniHeatmap points={heatPoints} />
        </div>

        {/* Efficiency bars — full width data table */}
        <div className="lg:col-span-12 hq-glass-inset">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-semibold mb-2 font-mono">
            Efficiency · Player Ratings · KDA / DPM proxy
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
            {efficiency.map((r, i) => {
              const pct = Math.min(100, ((r.rating ?? 0) / 10) * 100);
              const isBlue = r.side === 'BLUE';
              return (
                <div key={`${r.name}-${i}`} className="flex items-center gap-2 text-[10px]">
                  <span className="w-4 text-white/30 font-mono">{i + 1}</span>
                  {r.champion && (
                    <ChampionImage name={r.champion} variant="ban" className="!w-5 !h-5" />
                  )}
                  <span className={`w-10 font-mono ${isBlue ? 'text-sky-400' : 'text-lol-hq-orange'}`}>
                    {r.role}
                  </span>
                  <span className="flex-1 truncate text-white/75">
                    {r.name}
                    {r.mvp ? (
                      <span className="text-lol-hq-cyan ml-1 font-semibold">MVP</span>
                    ) : null}
                  </span>
                  <div className="w-24 sm:w-32 stat-bar">
                    <div
                      className={`stat-bar-fill ${isBlue ? 'bg-sky-400' : 'bg-lol-hq-orange'}`}
                      style={{
                        width: `${pct}%`,
                        color: isBlue ? '#38bdf8' : '#f97316',
                      }}
                    />
                  </div>
                  <span className="w-8 text-right font-mono text-white/90">
                    {(r.rating ?? 0).toFixed(1)}
                  </span>
                </div>
              );
            })}
            {efficiency.length === 0 && (
              <p className="text-[10px] text-white/30 col-span-full text-center py-2">
                Ratings indisponíveis
              </p>
            )}
          </div>
        </div>
      </div>

      {onClose && (
        <div className="px-3 pb-3 flex justify-end">
          <button type="button" onClick={onClose} className="btn-lol-primary">
            Continuar
          </button>
        </div>
      )}
    </div>
  );
}
