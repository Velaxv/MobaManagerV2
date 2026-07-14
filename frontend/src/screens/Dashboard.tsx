import { useState } from 'react';
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
} from 'lucide-react';
import { CalendarDayType, SplitPhase } from '../types/game';
import { ROLE_LABELS } from '../lib/champions';
import { RoleIcon } from '../components/RoleIcon';
import { ChampionImage } from '../components/ChampionImage';

export function Dashboard() {
  const [isAdvancing, setIsAdvancing] = useState(false);
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
  } = useGameStore();

  const myTeamId = manager?.teamId;

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

  return (
    <div className="flex flex-col gap-4">
      {/* Hero strip */}
      <div className="panel-lol p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-lol-header pointer-events-none" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-lol-gold/50 to-transparent" />
        <div className="relative">
          <p className="text-[10px] uppercase tracking-[0.25em] text-lol-gold/70 font-semibold mb-1">
            Hub de gestão · CBLOL 2026
          </p>
          <h2 className="font-display text-xl sm:text-2xl font-bold text-lol-gold-soft tracking-wide">
            {myTeamName}
          </h2>
          <p className="text-xs text-white/45 mt-1 font-mono">
            {splitPhase?.replace('_', ' ')}
            {myStanding && (
              <span className="text-lol-gold-soft">
                {' '}
                · #{myRank || '—'} · {myStanding.wins}V-{myStanding.losses}D · {myStanding.points} pts
              </span>
            )}
          </p>
        </div>
        <div className="relative flex items-center gap-3 flex-wrap">
          <div className="text-right hidden sm:block px-3 py-1.5 rounded-sm bg-black/30 border border-white/5">
            <span className="text-[9px] uppercase text-white/35 block">Hoje</span>
            <span className="font-mono text-sm font-bold text-white">
              Sem {currentWeek} · {calendar[currentDayIndex]?.dayOfWeek ?? 'SEG'}
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

      {/* Playoffs banner */}
      {(splitPhase === SplitPhase.PLAYOFFS || playoffBracket) && (
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

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="hub-stat-card">
          <div className="flex items-center gap-2 text-white/40 text-[10px] uppercase tracking-wider">
            <Wallet className="w-3.5 h-3.5 text-emerald-400" /> Orçamento
          </div>
          <div className="font-mono text-lg sm:text-xl font-bold text-emerald-400">
            €{(myBudget / 1_000_000).toFixed(2)}M
          </div>
        </div>
        <div className="hub-stat-card">
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
        </div>
        <div className="hub-stat-card">
          <div className="flex items-center gap-2 text-white/40 text-[10px] uppercase tracking-wider">
            <Users className="w-3.5 h-3.5 text-sky-400" /> CA médio (titulares)
          </div>
          <div className="font-mono text-lg sm:text-xl font-bold text-sky-300">{avgCa || '—'}</div>
        </div>
        <div className="hub-stat-card">
          <div className="flex items-center gap-2 text-white/40 text-[10px] uppercase tracking-wider">
            <Activity className="w-3.5 h-3.5 text-amber-400" /> Burnout médio
          </div>
          <div
            className={`font-mono text-lg sm:text-xl font-bold ${
              avgBurnout > 60 ? 'text-lol-red-side' : avgBurnout > 35 ? 'text-amber-400' : 'text-emerald-400'
            }`}
          >
            {avgBurnout}%
          </div>
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
        {/* Forma física */}
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
              <div className="flex flex-col gap-2 max-h-[280px] overflow-y-auto">
                {burnoutAlerts.map((player) => (
                  <div
                    key={player.id}
                    className="p-2.5 bg-black/40 border border-lol-red-side/30 rounded-sm"
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <ChampionImage
                          name={player.championPool?.[0]?.champion}
                          variant="ban"
                          className="!w-8 !h-8"
                        />
                        <span className="font-semibold text-sm text-white truncate">{player.name}</span>
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

        {/* Titulares */}
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
                <ChampionImage
                  name={player.championPool?.[0]?.champion}
                  variant="portrait"
                  className="shrink-0"
                />
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
                Avance um match day para ver todos os confrontos da rodada. Partidas de terceiros
                simulam automaticamente; a sua abre o draft.
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
                  const iWon =
                    involvesMe &&
                    r.winner_team_id &&
                    r.winner_team_id === myTeamId;
                  const iLost =
                    involvesMe &&
                    r.winner_team_id &&
                    r.winner_team_id !== myTeamId;
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
                        {r.is_playoff && (
                          <span className="text-[9px] uppercase text-lol-gold/70 border border-lol-gold/20 px-1 rounded-sm">
                            PO
                          </span>
                        )}
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
                            {r.duration != null && (
                              <span className="text-white/25">{Math.round(Number(r.duration))}′</span>
                            )}
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
                      {r.series_label && (
                        <span className="text-[9px] text-white/30">{r.series_label}</span>
                      )}
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
