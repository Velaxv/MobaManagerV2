import { useState, useEffect } from 'react';
import { useGameStore } from '../store/useGameStore';
import {
  Calendar,
  AlertTriangle,
  Play,
  ShieldAlert,
  Loader2,
  Swords,
  TrendingUp,
  Users,
  Wallet,
  Activity,
  Trophy,
  FileSignature,
  Dumbbell,
  Briefcase,
  Landmark,
  UserCircle2,
  TableProperties,
  FileCode2,
  ChevronRight,
} from 'lucide-react';
import { CalendarDayType, SplitPhase } from '../types/game';
import { ROLE_LABELS } from '../lib/champions';
import { RoleIcon } from '../components/RoleIcon';
import { PlayerPortrait } from '../components/PlayerPortrait';
import { api } from '../services/api';
import type { AppScreen } from '../types/screens';

/** Atalhos do hub (FM-like: overview → áreas dedicadas). */
const SHORTCUTS: {
  id: AppScreen;
  label: string;
  hint: string;
  icon: typeof Dumbbell;
  accent: string;
}[] = [
  {
    id: 'TRAINING',
    label: 'Treino',
    hint: 'Plano, moral, scrim, scout',
    icon: Dumbbell,
    accent: 'border-sky-500/25 hover:border-sky-400/45 hover:bg-sky-950/20',
  },
  {
    id: 'STAFF',
    label: 'Staff',
    hint: 'Comissão técnica',
    icon: Briefcase,
    accent: 'border-violet-500/25 hover:border-violet-400/45 hover:bg-violet-950/20',
  },
  {
    id: 'ORG',
    label: 'Organização',
    hint: 'Board, sponsors, caixa',
    icon: Landmark,
    accent: 'border-amber-500/25 hover:border-amber-400/45 hover:bg-amber-950/20',
  },
  {
    id: 'SQUAD',
    label: 'Elenco',
    hint: 'Titulares e academy',
    icon: UserCircle2,
    accent: 'border-emerald-500/25 hover:border-emerald-400/45 hover:bg-emerald-950/20',
  },
  {
    id: 'MARKET',
    label: 'Mercado',
    hint: 'Transfers e free agents',
    icon: Users,
    accent: 'border-white/15 hover:border-lol-gold/40 hover:bg-lol-gold/5',
  },
  {
    id: 'STANDINGS',
    label: 'Tabela',
    hint: 'Classificação e playoffs',
    icon: TableProperties,
    accent: 'border-white/15 hover:border-lol-gold/40 hover:bg-lol-gold/5',
  },
  {
    id: 'PATCH',
    label: 'Patch',
    hint: 'Meta e notas',
    icon: FileCode2,
    accent: 'border-white/15 hover:border-lol-gold/40 hover:bg-lol-gold/5',
  },
];

/**
 * Painel = inbox do manager (estilo FM):
 * o que fazer agora, calendário, forma, resultados e atalhos.
 * Detalhes ficam em Treino / Staff / Org / Elenco…
 */
export function Dashboard() {
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [offseasonBusy, setOffseasonBusy] = useState<string | null>(null);
  const [offseasonMsg, setOffseasonMsg] = useState<string | null>(null);
  const [faCount, setFaCount] = useState<number | null>(null);

  const {
    currentWeek,
    currentDayIndex,
    calendar,
    myPlayers,
    myTeamName,
    myBudget,
    advanceDay,
    activeMatch,
    setCurrentScreen,
    standings,
    roundResults,
    roundResultsWeek,
    matchLogPreview,
    openMatchLog,
    closeMatchLog,
    manager,
    splitPhase,
    playoffBracket,
    offseasonContracts,
    renewContract,
    releasePlayer,
    startNewSplit,
    startOffseasonDev,
    finance,
    lastBoardReview,
    patchStatus,
    practice,
    training,
  } = useGameStore();

  const myTeamId = manager?.teamId;
  const isOffseason = splitPhase === SplitPhase.OFFSEASON;

  useEffect(() => {
    if (isOffseason && myTeamId) {
      api
        .getFreeAgents({ managedTeamId: myTeamId })
        .then((r) => setFaCount(r.count ?? r.free_agents?.length ?? 0))
        .catch(() => undefined);
    }
  }, [myTeamId, isOffseason]);

  const burnoutAlerts = myPlayers.filter((p) => p.burnoutMeter > 70 || p.visualFatigue > 70);
  const myStanding = standings.find((s) => s.team_name === myTeamName);
  const myRank = standings.findIndex((s) => s.team_name === myTeamName) + 1;
  const starters = myPlayers.slice(0, 5);
  const avgCa =
    starters.length > 0
      ? Math.round(starters.reduce((s, p) => s + p.currentAbility, 0) / starters.length)
      : 0;
  const avgBurnout =
    myPlayers.length > 0
      ? Math.round(myPlayers.reduce((s, p) => s + p.burnoutMeter, 0) / myPlayers.length)
      : 0;

  const getDayTypeStyles = (type: CalendarDayType) => {
    switch (type) {
      case CalendarDayType.REST:
        return 'border-emerald-700/40 bg-emerald-950/25 text-emerald-300';
      case CalendarDayType.MATCH_DAY:
        return 'border-lol-gold/45 bg-lol-gold/10 text-lol-gold-soft';
      case CalendarDayType.TRAINING:
        return 'border-lol-hextech-bright/25 bg-lol-hextech/25 text-white/75';
      case CalendarDayType.SCRIM:
        return 'border-sky-700/40 bg-sky-950/25 text-sky-300';
      default:
        return 'border-white/10 bg-black/30 text-white/50';
    }
  };

  const today = calendar[currentDayIndex];

  return (
    <div className="flex flex-col gap-4">
      {/* Hero */}
      <div className="panel-lol p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-lol-header pointer-events-none" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-lol-gold/50 to-transparent" />
        <div className="relative">
          <p className="text-[10px] uppercase tracking-[0.25em] text-lol-gold/70 font-semibold mb-1">
            Painel · o que fazer agora
          </p>
          <h2 className="font-display text-xl sm:text-2xl font-bold text-lol-gold-soft tracking-wide">
            {myTeamName}
          </h2>
          <p className="text-xs text-white/45 mt-1 font-mono">
            {splitPhase?.replace('_', ' ')}
            {myStanding && (
              <span className="text-lol-gold-soft">
                {' '}
                · #{myRank || '—'} · {myStanding.wins}V-{myStanding.losses}D · {myStanding.points}{' '}
                pts
              </span>
            )}
          </p>
          {today && (
            <p className="text-[11px] text-white/50 mt-2">
              Hoje:{' '}
              <span className="text-white/80 font-semibold">
                {today.dayOfWeek} · {today.type.replace('_', ' ')}
              </span>
              {today.type === CalendarDayType.MATCH_DAY && today.opponentAbbr && (
                <span className="text-lol-gold-soft">
                  {' '}
                  · vs {today.opponentAbbr}
                  {today.isHome ? ' (casa)' : ' (fora)'}
                </span>
              )}
            </p>
          )}
        </div>
        <div className="relative flex items-center gap-3 flex-wrap">
          <div className="text-right hidden sm:block px-3 py-1.5 rounded-sm bg-black/30 border border-white/5">
            <span className="text-[9px] uppercase text-white/35 block">Semana</span>
            <span className="font-mono text-sm font-bold text-white">
              {currentWeek} · {today?.dayOfWeek ?? 'SEG'}
            </span>
          </div>
          {activeMatch && activeMatch.currentPhase === 'DRAFT' ? (
            <button
              onClick={() => setCurrentScreen('DRAFT')}
              className="btn-lol-primary flex items-center gap-2 py-2.5 px-4 shadow-lol-gold"
            >
              <Swords className="w-4 h-4" />
              Match Day — Draft
            </button>
          ) : (
            <button
              disabled={isAdvancing}
              onClick={async () => {
                setIsAdvancing(true);
                await advanceDay();
                setIsAdvancing(false);
              }}
              className="btn-lol-primary flex items-center gap-2 py-2.5 px-4"
            >
              {isAdvancing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4 fill-current" />
              )}
              {isAdvancing ? 'Avançando…' : 'Avançar dia'}
            </button>
          )}
        </div>
      </div>

      {/* Atalhos para áreas do jogo */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.18em] text-white/30 font-semibold mb-2 px-0.5">
          Ir para
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-2">
          {SHORTCUTS.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setCurrentScreen(s.id)}
                className={`group text-left rounded-sm border bg-black/30 p-2.5 transition-all ${s.accent}`}
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <Icon className="w-4 h-4 text-lol-gold/80 group-hover:text-lol-gold" />
                  <ChevronRight className="w-3 h-3 text-white/20 group-hover:text-lol-gold/60" />
                </div>
                <div className="text-[11px] font-semibold text-white/90 uppercase tracking-wide">
                  {s.label}
                </div>
                <div className="text-[9px] text-white/35 mt-0.5 leading-snug">{s.hint}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Playoffs */}
      {(splitPhase === SplitPhase.PLAYOFFS || playoffBracket) && !isOffseason && (
        <div className="panel-lol border-lol-gold/25 bg-lol-gold/5 px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-lol-gold" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-lol-gold-soft">
                {playoffBracket?.champion_name
                  ? `Campeão: ${playoffBracket.champion_name}`
                  : 'Playoffs CBLOL — Top 6'}
              </p>
              <p className="text-[10px] text-white/40 font-mono">
                {playoffBracket?.current_round?.replace(/_/g, ' ') || 'Bracket ativo'}
                {activeMatch?.seriesLabel ? ` · ${activeMatch.seriesLabel}` : ''}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setCurrentScreen('STANDINGS')}
            className="text-[10px] uppercase tracking-wide text-lol-gold border border-lol-gold/30 px-3 py-1.5 rounded-sm hover:bg-lol-gold/10"
          >
            Ver chave →
          </button>
        </div>
      )}

      {/* Offseason — urgência fica no painel */}
      {isOffseason && (
        <div className="panel-lol border-sky-500/25 bg-sky-950/20">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <FileSignature className="w-4 h-4 text-sky-300" />
              <span className="text-xs font-semibold uppercase tracking-wider text-sky-200">
                Offseason · Contratos
              </span>
            </div>
            <span className="text-[10px] text-white/35 font-mono">
              {offseasonContracts.filter((c) => c.needs_renewal).length} precisam atenção
              {faCount != null ? ` · ${faCount} FA` : ''}
            </span>
          </div>
          <div className="p-3 space-y-3">
            <p className="text-[11px] text-white/45 leading-relaxed">
              Renove ou liberte atletas. Janela de transferências completa — use{' '}
              <button
                type="button"
                className="text-lol-gold hover:underline"
                onClick={() => setCurrentScreen('MARKET')}
              >
                Mercado
              </button>
              .
            </p>
            <ul className="flex flex-col gap-1.5 max-h-[200px] overflow-y-auto">
              {offseasonContracts.length === 0 ? (
                <li className="text-xs text-white/35 font-mono p-2">Sem contratos listados.</li>
              ) : (
                offseasonContracts.map((c) => (
                  <li
                    key={c.player_id}
                    className={`flex flex-wrap items-center gap-2 p-2 rounded-sm border text-[11px] ${
                      c.needs_renewal
                        ? 'border-amber-500/30 bg-amber-950/20'
                        : 'border-white/5 bg-black/25'
                    }`}
                  >
                    <span className="font-semibold text-white min-w-[5rem]">{c.player_name}</span>
                    <span className="text-white/40 font-mono">
                      {c.role} · CA {c.current_ability}
                    </span>
                    <span className="text-white/30 font-mono">
                      {c.remaining_seasons}s · €{Math.round(c.monthly_salary).toLocaleString('pt-BR')}
                      /m
                    </span>
                    {c.needs_renewal && (
                      <span className="text-[9px] uppercase text-amber-300">Renovar</span>
                    )}
                    <div className="ml-auto flex gap-1">
                      <button
                        type="button"
                        disabled={!!offseasonBusy}
                        onClick={async () => {
                          setOffseasonBusy(c.player_id);
                          setOffseasonMsg(null);
                          try {
                            await renewContract(c.player_id);
                            setOffseasonMsg(`Renovado: ${c.player_name}`);
                          } catch (e) {
                            setOffseasonMsg(e instanceof Error ? e.message : 'Erro ao renovar');
                          } finally {
                            setOffseasonBusy(null);
                          }
                        }}
                        className="text-[9px] uppercase text-emerald-400 border border-emerald-700/40 px-2 py-1 rounded-sm disabled:opacity-40"
                      >
                        Renovar
                      </button>
                      <button
                        type="button"
                        disabled={!!offseasonBusy}
                        onClick={async () => {
                          if (!confirm(`Liberar ${c.player_name}?`)) return;
                          setOffseasonBusy(c.player_id);
                          setOffseasonMsg(null);
                          try {
                            await releasePlayer(c.player_id);
                            setOffseasonMsg(`Liberado: ${c.player_name}`);
                          } catch (e) {
                            setOffseasonMsg(e instanceof Error ? e.message : 'Erro ao liberar');
                          } finally {
                            setOffseasonBusy(null);
                          }
                        }}
                        className="text-[9px] uppercase text-lol-red-side border border-lol-red-side/30 px-2 py-1 rounded-sm disabled:opacity-40"
                      >
                        Liberar
                      </button>
                    </div>
                  </li>
                ))
              )}
            </ul>
            <div className="flex flex-wrap gap-2 items-center">
              <button
                type="button"
                disabled={!!offseasonBusy}
                onClick={async () => {
                  setOffseasonBusy('split');
                  setOffseasonMsg(null);
                  try {
                    await startNewSplit();
                    setOffseasonMsg('Novo split iniciado!');
                  } catch (e) {
                    setOffseasonMsg(e instanceof Error ? e.message : 'Erro no novo split');
                  } finally {
                    setOffseasonBusy(null);
                  }
                }}
                className="btn-lol-primary text-[10px] py-1.5 px-3"
              >
                {offseasonBusy === 'split' ? '…' : 'Iniciar novo split'}
              </button>
              {offseasonMsg && (
                <span className="text-[10px] font-mono text-white/50">{offseasonMsg}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {!isOffseason && splitPhase === SplitPhase.REGULAR_SEASON && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => void startOffseasonDev().catch(() => undefined)}
            className="text-[9px] uppercase tracking-wide text-white/25 hover:text-sky-300 border border-white/5 hover:border-sky-500/30 px-2 py-1 rounded-sm"
          >
            [Dev] Forçar offseason
          </button>
        </div>
      )}

      {lastBoardReview && !lastBoardReview.skipped && lastBoardReview.message && (
        <div
          className={`panel-lol border ${
            lastBoardReview.on_track
              ? 'border-emerald-500/30 bg-emerald-950/20'
              : 'border-amber-500/35 bg-amber-950/25'
          }`}
        >
          <div className="panel-lol-header">
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
              Board · Review semanal
            </span>
            <button
              type="button"
              onClick={() => setCurrentScreen('ORG')}
              className="text-[9px] uppercase text-lol-gold hover:underline"
            >
              Organização →
            </button>
          </div>
          <div className="p-3 text-[12px] text-white/75 leading-snug">
            {lastBoardReview.message}
            {lastBoardReview.fired && (
              <span className="block mt-1 text-red-400 font-semibold">Você foi demitido.</span>
            )}
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <button
          type="button"
          onClick={() => setCurrentScreen('ORG')}
          className="hub-stat-card text-left hover:border-emerald-500/30 transition-colors"
        >
          <div className="flex items-center gap-2 text-white/40 text-[10px] uppercase tracking-wider">
            <Wallet className="w-3.5 h-3.5 text-emerald-400" /> Caixa
          </div>
          <div
            className={`font-mono text-lg sm:text-xl font-bold ${
              finance?.health === 'critical'
                ? 'text-lol-red-side'
                : finance?.health === 'warning'
                  ? 'text-amber-400'
                  : 'text-emerald-400'
            }`}
          >
            €{(myBudget / 1_000_000).toFixed(2)}M
          </div>
          {finance && (
            <div className="text-[9px] font-mono text-white/35 mt-0.5">
              Folha €{(finance.monthly_payroll / 1000).toFixed(0)}k/mês
            </div>
          )}
        </button>
        <button
          type="button"
          onClick={() => setCurrentScreen('STANDINGS')}
          className="hub-stat-card text-left hover:border-lol-gold/30 transition-colors"
        >
          <div className="flex items-center gap-2 text-white/40 text-[10px] uppercase tracking-wider">
            <TrendingUp className="w-3.5 h-3.5 text-lol-gold" /> Posição
          </div>
          <div className="font-mono text-lg sm:text-xl font-bold text-lol-gold">
            {myRank > 0 ? `#${myRank}` : '—'}
            {myStanding && (
              <span className="text-sm text-white/40 font-normal ml-1">
                {myStanding.wins}V-{myStanding.losses}D
              </span>
            )}
          </div>
        </button>
        <button
          type="button"
          onClick={() => setCurrentScreen('SQUAD')}
          className="hub-stat-card text-left hover:border-sky-500/30 transition-colors"
        >
          <div className="flex items-center gap-2 text-white/40 text-[10px] uppercase tracking-wider">
            <Users className="w-3.5 h-3.5 text-sky-400" /> CA médio
          </div>
          <div className="font-mono text-lg sm:text-xl font-bold text-sky-300">{avgCa || '—'}</div>
        </button>
        <button
          type="button"
          onClick={() => setCurrentScreen('TRAINING')}
          className="hub-stat-card text-left hover:border-amber-500/30 transition-colors"
        >
          <div className="flex items-center gap-2 text-white/40 text-[10px] uppercase tracking-wider">
            <Activity className="w-3.5 h-3.5 text-amber-400" /> Burnout / Moral
          </div>
          <div
            className={`font-mono text-lg sm:text-xl font-bold ${
              avgBurnout > 60
                ? 'text-lol-red-side'
                : avgBurnout > 35
                  ? 'text-amber-400'
                  : 'text-emerald-400'
            }`}
          >
            {avgBurnout}%
            {practice?.morale?.team_morale != null && (
              <span className="text-sm text-rose-300/80 font-normal ml-1">
                · M{Math.round(practice.morale.team_morale)}
              </span>
            )}
          </div>
          {training && (
            <div className="text-[9px] font-mono text-white/35 mt-0.5">
              Treino {(training.focus || 'BALANCED').replace(/_/g, ' ')} ·{' '}
              {training.intensity || 'NORMAL'}
            </div>
          )}
        </button>
      </div>

      {/* Patch teaser */}
      <div className="panel-lol border-lol-gold/15">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <FileCode2 className="w-4 h-4 text-lol-gold" />
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
              Patch · meta
            </span>
          </div>
          <button
            type="button"
            onClick={() => setCurrentScreen('PATCH')}
            className="text-[9px] uppercase tracking-wide text-lol-gold border border-lol-gold/30 px-2 py-1 rounded-sm hover:bg-lol-gold/10"
          >
            Notas →
          </button>
        </div>
        <div className="p-3 flex flex-wrap items-center gap-3 text-[11px] font-mono">
          <span className="text-white/70">
            Ativo:{' '}
            <span className="text-emerald-400 font-bold">
              {patchStatus?.active?.version ? `v${patchStatus.active.version}` : '—'}
            </span>
          </span>
          {patchStatus?.active && (
            <>
              <span className="text-emerald-400/80">
                {patchStatus.active.buff_count ?? 0} buffs
              </span>
              <span className="text-red-400/80">{patchStatus.active.nerf_count ?? 0} nerfs</span>
            </>
          )}
          {patchStatus?.upcoming && (
            <span className="text-sky-300/80">
              Próx. v{patchStatus.upcoming.version} em {patchStatus.upcoming.days_until}d
            </span>
          )}
        </div>
      </div>

      {/* Calendário */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-lol-gold" />
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
              Semana {currentWeek}
            </span>
          </div>
          <span className="text-[10px] text-white/30 font-mono">Rotina do plantel</span>
        </div>
        <div className="p-3 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {calendar.map((day, idx) => {
            const isToday = idx === currentDayIndex;
            const isMatch = day.type === CalendarDayType.MATCH_DAY;
            const hasOpponent = Boolean(day.opponentAbbr);
            return (
              <div
                key={day.dayIndex}
                className={`hub-day-card ${getDayTypeStyles(day.type)} ${isToday ? 'hub-day-today' : 'opacity-80'}`}
              >
                {isToday && (
                  <span className="absolute top-1.5 right-1.5 text-[8px] font-bold bg-lol-gold text-lol-void px-1 rounded-sm uppercase">
                    Hoje
                  </span>
                )}
                <span className="font-mono font-bold text-[10px] opacity-70">{day.dayOfWeek}</span>
                <span className="text-[10px] font-semibold mt-1 uppercase tracking-wide">
                  {isMatch && hasOpponent
                    ? day.isHome
                      ? 'Casa'
                      : 'Fora'
                    : day.type.replace('_', ' ')}
                </span>
                {isMatch && hasOpponent ? (
                  <div className="mt-auto pt-2 space-y-0.5">
                    <p className="text-[11px] font-bold text-lol-gold leading-tight">
                      vs {day.opponentAbbr}
                    </p>
                    <p className="text-[9px] opacity-50 line-clamp-1 leading-snug">
                      {day.opponentName || day.eventName}
                    </p>
                  </div>
                ) : (
                  <p className="text-[10px] mt-auto pt-2 line-clamp-2 opacity-60 leading-snug">
                    {day.eventName || 'Rotina'}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="panel-lol flex flex-col">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2 text-lol-red-side">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Forma física</span>
            </div>
            {burnoutAlerts.length > 0 && (
              <span className="text-[10px] font-mono text-lol-red-side">{burnoutAlerts.length}</span>
            )}
          </div>
          <div className="p-3 flex-1">
            {burnoutAlerts.length > 0 ? (
              <div className="flex flex-col gap-2 max-h-[260px] overflow-y-auto">
                {burnoutAlerts.map((player) => (
                  <div
                    key={player.id}
                    className="p-2.5 bg-black/40 border border-lol-red-side/30 rounded-sm"
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <PlayerPortrait name={player.name} size="xs" />
                        <span className="font-semibold text-sm text-white truncate">
                          {player.name}
                        </span>
                      </div>
                      <span className="flex items-center gap-1 role-pill shrink-0">
                        <RoleIcon role={player.role} size={10} />
                        {ROLE_LABELS[player.role] || player.role}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-2 text-[10px] font-mono">
                      <div>
                        <span className="text-white/40 block">Burnout</span>
                        <div className="stat-bar mt-0.5">
                          <div
                            className="stat-bar-fill bg-lol-red-side"
                            style={{ width: `${player.burnoutMeter}%` }}
                          />
                        </div>
                      </div>
                      <div>
                        <span className="text-white/40 block">Fadiga visual</span>
                        <div className="stat-bar mt-0.5">
                          <div
                            className="stat-bar-fill bg-amber-500"
                            style={{ width: `${player.visualFatigue}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-white/35 text-center">
                <ShieldAlert className="w-8 h-8 mb-2 opacity-50" />
                <span className="text-xs">Elenco em boa forma. Sem alertas críticos.</span>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-2 panel-lol flex flex-col">
          <div className="panel-lol-header">
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
              Titulares
            </span>
            <button
              onClick={() => setCurrentScreen('SQUAD')}
              className="text-[10px] text-lol-gold hover:underline uppercase tracking-wide"
            >
              Ver elenco completo →
            </button>
          </div>
          <div className="p-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-2">
            {starters.map((player) => (
              <div
                key={player.id}
                className="flex sm:flex-col items-center sm:items-stretch gap-2 p-2.5 rounded-sm bg-black/30 border border-white/5 hover:border-lol-gold/25 transition-colors"
              >
                <PlayerPortrait name={player.name} size="md" className="shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1 text-[9px] text-white/40 mb-0.5">
                    <RoleIcon role={player.role} size={10} className="text-lol-gold/70" />
                    {ROLE_LABELS[player.role]}
                  </div>
                  <div className="font-semibold text-sm text-white truncate">{player.name}</div>
                  <div className="flex gap-2 mt-1 text-[10px] font-mono">
                    <span className="text-emerald-400 font-bold">CA {player.currentAbility}</span>
                    <span className="text-white/35">Mec {player.mechanics}</span>
                  </div>
                  <div className="stat-bar mt-1.5">
                    <div
                      className={`stat-bar-fill ${
                        player.burnoutMeter > 70
                          ? 'bg-lol-red-side'
                          : player.burnoutMeter > 40
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                      }`}
                      style={{ width: `${player.burnoutMeter}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
            {starters.length === 0 && (
              <p className="col-span-full text-xs text-white/40 p-4 font-mono">
                Elenco vazio — rode o seed e escolha um time.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Tabela + resultados */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="panel-lol">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-lol-gold" />
              <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
                Classificação
              </span>
            </div>
            <button
              onClick={() => setCurrentScreen('STANDINGS')}
              className="text-[10px] text-lol-gold hover:underline uppercase"
            >
              Completa →
            </button>
          </div>
          <div className="p-2 overflow-x-auto">
            {standings.length === 0 ? (
              <p className="text-xs text-white/40 p-4 font-mono">
                Avance match days para gerar standings.
              </p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-white/35 text-[10px] uppercase font-mono border-b border-white/5">
                    <th className="py-1.5 px-2 text-left">#</th>
                    <th className="text-left px-2">Time</th>
                    <th className="px-2">V</th>
                    <th className="px-2">D</th>
                    <th className="px-2">Pts</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {standings.slice(0, 8).map((row, idx) => (
                    <tr
                      key={row.team_id}
                      className={
                        row.team_name === myTeamName
                          ? 'hub-table-row-mine'
                          : idx < 6
                            ? 'hub-table-row-playoff text-white/80'
                            : 'hub-table-row-out text-white/55'
                      }
                    >
                      <td className="py-1.5 px-2 text-white/40 font-mono">{idx + 1}</td>
                      <td className="px-2 font-semibold">{row.team_name}</td>
                      <td className="px-2 text-center text-emerald-400 font-mono">{row.wins}</td>
                      <td className="px-2 text-center text-lol-red-side font-mono">{row.losses}</td>
                      <td className="px-2 text-center font-bold font-mono">{row.points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="panel-lol">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Swords className="w-4 h-4 text-lol-gold" />
              <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
                Resultados da rodada
              </span>
            </div>
            <span className="text-[10px] text-white/30 font-mono">
              {roundResultsWeek != null ? `Sem ${roundResultsWeek}` : '—'}
              {roundResults.length ? ` · ${roundResults.length} jogos` : ''}
            </span>
          </div>
          <div className="p-3">
            {roundResults.length === 0 ? (
              <p className="text-xs text-white/40 font-mono leading-relaxed">
                Avance um match day para ver confrontos. Partidas de terceiros simulam
                automaticamente; a sua abre o draft.
              </p>
            ) : (
              <ul className="flex flex-col gap-1.5 max-h-[280px] overflow-y-auto">
                {roundResults.map((r, i) => {
                  const involvesMe =
                    !!myTeamId &&
                    (r.blue_team_id === myTeamId || r.red_team_id === myTeamId);
                  const pending = r.status === 'pending' || (!r.winner_name && !r.match_id);
                  const blueTag = r.blue_team_abbr || r.blue_team_name || 'Blue';
                  const redTag = r.red_team_abbr || r.red_team_name || 'Red';
                  const iWon = involvesMe && r.winner_team_id && r.winner_team_id === myTeamId;
                  const iLost = involvesMe && r.winner_team_id && r.winner_team_id !== myTeamId;
                  return (
                    <li
                      key={r.match_id || `${blueTag}-${redTag}-${i}`}
                      className={`text-[11px] font-mono p-2.5 border rounded-sm flex flex-col gap-1 ${
                        involvesMe
                          ? 'border-lol-gold/35 bg-lol-gold/5'
                          : 'border-white/5 bg-black/30'
                      }`}
                    >
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className={involvesMe ? 'text-white/90 font-semibold' : 'text-white/55'}>
                          {blueTag}
                          <span className="text-white/25 mx-1">vs</span>
                          {redTag}
                        </span>
                        {pending ? (
                          <span className="text-amber-400/90 text-[10px]">Pendente</span>
                        ) : (
                          <>
                            <span className="text-lol-gold/60">→</span>
                            <span
                              className={
                                iWon
                                  ? 'text-emerald-400 font-bold'
                                  : iLost
                                    ? 'text-lol-red-side font-bold'
                                    : 'text-emerald-400/90 font-bold'
                              }
                            >
                              {r.winner_name || '—'}
                            </span>
                          </>
                        )}
                        {r.match_id && (
                          <button
                            type="button"
                            onClick={() => void openMatchLog(r.match_id!)}
                            className="ml-auto text-[9px] uppercase tracking-wide text-lol-gold/80 hover:text-lol-gold border border-lol-gold/20 px-1.5 py-0.5 rounded-sm"
                          >
                            Ver log
                          </button>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            {matchLogPreview && (
              <div className="mt-3 border border-lol-gold/25 bg-black/50 rounded-sm p-3">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-lol-gold-soft">
                    {matchLogPreview.title}
                  </span>
                  <button
                    type="button"
                    onClick={() => closeMatchLog()}
                    className="text-[9px] text-white/40 hover:text-white uppercase"
                  >
                    Fechar
                  </button>
                </div>
                <ul className="max-h-36 overflow-y-auto space-y-1">
                  {matchLogPreview.lines.map((line, idx) => (
                    <li key={idx} className="text-[10px] font-mono text-white/50 leading-snug">
                      {line}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
