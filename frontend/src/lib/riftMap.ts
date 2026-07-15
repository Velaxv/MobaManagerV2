/**
 * Lógica de posições no minimapa estilo Summoner's Rift.
 * Coordenadas normalizadas 0–100 (origem canto superior esquerdo).
 * Blue base = canto inferior esquerdo; Red base = canto superior direito.
 */

export type MapSide = 'BLUE' | 'RED';
export type MapRole = 'TOP' | 'JUNGLE' | 'MID' | 'BOT' | 'SUPPORT';
export type MapLocation =
  | 'TOP_LANE'
  | 'MID_LANE'
  | 'BOT_LANE'
  | 'DRAGON'
  | 'BARON'
  | 'RIVER'
  | 'BLUE_BASE'
  | 'RED_BASE'
  | 'BLUE_JG'
  | 'RED_JG'
  | 'HERALD';

export type LaneKey = 'TOP' | 'MID' | 'BOT';
export type StructureKind = 'T1' | 'T2' | 'T3' | 'INHIB' | 'NEXUS';

export interface MapPoint {
  x: number;
  y: number;
}

export interface RiftUnit {
  id: string;
  side: MapSide;
  role: MapRole;
  champion?: string;
  x: number;
  y: number;
  focused: boolean;
  intensity: number;
}

export interface RiftStructure {
  id: string;
  side: MapSide;
  lane: LaneKey | 'BASE';
  kind: StructureKind;
  x: number;
  y: number;
  alive: boolean;
  /** Acabou de cair (flash visual) */
  justDestroyed: boolean;
}

export interface RiftWard {
  id: string;
  side: MapSide;
  x: number;
  y: number;
  /** Controle / pink = maior e mais opaco */
  control: boolean;
}

export interface MapEventHint {
  eventType?: string;
  location?: MapLocation | string;
  role?: MapRole | string;
  side?: MapSide | string;
  intensity?: number;
  text?: string;
}

export interface ResolveRiftInput {
  phase: string;
  minute: number;
  bluePicks: { champion: string; role: string }[];
  redPicks: { champion: string; role: string }[];
  latestEvent?: MapEventHint | null;
  /** Histórico completo (ou janela) para torres/inibidores */
  eventHistory?: MapEventHint[];
  winnerSide?: string | null;
  isVictory?: boolean;
}

const ROLES: MapRole[] = ['TOP', 'JUNGLE', 'MID', 'BOT', 'SUPPORT'];

/** Âncoras do mapa (estilizado, não asset oficial). */
export const RIFT_ANCHORS = {
  blueBase: { x: 14, y: 86 },
  redBase: { x: 86, y: 14 },
  blueNexus: { x: 18, y: 82 },
  redNexus: { x: 82, y: 18 },

  topBlueT1: { x: 18, y: 42 },
  topBlueT2: { x: 17, y: 55 },
  topBlueT3: { x: 16, y: 68 },
  topRiver: { x: 28, y: 28 },
  topRedT1: { x: 42, y: 18 },
  topRedT2: { x: 55, y: 17 },
  topRedT3: { x: 68, y: 16 },

  midBlueT1: { x: 38, y: 62 },
  midBlueT2: { x: 30, y: 70 },
  midBlueT3: { x: 24, y: 76 },
  midCenter: { x: 50, y: 50 },
  midRedT1: { x: 62, y: 38 },
  midRedT2: { x: 70, y: 30 },
  midRedT3: { x: 76, y: 24 },

  botBlueT1: { x: 58, y: 82 },
  botBlueT2: { x: 45, y: 83 },
  botBlueT3: { x: 32, y: 84 },
  botRiver: { x: 72, y: 72 },
  botRedT1: { x: 82, y: 58 },
  botRedT2: { x: 83, y: 45 },
  botRedT3: { x: 84, y: 32 },

  blueTopInhib: { x: 16, y: 74 },
  blueMidInhib: { x: 22, y: 78 },
  blueBotInhib: { x: 28, y: 84 },
  redTopInhib: { x: 74, y: 16 },
  redMidInhib: { x: 78, y: 22 },
  redBotInhib: { x: 84, y: 28 },

  dragon: { x: 58, y: 66 },
  baron: { x: 42, y: 34 },
  herald: { x: 42, y: 34 },

  blueJgTop: { x: 32, y: 52 },
  blueJgBot: { x: 48, y: 72 },
  redJgTop: { x: 52, y: 28 },
  redJgBot: { x: 68, y: 48 },
} as const;

/** Definição estática das estruturas (posição + identidade). */
export const RIFT_STRUCTURE_DEFS: Omit<RiftStructure, 'alive' | 'justDestroyed'>[] = [
  // Blue top
  { id: 'BLUE_TOP_T1', side: 'BLUE', lane: 'TOP', kind: 'T1', x: 18, y: 42 },
  { id: 'BLUE_TOP_T2', side: 'BLUE', lane: 'TOP', kind: 'T2', x: 17, y: 55 },
  { id: 'BLUE_TOP_T3', side: 'BLUE', lane: 'TOP', kind: 'T3', x: 16, y: 68 },
  { id: 'BLUE_TOP_INHIB', side: 'BLUE', lane: 'TOP', kind: 'INHIB', x: 16, y: 74 },
  // Blue mid
  { id: 'BLUE_MID_T1', side: 'BLUE', lane: 'MID', kind: 'T1', x: 38, y: 62 },
  { id: 'BLUE_MID_T2', side: 'BLUE', lane: 'MID', kind: 'T2', x: 30, y: 70 },
  { id: 'BLUE_MID_T3', side: 'BLUE', lane: 'MID', kind: 'T3', x: 24, y: 76 },
  { id: 'BLUE_MID_INHIB', side: 'BLUE', lane: 'MID', kind: 'INHIB', x: 22, y: 78 },
  // Blue bot
  { id: 'BLUE_BOT_T1', side: 'BLUE', lane: 'BOT', kind: 'T1', x: 58, y: 82 },
  { id: 'BLUE_BOT_T2', side: 'BLUE', lane: 'BOT', kind: 'T2', x: 45, y: 83 },
  { id: 'BLUE_BOT_T3', side: 'BLUE', lane: 'BOT', kind: 'T3', x: 32, y: 84 },
  { id: 'BLUE_BOT_INHIB', side: 'BLUE', lane: 'BOT', kind: 'INHIB', x: 28, y: 84 },
  { id: 'BLUE_NEXUS', side: 'BLUE', lane: 'BASE', kind: 'NEXUS', x: 18, y: 82 },
  // Red top
  { id: 'RED_TOP_T1', side: 'RED', lane: 'TOP', kind: 'T1', x: 42, y: 18 },
  { id: 'RED_TOP_T2', side: 'RED', lane: 'TOP', kind: 'T2', x: 55, y: 17 },
  { id: 'RED_TOP_T3', side: 'RED', lane: 'TOP', kind: 'T3', x: 68, y: 16 },
  { id: 'RED_TOP_INHIB', side: 'RED', lane: 'TOP', kind: 'INHIB', x: 74, y: 16 },
  // Red mid
  { id: 'RED_MID_T1', side: 'RED', lane: 'MID', kind: 'T1', x: 62, y: 38 },
  { id: 'RED_MID_T2', side: 'RED', lane: 'MID', kind: 'T2', x: 70, y: 30 },
  { id: 'RED_MID_T3', side: 'RED', lane: 'MID', kind: 'T3', x: 76, y: 24 },
  { id: 'RED_MID_INHIB', side: 'RED', lane: 'MID', kind: 'INHIB', x: 78, y: 22 },
  // Red bot
  { id: 'RED_BOT_T1', side: 'RED', lane: 'BOT', kind: 'T1', x: 82, y: 58 },
  { id: 'RED_BOT_T2', side: 'RED', lane: 'BOT', kind: 'T2', x: 83, y: 45 },
  { id: 'RED_BOT_T3', side: 'RED', lane: 'BOT', kind: 'T3', x: 84, y: 32 },
  { id: 'RED_BOT_INHIB', side: 'RED', lane: 'BOT', kind: 'INHIB', x: 84, y: 28 },
  { id: 'RED_NEXUS', side: 'RED', lane: 'BASE', kind: 'NEXUS', x: 82, y: 18 },
];

const TOWER_ORDER: StructureKind[] = ['T1', 'T2', 'T3'];

function clamp(n: number, lo = 6, hi = 94) {
  return Math.max(lo, Math.min(hi, n));
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function mix(a: MapPoint, b: MapPoint, t: number): MapPoint {
  return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) };
}

function jitter(point: MapPoint, seed: number, amp = 1.2): MapPoint {
  const s = Math.sin(seed * 12.9898) * 43758.5453;
  const frac = s - Math.floor(s);
  const s2 = Math.sin(seed * 78.233) * 43758.5453;
  const frac2 = s2 - Math.floor(s2);
  return {
    x: clamp(point.x + (frac - 0.5) * amp * 2),
    y: clamp(point.y + (frac2 - 0.5) * amp * 2),
  };
}

function normalizeRole(role: string | undefined): MapRole | null {
  if (!role) return null;
  const r = role.toUpperCase();
  if (r === 'TOP' || r === 'JUNGLE' || r === 'MID' || r === 'BOT' || r === 'SUPPORT') {
    return r;
  }
  return null;
}

function parseRoleFromText(text?: string): MapRole | null {
  if (!text) return null;
  const m = text.match(/\[(TOP|JUNGLE|MID|BOT|SUPPORT)\]/i);
  return m ? (m[1].toUpperCase() as MapRole) : null;
}

export function parseLocationFromEvent(ev?: MapEventHint | null): MapLocation | null {
  if (!ev) return null;
  if (ev.location) {
    return String(ev.location).toUpperCase() as MapLocation;
  }
  const type = (ev.eventType || '').toUpperCase();
  const text = (ev.text || '').toLowerCase();
  if (type === 'DRAGON_SECURED' || text.includes('dragão') || text.includes('dragon')) return 'DRAGON';
  if (type === 'BARON_SECURED' || text.includes('baron')) return 'BARON';
  if (type === 'TEAMFIGHT' || text.includes('ace') || text.includes('teamfight')) return 'MID_LANE';
  if (type === 'SNOWBALL' || text.includes('inibidor')) return 'RED_BASE';
  if (type === 'VICTORY') return 'MID_LANE';
  if (type === 'TURRET_DESTROYED') {
    if (text.includes('mid')) return 'MID_LANE';
    if (text.includes('top') || text.includes('superior')) return 'TOP_LANE';
    if (text.includes('bot') || text.includes('inferior') || text.includes('lateral')) return 'BOT_LANE';
    return 'MID_LANE';
  }
  if (type === 'SOLO_KILL' || type === 'FARM' || type === 'COACH_COMM') {
    const role = normalizeRole(ev.role as string) || parseRoleFromText(ev.text);
    if (role === 'TOP') return 'TOP_LANE';
    if (role === 'MID') return 'MID_LANE';
    if (role === 'BOT' || role === 'SUPPORT') return 'BOT_LANE';
    if (role === 'JUNGLE') return 'RIVER';
  }
  return null;
}

function locationToLane(loc: MapLocation | null): LaneKey {
  if (loc === 'TOP_LANE') return 'TOP';
  if (loc === 'BOT_LANE') return 'BOT';
  return 'MID';
}

function basePosition(
  side: MapSide,
  role: MapRole,
  phase: string,
  minute: number,
): MapPoint {
  const A = RIFT_ANCHORS;
  const isBlue = side === 'BLUE';
  const p = phase.toUpperCase();
  const late = p.includes('LATE') || p === 'COMPLETE' || p === 'FINISHED';
  const mid = p.includes('MID');
  const early = !late && !mid;

  const tEarly = Math.min(1, minute / 14);
  const tMid = Math.min(1, Math.max(0, (minute - 14) / 14));
  const tLate = Math.min(1, Math.max(0, (minute - 28) / 12));

  if (role === 'TOP') {
    if (early) {
      return isBlue
        ? mix(A.topBlueT1, A.topRiver, 0.15 + tEarly * 0.25)
        : mix(A.topRedT1, A.topRiver, 0.15 + tEarly * 0.25);
    }
    if (mid) {
      return mix(A.topRiver, A.midCenter, 0.2 + tMid * 0.3);
    }
    return isBlue
      ? mix(A.midCenter, A.redNexus, 0.15 + tLate * 0.35)
      : mix(A.midCenter, A.blueNexus, 0.15 + tLate * 0.35);
  }

  if (role === 'MID') {
    if (early) {
      return isBlue
        ? mix(A.midBlueT1, A.midCenter, 0.2 + tEarly * 0.25)
        : mix(A.midRedT1, A.midCenter, 0.2 + tEarly * 0.25);
    }
    if (mid) return mix(isBlue ? A.midBlueT1 : A.midRedT1, A.midCenter, 0.55);
    return isBlue
      ? mix(A.midCenter, A.redNexus, 0.2 + tLate * 0.4)
      : mix(A.midCenter, A.blueNexus, 0.2 + tLate * 0.4);
  }

  if (role === 'BOT') {
    if (early) {
      return isBlue
        ? mix(A.botBlueT1, A.botRiver, 0.2 + tEarly * 0.2)
        : mix(A.botRedT1, A.botRiver, 0.2 + tEarly * 0.2);
    }
    if (mid) {
      return mix(A.botRiver, A.dragon, 0.35 + tMid * 0.3);
    }
    return isBlue
      ? mix(A.midCenter, A.redNexus, 0.25 + tLate * 0.35)
      : mix(A.midCenter, A.blueNexus, 0.25 + tLate * 0.35);
  }

  if (role === 'SUPPORT') {
    if (early) {
      const bot = basePosition(side, 'BOT', phase, minute);
      const base = isBlue ? A.blueBase : A.redBase;
      return mix(bot, base, 0.12);
    }
    if (mid) {
      return mix(A.dragon, A.midCenter, isBlue ? 0.3 : 0.35);
    }
    return isBlue
      ? mix(A.midCenter, A.redNexus, 0.22 + tLate * 0.3)
      : mix(A.midCenter, A.blueNexus, 0.22 + tLate * 0.3);
  }

  // JUNGLE
  if (early) {
    const cycle = (minute % 6) / 6;
    if (isBlue) {
      return cycle < 0.5
        ? mix(A.blueJgTop, A.blueJgBot, cycle * 2)
        : mix(A.blueJgBot, A.topRiver, (cycle - 0.5) * 2);
    }
    return cycle < 0.5
      ? mix(A.redJgTop, A.redJgBot, cycle * 2)
      : mix(A.redJgBot, A.botRiver, (cycle - 0.5) * 2);
  }
  if (mid) {
    const cycle = (minute % 4) / 4;
    return isBlue ? mix(A.dragon, A.herald, cycle) : mix(A.herald, A.dragon, cycle);
  }
  return isBlue
    ? mix(A.midCenter, A.baron, 0.4 + tLate * 0.2)
    : mix(A.midCenter, A.baron, 0.45 + tLate * 0.2);
}

function locationAnchor(loc: MapLocation, side?: MapSide | string | null): MapPoint {
  const A = RIFT_ANCHORS;
  switch (loc) {
    case 'TOP_LANE':
      return A.topRiver;
    case 'MID_LANE':
      return A.midCenter;
    case 'BOT_LANE':
      return A.botRiver;
    case 'DRAGON':
      return A.dragon;
    case 'BARON':
    case 'HERALD':
      return A.baron;
    case 'RIVER':
      return A.midCenter;
    case 'BLUE_BASE':
      return A.blueNexus;
    case 'RED_BASE':
      return A.redNexus;
    case 'BLUE_JG':
      return A.blueJgTop;
    case 'RED_JG':
      return A.redJgTop;
    default:
      return side === 'RED' ? A.redNexus : A.blueNexus;
  }
}

function championFor(
  picks: { champion: string; role: string }[],
  role: MapRole,
): string | undefined {
  return picks.find((p) => p.role?.toUpperCase() === role)?.champion;
}

function roleOffset(role: MapRole, side: MapSide): MapPoint {
  const sign = side === 'BLUE' ? 1 : -1;
  const table: Record<MapRole, MapPoint> = {
    TOP: { x: -4 * sign, y: -5 },
    JUNGLE: { x: -2 * sign, y: 1 },
    MID: { x: 0, y: 0 },
    BOT: { x: 4 * sign, y: 5 },
    SUPPORT: { x: 5 * sign, y: 3 },
  };
  return table[role];
}

/**
 * Resolve as 10 unidades no mapa a partir da fase, minuto e evento recente.
 */
export function resolveRiftUnits(input: ResolveRiftInput): RiftUnit[] {
  const {
    phase,
    minute,
    bluePicks,
    redPicks,
    latestEvent,
    winnerSide,
    isVictory,
  } = input;

  const location = parseLocationFromEvent(latestEvent);
  const focusRole =
    normalizeRole(latestEvent?.role as string) ||
    parseRoleFromText(latestEvent?.text) ||
    null;
  const eventType = (latestEvent?.eventType || '').toUpperCase();
  const eventSide = (latestEvent?.side || '').toUpperCase() as MapSide | '';
  const intensity = Math.min(1, Math.max(0, latestEvent?.intensity ?? (eventType ? 0.75 : 0)));

  const isObjective =
    eventType === 'DRAGON_SECURED' ||
    eventType === 'BARON_SECURED' ||
    eventType === 'TEAMFIGHT' ||
    eventType === 'SNOWBALL' ||
    eventType === 'VICTORY';
  const isKill = eventType === 'SOLO_KILL';
  const isTurret = eventType === 'TURRET_DESTROYED';
  const isFarm = eventType === 'FARM' || eventType === 'COACH_COMM';

  const units: RiftUnit[] = [];

  for (const side of ['BLUE', 'RED'] as MapSide[]) {
    const picks = side === 'BLUE' ? bluePicks : redPicks;
    for (const role of ROLES) {
      let pos = basePosition(side, role, phase, minute);
      let focused = false;
      let unitIntensity = 0;

      if (isVictory && winnerSide) {
        const win = winnerSide.toUpperCase() === 'BLUE' ? 'BLUE' : 'RED';
        if (side === win) {
          pos = mix(pos, locationAnchor(win === 'BLUE' ? 'RED_BASE' : 'BLUE_BASE'), 0.55);
        } else {
          pos = mix(pos, locationAnchor(side === 'BLUE' ? 'BLUE_BASE' : 'RED_BASE'), 0.45);
        }
        focused = true;
        unitIntensity = 0.9;
      } else if (location && (isObjective || isKill || isTurret || isFarm)) {
        const anchor = locationAnchor(location as MapLocation, eventSide || side);

        if (isObjective) {
          const pull =
            side === (eventSide || (latestEvent?.side as MapSide)) ? 0.72 : 0.55;
          const off = roleOffset(role, side);
          pos = {
            x: clamp(lerp(pos.x, anchor.x, pull) + off.x * 0.35),
            y: clamp(lerp(pos.y, anchor.y, pull) + off.y * 0.35),
          };
          focused = true;
          unitIntensity = intensity;
        } else if (
          (isKill && focusRole === role) ||
          (isTurret && (role === focusRole || role === 'JUNGLE' || role === 'MID')) ||
          (isFarm && focusRole === role)
        ) {
          const pull = isKill ? 0.85 : isTurret ? 0.7 : 0.55;
          pos = mix(pos, anchor, pull);
          const off = side === 'BLUE' ? -2.2 : 2.2;
          pos = { x: clamp(pos.x + off), y: clamp(pos.y + off * 0.4) };
          focused = true;
          unitIntensity = intensity;
        } else if (role === 'JUNGLE' && (isKill || isTurret) && intensity > 0.5) {
          pos = mix(pos, anchor, 0.4);
          unitIntensity = intensity * 0.5;
        }
      }

      const seed = minute * 10 + ROLES.indexOf(role) + (side === 'BLUE' ? 0 : 5) + intensity * 3;
      pos = jitter(pos, seed, focused ? 0.6 : 1.4);

      units.push({
        id: `${side}-${role}`,
        side,
        role,
        champion: championFor(picks, role),
        x: pos.x,
        y: pos.y,
        focused,
        intensity: unitIntensity,
      });
    }
  }

  return units;
}

function destroyNextTower(
  state: Map<string, RiftStructure>,
  ownerSide: MapSide,
  lane: LaneKey,
  justId: string | null,
): string | null {
  for (const kind of TOWER_ORDER) {
    const id = `${ownerSide}_${lane}_${kind}`;
    const s = state.get(id);
    if (s?.alive) {
      s.alive = false;
      s.justDestroyed = justId === null || justId === id;
      return id;
    }
  }
  // Todas as torres da lane caíram → inibidor
  const inhibId = `${ownerSide}_${lane}_INHIB`;
  const inhib = state.get(inhibId);
  if (inhib?.alive) {
    inhib.alive = false;
    inhib.justDestroyed = justId === null || justId === inhibId;
    return inhibId;
  }
  return null;
}

/**
 * Deriva estado de torres/inibidores/nexus a partir do histórico de eventos.
 * side no evento = time que causou a destruição (atacante).
 */
export function resolveStructures(
  eventHistory: MapEventHint[] = [],
  latestEvent?: MapEventHint | null,
  winnerSide?: string | null,
  isVictory?: boolean,
): RiftStructure[] {
  const state = new Map<string, RiftStructure>();
  for (const def of RIFT_STRUCTURE_DEFS) {
    state.set(def.id, { ...def, alive: true, justDestroyed: false });
  }

  let lastDestroyedId: string | null = null;

  const applyTurret = (ev: MapEventHint) => {
    const attacker = (ev.side || '').toUpperCase() as MapSide;
    const owner: MapSide = attacker === 'BLUE' ? 'RED' : attacker === 'RED' ? 'BLUE' : 'RED';
    const lane = locationToLane(parseLocationFromEvent(ev));
    lastDestroyedId = destroyNextTower(state, owner, lane, null);
  };

  const applySnowball = (ev: MapEventHint) => {
    const attacker = (ev.side || '').toUpperCase() as MapSide;
    if (attacker !== 'BLUE' && attacker !== 'RED') return;
    const owner: MapSide = attacker === 'BLUE' ? 'RED' : 'BLUE';
    // Derruba progressão mid + inib mid (snowball clássico)
    for (const lane of ['MID', 'TOP', 'BOT'] as LaneKey[]) {
      for (let i = 0; i < 4; i++) destroyNextTower(state, owner, lane, null);
    }
    const midInhib = state.get(`${owner}_MID_INHIB`);
    if (midInhib) {
      midInhib.alive = false;
      lastDestroyedId = midInhib.id;
    }
  };

  for (const ev of eventHistory) {
    const type = (ev.eventType || '').toUpperCase();
    if (type === 'TURRET_DESTROYED') applyTurret(ev);
    else if (type === 'SNOWBALL') applySnowball(ev);
  }

  if (isVictory && winnerSide) {
    const win = winnerSide.toUpperCase() === 'BLUE' ? 'BLUE' : 'RED';
    const lose: MapSide = win === 'BLUE' ? 'RED' : 'BLUE';
    for (const lane of ['TOP', 'MID', 'BOT'] as LaneKey[]) {
      for (let i = 0; i < 4; i++) destroyNextTower(state, lose, lane, null);
    }
    const nexus = state.get(`${lose}_NEXUS`);
    if (nexus) {
      nexus.alive = false;
      lastDestroyedId = nexus.id;
    }
  }

  // Marca justDestroyed só no último alvo relevante
  if (latestEvent) {
    const type = (latestEvent.eventType || '').toUpperCase();
    if (type === 'TURRET_DESTROYED' || type === 'SNOWBALL' || type === 'VICTORY') {
      for (const s of state.values()) {
        s.justDestroyed = s.id === lastDestroyedId && !s.alive;
      }
      // Se não achamos id, marca a última estrutura morta do lado atacado
      if (!lastDestroyedId) {
        const attacker = (latestEvent.side || winnerSide || '').toUpperCase();
        const owner: MapSide = attacker === 'BLUE' ? 'RED' : 'BLUE';
        const dead = [...state.values()].filter((s) => s.side === owner && !s.alive);
        const last = dead[dead.length - 1];
        if (last) last.justDestroyed = true;
      }
    }
  }

  return [...state.values()];
}

/**
 * Wards determinísticas por fase/minuto (visão de suporte + jungle).
 */
export function resolveWards(phase: string, minute: number): RiftWard[] {
  const p = phase.toUpperCase();
  const late = p.includes('LATE') || p === 'COMPLETE' || p === 'FINISHED';
  const mid = p.includes('MID');
  const wards: RiftWard[] = [];

  // Seeds estáveis por "slot" de ward que rotacionam com o minuto
  const slot = Math.floor(minute / 3) % 4;

  const blueSpots: { x: number; y: number; control?: boolean }[] = mid || late
    ? [
        { x: 44, y: 62 }, // river bot side
        { x: 36, y: 48 }, // raptor / pixel
        { x: 52, y: 58, control: true }, // dragon pit
        { x: 40, y: 38 }, // near baron approach
      ]
    : [
        { x: 62, y: 78 }, // bot tri
        { x: 48, y: 70 }, // blue krugs river
        { x: 34, y: 56 }, // blue raptors
        { x: 28, y: 40 }, // top river blue
      ];

  const redSpots: { x: number; y: number; control?: boolean }[] = mid || late
    ? [
        { x: 56, y: 38 },
        { x: 64, y: 52 },
        { x: 48, y: 42, control: true }, // baron
        { x: 60, y: 62 },
      ]
    : [
        { x: 38, y: 22 },
        { x: 52, y: 30 },
        { x: 66, y: 44 },
        { x: 72, y: 60 },
      ];

  // 2–3 wards por time, rotacionando slots
  const count = late ? 3 : mid ? 3 : 2;
  for (let i = 0; i < count; i++) {
    const bi = (slot + i) % blueSpots.length;
    const ri = (slot + i + 1) % redSpots.length;
    const b = blueSpots[bi];
    const r = redSpots[ri];
    // Micro offset por minuto para “piscar” troca de ward
    const j = minute * 0.15 + i;
    wards.push({
      id: `BLUE_W${i}`,
      side: 'BLUE',
      x: clamp(b.x + Math.sin(j) * 0.8, 8, 92),
      y: clamp(b.y + Math.cos(j) * 0.8, 8, 92),
      control: !!b.control && (mid || late),
    });
    wards.push({
      id: `RED_W${i}`,
      side: 'RED',
      x: clamp(r.x + Math.cos(j) * 0.8, 8, 92),
      y: clamp(r.y + Math.sin(j) * 0.8, 8, 92),
      control: !!r.control && (mid || late),
    });
  }

  return wards;
}

/** Contagem rápida de torres vivas por lado (UI). */
export function countAliveTowers(structures: RiftStructure[]): { blue: number; red: number } {
  let blue = 0;
  let red = 0;
  for (const s of structures) {
    if (!s.alive) continue;
    if (s.kind === 'T1' || s.kind === 'T2' || s.kind === 'T3') {
      if (s.side === 'BLUE') blue += 1;
      else red += 1;
    }
  }
  return { blue, red };
}

export function locationLabel(loc?: string | null): string {
  if (!loc) return '';
  const map: Record<string, string> = {
    TOP_LANE: 'Top',
    MID_LANE: 'Mid',
    BOT_LANE: 'Bot',
    DRAGON: 'Dragão',
    BARON: 'Baron',
    HERALD: 'Arauto',
    RIVER: 'Rio',
    BLUE_BASE: 'Base Blue',
    RED_BASE: 'Base Red',
    BLUE_JG: 'JG Blue',
    RED_JG: 'JG Red',
  };
  return map[loc.toUpperCase()] || loc;
}

/** Âncora visual do flash de evento. */
export function flashAnchor(flashLoc: string | null | undefined): MapPoint {
  if (!flashLoc) return { x: 50, y: 50 };
  const u = flashLoc.toUpperCase();
  if (u.includes('DRAGON')) return RIFT_ANCHORS.dragon;
  if (u.includes('BARON') || u.includes('HERALD')) return RIFT_ANCHORS.baron;
  if (u.includes('TOP')) return RIFT_ANCHORS.topRiver;
  if (u.includes('BOT')) return RIFT_ANCHORS.botRiver;
  if (u.includes('RED')) return RIFT_ANCHORS.redNexus;
  if (u.includes('BLUE')) return RIFT_ANCHORS.blueNexus;
  return RIFT_ANCHORS.midCenter;
}
