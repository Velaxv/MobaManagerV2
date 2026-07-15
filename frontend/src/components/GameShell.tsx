import { useMemo, useState, type ReactNode } from 'react';
import {
  LayoutDashboard,
  Users,
  Swords,
  Trophy,
  UserCircle2,
  TableProperties,
  ChevronRight,
  Radio,
  Save,
  Loader2,
  FileCode2,
  Dumbbell,
  Briefcase,
  Landmark,
} from 'lucide-react';
import { useGameStore } from '../store/useGameStore';
import { getOrgBrand, orgCrestStyle } from '../lib/orgBrands';
import { badgeForScreen, type HubAlertInput } from '../lib/hubAlerts';
import type { AppScreen } from '../types/screens';

/**
 * Navegação inspirada em management sims (FM):
 * - categorias no sidebar (Rotina / Time / Clube / Competição)
 * - Competição: ações de partida primeiro (Draft → Live → Tabela → Patch)
 * - Painel = inbox; badges só em alertas reais
 */
const NAV: {
  id: AppScreen;
  label: string;
  short: string;
  icon: typeof LayoutDashboard;
  hint?: string;
  group: 'routine' | 'squad' | 'club' | 'compete';
  /** 1 = ação prioritária no grupo */
  priority?: number;
}[] = [
  {
    id: 'DASHBOARD',
    label: 'Painel',
    short: 'Home',
    icon: LayoutDashboard,
    hint: 'O que fazer agora',
    group: 'routine',
    priority: 1,
  },
  {
    id: 'TRAINING',
    label: 'Treino',
    short: 'Treino',
    icon: Dumbbell,
    hint: 'Plano & moral',
    group: 'routine',
    priority: 2,
  },
  {
    id: 'SQUAD',
    label: 'Elenco',
    short: 'Elenco',
    icon: UserCircle2,
    hint: 'Plantel',
    group: 'squad',
    priority: 1,
  },
  {
    id: 'STAFF',
    label: 'Staff',
    short: 'Staff',
    icon: Briefcase,
    hint: 'Comissão',
    group: 'squad',
    priority: 2,
  },
  {
    id: 'ORG',
    label: 'Organização',
    short: 'Org',
    icon: Landmark,
    hint: 'Board, $ e sede',
    group: 'club',
    priority: 1,
  },
  {
    id: 'MARKET',
    label: 'Mercado',
    short: 'Mercado',
    icon: Users,
    hint: 'Transfers',
    group: 'club',
    priority: 2,
  },
  // Competição: match actions first
  {
    id: 'DRAFT',
    label: 'Draft',
    short: 'Draft',
    icon: Swords,
    hint: 'Picks & bans',
    group: 'compete',
    priority: 1,
  },
  {
    id: 'SIMULATION',
    label: 'Partida',
    short: 'Live',
    icon: Trophy,
    hint: 'Ao vivo',
    group: 'compete',
    priority: 2,
  },
  {
    id: 'STANDINGS',
    label: 'Tabela',
    short: 'Tabela',
    icon: TableProperties,
    hint: 'Classificação',
    group: 'compete',
    priority: 3,
  },
  {
    id: 'PATCH',
    label: 'Patch',
    short: 'Patch',
    icon: FileCode2,
    hint: 'Meta',
    group: 'compete',
    priority: 4,
  },
];

const GROUP_LABELS: Record<(typeof NAV)[number]['group'], string> = {
  routine: '1 · Rotina',
  squad: '2 · Time',
  club: '3 · Clube',
  compete: '4 · Competição',
};

interface GameShellProps {
  children: ReactNode;
}

function teamInitials(name: string) {
  const parts = name.replace(/[^\w\s]/g, '').trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export function GameShell({ children }: GameShellProps) {
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const currentScreen = useGameStore((s) => s.currentScreen) as AppScreen;
  const setCurrentScreen = useGameStore((s) => s.setCurrentScreen);
  const manager = useGameStore((s) => s.manager);
  const myTeamName = useGameStore((s) => s.myTeamName);
  const myBudget = useGameStore((s) => s.myBudget);
  const currentWeek = useGameStore((s) => s.currentWeek);
  const currentDayIndex = useGameStore((s) => s.currentDayIndex);
  const calendar = useGameStore((s) => s.calendar);
  const splitPhase = useGameStore((s) => s.splitPhase);
  const activeMatch = useGameStore((s) => s.activeMatch);
  const standings = useGameStore((s) => s.standings);
  const myPlayers = useGameStore((s) => s.myPlayers);
  const saveCareer = useGameStore((s) => s.saveCareer);

  const dayLabel = calendar[currentDayIndex]?.dayOfWeek ?? 'SEG';
  const dayType = calendar[currentDayIndex]?.type;
  const matchPending = activeMatch && activeMatch.currentPhase === 'DRAFT';
  const matchLive =
    activeMatch?.matchId &&
    activeMatch.currentPhase !== 'DRAFT' &&
    activeMatch.currentPhase !== 'DRAFT_COMPLETE' &&
    activeMatch.currentPhase !== 'COMPLETE' &&
    activeMatch.currentPhase !== 'FINISHED';

  const myRank = standings.findIndex((s) => s.team_name === myTeamName) + 1;
  const myStanding = standings.find((s) => s.team_name === myTeamName);
  const burnoutCount = myPlayers.filter((p) => p.burnoutMeter > 70 || p.visualFatigue > 70).length;
  const brand = getOrgBrand(myTeamName);
  const crestStyle = orgCrestStyle(myTeamName);
  const crestTag = brand.tag !== '???' ? brand.tag : teamInitials(myTeamName);

  const finance = useGameStore((s) => s.finance);
  const lastBoardReview = useGameStore((s) => s.lastBoardReview);
  const offseasonContracts = useGameStore((s) => s.offseasonContracts);
  const scouting = useGameStore((s) => s.scouting);

  const alertInput: HubAlertInput = useMemo(
    () => ({
      burnoutCount,
      matchPending: !!matchPending,
      matchLive: !!matchLive,
      financeHealth: finance?.health ?? null,
      boardOnTrack:
        lastBoardReview && !lastBoardReview.skipped ? lastBoardReview.on_track : null,
      boardFired: !!lastBoardReview?.fired,
      boardMessage: lastBoardReview?.message,
      renewalsNeeded: offseasonContracts.filter((c) => c.needs_renewal).length,
      isOffseason: String(splitPhase || '').includes('OFFSEASON'),
      scoutingActive: !!scouting?.assignment,
      scoutingProgress: scouting?.assignment?.progress ?? null,
    }),
    [
      burnoutCount,
      matchPending,
      matchLive,
      finance?.health,
      lastBoardReview,
      offseasonContracts,
      splitPhase,
      scouting,
    ],
  );

  const groups = (['routine', 'squad', 'club', 'compete'] as const).map((g) => ({
    key: g,
    label: GROUP_LABELS[g],
    items: NAV.filter((n) => n.group === g).sort(
      (a, b) => (a.priority ?? 99) - (b.priority ?? 99),
    ),
  }));

  const renderNav = (items: typeof NAV) =>
    items.map((item) => {
      const active = currentScreen === item.id;
      const Icon = item.icon;
      const badge = badgeForScreen(item.id, alertInput);
      const toneCls =
        badge?.tone === 'critical'
          ? 'hub-nav-badge-critical'
          : badge?.tone === 'warning'
            ? 'hub-nav-badge-warning'
            : 'hub-nav-badge-info';
      return (
        <button
          key={item.id}
          onClick={() => setCurrentScreen(item.id as never)}
          className={`hub-nav-item group ${active ? 'hub-nav-item-active' : 'hub-nav-item-idle'}`}
        >
          <Icon
            className={`w-4 h-4 shrink-0 ${active ? 'text-lol-hq-cyan' : 'text-white/35 group-hover:text-lol-hq-cyan/80'}`}
          />
          <span className="flex-1 min-w-0">
            <span className="block text-xs font-semibold uppercase tracking-wide">{item.label}</span>
            <span className="block text-[10px] text-white/30 normal-case tracking-normal truncate">
              {item.hint}
            </span>
          </span>
          {badge?.show && (
            <span className={`hub-nav-badge ${toneCls}`} aria-label="alerta">
              {badge.count != null && badge.count > 0 ? badge.count : '!'}
            </span>
          )}
          {active && <ChevronRight className="w-3.5 h-3.5 text-lol-hq-cyan/70 shrink-0" />}
        </button>
      );
    });

  return (
    <div className="hub-shell">
      <aside className="hub-sidebar">
        <div className="px-4 py-4 border-b border-lol-hq-cyan/15 relative">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-lol-hq-cyan/50 via-transparent to-lol-hq-orange/30" />
          <div className="flex items-center gap-3">
            <div className="team-crest text-xs" style={crestStyle}>
              {crestTag.slice(0, 3)}
            </div>
            <div>
              <div className="font-display font-bold text-sm tracking-[0.14em] text-white uppercase leading-tight">
                War Room
              </div>
              <div className="text-[10px] text-lol-hq-cyan/70 uppercase tracking-[0.22em] font-mono">
                CBLOL 2026
              </div>
            </div>
          </div>
        </div>

        <div
          className="px-3 py-3 border-b border-white/5 bg-black/30 backdrop-blur-sm"
          style={{ boxShadow: `inset 3px 0 0 ${brand.primary}` }}
        >
          <div className="flex items-center gap-2.5">
            <div className="team-crest !w-11 !h-11 text-sm font-bold" style={crestStyle}>
              {crestTag.slice(0, 3)}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-bold text-white truncate tracking-wide">{myTeamName}</div>
              {manager && (
                <div className="text-[10px] text-white/40 truncate font-mono">COACH · {manager.name}</div>
              )}
              <div className="text-[10px] font-mono text-lol-hq-cyan/90 mt-0.5">
                {myStanding
                  ? `#${myRank} · ${myStanding.wins}V-${myStanding.losses}D`
                  : 'Sem standings'}
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 py-2 px-2 overflow-y-auto">
          {groups.map((g, idx) => (
            <div key={g.key}>
              <p
                className={`px-2 pb-1.5 text-[9px] uppercase tracking-[0.2em] text-white/25 font-semibold ${
                  idx === 0 ? 'pt-1' : 'pt-3'
                }`}
              >
                {g.label}
              </p>
              <div className="space-y-0.5">{renderNav(g.items)}</div>
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-lol-hq-cyan/12 space-y-2 bg-black/35">
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-white/35 uppercase tracking-wider">Budget</span>
            <span className="text-emerald-400 font-bold">€{(myBudget / 1_000_000).toFixed(2)}M</span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-white/35 uppercase tracking-wider">Roster</span>
            <span className="text-white/70">{myPlayers.length} atletas</span>
          </div>
          {burnoutCount > 0 && (
            <div className="text-[10px] text-lol-hq-orange font-mono flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-lol-hq-orange animate-neon-breathe" />
              {burnoutCount} alerta(s) fadiga
            </div>
          )}
        </div>
      </aside>

      <div className="hub-main">
        {/* Sede HQ borrada — profundidade atrás do glass */}
        <div className="hub-facility" aria-hidden>
          <div className="hub-facility-scene" />
          <div className="hub-facility-scanlines" />
          <div className="hub-facility-vignette" />
        </div>

        <header className="hub-topbar">
          <div className="px-3 sm:px-5 py-2.5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div
                className="md:hidden team-crest !w-8 !h-8 text-[10px] font-bold"
                style={crestStyle}
              >
                {crestTag.slice(0, 3)}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-display font-bold text-sm sm:text-base text-white tracking-wide truncate">
                    {myTeamName}
                  </span>
                  {manager && (
                    <span className="text-[10px] sm:text-xs text-lol-hq-cyan/70 uppercase tracking-wider truncate hidden sm:inline font-mono">
                      · {manager.name}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[10px] sm:text-[11px] text-white/45 font-mono uppercase tracking-wider">
                  <span className="text-lol-hq-cyan">Sem {currentWeek}</span>
                  <span className="text-white/15">·</span>
                  <span>{dayLabel}</span>
                  {dayType && (
                    <>
                      <span className="text-white/15">·</span>
                      <span className="text-white/35 normal-case tracking-normal">
                        {dayType.replace('_', ' ')}
                      </span>
                    </>
                  )}
                  <span className="text-white/15">·</span>
                  <span className="text-white/35">{splitPhase?.replace('_', ' ')}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
              {matchLive && (
                <button
                  onClick={() => setCurrentScreen('SIMULATION' as never)}
                  className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-emerald-500/40 bg-emerald-950/40 text-emerald-400 text-[10px] font-bold uppercase tracking-wide shadow-[0_0_12px_rgba(52,211,153,0.2)]"
                >
                  <span className="hq-live-dot" />
                  <Radio className="w-3 h-3" />
                  Ao vivo
                </button>
              )}
              <button
                type="button"
                disabled={saving || !manager}
                title="Salvar carreira (slot1)"
                onClick={async () => {
                  setSaving(true);
                  setSaveMsg(null);
                  try {
                    await saveCareer('slot1');
                    setSaveMsg('Salvo!');
                    setTimeout(() => setSaveMsg(null), 2500);
                  } catch (e) {
                    setSaveMsg(e instanceof Error ? e.message : 'Erro ao salvar');
                  } finally {
                    setSaving(false);
                  }
                }}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-lol-hq-cyan/35 bg-lol-hq-cyan/10 text-lol-hq-cyan text-[10px] font-bold uppercase tracking-wide hover:bg-lol-hq-cyan/20 hover:shadow-hq-cyan-sm disabled:opacity-40 transition-all"
              >
                {saving ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Save className="w-3 h-3" />
                )}
                {saveMsg || 'Salvar'}
              </button>
              <div className="px-2.5 py-1 rounded-sm bg-black/45 border border-emerald-500/25 backdrop-blur-sm">
                <span className="text-[9px] uppercase tracking-hud text-white/35 block">Budget</span>
                <span className="text-xs sm:text-sm font-bold text-emerald-400 font-mono">
                  €{(myBudget / 1_000_000).toFixed(2)}M
                </span>
              </div>
              {myStanding && (
                <div className="hidden lg:block px-2.5 py-1 rounded-sm bg-black/45 border border-lol-hq-cyan/25 backdrop-blur-sm">
                  <span className="text-[9px] uppercase tracking-hud text-white/35 block">Rank</span>
                  <span className="text-xs font-bold text-lol-hq-cyan font-mono">
                    #{myRank} · {myStanding.points} pts
                  </span>
                </div>
              )}
              {matchPending && (
                <button
                  onClick={() => setCurrentScreen('DRAFT' as never)}
                  className="px-3 py-1.5 rounded-sm bg-gradient-to-r from-lol-hq-cyan to-lol-hq-cyan-dim text-lol-void text-[10px] sm:text-xs font-bold uppercase tracking-wide shadow-hq-cyan animate-pulse"
                >
                  Match Day →
                </button>
              )}
            </div>
          </div>

          {/* Mobile nav — scroll horizontal */}
          <div className="md:hidden flex overflow-x-auto border-t border-white/5 px-1 gap-0.5 pb-1 scrollbar-none">
            {NAV.map((item) => {
              const active = currentScreen === item.id;
              const Icon = item.icon;
              const badge = badgeForScreen(item.id, alertInput);
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentScreen(item.id as never)}
                  className={`relative flex flex-col items-center gap-0.5 px-2.5 py-2 min-w-[3.6rem] rounded-sm text-[8px] uppercase tracking-wide ${
                    active ? 'text-lol-hq-cyan bg-lol-hq-cyan/15' : 'text-white/45'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.short}
                  {badge?.show && (
                    <span
                      className={`absolute top-1 right-1 w-1.5 h-1.5 rounded-full ${
                        badge.tone === 'critical'
                          ? 'bg-red-500'
                          : badge.tone === 'warning'
                            ? 'bg-amber-400'
                            : 'bg-sky-400'
                      }`}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </header>

        <main className="hub-main-content">
          <div className="relative max-w-[1400px] mx-auto animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}
