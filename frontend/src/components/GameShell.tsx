import type { ReactNode } from 'react';
import {
  LayoutDashboard,
  Users,
  Swords,
  Trophy,
  UserCircle2,
  TableProperties,
  ChevronRight,
  Radio,
} from 'lucide-react';
import { useGameStore } from '../store/useGameStore';

export type AppScreen = 'DASHBOARD' | 'SQUAD' | 'MARKET' | 'DRAFT' | 'SIMULATION' | 'STANDINGS';

const NAV: {
  id: AppScreen;
  label: string;
  short: string;
  icon: typeof LayoutDashboard;
  hint?: string;
  group: 'manage' | 'compete';
}[] = [
  { id: 'DASHBOARD', label: 'Painel', short: 'Home', icon: LayoutDashboard, hint: 'Dia a dia', group: 'manage' },
  { id: 'SQUAD', label: 'Elenco', short: 'Elenco', icon: UserCircle2, hint: 'Plantel', group: 'manage' },
  { id: 'STANDINGS', label: 'Tabela', short: 'Tabela', icon: TableProperties, hint: 'CBLOL', group: 'manage' },
  { id: 'MARKET', label: 'Mercado', short: 'Mercado', icon: Users, hint: 'Contratações', group: 'manage' },
  { id: 'DRAFT', label: 'Draft', short: 'Draft', icon: Swords, hint: 'Picks & bans', group: 'compete' },
  { id: 'SIMULATION', label: 'Partida', short: 'Live', icon: Trophy, hint: 'Ao vivo', group: 'compete' },
];

interface GameShellProps {
  children: ReactNode;
}

function teamInitials(name: string) {
  const parts = name.replace(/[^\w\s]/g, '').trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export function GameShell({ children }: GameShellProps) {
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

  const manageNav = NAV.filter((n) => n.group === 'manage');
  const competeNav = NAV.filter((n) => n.group === 'compete');

  const renderNav = (items: typeof NAV) =>
    items.map((item) => {
      const active = currentScreen === item.id;
      const Icon = item.icon;
      const badge =
        (item.id === 'DRAFT' && matchPending) ||
        (item.id === 'SIMULATION' && matchLive) ||
        (item.id === 'DASHBOARD' && burnoutCount > 0);
      return (
        <button
          key={item.id}
          onClick={() => setCurrentScreen(item.id as never)}
          className={`hub-nav-item ${active ? 'hub-nav-item-active' : 'hub-nav-item-idle'}`}
        >
          <Icon
            className={`w-4 h-4 shrink-0 ${active ? 'text-lol-gold' : 'text-white/35 group-hover:text-lol-gold-soft'}`}
          />
          <span className="flex-1 min-w-0">
            <span className="block text-xs font-semibold uppercase tracking-wide">{item.label}</span>
            <span className="block text-[10px] text-white/30 normal-case tracking-normal truncate">
              {item.hint}
            </span>
          </span>
          {badge && (
            <span className="w-2 h-2 rounded-full bg-lol-gold animate-pulse shadow-lol-gold shrink-0" />
          )}
          {active && <ChevronRight className="w-3.5 h-3.5 text-lol-gold/70 shrink-0" />}
        </button>
      );
    });

  return (
    <div className="hub-shell">
      {/* Sidebar FM */}
      <aside className="hub-sidebar">
        <div className="px-4 py-4 border-b border-lol-gold/15">
          <div className="flex items-center gap-3">
            <div className="team-crest text-xs shadow-lol-gold">LM</div>
            <div>
              <div className="font-display font-bold text-sm tracking-wide text-lol-gold-soft uppercase leading-tight">
                LoL Manager
              </div>
              <div className="text-[10px] text-white/35 uppercase tracking-widest">CBLOL 2026</div>
            </div>
          </div>
        </div>

        {/* Team strip */}
        <div className="px-3 py-3 border-b border-white/5 bg-black/20">
          <div className="flex items-center gap-2.5">
            <div className="team-crest !w-11 !h-11 text-sm">{teamInitials(myTeamName)}</div>
            <div className="min-w-0">
              <div className="text-xs font-bold text-white truncate">{myTeamName}</div>
              {manager && (
                <div className="text-[10px] text-white/40 truncate">Coach {manager.name}</div>
              )}
              <div className="text-[10px] font-mono text-lol-gold/80 mt-0.5">
                {myStanding
                  ? `#${myRank} · ${myStanding.wins}V-${myStanding.losses}D`
                  : 'Sem standings'}
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 py-2 px-2 overflow-y-auto">
          <p className="px-2 pt-1 pb-1.5 text-[9px] uppercase tracking-[0.2em] text-white/25 font-semibold">
            Gestão
          </p>
          <div className="space-y-0.5">{renderNav(manageNav)}</div>

          <p className="px-2 pt-4 pb-1.5 text-[9px] uppercase tracking-[0.2em] text-white/25 font-semibold">
            Competição
          </p>
          <div className="space-y-0.5">{renderNav(competeNav)}</div>
        </nav>

        <div className="p-3 border-t border-lol-gold/10 space-y-2 bg-black/25">
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-white/35">Orçamento</span>
            <span className="text-emerald-400 font-bold">€{(myBudget / 1_000_000).toFixed(2)}M</span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-white/35">Elenco</span>
            <span className="text-white/70">{myPlayers.length} atletas</span>
          </div>
          {burnoutCount > 0 && (
            <div className="text-[10px] text-lol-red-side font-mono">
              ⚠ {burnoutCount} alerta(s) de forma
            </div>
          )}
        </div>
      </aside>

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <header className="hub-topbar">
          <div className="px-3 sm:px-5 py-2.5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="md:hidden team-crest !w-8 !h-8 text-[10px]">
                {teamInitials(myTeamName)}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-display font-bold text-sm sm:text-base text-lol-gold-soft truncate">
                    {myTeamName}
                  </span>
                  {manager && (
                    <span className="text-[10px] sm:text-xs text-white/40 uppercase tracking-wider truncate hidden sm:inline">
                      · {manager.name}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[10px] sm:text-[11px] text-white/45 font-mono uppercase tracking-wider">
                  <span className="text-lol-gold/90">Sem {currentWeek}</span>
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
                  className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-emerald-500/40 bg-emerald-950/40 text-emerald-400 text-[10px] font-bold uppercase tracking-wide"
                >
                  <Radio className="w-3 h-3 animate-pulse" />
                  Ao vivo
                </button>
              )}
              <div className="px-2.5 py-1 rounded-sm bg-black/40 border border-emerald-800/35">
                <span className="text-[9px] uppercase text-white/35 block">Orçamento</span>
                <span className="text-xs sm:text-sm font-bold text-emerald-400 font-mono">
                  €{(myBudget / 1_000_000).toFixed(2)}M
                </span>
              </div>
              {myStanding && (
                <div className="hidden lg:block px-2.5 py-1 rounded-sm bg-black/40 border border-lol-gold/25">
                  <span className="text-[9px] uppercase text-white/35 block">Posição</span>
                  <span className="text-xs font-bold text-lol-gold font-mono">
                    #{myRank} · {myStanding.points} pts
                  </span>
                </div>
              )}
              {matchPending && (
                <button
                  onClick={() => setCurrentScreen('DRAFT' as never)}
                  className="px-3 py-1.5 rounded-sm bg-gradient-to-r from-lol-gold to-lol-gold-dim text-lol-void text-[10px] sm:text-xs font-bold uppercase tracking-wide shadow-lol-gold animate-pulse"
                >
                  Match Day →
                </button>
              )}
            </div>
          </div>

          {/* Mobile nav */}
          <div className="md:hidden flex overflow-x-auto border-t border-white/5 px-1 gap-0.5 pb-1 scrollbar-none">
            {NAV.map((item) => {
              const active = currentScreen === item.id;
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentScreen(item.id as never)}
                  className={`flex flex-col items-center gap-0.5 px-3 py-2 min-w-[4.2rem] rounded-sm text-[9px] uppercase tracking-wide ${
                    active ? 'text-lol-gold bg-lol-hextech/40' : 'text-white/45'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.short}
                </button>
              );
            })}
          </div>
        </header>

        <main className="flex-1 p-3 sm:p-5 overflow-x-hidden">
          <div className="max-w-[1400px] mx-auto animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}
