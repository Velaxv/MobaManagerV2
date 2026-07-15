import { useEffect, useMemo, useRef, useState } from 'react';
import { Map as MapIcon, Eye } from 'lucide-react';
import { ChampionImage } from './ChampionImage';
import { RoleIcon } from './RoleIcon';
import {
  applyTowerHpFromPressure,
  buildMiniFeed,
  countAliveTowers,
  eventTypeGlyph,
  flashAnchor,
  locationLabel,
  resolveObjectiveContest,
  resolveRiftUnits,
  resolveStructures,
  resolveWards,
  type MapEventHint,
  type MapPoint,
  type MiniFeedItem,
  type ObjectiveContest,
  type RiftStructure,
  type RiftUnit,
  type RiftWard,
} from '../lib/riftMap';
import { PlayerRole } from '../types/game';

interface Pick {
  champion: string;
  role: string;
}

interface MapStructuresBE {
  blue?: { top?: number; mid?: number; bot?: number; inhibs?: number; nexus?: number; towers_total?: number };
  red?: { top?: number; mid?: number; bot?: number; inhibs?: number; nexus?: number; towers_total?: number };
}

interface SummonersRiftMapProps {
  phase: string;
  minute: number;
  bluePicks: Pick[];
  redPicks: Pick[];
  latestEvent?: MapEventHint | null;
  /** Histórico de eventos com map meta (para torres) */
  eventHistory?: MapEventHint[];
  /** Estruturas do backend (fonte da verdade quando presente) */
  mapStructures?: MapStructuresBE | null;
  lanePressure?: Record<string, number> | null;
  winnerSide?: string | null;
  isVictory?: boolean;
  blueTeam?: string;
  redTeam?: string;
  /** Eventos recentes para mini-feed no mapa (ME-7) */
  feedItems?: MiniFeedItem[];
  className?: string;
}

const ROLE_TO_ENUM: Record<string, PlayerRole> = {
  TOP: PlayerRole.TOP,
  JUNGLE: PlayerRole.JUNGLE,
  MID: PlayerRole.MID,
  BOT: PlayerRole.BOT,
  SUPPORT: PlayerRole.SUPPORT,
};

const TRAIL_MAX = 7;
const TRAIL_MIN_DIST = 1.2;

function UnitMarker({ unit }: { unit: RiftUnit }) {
  const isBlue = unit.side === 'BLUE';
  const pulse = unit.focused && unit.intensity > 0.4;

  return (
    <div
      className="absolute z-10 -translate-x-1/2 -translate-y-1/2 transition-all duration-700 ease-out will-change-transform"
      style={{
        left: `${unit.x}%`,
        top: `${unit.y}%`,
        zIndex: unit.focused ? 20 : 10,
      }}
      title={`${unit.role} · ${unit.champion || '—'}`}
    >
      {pulse && (
        <span
          className={`absolute inset-0 -m-1 rounded-full animate-ping opacity-40 ${
            isBlue ? 'bg-sky-400' : 'bg-rose-400'
          }`}
        />
      )}
      <div
        className={`relative rounded-full overflow-hidden border-2 shadow-lg transition-transform duration-500 ${
          isBlue
            ? 'border-sky-400 shadow-sky-500/40'
            : 'border-rose-400 shadow-rose-500/40'
        } ${unit.focused ? 'scale-110 ring-2 ring-lol-gold/70' : 'scale-100'} ${
          pulse ? 'rift-unit-pulse' : ''
        }`}
        style={{ width: 28, height: 28 }}
      >
        {unit.champion ? (
          <ChampionImage
            name={unit.champion}
            variant="ban"
            locked
            className="!w-full !h-full !ring-0 rounded-full"
          />
        ) : (
          <div
            className={`w-full h-full flex items-center justify-center text-[9px] font-bold ${
              isBlue ? 'bg-sky-950 text-sky-300' : 'bg-rose-950 text-rose-300'
            }`}
          >
            {unit.role.slice(0, 1)}
          </div>
        )}
      </div>
      <div
        className={`absolute -bottom-3 left-1/2 -translate-x-1/2 flex items-center justify-center ${
          isBlue ? 'text-sky-300' : 'text-rose-300'
        }`}
      >
        <RoleIcon
          role={ROLE_TO_ENUM[unit.role] || PlayerRole.MID}
          size={9}
          className="opacity-90 drop-shadow"
        />
      </div>
    </div>
  );
}

function HpBar({
  x,
  y,
  width,
  hp,
  underSiege,
}: {
  x: number;
  y: number;
  width: number;
  hp: number;
  underSiege?: boolean;
}) {
  const h = Math.max(0, Math.min(100, hp)) / 100;
  const barH = 0.7;
  const fill =
    h > 0.55 ? '#4ade80' : h > 0.28 ? '#fbbf24' : '#f87171';
  return (
    <g className={underSiege ? 'rift-hp-siege' : undefined}>
      <rect
        x={x}
        y={y}
        width={width}
        height={barH}
        rx={0.15}
        fill="rgba(0,0,0,0.55)"
        stroke="rgba(255,255,255,0.12)"
        strokeWidth={0.12}
      />
      <rect
        x={x}
        y={y}
        width={Math.max(0.2, width * h)}
        height={barH}
        rx={0.15}
        fill={fill}
        opacity={0.95}
      />
    </g>
  );
}

function StructureLayer({ structures }: { structures: RiftStructure[] }) {
  return (
    <g className="rift-structures">
      {structures.map((s) => {
        const isBlue = s.side === 'BLUE';
        const aliveColor = isBlue ? '#38bdf8' : '#fb7185';
        const deadColor = 'rgba(80,80,80,0.55)';
        const fill = s.alive ? aliveColor : deadColor;
        const showHp = s.alive && s.hp != null && (s.underSiege || (s.hp ?? 100) < 100);

        if (s.kind === 'NEXUS') {
          return (
            <g key={s.id}>
              <circle
                cx={s.x}
                cy={s.y}
                r={s.alive ? 3.4 : 2.6}
                fill={s.alive ? (isBlue ? '#0ea5e9' : '#f43f5e') : deadColor}
                stroke={s.alive ? '#fbbf24' : 'rgba(255,255,255,0.15)'}
                strokeWidth={0.55}
                opacity={s.alive ? 1 : 0.45}
                className={s.justDestroyed ? 'rift-structure-pop' : undefined}
              />
              {!s.alive && (
                <text
                  x={s.x}
                  y={s.y + 0.6}
                  textAnchor="middle"
                  fontSize="2.4"
                  fill="rgba(255,200,80,0.7)"
                >
                  ×
                </text>
              )}
            </g>
          );
        }

        if (s.kind === 'INHIB') {
          return (
            <g key={s.id}>
              {s.underSiege && s.alive && (
                <circle
                  cx={s.x}
                  cy={s.y}
                  r={3.2}
                  fill="none"
                  stroke="rgba(251,191,36,0.55)"
                  strokeWidth={0.35}
                  className="rift-siege-ring"
                />
              )}
              <rect
                x={s.x - 1.6}
                y={s.y - 1.6}
                width="3.2"
                height="3.2"
                rx="0.4"
                fill={s.alive ? (isBlue ? 'rgba(14,165,233,0.75)' : 'rgba(244,63,94,0.75)') : deadColor}
                stroke={s.alive ? '#fbbf24' : 'rgba(255,255,255,0.12)'}
                strokeWidth={0.45}
                opacity={s.alive ? 0.95 : 0.4}
                transform={!s.alive ? `rotate(12 ${s.x} ${s.y})` : undefined}
                className={s.justDestroyed ? 'rift-structure-pop' : undefined}
              />
              {showHp && (
                <HpBar x={s.x - 2.2} y={s.y + 2.2} width={4.4} hp={s.hp ?? 100} underSiege />
              )}
            </g>
          );
        }

        // Torres T1–T3
        const size = s.kind === 'T1' ? 2.0 : s.kind === 'T2' ? 2.2 : 2.4;
        return (
          <g key={s.id}>
            {s.underSiege && s.alive && (
              <circle
                cx={s.x}
                cy={s.y}
                r={size * 1.35}
                fill="none"
                stroke="rgba(251,191,36,0.65)"
                strokeWidth={0.3}
                className="rift-siege-ring"
              />
            )}
            <rect
              x={s.x - size / 2}
              y={s.y - size / 2}
              width={size}
              height={size}
              rx="0.3"
              fill={s.alive ? 'rgba(200,180,100,0.75)' : deadColor}
              stroke={s.alive ? fill : 'rgba(255,255,255,0.12)'}
              strokeWidth={0.35}
              opacity={s.alive ? 0.95 : 0.4}
              className={s.justDestroyed ? 'rift-structure-pop' : undefined}
            />
            {!s.alive && (
              <line
                x1={s.x - size * 0.55}
                y1={s.y - size * 0.55}
                x2={s.x + size * 0.55}
                y2={s.y + size * 0.55}
                stroke="rgba(255,120,100,0.7)"
                strokeWidth="0.45"
              />
            )}
            {showHp && (
              <HpBar
                x={s.x - size * 0.85}
                y={s.y + size * 0.75}
                width={size * 1.7}
                hp={s.hp ?? 100}
                underSiege={s.underSiege}
              />
            )}
          </g>
        );
      })}
    </g>
  );
}

function ContestOverlay({ contest }: { contest: ObjectiveContest }) {
  if (!contest.kind || !contest.active) return null;
  const barW = 14;
  const barH = 1.35;
  const x = contest.x - barW / 2;
  const y = contest.y - 7.2;
  const blueW = (barW * contest.bluePct) / 100;
  return (
    <g className="rift-contest" style={{ pointerEvents: 'none' }}>
      <rect
        x={x - 0.4}
        y={y - 2.2}
        width={barW + 0.8}
        height={barH + 3.4}
        rx={0.5}
        fill="rgba(0,0,0,0.55)"
        stroke="rgba(251,191,36,0.35)"
        strokeWidth={0.25}
      />
      <text
        x={contest.x}
        y={y - 0.55}
        textAnchor="middle"
        fontSize="2.1"
        fill="rgba(251,191,36,0.95)"
        fontFamily="monospace"
      >
        {contest.label}
        {contest.leading ? ` · ${contest.leading === 'BLUE' ? 'B' : 'R'}` : ''}
      </text>
      <rect x={x} y={y + 0.5} width={barW} height={barH} rx={0.25} fill="rgba(30,30,30,0.9)" />
      <rect
        x={x}
        y={y + 0.5}
        width={blueW}
        height={barH}
        rx={0.25}
        fill="rgba(56,189,248,0.9)"
        className="rift-contest-fill"
      />
      <rect
        x={x + blueW}
        y={y + 0.5}
        width={barW - blueW}
        height={barH}
        rx={0.25}
        fill="rgba(251,113,133,0.9)"
      />
    </g>
  );
}

function LanePressureArrows({
  pressure,
}: {
  pressure: Record<string, number> | null | undefined;
}) {
  if (!pressure) return null;
  const anchors: { key: string; x: number; y: number }[] = [
    { key: 'TOP', x: 28, y: 28 },
    { key: 'MID', x: 50, y: 50 },
    { key: 'BOT', x: 72, y: 72 },
  ];
  return (
    <g className="rift-pressure-arrows">
      {anchors.map(({ key, x, y }) => {
        const v = Number(pressure[key] ?? 0);
        if (Math.abs(v) < 14) return null;
        const towardRed = v > 0; // Blue empurra → seta NE
        const len = Math.min(5.5, 1.8 + Math.abs(v) / 28);
        const dx = towardRed ? len * 0.7 : -len * 0.7;
        const dy = towardRed ? -len * 0.7 : len * 0.7;
        const color = towardRed ? 'rgba(56,189,248,0.75)' : 'rgba(251,113,133,0.75)';
        return (
          <g key={key} opacity={0.85}>
            <line
              x1={x - dx * 0.2}
              y1={y - dy * 0.2}
              x2={x + dx}
              y2={y + dy}
              stroke={color}
              strokeWidth={0.55}
              strokeLinecap="round"
              markerEnd="url(#riftArrow)"
            />
          </g>
        );
      })}
    </g>
  );
}

function MiniFeedOverlay({ items }: { items: MiniFeedItem[] }) {
  if (!items.length) return null;
  return (
    <div className="rift-mini-feed" aria-label="Mini feed do mapa">
      {items.map((it, idx) => {
        const side = String(it.side || '').toUpperCase();
        const sideCls =
          side === 'BLUE'
            ? 'border-sky-500/40 bg-sky-950/70 text-sky-100'
            : side === 'RED'
              ? 'border-rose-500/40 bg-rose-950/70 text-rose-100'
              : 'border-white/15 bg-black/70 text-white/80';
        return (
          <div
            key={it.id}
            className={`rift-mini-feed-item ${sideCls}`}
            style={{ animationDelay: `${idx * 40}ms` }}
          >
            <span className="shrink-0 opacity-80">{eventTypeGlyph(it.eventType)}</span>
            <span className="min-w-0 truncate">
              {it.timestamp ? (
                <span className="text-white/35 mr-1 tabular-nums">[{it.timestamp}]</span>
              ) : null}
              {it.text}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function WardLayer({ wards }: { wards: RiftWard[] }) {
  return (
    <g className="rift-wards">
      {wards.map((w) => {
        const isBlue = w.side === 'BLUE';
        const color = isBlue ? '#7dd3fc' : '#fda4af';
        const r = w.control ? 1.35 : 0.95;
        return (
          <g key={w.id} opacity={w.control ? 0.9 : 0.7}>
            {w.control && (
              <circle
                cx={w.x}
                cy={w.y}
                r={r + 1.2}
                fill="none"
                stroke={color}
                strokeWidth="0.25"
                opacity="0.45"
                className="rift-ward-ping"
              />
            )}
            <circle
              cx={w.x}
              cy={w.y}
              r={r}
              fill={color}
              stroke="rgba(0,0,0,0.45)"
              strokeWidth="0.25"
            />
            <circle cx={w.x} cy={w.y} r={r * 0.35} fill="rgba(255,255,255,0.85)" />
          </g>
        );
      })}
    </g>
  );
}

function TrailLayer({
  trails,
}: {
  trails: Record<string, { side: 'BLUE' | 'RED'; points: MapPoint[] }>;
}) {
  return (
    <g className="rift-trails" opacity="0.85">
      {Object.entries(trails).map(([id, trail]) => {
        if (trail.points.length < 2) return null;
        const isBlue = trail.side === 'BLUE';
        const stroke = isBlue ? 'rgba(56,189,248,0.55)' : 'rgba(251,113,133,0.55)';
        // Desenha segmentos com opacidade crescente até a cabeça
        return (
          <g key={id}>
            {trail.points.slice(0, -1).map((p, i) => {
              const next = trail.points[i + 1];
              const t = (i + 1) / trail.points.length;
              return (
                <line
                  key={`${id}-${i}`}
                  x1={p.x}
                  y1={p.y}
                  x2={next.x}
                  y2={next.y}
                  stroke={stroke}
                  strokeWidth={0.35 + t * 0.55}
                  strokeLinecap="round"
                  opacity={0.25 + t * 0.65}
                />
              );
            })}
          </g>
        );
      })}
    </g>
  );
}

/** Minimapa estilizado do Summoner's Rift com unidades, trilhas, wards e estruturas. */
export function SummonersRiftMap({
  phase,
  minute,
  bluePicks,
  redPicks,
  latestEvent,
  eventHistory = [],
  mapStructures: mapStructuresBE = null,
  lanePressure = null,
  winnerSide,
  isVictory,
  blueTeam = 'Blue',
  redTeam = 'Red',
  feedItems = [],
  className = '',
}: SummonersRiftMapProps) {
  const [tick, setTick] = useState(0);
  const prevEventKey = useRef('');
  const [flashLoc, setFlashLoc] = useState<string | null>(null);
  const trailsRef = useRef<Record<string, { side: 'BLUE' | 'RED'; points: MapPoint[] }>>({});
  const [trails, setTrails] = useState<
    Record<string, { side: 'BLUE' | 'RED'; points: MapPoint[] }>
  >({});

  useEffect(() => {
    if (isVictory) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 900);
    return () => clearInterval(id);
  }, [isVictory]);

  useEffect(() => {
    const key = `${latestEvent?.eventType || ''}|${latestEvent?.location || ''}|${latestEvent?.text || ''}`;
    if (!key || key === '|' || key === prevEventKey.current) return;
    prevEventKey.current = key;
    if (latestEvent?.location || latestEvent?.eventType) {
      setFlashLoc(latestEvent.location || latestEvent.eventType || null);
      const t = window.setTimeout(() => setFlashLoc(null), 1200);
      return () => clearTimeout(t);
    }
  }, [latestEvent]);

  // Limpa trilhas ao reiniciar partida (minuto volta a 0)
  useEffect(() => {
    if (minute <= 1) {
      trailsRef.current = {};
      setTrails({});
    }
  }, [minute]);

  const units = useMemo(
    () =>
      resolveRiftUnits({
        phase,
        minute: minute + tick * 0.08,
        bluePicks,
        redPicks,
        latestEvent,
        winnerSide,
        isVictory,
      }),
    [phase, minute, tick, bluePicks, redPicks, latestEvent, winnerSide, isVictory],
  );

  // Atualiza trilhas quando unidades se movem
  useEffect(() => {
    let changed = false;
    const next = { ...trailsRef.current };
    for (const u of units) {
      const prev = next[u.id]?.points || [];
      const last = prev[prev.length - 1];
      const dist = last
        ? Math.hypot(u.x - last.x, u.y - last.y)
        : TRAIL_MIN_DIST + 1;
      if (!last || dist >= TRAIL_MIN_DIST) {
        const points = [...prev, { x: u.x, y: u.y }].slice(-TRAIL_MAX);
        next[u.id] = { side: u.side, points };
        changed = true;
      }
    }
    if (changed) {
      trailsRef.current = next;
      setTrails(next);
    }
  }, [units]);

  const structures = useMemo(() => {
    const fromEvents = resolveStructures(eventHistory, latestEvent, winnerSide, isVictory);
    let merged = fromEvents;
    if (mapStructuresBE?.blue || mapStructuresBE?.red) {
      // Sobrescreve alive a partir do BE (torres por lane)
      merged = fromEvents.map((s) => {
        const sideKey = s.side === 'BLUE' ? 'blue' : 'red';
        const pack = mapStructuresBE[sideKey];
        if (!pack) return s;
        let alive = s.alive;
        if (s.kind === 'NEXUS') {
          alive = (pack.nexus ?? 1) > 0;
        } else if (s.kind === 'INHIB') {
          const left = pack.inhibs ?? 3;
          const destroyedInhibs = Math.max(0, 3 - left);
          const laneOrder = ['TOP', 'MID', 'BOT'];
          const idx = laneOrder.indexOf(s.lane as string);
          alive = idx < 0 ? left > 0 : idx >= destroyedInhibs;
        } else if (s.kind === 'T1' || s.kind === 'T2' || s.kind === 'T3') {
          const lane = (s.lane as string).toLowerCase() as 'top' | 'mid' | 'bot';
          const remaining = pack[lane] ?? 3;
          // remaining 3 = todas vivas; 2 = T1 caiu; 1 = T1+T2; 0 = todas
          const destroyed = Math.max(0, 3 - remaining);
          if (s.kind === 'T1') alive = destroyed < 1;
          else if (s.kind === 'T2') alive = destroyed < 2;
          else alive = destroyed < 3;
        }
        return { ...s, alive };
      });
    }
    // ME-7: HP visual sob siege a partir da pressão de lane
    return applyTowerHpFromPressure(merged, lanePressure);
  }, [eventHistory, latestEvent, winnerSide, isVictory, mapStructuresBE, lanePressure]);

  const wards = useMemo(() => resolveWards(phase, minute + tick * 0.05), [phase, minute, tick]);

  const towerCount = useMemo(() => countAliveTowers(structures), [structures]);

  const contest = useMemo(
    () => resolveObjectiveContest(phase, minute, latestEvent, eventHistory),
    [phase, minute, latestEvent, eventHistory],
  );

  const miniFeed = useMemo(() => {
    if (feedItems.length) return buildMiniFeed(feedItems, 4);
    // fallback: deriva do histórico de mapa
    return buildMiniFeed(
      eventHistory.map((e, i) => ({
        text: e.text,
        eventType: e.eventType,
        side: e.side as string,
        id: `hist-${i}`,
      })),
      3,
    );
  }, [feedItems, eventHistory]);

  const siegeCount = useMemo(
    () => structures.filter((s) => s.alive && s.underSiege).length,
    [structures],
  );

  const eventCaption = useMemo(() => {
    if (!latestEvent) return null;
    const loc = locationLabel(latestEvent.location);
    const type = (latestEvent.eventType || '').replace(/_/g, ' ');
    if (!type && !loc) return null;
    return { type, loc };
  }, [latestEvent]);

  const flash = flashAnchor(flashLoc);

  return (
    <div className={`rift-map-shell ${className}`}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10 bg-black/50">
        <div className="flex items-center gap-2">
          <MapIcon className="w-3.5 h-3.5 text-lol-gold" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-lol-gold-soft">
            Summoner&apos;s Rift
          </span>
        </div>
        <div className="flex items-center gap-2 text-[9px] font-mono text-white/40">
          <span className="text-sky-400/90 truncate max-w-[64px]" title={blueTeam}>
            {blueTeam}
          </span>
          <span className="text-white/20">vs</span>
          <span className="text-rose-400/90 truncate max-w-[64px]" title={redTeam}>
            {redTeam}
          </span>
        </div>
      </div>

      <div className="relative aspect-square w-full max-h-[min(420px,52vw)] mx-auto">
        <svg
          viewBox="0 0 100 100"
          className="absolute inset-0 w-full h-full"
          preserveAspectRatio="xMidYMid meet"
          aria-hidden
        >
          <defs>
            <linearGradient id="riftGrass" x1="0%" y1="100%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#0d2818" />
              <stop offset="45%" stopColor="#143d24" />
              <stop offset="100%" stopColor="#0a1f14" />
            </linearGradient>
            <linearGradient id="riftRiver" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1a4a6e" />
              <stop offset="50%" stopColor="#2a6a9a" />
              <stop offset="100%" stopColor="#1a4a6e" />
            </linearGradient>
            <radialGradient id="blueBaseGlow" cx="15%" cy="85%" r="35%">
              <stop offset="0%" stopColor="rgba(56,189,248,0.35)" />
              <stop offset="100%" stopColor="rgba(56,189,248,0)" />
            </radialGradient>
            <radialGradient id="redBaseGlow" cx="85%" cy="15%" r="35%">
              <stop offset="0%" stopColor="rgba(251,113,133,0.35)" />
              <stop offset="100%" stopColor="rgba(251,113,133,0)" />
            </radialGradient>
            <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="0.8" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <marker
              id="riftArrow"
              markerWidth="4"
              markerHeight="4"
              refX="3"
              refY="2"
              orient="auto"
            >
              <path d="M0,0 L4,2 L0,4 Z" fill="rgba(200,180,100,0.85)" />
            </marker>
          </defs>

          <rect x="0" y="0" width="100" height="100" fill="url(#riftGrass)" rx="1.5" />
          <rect x="0" y="0" width="100" height="100" fill="url(#blueBaseGlow)" />
          <rect x="0" y="0" width="100" height="100" fill="url(#redBaseGlow)" />

          <g stroke="rgba(255,255,255,0.04)" strokeWidth="0.25">
            {[20, 40, 60, 80].map((v) => (
              <g key={v}>
                <line x1={v} y1="0" x2={v} y2="100" />
                <line x1="0" y1={v} x2="100" y2={v} />
              </g>
            ))}
          </g>

          <path
            d="M 8 22 Q 35 40 50 50 Q 65 60 92 78"
            fill="none"
            stroke="url(#riftRiver)"
            strokeWidth="7"
            strokeLinecap="round"
            opacity="0.85"
          />
          <path
            d="M 8 22 Q 35 40 50 50 Q 65 60 92 78"
            fill="none"
            stroke="rgba(120,200,255,0.25)"
            strokeWidth="2"
            strokeLinecap="round"
          />

          <path
            d="M 16 78 L 16 28 L 28 16 L 78 16"
            fill="none"
            stroke="rgba(180,160,100,0.35)"
            strokeWidth="3.2"
            strokeLinejoin="round"
          />
          <path
            d="M 22 78 L 50 50 L 78 22"
            fill="none"
            stroke="rgba(180,160,100,0.45)"
            strokeWidth="3.5"
            strokeLinecap="round"
          />
          <path
            d="M 22 84 L 72 84 L 84 72 L 84 22"
            fill="none"
            stroke="rgba(180,160,100,0.35)"
            strokeWidth="3.2"
            strokeLinejoin="round"
          />

          <ellipse cx="34" cy="54" rx="6" ry="4.5" fill="rgba(20,60,35,0.85)" />
          <ellipse cx="48" cy="70" rx="5.5" ry="4" fill="rgba(20,60,35,0.8)" />
          <ellipse cx="52" cy="30" rx="5.5" ry="4" fill="rgba(20,60,35,0.8)" />
          <ellipse cx="66" cy="46" rx="6" ry="4.5" fill="rgba(20,60,35,0.85)" />

          {/* Bases (halo) — nexus desenhado na layer de estruturas */}
          <circle cx="16" cy="84" r="9" fill="rgba(14,80,140,0.45)" stroke="#38bdf8" strokeWidth="0.55" />
          <circle cx="84" cy="16" r="9" fill="rgba(140,30,50,0.45)" stroke="#fb7185" strokeWidth="0.55" />

          {/* Trilhas sob unidades */}
          <TrailLayer trails={trails} />

          {/* Wards */}
          <WardLayer wards={wards} />

          {/* Torres / inhib / nexus + HP sob siege */}
          <StructureLayer structures={structures} />

          {/* Pressão de lane (setas) */}
          <LanePressureArrows pressure={lanePressure} />

          {/* Dragão / Baron */}
          <g transform="translate(58,66)">
            <circle
              r="4.2"
              fill="rgba(220,80,40,0.35)"
              stroke="#f97316"
              strokeWidth="0.5"
              className={contest.kind === 'DRAGON' && contest.active ? 'rift-obj-pulse' : undefined}
            />
            <text textAnchor="middle" dominantBaseline="central" fontSize="3.6" fill="#fdba74">
              🐉
            </text>
          </g>
          <g transform="translate(42,34)">
            <circle
              r="4.2"
              fill="rgba(120,60,180,0.4)"
              stroke="#c084fc"
              strokeWidth="0.5"
              className={
                (contest.kind === 'BARON' || contest.kind === 'HERALD') && contest.active
                  ? 'rift-obj-pulse'
                  : undefined
              }
            />
            <text textAnchor="middle" dominantBaseline="central" fontSize="3.6" fill="#e9d5ff">
              👑
            </text>
          </g>

          {/* Contest bar do objetivo neutro */}
          <ContestOverlay contest={contest} />

          <text x="12" y="32" fontSize="3" fill="rgba(255,255,255,0.28)" fontFamily="monospace">
            TOP
          </text>
          <text x="46" y="48" fontSize="3" fill="rgba(255,255,255,0.28)" fontFamily="monospace">
            MID
          </text>
          <text x="78" y="88" fontSize="3" fill="rgba(255,255,255,0.28)" fontFamily="monospace">
            BOT
          </text>

          {flashLoc && (
            <circle
              cx={flash.x}
              cy={flash.y}
              r="8"
              fill="none"
              stroke="rgba(200,155,60,0.85)"
              strokeWidth="0.8"
              className="rift-event-ring"
            />
          )}
        </svg>

        <div className="absolute inset-0 pointer-events-none">
          {units.map((u) => (
            <UnitMarker key={u.id} unit={u} />
          ))}
        </div>

        {/* Mini-feed no canto do mapa */}
        {!isVictory && <MiniFeedOverlay items={miniFeed} />}
      </div>

      <div className="px-3 py-2 border-t border-white/10 bg-black/45 space-y-1.5">
        <div className="flex items-center justify-between gap-2 min-h-[18px]">
          <div className="flex items-center gap-3 text-[9px] uppercase tracking-wider text-white/40">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-sky-400" /> Blue
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-rose-400" /> Red
            </span>
            <span className="flex items-center gap-1 text-white/35 normal-case tracking-normal">
              <Eye className="w-3 h-3" /> {wards.length}
            </span>
            {siegeCount > 0 && (
              <span className="text-amber-400/90 normal-case tracking-normal font-mono">
                ⚔ {siegeCount} siege
              </span>
            )}
          </div>
          {eventCaption ? (
            <div className="text-[10px] font-mono text-lol-gold-soft/90 truncate max-w-[55%] text-right animate-fade-in">
              {eventCaption.type}
              {eventCaption.loc ? ` · ${eventCaption.loc}` : ''}
            </div>
          ) : (
            <div className="text-[9px] text-white/30 font-mono">Aguardando ação…</div>
          )}
        </div>
        <div className="flex items-center justify-between text-[9px] font-mono text-white/40">
          <span>
            🏰 <span className="text-sky-400">{towerCount.blue}</span>
            <span className="text-white/25"> · </span>
            <span className="text-rose-400">{towerCount.red}</span> torres
            {contest.active && contest.kind ? (
              <span className="ml-2 text-amber-300/80">
                · {contest.label} {contest.bluePct}/{contest.redPct}
              </span>
            ) : null}
          </span>
          {lanePressure && (
            <span className="text-white/35 truncate max-w-[48%] text-right" title="Pressão de lane (Blue +)">
              press{' '}
              {(['TOP', 'MID', 'BOT'] as const).map((k) => {
                const v = lanePressure[k] ?? 0;
                const cls =
                  v > 8 ? 'text-sky-400' : v < -8 ? 'text-rose-400' : 'text-white/40';
                return (
                  <span key={k} className={`ml-1 ${cls}`}>
                    {k[0]}
                    {v > 0 ? '+' : ''}
                    {Math.round(v)}
                  </span>
                );
              })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
