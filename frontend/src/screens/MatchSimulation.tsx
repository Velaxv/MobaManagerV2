import { useEffect, useMemo, useRef, useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import {
  Play,
  Zap,
  Swords,
  Trophy,
  Activity,
  MessageSquare,
  AlertCircle,
  Calendar,
  Crosshair,
  Flame,
  Radar,
} from 'lucide-react';
import { ChampionImage } from '../components/ChampionImage';
import { RoleIcon } from '../components/RoleIcon';
import { SummonersRiftMap } from '../components/SummonersRiftMap';
import { ROLE_LABELS, championSplashUrl } from '../lib/champions';
import { PlayerRole } from '../types/game';
import type { MapEventHint } from '../lib/riftMap';

const PHASES = [
  { key: 'EARLY_GAME', label: 'Early' },
  { key: 'MID_GAME', label: 'Mid' },
  { key: 'LATE_GAME', label: 'Late' },
] as const;

const ROLE_ORDER = [
  PlayerRole.TOP,
  PlayerRole.JUNGLE,
  PlayerRole.MID,
  PlayerRole.BOT,
  PlayerRole.SUPPORT,
];

function formatMinute(m?: number) {
  const n = Math.max(0, m ?? 0);
  return `${String(n).padStart(2, '0')}:00`;
}

function phaseProgress(phase: string, minute = 0): number {
  if (phase === 'COMPLETE' || phase === 'FINISHED') return 100;
  if (phase === 'SETUP' || phase === 'EARLY_GAME') return Math.min(33, (minute / 14) * 33);
  if (phase === 'MID_GAME') return 33 + Math.min(33, ((minute - 14) / 14) * 33);
  if (phase === 'LATE_GAME') return 66 + Math.min(34, ((minute - 28) / 12) * 34);
  return 10;
}

function TeamChampRow({
  picks,
  side,
}: {
  picks: { champion: string; role: string }[];
  side: 'blue' | 'red';
}) {
  const ordered = ROLE_ORDER.map((role) => {
    const pick = picks.find((p) => p.role === role);
    return { role, champion: pick?.champion };
  });

  return (
    <div className={`flex gap-1.5 flex-wrap ${side === 'red' ? 'justify-end' : 'justify-start'}`}>
      {ordered.map(({ role, champion }) => (
        <div key={role} className="flex flex-col items-center gap-0.5">
          <ChampionImage
            name={champion}
            variant="pick"
            locked={!!champion}
            className={side === 'blue' ? 'ring-lol-blue-side/40' : 'ring-lol-red-side/40'}
          />
          <RoleIcon
            role={role}
            size={11}
            className={side === 'blue' ? 'text-lol-blue-side/80' : 'text-lol-red-side/80'}
          />
        </div>
      ))}
    </div>
  );
}

export function MatchSimulation() {
  const activeMatch = useGameStore((s) => s.activeMatch);
  const startSimulation = useGameStore((s) => s.startSimulation);
  const triggerCoachComm = useGameStore((s) => s.triggerCoachComm);
  const myPlayers = useGameStore((s) => s.myPlayers);
  const myTeamName = useGameStore((s) => s.myTeamName);
  const teams = useGameStore((s) => s.teams);
  const manager = useGameStore((s) => s.manager);
  const submitDraftAndStartMatch = useGameStore((s) => s.submitDraftAndStartMatch);
  const setLiveSpeed = useGameStore((s) => s.setLiveSpeed);
  const syncMatchState = useGameStore((s) => s.syncMatchState);
  const clearActiveMatch = useGameStore((s) => s.clearActiveMatch);
  const draft = useGameStore((s) => s.draft);
  const lastScoutReport = useGameStore((s) => s.lastScoutReport);
  const setCurrentScreen = useGameStore((s) => s.setCurrentScreen);

  const [killPop, setKillPop] = useState<'blue' | 'red' | null>(null);
  const [commPulse, setCommPulse] = useState(false);
  const [starting, setStarting] = useState(false);
  const [preferredSpeed, setPreferredSpeed] = useState<'1x' | '2x' | '4x' | 'instant'>('2x');
  const prevKills = useRef({ blue: 0, red: 0 });
  const feedRef = useRef<HTMLDivElement>(null);

  // Polling live
  useEffect(() => {
    let interval: number | undefined;
    if (
      activeMatch?.matchId &&
      activeMatch.currentPhase !== 'COMPLETE' &&
      activeMatch.currentPhase !== 'FINISHED' &&
      activeMatch.currentPhase !== 'DRAFT' &&
      activeMatch.currentPhase !== 'DRAFT_COMPLETE'
    ) {
      interval = window.setInterval(() => syncMatchState(), 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeMatch?.matchId, activeMatch?.currentPhase, syncMatchState]);

  // Kill pop animation
  useEffect(() => {
    if (!activeMatch) return;
    const b = activeMatch.blueKills;
    const r = activeMatch.redKills;
    if (b > prevKills.current.blue) {
      setKillPop('blue');
      setTimeout(() => setKillPop(null), 500);
    } else if (r > prevKills.current.red) {
      setKillPop('red');
      setTimeout(() => setKillPop(null), 500);
    }
    prevKills.current = { blue: b, red: r };
  }, [activeMatch?.blueKills, activeMatch?.redKills]);

  // Auto-scroll feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [activeMatch?.logs.length]);

  const handleStartDraft = () => {
    const myTeam = teams.find((t) => t.id === manager?.teamId) || teams[0];
    const opponent = teams.find((t) => t.id !== myTeam?.id) || teams[1];
    if (!myTeam || !opponent) return;
    startSimulation(myTeam.name, opponent.name, myTeam.id, opponent.id);
    setCurrentScreen('DRAFT');
  };

  const handleCoachComm = async () => {
    setCommPulse(true);
    await triggerCoachComm();
    setTimeout(() => setCommPulse(false), 600);
  };

  const goldLeadLive = (activeMatch?.blueGold ?? 0) - (activeMatch?.redGold ?? 0);

  const splashChamp = useMemo(() => {
    const leadingPicks = goldLeadLive >= 0 ? draft.bluePicks : draft.redPicks;
    const mid = leadingPicks.find((p) => p.role === PlayerRole.MID);
    return mid?.champion || draft.bluePicks[0]?.champion || draft.redPicks[0]?.champion || 'Aatrox';
  }, [draft.bluePicks, draft.redPicks, goldLeadLive]);

  // Histórico de eventos (map meta) para torres/inibidores + evento em foco
  const mapEventHistory = useMemo((): MapEventHint[] => {
    const logs = activeMatch?.logs;
    if (!logs?.length) return [];
    return logs.map((log) => ({
      eventType: log.eventType,
      location: log.map?.location,
      role: log.map?.role,
      side: log.map?.side,
      intensity: log.map?.intensity,
      text: log.text,
    }));
  }, [activeMatch?.logs]);

  const latestMapEvent = useMemo((): MapEventHint | null => {
    if (!mapEventHistory.length) return null;
    const priority = [
      'VICTORY',
      'SNOWBALL',
      'BARON_SECURED',
      'TEAMFIGHT',
      'DRAGON_SECURED',
      'SOLO_KILL',
      'TURRET_DESTROYED',
      'COACH_COMM',
      'FARM',
    ];
    const window = mapEventHistory.slice(-4);
    let best: MapEventHint | null = null;
    let bestRank = 999;
    for (let i = window.length - 1; i >= 0; i--) {
      const log = window[i];
      const et = (log.eventType || '').toUpperCase();
      const rank = priority.indexOf(et);
      const r = rank === -1 ? 50 : rank;
      if (r < bestRank) {
        bestRank = r;
        best = log;
      }
    }
    return best || mapEventHistory[mapEventHistory.length - 1];
  }, [mapEventHistory]);

  // Empty state
  if (!activeMatch) {
    return (
      <div className="match-stage min-h-[420px] flex flex-col items-center justify-center py-16 px-6 text-center">
        <div
          className="match-splash-bg opacity-40"
          style={{ backgroundImage: `url(${championSplashUrl('Aatrox')})` }}
        />
        <div className="match-splash-veil" />
        <div className="relative z-10 flex flex-col items-center animate-fade-in">
          <Calendar className="w-14 h-14 text-lol-gold mb-4 opacity-90" />
          <h3 className="font-display text-xl text-lol-gold-soft uppercase tracking-wide">
            Nenhuma partida ao vivo
          </h3>
          <p className="text-xs text-white/50 mt-2 max-w-md leading-relaxed">
            Avance o calendário até um Match Day de {myTeamName}, ou inicie um amistoso com draft completo.
          </p>
          <button onClick={handleStartDraft} className="btn-lol-primary mt-6 flex items-center gap-2">
            <Play className="w-4 h-4" />
            Preparar amistoso
          </button>
        </div>
      </div>
    );
  }

  // Draft pending
  if (activeMatch.currentPhase === 'DRAFT') {
    return (
      <div className="match-stage min-h-[420px] flex flex-col items-center justify-center py-16 px-6 text-center">
        <div
          className="match-splash-bg"
          style={{ backgroundImage: `url(${championSplashUrl('Azir')})` }}
        />
        <div className="match-splash-veil" />
        <div className="relative z-10 animate-fade-in">
          <Activity className="w-14 h-14 text-lol-blue mx-auto mb-4 animate-pulse" />
          <h3 className="font-display text-xl text-lol-gold-soft uppercase">Draft em andamento</h3>
          <p className="text-xs text-white/50 mt-2 max-w-sm mx-auto">
            <span className="text-lol-blue-side">{activeMatch.blueTeam}</span>
            <span className="text-white/30 mx-2">vs</span>
            <span className="text-lol-red-side">{activeMatch.redTeam}</span>
          </p>
          <button onClick={() => setCurrentScreen('DRAFT')} className="btn-lol-primary mt-6">
            Ir para Champion Select
          </button>
        </div>
      </div>
    );
  }

  // Draft complete — pre-game
  if (activeMatch.currentPhase === 'DRAFT_COMPLETE') {
    return (
      <div className="match-stage min-h-[480px] flex flex-col items-center justify-center py-12 px-6 text-center">
        <div
          className="match-splash-bg"
          style={{
            backgroundImage: `url(${championSplashUrl(draft.bluePicks[2]?.champion || 'Aatrox')})`,
          }}
        />
        <div className="match-splash-veil" />
        <div className="relative z-10 flex flex-col items-center gap-5 animate-fade-in">
          <Swords className="w-12 h-12 text-lol-gold" />
          <h3 className="font-display text-xl text-lol-gold-soft uppercase tracking-wide">
            Táticas definidas
          </h3>
          <div className="flex items-center gap-3 sm:gap-6 flex-wrap justify-center">
            <div className="flex flex-col items-center gap-2">
              <span className="text-[10px] uppercase tracking-widest text-lol-blue-side font-bold">
                {activeMatch.blueTeam}
              </span>
              <div className="flex gap-1">
                {draft.bluePicks.map((p) => (
                  <ChampionImage key={p.champion} name={p.champion} variant="pick" locked showName />
                ))}
              </div>
            </div>
            <span className="font-display text-2xl text-white/25">VS</span>
            <div className="flex flex-col items-center gap-2">
              <span className="text-[10px] uppercase tracking-widest text-lol-red-side font-bold">
                {activeMatch.redTeam}
              </span>
              <div className="flex gap-1">
                {draft.redPicks.map((p) => (
                  <ChampionImage key={p.champion} name={p.champion} variant="pick" locked showName />
                ))}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="text-[10px] uppercase tracking-wider text-white/40">Velocidade</span>
            {(['1x', '2x', '4x', 'instant'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setPreferredSpeed(s)}
                className={`px-2.5 py-1 text-[10px] font-bold uppercase border rounded-sm ${
                  preferredSpeed === s
                    ? 'border-lol-gold bg-lol-gold/20 text-lol-gold'
                    : 'border-white/15 text-white/45 hover:border-white/30'
                }`}
              >
                {s === 'instant' ? 'Instant' : s}
              </button>
            ))}
          </div>
          <button
            disabled={starting}
            onClick={async () => {
              setStarting(true);
              try {
                await submitDraftAndStartMatch(preferredSpeed);
              } finally {
                setStarting(false);
              }
            }}
            className="btn-lol-primary flex items-center gap-2 px-8 py-3 text-sm"
          >
            <Zap className="w-4 h-4" />
            {starting ? 'Carregando Rift…' : 'Entrar no Rift'}
          </button>
        </div>
      </div>
    );
  }

  const isLive =
    activeMatch.currentPhase !== 'COMPLETE' && activeMatch.currentPhase !== 'FINISHED';
  const isVictory =
    activeMatch.currentPhase === 'COMPLETE' || activeMatch.currentPhase === 'FINISHED';

  const goldLead = goldLeadLive;
  const minute = activeMatch.currentMinute ?? 0;
  const progress = phaseProgress(activeMatch.currentPhase, minute);

  const winnerName =
    activeMatch.winnerSide === 'BLUE'
      ? activeMatch.blueTeam
      : activeMatch.winnerSide === 'RED'
        ? activeMatch.redTeam
        : null;

  const winnerPicks =
    activeMatch.winnerSide === 'RED' ? draft.redPicks : draft.bluePicks;

  const scoutReport = activeMatch.scoutEvaluation || lastScoutReport;

  return (
    <div className="match-stage">
      {/* Splash dinâmico */}
      <div
        key={splashChamp}
        className="match-splash-bg transition-opacity duration-1000"
        style={{ backgroundImage: `url(${championSplashUrl(splashChamp)})` }}
      />
      <div className="match-splash-veil" />

      {/* Victory overlay */}
      {isVictory && (
        <div className="victory-overlay">
          <div className="lock-in-card text-center max-w-lg px-4">
            <Trophy className="w-14 h-14 text-lol-gold mx-auto mb-2 animate-lock-shine" />
            <div className="lock-in-label text-lol-gold mb-2">VICTORY</div>
            <p className="font-display text-lg sm:text-xl text-lol-gold-soft mb-1">
              {winnerName || 'Fim de jogo'}
            </p>
            <p className="text-xs text-white/45 font-mono mb-2">
              {activeMatch.blueKills} – {activeMatch.redKills} kills · {formatMinute(minute)}
            </p>
            {activeMatch.winReason?.summary && (
              <p className="text-[11px] text-lol-gold/90 leading-snug mb-2 max-w-md mx-auto">
                {activeMatch.winReason.summary}
              </p>
            )}
            {activeMatch.winReason?.factors && activeMatch.winReason.factors.length > 0 && (
              <p className="text-[10px] font-mono text-white/40 mb-3">
                {activeMatch.winReason.factors.join(' · ')}
              </p>
            )}
            <div className="flex gap-1.5 justify-center flex-wrap mb-4">
              {winnerPicks.map((p) => (
                <ChampionImage key={p.champion} name={p.champion} variant="pick" locked />
              ))}
            </div>
            {activeMatch.playerRatings && activeMatch.playerRatings.length > 0 && (
              <div className="mb-4 text-left border border-white/15 bg-black/50 rounded-sm p-3 max-h-[200px] overflow-y-auto">
                <div className="text-[10px] uppercase tracking-wider text-lol-gold font-semibold mb-2">
                  Ratings da partida
                </div>
                <div className="space-y-1">
                  {[...activeMatch.playerRatings]
                    .sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
                    .slice(0, 10)
                    .map((r) => (
                      <div
                        key={`${r.side}-${r.role}-${r.name}`}
                        className="flex items-center gap-2 text-[11px]"
                      >
                        <span
                          className={`font-mono font-bold w-8 text-right tabular-nums ${
                            (r.rating ?? 0) >= 8
                              ? 'text-lol-gold'
                              : (r.rating ?? 0) >= 6
                                ? 'text-white/80'
                                : 'text-white/45'
                          }`}
                        >
                          {(r.rating ?? 0).toFixed(1)}
                        </span>
                        <span
                          className={
                            r.side === 'BLUE' ? 'text-sky-400' : 'text-rose-400'
                          }
                        >
                          {r.role}
                        </span>
                        <span className="text-white/80 truncate flex-1">
                          {r.name}
                          {r.mvp ? (
                            <span className="text-lol-gold ml-1 text-[9px]">MVP</span>
                          ) : null}
                        </span>
                        <span className="text-white/35 truncate max-w-[90px] text-[10px]">
                          {r.note}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
            {activeMatch.seriesMapResult && (
              <div className="mb-4 text-left border border-lol-gold/30 bg-black/50 rounded-sm p-3 space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-lol-gold font-semibold">
                  Série de playoffs
                </div>
                <p className="text-[12px] text-white/80 font-mono">
                  Map {activeMatch.seriesMapResult.map_index ?? activeMatch.mapIndex ?? '?'} ·
                  Placar {activeMatch.seriesMapResult.score_display || activeMatch.seriesScoreDisplay || '—'}
                </p>
                <p className="text-[10px] text-white/45">
                  {activeMatch.seriesMapResult.series_complete
                    ? 'Série encerrada — avance o dia para a próxima chave.'
                    : 'Série continua — avance o dia (ou o calendário) para o próximo map.'}
                </p>
              </div>
            )}
            {scoutReport?.summary && (
              <div className="mb-5 text-left border border-cyan-500/30 bg-cyan-950/40 rounded-sm p-3 space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] uppercase tracking-wider text-cyan-300 font-semibold flex items-center gap-1">
                    <Radar className="w-3.5 h-3.5" /> Relatório do Scout
                  </span>
                  {scoutReport.grade && (
                    <span className="text-xs font-mono text-lol-gold">
                      Grade {scoutReport.grade}
                      {scoutReport.accuracy != null
                        ? ` · ${Math.round(scoutReport.accuracy * 100)}%`
                        : ''}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-white/70 leading-snug">{scoutReport.summary}</p>
                <p className="text-[9px] text-white/40 font-mono">
                  {scoutReport.hits ?? 0} acertos · {scoutReport.misses ?? 0} erros ·{' '}
                  {scoutReport.partials ?? 0} parciais
                  {scoutReport.scout_name ? ` · ${scoutReport.scout_name}` : ''}
                </p>
              </div>
            )}
            <button onClick={() => clearActiveMatch()} className="btn-lol-primary px-8 py-3">
              Voltar ao hub
            </button>
          </div>
        </div>
      )}

      <div className="relative z-10 flex flex-col">
        {/* Top bar: timer + live + phases */}
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 sm:px-4 py-2 border-b border-white/10 bg-black/50 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="font-display text-lg sm:text-xl font-bold text-lol-gold-soft tabular-nums tracking-wider">
              {formatMinute(minute)}
            </div>
            {isLive ? (
              <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-emerald-400 font-bold">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
                Live
              </span>
            ) : (
              <span className="text-[10px] uppercase tracking-widest text-white/40">Final</span>
            )}
          </div>

          {/* Speed controls mid-match */}
          {isLive && activeMatch.matchId && (
            <div className="flex items-center gap-1 flex-wrap">
              {(['1x', '2x', '4x', 'instant'] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setLiveSpeed(s)}
                  className={`px-2 py-0.5 text-[9px] font-bold uppercase border rounded-sm transition-all ${
                    (activeMatch.speed || '2x') === s
                      ? 'border-lol-gold bg-lol-gold/25 text-lol-gold'
                      : 'border-white/15 text-white/40 hover:border-white/30'
                  }`}
                >
                  {s === 'instant' ? '>>' : s}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-center gap-1.5">
            {PHASES.map((p) => {
              const order = ['EARLY_GAME', 'MID_GAME', 'LATE_GAME'];
              const cur = order.indexOf(activeMatch.currentPhase);
              const pi = order.indexOf(p.key);
              const cls =
                isVictory || cur > pi
                  ? 'phase-chip-done'
                  : cur === pi
                    ? 'phase-chip-active'
                    : 'phase-chip-idle';
              return (
                <span key={p.key} className={`phase-chip ${cls}`}>
                  {p.label}
                </span>
              );
            })}
          </div>
        </div>

        {/* Phase progress */}
        <div className="h-1 bg-black/60">
          <div
            className="h-full bg-gradient-to-r from-lol-blue-side via-lol-gold to-lol-red-side transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Scoreboard principal */}
        <div className="px-3 sm:px-5 py-4 sm:py-5">
          <div className="grid grid-cols-[1fr_auto_1fr] gap-2 sm:gap-4 items-center">
            {/* BLUE */}
            <div className="min-w-0">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-lol-blue-side mb-0.5">
                Blue side
              </div>
              <div className="font-display font-bold text-sm sm:text-lg text-white truncate leading-tight">
                {activeMatch.blueTeam}
              </div>
              <div className="mt-2">
                <TeamChampRow picks={draft.bluePicks} side="blue" />
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-[10px] font-mono text-white/55">
                <span className="text-lol-gold-soft">
                  {(activeMatch.blueGold / 1000).toFixed(1)}k
                </span>
                <span className="text-white/25">·</span>
                <span title="Dragões">🐉 {activeMatch.blueDragons ?? 0}</span>
                <span title="Barons">👑 {activeMatch.blueBarons ?? 0}</span>
              </div>
            </div>

            {/* CENTER SCORE */}
            <div className="text-center px-1 sm:px-3">
              <div className="font-display text-3xl sm:text-5xl font-black tracking-tight flex items-center justify-center gap-2 sm:gap-3">
                <span
                  className={`text-lol-blue-side tabular-nums ${killPop === 'blue' ? 'kill-pop' : ''}`}
                >
                  {activeMatch.blueKills}
                </span>
                <span className="text-white/15 text-2xl sm:text-3xl">:</span>
                <span
                  className={`text-lol-red-side tabular-nums ${killPop === 'red' ? 'kill-pop' : ''}`}
                >
                  {activeMatch.redKills}
                </span>
              </div>
              <div className="text-[9px] uppercase tracking-widest text-white/35 mt-1 flex items-center justify-center gap-1">
                <Crosshair className="w-3 h-3" /> Kills
              </div>

              {/* Gold bar */}
              <div className="mt-3 w-[120px] sm:w-[180px] mx-auto">
                <div className="h-2.5 bg-black/70 rounded-full overflow-hidden relative border border-white/10 flex">
                  <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/30 z-10" />
                  <div className="w-1/2 h-full relative">
                    {goldLead > 0 && (
                      <div
                        className="absolute right-0 top-0 bottom-0 bg-gradient-to-l from-lol-blue-side to-lol-blue-side/40 transition-all duration-500"
                        style={{ width: `${Math.min(100, (goldLead / 8000) * 100)}%` }}
                      />
                    )}
                  </div>
                  <div className="w-1/2 h-full relative">
                    {goldLead < 0 && (
                      <div
                        className="absolute left-0 top-0 bottom-0 bg-gradient-to-r from-lol-red-side to-lol-red-side/40 transition-all duration-500"
                        style={{ width: `${Math.min(100, (Math.abs(goldLead) / 8000) * 100)}%` }}
                      />
                    )}
                  </div>
                </div>
                <div
                  className={`text-[10px] font-mono mt-1 ${
                    goldLead > 0
                      ? 'text-lol-blue-side'
                      : goldLead < 0
                        ? 'text-lol-red-side'
                        : 'text-white/40'
                  }`}
                >
                  {goldLead > 0 ? 'Blue +' : goldLead < 0 ? 'Red +' : ''}
                  {Math.abs(goldLead).toLocaleString()}g
                </div>
              </div>
            </div>

            {/* RED */}
            <div className="min-w-0 text-right">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-lol-red-side mb-0.5">
                Red side
              </div>
              <div className="font-display font-bold text-sm sm:text-lg text-white truncate leading-tight">
                {activeMatch.redTeam}
              </div>
              <div className="mt-2">
                <TeamChampRow picks={draft.redPicks} side="red" />
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-[10px] font-mono text-white/55 justify-end">
                <span title="Dragões">🐉 {activeMatch.redDragons ?? 0}</span>
                <span title="Barons">👑 {activeMatch.redBarons ?? 0}</span>
                <span className="text-white/25">·</span>
                <span className="text-lol-gold-soft">
                  {(activeMatch.redGold / 1000).toFixed(1)}k
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Body: mapa + feed + sidebar */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-0 border-t border-white/10">
          {/* Minimapa Summoner's Rift */}
          <div className="xl:col-span-4 border-b xl:border-b-0 xl:border-r border-white/10 bg-black/30 p-2 sm:p-3">
            <SummonersRiftMap
              phase={activeMatch.currentPhase}
              minute={minute}
              bluePicks={draft.bluePicks}
              redPicks={draft.redPicks}
              latestEvent={latestMapEvent}
              eventHistory={mapEventHistory}
              mapStructures={activeMatch.mapStructures}
              lanePressure={activeMatch.lanePressure}
              winnerSide={activeMatch.winnerSide}
              isVictory={isVictory}
              blueTeam={activeMatch.blueTeam}
              redTeam={activeMatch.redTeam}
              feedItems={activeMatch.logs.slice(-8).map((log, i) => ({
                id: `feed-${log.timestamp}-${i}-${log.eventType || ''}`,
                text: log.text,
                eventType: log.eventType || log.phase,
                timestamp: log.timestamp,
                side:
                  log.map?.side ||
                  (/\[BLUE\]|\bblue\b/i.test(log.text)
                    ? 'BLUE'
                    : /\[RED\]|\bred\b/i.test(log.text)
                      ? 'RED'
                      : undefined),
              }))}
            />
          </div>

          {/* Event feed */}
          <div className="xl:col-span-5 flex flex-col min-h-[280px] border-b xl:border-b-0 xl:border-r border-white/10 bg-black/35 backdrop-blur-sm">
            <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 border-b border-white/5">
              <div className="flex items-center gap-2">
                <Swords className="w-4 h-4 text-lol-gold" />
                <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
                  Feed da partida
                </span>
              </div>
              <span className="text-[10px] font-mono text-white/30">
                {activeMatch.logs.length} eventos
              </span>
            </div>
            <div
              ref={feedRef}
              className="flex-1 overflow-y-auto max-h-[420px] p-2 sm:p-3 space-y-1 font-mono text-[11px]"
            >
              {activeMatch.logs.map((log, idx) => {
                const isLatest = idx === activeMatch.logs.length - 1;
                return (
                  <div
                    key={`${log.timestamp}-${idx}`}
                    className={`p-2 rounded-sm border flex gap-2 transition-colors ${
                      log.type === 'alert'
                        ? 'border-lol-gold/35 bg-lol-gold/10 text-lol-gold-soft'
                        : log.type === 'warning'
                          ? 'border-lol-red-side/30 bg-red-950/25 text-red-200'
                          : 'border-white/5 bg-black/25 text-white/70'
                    } ${isLatest ? 'event-flash' : ''}`}
                  >
                    <span className="text-white/30 shrink-0 tabular-nums">[{log.timestamp}]</span>
                    <span className="min-w-0">
                      <span className="inline-flex items-center gap-0.5 text-[8px] uppercase border border-current/25 px-1 mr-1.5 opacity-70 align-middle">
                        {log.phase?.replace('_GAME', '') || 'EVT'}
                      </span>
                      <span className="leading-snug">{log.text}</span>
                    </span>
                  </div>
                );
              })}
              {activeMatch.logs.length === 0 && (
                <div className="flex flex-col items-center justify-center py-16 text-white/30 gap-2">
                  <Flame className="w-8 h-8 opacity-40 animate-pulse" />
                  <p className="text-xs">Aguardando primeiros eventos no Rift…</p>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar coach + lineup */}
          <div className="xl:col-span-3 flex flex-col bg-black/40 backdrop-blur-sm">
            {/* Coach */}
            <div className="border-b border-white/10">
              <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/5">
                <MessageSquare className="w-4 h-4 text-lol-gold" />
                <span className="text-xs font-semibold uppercase tracking-wider text-white/70">
                  Centro de comando
                </span>
              </div>
              <div className="p-3 space-y-3">
                {activeMatch.currentPhase === 'EARLY_GAME' ? (
                  <>
                    <p className="text-[11px] text-white/50 leading-relaxed">
                      Comms no Early Game podem virar a lane do mid — ou gerar confusão se abusar.
                    </p>
                    <button
                      onClick={handleCoachComm}
                      className={`btn-lol-primary w-full flex items-center justify-center gap-2 py-2.5 ${
                        commPulse ? 'animate-lock-shine' : ''
                      }`}
                    >
                      <Zap className="w-4 h-4" />
                      Coach Comms
                    </button>
                    <div className="flex gap-1 justify-center">
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className={`w-8 h-1.5 rounded-full ${
                            i < activeMatch.coachCommsUsed
                              ? 'bg-lol-gold shadow-lol-gold'
                              : 'bg-white/10'
                          }`}
                        />
                      ))}
                    </div>
                    <p className="text-[10px] text-center text-white/35 font-mono">
                      {activeMatch.coachCommsUsed}/3 no limite seguro
                      {activeMatch.coachCommsUsed > 3 && (
                        <span className="text-lol-red-side"> · risco de confusão</span>
                      )}
                    </p>
                  </>
                ) : isVictory ? (
                  <p className="text-[11px] text-center text-white/40 py-2">
                    Partida encerrada. Use o overlay de vitória para voltar.
                  </p>
                ) : (
                  <div className="flex items-center gap-2 text-[11px] text-white/40 justify-center py-3">
                    <AlertCircle className="w-4 h-4" />
                    Comms só no Early Game
                  </div>
                )}
                {activeMatch.coachCommsFeedback && (
                  <p
                    className={`text-[10px] p-2.5 border rounded-sm leading-relaxed ${
                      commPulse
                        ? 'border-lol-gold/40 bg-lol-gold/10 text-lol-gold-soft'
                        : 'border-white/10 bg-black/40 text-white/60'
                    }`}
                  >
                    {activeMatch.coachCommsFeedback}
                  </p>
                )}
              </div>
            </div>

            {/* Lineup monitor */}
            <div className="flex-1">
              <div className="px-3 py-2.5 border-b border-white/5">
                <span className="text-xs font-semibold uppercase tracking-wider text-white/60">
                  Lineup · {myTeamName}
                </span>
              </div>
              <div className="p-2 space-y-1">
                {ROLE_ORDER.map((role) => {
                  const player = myPlayers.find((p) => p.role === role);
                  const pick =
                    draft.bluePicks.find((p) => p.role === role) ||
                    draft.redPicks.find((p) => p.role === role);
                  // Prefer pick from manager side
                  const mySidePick =
                    activeMatch.blueTeam === myTeamName
                      ? draft.bluePicks.find((p) => p.role === role)
                      : activeMatch.redTeam === myTeamName
                        ? draft.redPicks.find((p) => p.role === role)
                        : pick;

                  if (!player && !mySidePick) return null;

                  return (
                    <div
                      key={role}
                      className="flex items-center gap-2 p-1.5 bg-black/35 border border-white/5 rounded-sm"
                    >
                      <ChampionImage
                        name={mySidePick?.champion}
                        variant="ban"
                        locked={!!mySidePick}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1 text-[10px] text-white/40">
                          <RoleIcon role={role} size={10} className="text-lol-gold/70" />
                          {ROLE_LABELS[role]}
                        </div>
                        <div className="text-xs font-semibold text-white truncate">
                          {player?.name || '—'}
                        </div>
                        {mySidePick && (
                          <div className="text-[10px] text-lol-gold-soft/80 truncate">
                            {mySidePick.champion}
                          </div>
                        )}
                      </div>
                      {player && (
                        <div className="text-right shrink-0">
                          <div className="text-[8px] uppercase text-white/30">Foco</div>
                          <div
                            className={`font-mono text-xs font-bold ${
                              player.focus > 15
                                ? 'text-emerald-400'
                                : player.focus < 10
                                  ? 'text-lol-red-side'
                                  : 'text-white/80'
                            }`}
                          >
                            {player.focus}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
