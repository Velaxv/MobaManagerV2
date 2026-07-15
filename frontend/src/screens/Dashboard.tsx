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
  Binoculars,
  FileCode2,
  Briefcase,
  UserPlus,
  Heart,
  Target,
  Clapperboard,
  Building2,
  Landmark,
} from 'lucide-react';
import { CalendarDayType, SplitPhase } from '../types/game';
import { ROLE_LABELS } from '../lib/champions';
import { RoleIcon } from '../components/RoleIcon';
import { PlayerPortrait } from '../components/PlayerPortrait';
import { api, type StaffCandidate, type StaffMember } from '../services/api';

export function Dashboard() {
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [offseasonBusy, setOffseasonBusy] = useState<string | null>(null);
  const [offseasonMsg, setOffseasonMsg] = useState<string | null>(null);
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
    lastFinanceEvent,
    training,
    lastTrainingEvent,
    setTrainingPlan,
    scouting,
    lastScoutingEvent,
    clearScout,
    patchStatus,
    practice,
    lastPracticeEvent,
    refreshPractice,
  } = useGameStore();
  const [trainingBusy, setTrainingBusy] = useState(false);
  const [trainingMsg, setTrainingMsg] = useState<string | null>(null);
  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [staffCandidates, setStaffCandidates] = useState<StaffCandidate[]>([]);
  const [staffBusy, setStaffBusy] = useState<string | null>(null);
  const [staffMsg, setStaffMsg] = useState<string | null>(null);
  const [staffPower, setStaffPower] = useState<{
    avg_meta_reading?: number;
    scout_mult?: number;
    coach_comms_max?: number;
    powers?: string[];
    burnout_recovery_bonus?: number;
    draft_confidence?: number;
  } | null>(null);
  const lastBoardReview = useGameStore((s) => s.lastBoardReview);
  const [faCount, setFaCount] = useState<number | null>(null);
  const [org, setOrg] = useState<Record<string, unknown> | null>(null);
  const [orgBusy, setOrgBusy] = useState<string | null>(null);
  const [orgMsg, setOrgMsg] = useState<string | null>(null);

  const myTeamId = manager?.teamId;

  const reloadOrg = async () => {
    if (!myTeamId) return;
    try {
      const o = await api.getTeamOrg(myTeamId);
      setOrg(o);
    } catch {
      /* ignore */
    }
  };
  const isOffseason = splitPhase === SplitPhase.OFFSEASON;

  const reloadStaff = async () => {
    if (!myTeamId) return;
    try {
      const [st, cand] = await Promise.all([
        api.getTeamStaff(myTeamId),
        api.getStaffCandidates(myTeamId),
      ]);
      setStaffList(st.staff || []);
      setStaffPower(st.power || null);
      setStaffCandidates((cand.candidates || []).slice(0, 6));
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    void reloadStaff();
    void refreshPractice?.();
    void reloadOrg();
    if (isOffseason && myTeamId) {
      api
        .getFreeAgents({ managedTeamId: myTeamId })
        .then((r) => setFaCount(r.count ?? r.free_agents?.length ?? 0))
        .catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myTeamId, isOffseason]);
  const fmtK = (n: number) =>
    Math.abs(n) >= 1_000_000
      ? `€${(n / 1_000_000).toFixed(2)}M`
      : `€${(n / 1000).toFixed(0)}k`;

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

      {/* Offseason panel */}
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
            </span>
          </div>
          <div className="p-3 space-y-3">
            <p className="text-[11px] text-white/45 leading-relaxed">
              Renove ou liberte atletas com contrato curto. Janela de transferências{' '}
              <strong className="text-emerald-300/90">aberta</strong>
              {faCount != null ? (
                <>
                  {' '}
                  · <strong className="text-cyan-300/90">{faCount} free agents</strong> no circuito
                </>
              ) : null}
              . Use o Mercado para assinar FA ou comprar de clubes. Depois inicie o novo split.
            </p>
            <button
              type="button"
              onClick={() => setCurrentScreen('MARKET')}
              className="text-[10px] uppercase tracking-wide text-cyan-300 border border-cyan-600/40 px-3 py-1.5 rounded-sm hover:bg-cyan-950/40"
            >
              Abrir mercado (FA + clubes) →
            </button>
            <ul className="flex flex-col gap-1.5 max-h-[240px] overflow-y-auto">
              {offseasonContracts.length === 0 ? (
                <li className="text-xs text-white/35 font-mono p-2">Carregando elenco…</li>
              ) : (
                offseasonContracts.map((c) => (
                  <li
                    key={c.player_id}
                    className={`flex flex-wrap items-center gap-2 p-2.5 rounded-sm border text-[11px] ${
                      c.needs_renewal
                        ? 'border-amber-600/40 bg-amber-950/20'
                        : 'border-white/5 bg-black/30'
                    }`}
                  >
                    <span className="font-semibold text-white min-w-[7rem]">{c.player_name}</span>
                    <span className="text-white/35 font-mono">
                      {c.role} · CA {c.current_ability}
                    </span>
                    <span className="text-white/40 font-mono">
                      {c.remaining_seasons} split(s) · €
                      {Math.round(c.monthly_salary).toLocaleString('pt-BR')}/mês
                    </span>
                    {c.needs_renewal && (
                      <span className="text-[9px] uppercase text-amber-400 border border-amber-600/30 px-1 rounded-sm">
                        Renovar
                      </span>
                    )}
                    <div className="ml-auto flex gap-1.5">
                      <button
                        type="button"
                        disabled={!!offseasonBusy}
                        onClick={async () => {
                          setOffseasonBusy(c.player_id);
                          setOffseasonMsg(null);
                          try {
                            await renewContract(c.player_id, 1);
                            setOffseasonMsg(`Renovado: ${c.player_name}`);
                          } catch (e) {
                            setOffseasonMsg(e instanceof Error ? e.message : 'Erro ao renovar');
                          } finally {
                            setOffseasonBusy(null);
                          }
                        }}
                        className="text-[9px] uppercase tracking-wide text-emerald-400 border border-emerald-700/40 px-2 py-1 rounded-sm hover:bg-emerald-950/40 disabled:opacity-40"
                      >
                        {offseasonBusy === c.player_id ? '…' : '+1 split'}
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
                        className="text-[9px] uppercase tracking-wide text-lol-red-side border border-lol-red-side/30 px-2 py-1 rounded-sm hover:bg-red-950/30 disabled:opacity-40"
                      >
                        Liberar
                      </button>
                    </div>
                  </li>
                ))
              )}
            </ul>
            <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-white/5">
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
                className="btn-lol-primary text-xs py-2 px-4"
              >
                {offseasonBusy === 'split' ? 'Iniciando…' : 'Iniciar novo split'}
              </button>
              {offseasonMsg && (
                <span className="text-[10px] font-mono text-white/50">{offseasonMsg}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Comissão técnica */}
      {myTeamId && (
        <div className="panel-lol border-violet-500/20 bg-violet-950/15">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-violet-300" />
              <span className="text-xs font-semibold uppercase tracking-wider text-violet-200">
                Comissão técnica
              </span>
            </div>
            <span className="text-[10px] text-white/35 font-mono">
              meta {staffPower?.avg_meta_reading ?? '—'} · scout ×
              {staffPower?.scout_mult ?? '—'}
            </span>
          </div>
          <div className="p-3 space-y-3">
            <p className="text-[11px] text-white/45 leading-relaxed">
              Contrate coaches e analysts. Meta reading melhora scouting e o draft scout; performance
              coach ajuda na recuperação de burnout.
            </p>
            <ul className="flex flex-col gap-1.5 max-h-[160px] overflow-y-auto">
              {staffList.length === 0 ? (
                <li className="text-xs text-white/35 font-mono p-2">Sem staff — contrate abaixo.</li>
              ) : (
                staffList.map((s) => (
                  <li
                    key={s.id}
                    className="flex flex-wrap items-center gap-2 p-2 rounded-sm border border-white/5 bg-black/30 text-[11px]"
                  >
                    <span className="font-semibold text-white min-w-[6rem]">{s.name}</span>
                    <span className="text-violet-300/80 text-[10px] uppercase">
                      {s.role_label || s.role}
                    </span>
                    <span className="text-white/35 font-mono">
                      meta {s.meta_reading} · comm {s.communication} · €
                      {Math.round(s.monthly_cost).toLocaleString('pt-BR')}/mês
                    </span>
                    <button
                      type="button"
                      disabled={!!staffBusy}
                      onClick={async () => {
                        if (!confirm(`Demitir ${s.name}?`)) return;
                        setStaffBusy(s.id);
                        setStaffMsg(null);
                        try {
                          await api.fireStaff(myTeamId, s.id);
                          setStaffMsg(`Demitido: ${s.name}`);
                          await reloadStaff();
                        } catch (e) {
                          setStaffMsg(e instanceof Error ? e.message : 'Erro ao demitir');
                        } finally {
                          setStaffBusy(null);
                        }
                      }}
                      className="ml-auto text-[9px] uppercase text-lol-red-side border border-lol-red-side/30 px-2 py-1 rounded-sm hover:bg-red-950/30 disabled:opacity-40"
                    >
                      Demitir
                    </button>
                  </li>
                ))
              )}
            </ul>
            {staffPower && (staffPower.powers?.length || staffPower.coach_comms_max) && (
              <div className="text-[10px] font-mono text-violet-200/70 space-y-0.5 px-1 pb-1">
                <div>
                  Poderes · comms máx {staffPower.coach_comms_max ?? '—'} · scout ×
                  {staffPower.scout_mult ?? '—'} · draft conf{' '}
                  {staffPower.draft_confidence != null
                    ? Math.round(staffPower.draft_confidence * 100)
                    : '—'}
                  %
                </div>
                {(staffPower.powers || []).map((p) => (
                  <div key={p} className="text-white/40">
                    · {p}
                  </div>
                ))}
              </div>
            )}
            <div className="border-t border-white/5 pt-2 space-y-1.5">
              <div className="text-[10px] uppercase tracking-wider text-white/40 flex items-center gap-1">
                <UserPlus className="w-3 h-3" /> Candidatos no mercado
              </div>
              <ul className="flex flex-col gap-1 max-h-[180px] overflow-y-auto">
                {staffCandidates.map((c) => (
                  <li
                    key={c.candidate_id}
                    className="flex flex-wrap items-center gap-2 p-2 rounded-sm border border-violet-500/15 bg-black/25 text-[11px]"
                  >
                    <span className="font-semibold text-white/90">{c.name}</span>
                    <span className="text-violet-300/70 text-[10px]">{c.role_label}</span>
                    <span className="text-white/35 font-mono">
                      meta {c.meta_reading} · taxa €
                      {Math.round(c.signing_fee).toLocaleString('pt-BR')}
                    </span>
                    <button
                      type="button"
                      disabled={!!staffBusy || !c.slot_available}
                      title={!c.slot_available ? 'Slot do cargo cheio' : 'Contratar'}
                      onClick={async () => {
                        setStaffBusy(c.candidate_id);
                        setStaffMsg(null);
                        try {
                          const res = await api.hireStaff(myTeamId, {
                            name: c.name,
                            role: c.role,
                            meta_reading: c.meta_reading,
                            communication: c.communication,
                            candidate_id: c.candidate_id,
                          });
                          setStaffMsg(res.message || `Contratado: ${c.name}`);
                          await reloadStaff();
                          // budget refresh
                          void useGameStore.getState().refreshRosterAndMarket?.();
                        } catch (e) {
                          setStaffMsg(e instanceof Error ? e.message : 'Erro ao contratar');
                        } finally {
                          setStaffBusy(null);
                        }
                      }}
                      className="ml-auto text-[9px] uppercase text-emerald-400 border border-emerald-700/40 px-2 py-1 rounded-sm hover:bg-emerald-950/40 disabled:opacity-40"
                    >
                      {staffBusy === c.candidate_id ? '…' : 'Contratar'}
                    </button>
                  </li>
                ))}
              </ul>
              {staffMsg && (
                <span className="text-[10px] font-mono text-white/50 block">{staffMsg}</span>
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

      {/* Board review semanal */}
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
            {lastBoardReview.rank != null && (
              <span className="text-[10px] font-mono text-white/45">#{lastBoardReview.rank}</span>
            )}
          </div>
          <div className="p-3 text-[12px] text-white/75 leading-snug">
            {lastBoardReview.message}
            {lastBoardReview.fired && (
              <span className="block mt-1 text-red-400 font-semibold">Você foi demitido.</span>
            )}
          </div>
        </div>
      )}

      {/* S4 — Dono da org */}
      {myTeamId && org && (
        <div
          className={`panel-lol ${
            org.fired
              ? 'border-red-600/50 bg-red-950/40'
              : 'border-amber-500/25 bg-amber-950/15'
          }`}
        >
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Landmark className="w-4 h-4 text-amber-300" />
              <span className="text-xs font-semibold uppercase tracking-wider text-amber-200">
                Organização · Board & Sponsors
              </span>
            </div>
            <span className="text-[10px] font-mono text-white/40">
              Brand {Math.round(Number(org.brand) || 0)} · Confiança{' '}
              {String(org.board_confidence_label || '—')}
            </span>
          </div>
          <div className="p-3 space-y-3">
            {org.fired ? (
              <p className="text-sm text-red-300 font-semibold">
                Você foi demitido pela diretoria. Inicie uma nova carreira.
              </p>
            ) : (
              <>
                <div className="grid sm:grid-cols-3 gap-2 text-[11px]">
                  <div className="bg-black/30 border border-white/5 rounded-sm p-2">
                    <div className="text-white/35 text-[9px] uppercase">Board</div>
                    <div className="font-mono text-amber-200 text-lg">
                      {Math.round(Number(org.board_confidence) || 0)}
                    </div>
                    <div className="text-[9px] text-white/40">
                      {String(org.board_goal_label || '')}
                    </div>
                  </div>
                  <div className="bg-black/30 border border-white/5 rounded-sm p-2">
                    <div className="text-white/35 text-[9px] uppercase flex items-center gap-1">
                      <Building2 className="w-3 h-3" /> Facility Nv.
                      {(org.facility as { level?: number })?.level ?? 1}
                    </div>
                    <div className="text-white/80 text-[10px] mt-0.5">
                      {(org.facility as { name?: string })?.name}
                    </div>
                    <div className="font-mono text-[9px] text-white/35">
                      −€{Math.round(Number(org.facility_monthly_cost) || 0).toLocaleString('pt-BR')}
                      /mês
                    </div>
                  </div>
                  <div className="bg-black/30 border border-white/5 rounded-sm p-2">
                    <div className="text-white/35 text-[9px] uppercase">Sponsors</div>
                    <div className="font-mono text-emerald-300 text-lg">
                      +€
                      {Math.round(Number(org.sponsor_monthly_income) || 0).toLocaleString(
                        'pt-BR'
                      )}
                    </div>
                    <div className="text-[9px] text-white/40">/mês líquido org</div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {(
                    (org.goals_available as { id: string; label: string }[]) || []
                  ).map((g) => (
                    <button
                      key={g.id}
                      type="button"
                      disabled={!!orgBusy || org.board_goal === g.id}
                      onClick={async () => {
                        setOrgBusy(g.id);
                        setOrgMsg(null);
                        try {
                          const o = await api.setBoardGoal(myTeamId, g.id);
                          setOrg(o);
                          setOrgMsg(`Meta: ${g.label}`);
                        } catch (e) {
                          setOrgMsg(e instanceof Error ? e.message : 'Erro meta');
                        } finally {
                          setOrgBusy(null);
                        }
                      }}
                      className={`text-[9px] uppercase px-2 py-1 rounded-sm border ${
                        org.board_goal === g.id
                          ? 'border-amber-400/50 bg-amber-950/40 text-amber-200'
                          : 'border-white/10 text-white/45 hover:border-amber-500/30'
                      } disabled:opacity-40`}
                    >
                      {g.id}
                    </button>
                  ))}
                </div>

                <div className="space-y-1">
                  <div className="text-[9px] uppercase text-white/35">Ativos</div>
                  {((org.sponsors as { id: string; name: string; monthly_payout: number; months_left?: number }[]) ||
                    []
                  ).length === 0 && (
                    <p className="text-[10px] text-white/35">Nenhum sponsor ativo.</p>
                  )}
                  {(
                    (org.sponsors as {
                      id: string;
                      name: string;
                      monthly_payout: number;
                      months_left?: number;
                    }[]) || []
                  ).map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center gap-2 text-[10px] bg-black/25 border border-white/5 rounded-sm px-2 py-1"
                    >
                      <span className="font-semibold text-white/85">{s.name}</span>
                      <span className="font-mono text-emerald-400/90">
                        +€{Math.round(s.monthly_payout).toLocaleString('pt-BR')}
                      </span>
                      <span className="text-white/30">{s.months_left ?? '—'}m</span>
                      <button
                        type="button"
                        className="ml-auto text-red-400/80 hover:text-red-300"
                        disabled={!!orgBusy}
                        onClick={async () => {
                          if (!confirm(`Encerrar ${s.name}?`)) return;
                          setOrgBusy(s.id);
                          try {
                            setOrg(await api.dropSponsor(myTeamId, s.id));
                          } catch (e) {
                            setOrgMsg(e instanceof Error ? e.message : 'Erro');
                          } finally {
                            setOrgBusy(null);
                          }
                        }}
                      >
                        Encerrar
                      </button>
                    </div>
                  ))}
                </div>

                <div className="space-y-1">
                  <div className="text-[9px] uppercase text-white/35">Ofertas</div>
                  {(
                    (org.sponsor_offers as {
                      offer_id: string;
                      name: string;
                      monthly_payout: number;
                      goal_label?: string;
                      tier?: string;
                    }[]) || []
                  ).map((o) => (
                    <div
                      key={o.offer_id}
                      className="flex flex-wrap items-center gap-2 text-[10px] border border-amber-500/15 bg-black/20 rounded-sm px-2 py-1.5"
                    >
                      <span className="font-semibold">{o.name}</span>
                      <span className="text-white/30">T{o.tier}</span>
                      <span className="font-mono text-emerald-300">
                        +€{Math.round(o.monthly_payout).toLocaleString('pt-BR')}/m
                      </span>
                      <span className="text-white/35 truncate max-w-[10rem]">
                        {o.goal_label}
                      </span>
                      <button
                        type="button"
                        disabled={!!orgBusy}
                        className="ml-auto text-[9px] uppercase text-emerald-400 border border-emerald-700/40 px-2 py-0.5 rounded-sm"
                        onClick={async () => {
                          setOrgBusy(o.offer_id);
                          try {
                            setOrg(await api.acceptSponsor(myTeamId, o.offer_id));
                            setOrgMsg(`Sponsor: ${o.name}`);
                          } catch (e) {
                            setOrgMsg(e instanceof Error ? e.message : 'Erro');
                          } finally {
                            setOrgBusy(null);
                          }
                        }}
                      >
                        Aceitar
                      </button>
                    </div>
                  ))}
                </div>

                {(org.facility as { next_upgrade_cost?: number; next_name?: string })
                  ?.next_upgrade_cost != null && (
                  <button
                    type="button"
                    disabled={!!orgBusy}
                    className="btn-lol-primary text-[10px] py-1.5 px-3"
                    onClick={async () => {
                      setOrgBusy('fac');
                      setOrgMsg(null);
                      try {
                        const o = await api.upgradeFacility(myTeamId);
                        setOrg(o);
                        if (o.team_budget != null) {
                          /* budget refresh */
                          void useGameStore.getState().refreshRosterAndMarket?.();
                          void useGameStore.getState().refreshFinance?.();
                        }
                        setOrgMsg(
                          `Sede: ${(o.facility as { name?: string })?.name || 'upgrade'}`
                        );
                      } catch (e) {
                        setOrgMsg(e instanceof Error ? e.message : 'Erro upgrade');
                      } finally {
                        setOrgBusy(null);
                      }
                    }}
                  >
                    Upgrade sede → {(org.facility as { next_name?: string }).next_name} (€
                    {Math.round(
                      Number((org.facility as { next_upgrade_cost?: number }).next_upgrade_cost) ||
                        0
                    ).toLocaleString('pt-BR')}
                    )
                  </button>
                )}

                {orgMsg && (
                  <p className="text-[10px] font-mono text-white/45">{orgMsg}</p>
                )}
                <ul className="text-[9px] text-white/35 space-y-0.5 max-h-[60px] overflow-y-auto">
                  {((org.last_events as { text: string }[]) || []).slice(-4).map((e, i) => (
                    <li key={i}>· {e.text}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>
      )}

      {/* Moral + prática pro */}
      {myTeamId && (
        <div className="grid lg:grid-cols-3 gap-3">
          <div className="panel-lol border-rose-500/20 bg-rose-950/15">
            <div className="panel-lol-header">
              <div className="flex items-center gap-2">
                <Heart className="w-4 h-4 text-rose-300" />
                <span className="text-xs font-semibold uppercase tracking-wider text-rose-200">
                  Moral & chemistry
                </span>
              </div>
              <span className="text-[10px] font-mono text-white/35">
                {practice?.morale?.morale_label || '—'} /{' '}
                {practice?.morale?.chemistry_label || '—'}
              </span>
            </div>
            <div className="p-3 space-y-2">
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="bg-black/30 border border-white/5 rounded-sm p-2">
                  <div className="text-white/35 text-[9px] uppercase">Moral</div>
                  <div className="font-mono text-rose-200 text-lg">
                    {practice?.morale?.team_morale != null
                      ? Math.round(practice.morale.team_morale)
                      : '—'}
                  </div>
                </div>
                <div className="bg-black/30 border border-white/5 rounded-sm p-2">
                  <div className="text-white/35 text-[9px] uppercase">Chemistry</div>
                  <div className="font-mono text-violet-200 text-lg">
                    {practice?.morale?.chemistry != null
                      ? Math.round(practice.morale.chemistry)
                      : '—'}
                  </div>
                </div>
                <div className="bg-black/30 border border-white/5 rounded-sm p-2">
                  <div className="text-white/35 text-[9px] uppercase">Bot duo</div>
                  <div className="font-mono text-white/80">
                    {practice?.morale?.bot_synergy != null
                      ? Math.round(practice.morale.bot_synergy)
                      : '—'}
                  </div>
                </div>
                <div className="bg-black/30 border border-white/5 rounded-sm p-2">
                  <div className="text-white/35 text-[9px] uppercase">JG–MID</div>
                  <div className="font-mono text-white/80">
                    {practice?.morale?.jg_mid_synergy != null
                      ? Math.round(practice.morale.jg_mid_synergy)
                      : '—'}
                  </div>
                </div>
              </div>
              {(practice?.morale?.win_streak || practice?.morale?.loss_streak) ? (
                <p className="text-[9px] font-mono text-white/40">
                  Streak V{practice?.morale?.win_streak || 0} / D
                  {practice?.morale?.loss_streak || 0}
                </p>
              ) : null}
              <ul className="space-y-1 max-h-[72px] overflow-y-auto">
                {(practice?.morale?.last_events || []).slice(-3).map((e, i) => (
                  <li key={i} className="text-[10px] text-white/45 leading-snug">
                    · {e.text}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="panel-lol border-orange-500/20 bg-orange-950/15">
            <div className="panel-lol-header">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-orange-300" />
                <span className="text-xs font-semibold uppercase tracking-wider text-orange-200">
                  Último scrim
                </span>
              </div>
            </div>
            <div className="p-3 text-[11px] space-y-1.5">
              {practice?.last_scrim ? (
                <>
                  <p className="font-semibold text-white/90">
                    {(practice.last_scrim as { result?: string }).result === 'WIN' ? (
                      <span className="text-emerald-400">Vitória</span>
                    ) : (
                      <span className="text-red-400">Derrota</span>
                    )}{' '}
                    vs {(practice.last_scrim as { opponent_abbr?: string }).opponent_abbr}{' '}
                    <span className="font-mono text-white/40">
                      {(practice.last_scrim as { score?: string }).score}
                    </span>
                  </p>
                  <p className="text-white/50 leading-relaxed">
                    {(practice.last_scrim as { notes?: string }).notes}
                  </p>
                  {(practice.last_scrim as { intel_gained?: { ban_suggestion?: string } })
                    .intel_gained?.ban_suggestion && (
                    <p className="text-[10px] text-orange-200/80 font-mono">
                      Tip ban:{' '}
                      {
                        (practice.last_scrim as { intel_gained?: { ban_suggestion?: string } })
                          .intel_gained?.ban_suggestion
                      }
                    </p>
                  )}
                </>
              ) : (
                <p className="text-white/35 font-mono">
                  Avance um dia de SCRIM (qui na regular) para treinar vs orgs da liga.
                </p>
              )}
            </div>
          </div>

          <div className="panel-lol border-sky-500/20 bg-sky-950/15">
            <div className="panel-lol-header">
              <div className="flex items-center gap-2">
                <Clapperboard className="w-4 h-4 text-sky-300" />
                <span className="text-xs font-semibold uppercase tracking-wider text-sky-200">
                  VOD / intel
                </span>
              </div>
            </div>
            <div className="p-3 text-[11px] space-y-1.5">
              {practice?.last_vod ? (
                <>
                  <p className="font-semibold text-white/90">
                    Review vs {(practice.last_vod as { opponent_name?: string }).opponent_name}
                  </p>
                  <p className="text-white/50 leading-relaxed">
                    {(practice.last_vod as { summary?: string }).summary}
                  </p>
                  <p className="text-[10px] text-sky-200/80 font-mono">
                    Estilo {(practice.last_vod as { likely_style?: string }).likely_style} ·
                    fraqueza {(practice.last_vod as { weak_role?: string }).weak_role} · ban{' '}
                    {(practice.last_vod as { ban_suggestion?: string }).ban_suggestion}
                  </p>
                </>
              ) : (
                <p className="text-white/35 font-mono">
                  Dias MEDIA / TRAINING geram VOD do próximo adversário.
                </p>
              )}
              {lastPracticeEvent && (
                <p className="text-[9px] text-white/30 font-mono pt-1 border-t border-white/5">
                  Último evento de prática registrado no advance day.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="hub-stat-card">
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
              Folha {fmtK(finance.monthly_payroll)}/mês
            </div>
          )}
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

      {/* Patch meta */}
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

      {/* Scouting */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <Binoculars className="w-4 h-4 text-violet-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
              Scouting · atributos ocultos
            </span>
          </div>
          <span className="text-[10px] text-white/35 font-mono">
            Staff meta {scouting?.staff_power?.avg_meta_reading?.toFixed?.(1) ?? '—'} · mult{' '}
            {scouting?.staff_power?.power_mult?.toFixed?.(2) ?? '—'}
          </span>
        </div>
        <div className="p-3 space-y-2">
          <p className="text-[11px] text-white/45 leading-relaxed">
            Consistência, BMA e PA começam ocultos. Atribua o scout no Elenco ou Mercado; o progresso
            sobe ao avançar o dia (treino/scrim mais rápido).
          </p>
          {scouting?.assignment ? (
            <div className="rounded-sm border border-violet-500/25 bg-violet-950/20 p-2.5 flex flex-wrap items-center gap-2">
              <div className="flex-1 min-w-[10rem]">
                <p className="text-[10px] uppercase text-violet-200/80">Alvo ativo</p>
                <p className="text-sm font-semibold text-white">
                  {scouting.assignment.player_name || '—'}
                  {scouting.assignment.player_role ? (
                    <span className="text-white/40 font-mono text-[10px] ml-1">
                      {scouting.assignment.player_role}
                    </span>
                  ) : null}
                </p>
                <p className="text-[10px] font-mono text-white/50 mt-0.5">
                  {Math.round(scouting.assignment.progress || 0)}% · foco{' '}
                  {scouting.assignment.focus || 'ALL'} ·{' '}
                  {scouting.assignment.days_invested || 0} dia(s)
                </p>
                <div className="stat-bar mt-1 max-w-xs">
                  <div
                    className="stat-bar-fill bg-violet-500/80"
                    style={{
                      width: `${Math.min(100, scouting.assignment.progress || 0)}%`,
                    }}
                  />
                </div>
              </div>
              <button
                type="button"
                onClick={() => void clearScout().catch(() => undefined)}
                className="text-[9px] uppercase tracking-wide text-white/40 border border-white/10 px-2 py-1 rounded-sm hover:border-violet-400/40"
              >
                Cancelar
              </button>
            </div>
          ) : (
            <p className="text-[11px] font-mono text-white/35">
              Nenhum alvo. Abra Elenco ou Mercado e clique em Scoutar.
            </p>
          )}
          {lastScoutingEvent?.events && lastScoutingEvent.events.length > 0 && (
            <ul className="text-[10px] font-mono text-white/45 space-y-0.5">
              {lastScoutingEvent.events.slice(0, 4).map((e, i) => (
                <li key={i}>
                  {e.type === 'SCOUT_COMPLETE' ? (
                    <span className="text-emerald-400">Completo: {e.player_name}</span>
                  ) : (
                    <span>
                      {e.player_name}: +{e.gain ?? 0} → {e.progress_after ?? 0}%
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Treino / desenvolvimento */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <Dumbbell className="w-4 h-4 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
              Treino · CA → PA
            </span>
          </div>
          <span className="text-[10px] text-white/35 font-mono">
            {(training?.focus || 'BALANCED').replace(/_/g, ' ')} ·{' '}
            {training?.intensity || 'NORMAL'}
          </span>
        </div>
        <div className="p-3 space-y-3">
          <p className="text-[11px] text-white/45 leading-relaxed">
            Dias de treino e scrim desenvolvem o elenco. Partidas dão XP aos titulares. Rookies e
            jovens crescem mais; burnout alto freia o progresso.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[9px] uppercase tracking-wide text-white/35 block mb-1">
                Foco
              </label>
              <div className="flex flex-wrap gap-1">
                {(
                  [
                    ['BALANCED', 'Equilíbrio'],
                    ['MECHANICS', 'Mecânica'],
                    ['MENTAL', 'Mental'],
                    ['TEAMPLAY', 'Teamplay'],
                    ['ROLE', 'Role'],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    disabled={trainingBusy}
                    onClick={async () => {
                      setTrainingBusy(true);
                      setTrainingMsg(null);
                      try {
                        await setTrainingPlan(id, training?.intensity || 'NORMAL');
                        setTrainingMsg(`Foco: ${label}`);
                      } catch (e) {
                        setTrainingMsg(e instanceof Error ? e.message : 'Erro');
                      } finally {
                        setTrainingBusy(false);
                      }
                    }}
                    className={`text-[9px] uppercase tracking-wide px-2 py-1 rounded-sm border ${
                      (training?.focus || 'BALANCED') === id
                        ? 'border-sky-400/50 bg-sky-950/40 text-sky-200'
                        : 'border-white/10 text-white/40 hover:border-white/25'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-[9px] uppercase tracking-wide text-white/35 block mb-1">
                Intensidade
              </label>
              <div className="flex flex-wrap gap-1">
                {(
                  [
                    ['LIGHT', 'Leve'],
                    ['NORMAL', 'Normal'],
                    ['HARD', 'Intenso'],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    disabled={trainingBusy}
                    onClick={async () => {
                      setTrainingBusy(true);
                      setTrainingMsg(null);
                      try {
                        await setTrainingPlan(training?.focus || 'BALANCED', id);
                        setTrainingMsg(`Intensidade: ${label}`);
                      } catch (e) {
                        setTrainingMsg(e instanceof Error ? e.message : 'Erro');
                      } finally {
                        setTrainingBusy(false);
                      }
                    }}
                    className={`text-[9px] uppercase tracking-wide px-2 py-1 rounded-sm border ${
                      (training?.intensity || 'NORMAL') === id
                        ? 'border-amber-400/50 bg-amber-950/30 text-amber-200'
                        : 'border-white/10 text-white/40 hover:border-white/25'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {(lastTrainingEvent || training?.last_session) && (
            <div className="rounded-sm border border-white/5 bg-black/30 p-2.5">
              <p className="text-[10px] uppercase tracking-wide text-white/40 mb-1.5">
                Última sessão
                {(lastTrainingEvent?.day_type || training?.last_session?.day_type) && (
                  <span className="font-mono text-white/30 ml-1">
                    · {lastTrainingEvent?.day_type || training?.last_session?.day_type}
                  </span>
                )}
              </p>
              <p className="text-[11px] font-mono text-white/70">
                +
                {lastTrainingEvent?.ca_gains ?? training?.last_session?.ca_gains ?? 0} CA ·{' '}
                {lastTrainingEvent?.attr_gains ?? training?.last_session?.attr_gains ?? 0} attrs ·{' '}
                {lastTrainingEvent?.players_trained ??
                  training?.last_session?.players_trained ??
                  0}{' '}
                atletas
              </p>
              <ul className="mt-1.5 space-y-0.5 max-h-24 overflow-y-auto">
                {(
                  lastTrainingEvent?.gains ||
                  training?.last_session?.gains ||
                  []
                )
                  .slice(0, 8)
                  .map((g, i) => (
                    <li key={`${g.player_name}-${i}`} className="text-[10px] font-mono text-white/50">
                      <span className="text-white/75">{g.player_name}</span>
                      {g.ca_delta ? (
                        <span className="text-emerald-400">
                          {' '}
                          CA {g.ca_before}→{g.ca_after}
                        </span>
                      ) : null}
                      {g.attr_deltas &&
                        Object.keys(g.attr_deltas).length > 0 && (
                          <span className="text-sky-300/80">
                            {' '}
                            ·{' '}
                            {Object.entries(g.attr_deltas)
                              .map(([k, v]) => `${k}+${v}`)
                              .join(', ')}
                          </span>
                        )}
                    </li>
                  ))}
              </ul>
            </div>
          )}
          {trainingMsg && (
            <p className="text-[10px] font-mono text-sky-300/80">{trainingMsg}</p>
          )}
        </div>
      </div>

      {/* Finanças */}
      {finance && (
        <div className="panel-lol">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Wallet className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
                Finanças do clube
              </span>
            </div>
            <span
              className={`text-[9px] uppercase font-mono px-1.5 py-0.5 rounded-sm border ${
                finance.health === 'healthy'
                  ? 'text-emerald-400 border-emerald-700/40'
                  : finance.health === 'tight'
                    ? 'text-sky-300 border-sky-700/40'
                    : finance.health === 'warning'
                      ? 'text-amber-400 border-amber-600/40'
                      : 'text-lol-red-side border-lol-red-side/40'
              }`}
            >
              {finance.health}
            </span>
          </div>
          <div className="p-3 space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="hub-stat-card !p-2.5">
                <div className="text-[9px] text-white/35 uppercase">Receita/mês</div>
                <div className="font-mono font-bold text-emerald-400">
                  +{fmtK(finance.monthly_revenue)}
                </div>
              </div>
              <div className="hub-stat-card !p-2.5">
                <div className="text-[9px] text-white/35 uppercase">Folha/mês</div>
                <div className="font-mono font-bold text-lol-red-side">
                  −{fmtK(finance.monthly_payroll)}
                </div>
              </div>
              <div className="hub-stat-card !p-2.5">
                <div className="text-[9px] text-white/35 uppercase">Saldo/mês</div>
                <div
                  className={`font-mono font-bold ${
                    finance.monthly_net >= 0 ? 'text-emerald-400' : 'text-amber-400'
                  }`}
                >
                  {finance.monthly_net >= 0 ? '+' : ''}
                  {fmtK(finance.monthly_net)}
                </div>
              </div>
              <div className="hub-stat-card !p-2.5">
                <div className="text-[9px] text-white/35 uppercase">Runway</div>
                <div className="font-mono font-bold text-white/80">
                  {finance.runway_months == null
                    ? '∞'
                    : `${finance.runway_months.toFixed(1)} m`}
                </div>
              </div>
            </div>

            {lastFinanceEvent && (
              <div
                className={`text-[11px] font-mono p-2.5 rounded-sm border ${
                  lastFinanceEvent.insolvent
                    ? 'border-lol-red-side/40 bg-red-950/20 text-lol-red-side'
                    : 'border-emerald-700/30 bg-emerald-950/20 text-emerald-300/90'
                }`}
              >
                Último mês:{' '}
                {fmtK(lastFinanceEvent.budget_before || 0)} +
                {fmtK(lastFinanceEvent.revenue || 0)} −
                {fmtK(lastFinanceEvent.paid || 0)} ={' '}
                <strong>{fmtK(lastFinanceEvent.budget_after || 0)}</strong>
                {lastFinanceEvent.insolvent && ' · INSOLVÊNCIA'}
                {lastFinanceEvent.released && lastFinanceEvent.released.length > 0 && (
                  <span className="block mt-1 text-white/50">
                    Liberados: {lastFinanceEvent.released.join(', ')}
                  </span>
                )}
              </div>
            )}

            {finance.wages.length > 0 && (
              <div>
                <p className="text-[10px] uppercase tracking-wider text-white/35 mb-1.5">
                  Maiores salários
                </p>
                <ul className="max-h-28 overflow-y-auto space-y-1">
                  {finance.wages.slice(0, 8).map((w) => (
                    <li
                      key={w.player_id}
                      className="flex justify-between text-[11px] font-mono text-white/60 px-1"
                    >
                      <span className="truncate mr-2">
                        {w.player_name}
                        {w.role ? (
                          <span className="text-white/30"> · {w.role}</span>
                        ) : null}
                      </span>
                      <span className="text-white/80 shrink-0">
                        {fmtK(w.monthly_salary)}/m
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-[9px] text-white/30 font-mono">
              Tick financeiro a cada 28 dias de calendário (receita − folha).
            </p>
          </div>
        </div>
      )}

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
                        <PlayerPortrait name={player.name} size="xs" />
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
