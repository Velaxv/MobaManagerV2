import { useEffect, useState } from 'react';
import { Landmark, Building2, Wallet } from 'lucide-react';
import { useGameStore } from '../store/useGameStore';
import { api } from '../services/api';
import { HubPageHeader } from '../components/HubPageHeader';

/**
 * Organização: board, sponsors, facility e finanças do clube.
 */
export function Organization() {
  const manager = useGameStore((s) => s.manager);
  const finance = useGameStore((s) => s.finance);
  const lastFinanceEvent = useGameStore((s) => s.lastFinanceEvent);
  const lastBoardReview = useGameStore((s) => s.lastBoardReview);
  const myBudget = useGameStore((s) => s.myBudget);
  const myTeamId = manager?.teamId;

  const [org, setOrg] = useState<Record<string, unknown> | null>(null);
  const [orgBusy, setOrgBusy] = useState<string | null>(null);
  const [orgMsg, setOrgMsg] = useState<string | null>(null);

  const fmtK = (n: number) =>
    Math.abs(n) >= 1_000_000
      ? `€${(n / 1_000_000).toFixed(2)}M`
      : `€${(n / 1000).toFixed(0)}k`;

  const reloadOrg = async () => {
    if (!myTeamId) return;
    try {
      setOrg(await api.getTeamOrg(myTeamId));
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    void reloadOrg();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myTeamId]);

  return (
    <div className="flex flex-col gap-4">
      <HubPageHeader
        icon={Landmark}
        eyebrow="Club HQ"
        title="Organização"
        subtitle="Dinheiro e política: board, sponsors, sede e finanças. O Rift é no Draft/Live; a pressão de carreira fica aqui."
        actions={
          <div className="flex items-center gap-2">
            {finance?.health && finance.health !== 'healthy' && (
              <span
                className={`text-[9px] uppercase font-mono px-2 py-1 rounded-sm border ${
                  finance.health === 'critical'
                    ? 'text-lol-red-side border-lol-red-side/40 bg-red-950/30'
                    : 'text-amber-300 border-amber-600/40 bg-amber-950/25'
                }`}
              >
                {finance.health}
              </span>
            )}
            <div className="text-right px-3 py-1.5 rounded-sm bg-black/30 border border-white/5">
              <span className="text-[9px] uppercase text-white/35 block">Caixa</span>
              <span className="font-mono text-sm font-bold text-emerald-400">
                €{(myBudget / 1_000_000).toFixed(2)}M
              </span>
            </div>
          </div>
        }
      />

      {/* Finanças no topo — hierarquia: $ primeiro, depois board/sponsors */}
      {finance && (
        <div className="panel-lol border-emerald-800/25">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Wallet className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-white">
                Finanças · prioridade
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
          <div className="p-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
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
                {finance.runway_months == null ? '∞' : `${finance.runway_months.toFixed(1)} m`}
              </div>
            </div>
          </div>
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
            <span className="text-xs font-semibold uppercase tracking-wider text-white">
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

      {myTeamId && org && (
        <div
          className={`panel-lol ${
            org.fired ? 'border-red-600/50 bg-red-950/40' : 'border-amber-500/25 bg-amber-950/15'
          }`}
        >
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Landmark className="w-4 h-4 text-amber-300" />
              <span className="text-xs font-semibold uppercase tracking-wider text-amber-200">
                Board & Sponsors
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
                      {Math.round(Number(org.sponsor_monthly_income) || 0).toLocaleString('pt-BR')}
                    </div>
                    <div className="text-[9px] text-white/40">/mês</div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {((org.goals_available as { id: string; label: string }[]) || []).map((g) => (
                    <button
                      key={g.id}
                      type="button"
                      disabled={!!orgBusy || org.board_goal === g.id}
                      onClick={async () => {
                        setOrgBusy(g.id);
                        setOrgMsg(null);
                        try {
                          setOrg(await api.setBoardGoal(myTeamId, g.id));
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
                      title={g.label}
                    >
                      {g.id}
                    </button>
                  ))}
                </div>

                <div className="space-y-1">
                  <div className="text-[9px] uppercase text-white/35">Sponsors ativos</div>
                  {(
                    (org.sponsors as {
                      id: string;
                      name: string;
                      monthly_payout: number;
                      months_left?: number;
                      goal_detail?: string;
                      on_track?: boolean;
                    }[]) || []
                  ).length === 0 && (
                    <p className="text-[10px] text-white/35">Nenhum sponsor ativo.</p>
                  )}
                  {(
                    (org.sponsors as {
                      id: string;
                      name: string;
                      monthly_payout: number;
                      months_left?: number;
                      goal_detail?: string;
                      on_track?: boolean;
                    }[]) || []
                  ).map((s) => (
                    <div
                      key={s.id}
                      className="flex flex-wrap items-center gap-2 text-[10px] bg-black/25 border border-white/5 rounded-sm px-2 py-1.5"
                    >
                      <span className="font-semibold text-white/85">{s.name}</span>
                      <span className="font-mono text-emerald-400/90">
                        +€{Math.round(s.monthly_payout).toLocaleString('pt-BR')}
                      </span>
                      <span className="text-white/30">{s.months_left ?? '—'}m</span>
                      {s.goal_detail && (
                        <span
                          className={`text-[9px] ${
                            s.on_track === false ? 'text-amber-300/80' : 'text-white/35'
                          }`}
                        >
                          {s.goal_detail}
                        </span>
                      )}
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
                      goal_detail?: string;
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
                      <span className="text-white/35 truncate max-w-[14rem]">
                        {o.goal_detail || o.goal_label}
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
                        void useGameStore.getState().refreshRosterAndMarket?.();
                        void useGameStore.getState().refreshFinance?.();
                        setOrgMsg(`Sede: ${(o.facility as { name?: string })?.name || 'upgrade'}`);
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
                        0,
                    ).toLocaleString('pt-BR')}
                    )
                  </button>
                )}

                {orgMsg && <p className="text-[10px] font-mono text-white/45">{orgMsg}</p>}
                <ul className="text-[9px] text-white/35 space-y-0.5 max-h-[72px] overflow-y-auto">
                  {((org.last_events as { text: string }[]) || []).slice(-6).map((e, i) => (
                    <li key={i}>· {e.text}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>
      )}

      {/* Detalhe de folha / último tick — abaixo de board */}
      {finance && (
        <div className="panel-lol">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Wallet className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-white">
                Folha e histórico
              </span>
            </div>
          </div>
          <div className="p-3 space-y-3">
            {lastFinanceEvent && (
              <div
                className={`text-[11px] font-mono p-2.5 rounded-sm border ${
                  lastFinanceEvent.insolvent
                    ? 'border-lol-red-side/40 bg-red-950/20 text-lol-red-side'
                    : 'border-emerald-700/30 bg-emerald-950/20 text-emerald-300/90'
                }`}
              >
                Último mês: {fmtK(lastFinanceEvent.budget_before || 0)} +
                {fmtK(lastFinanceEvent.revenue || 0)} −{fmtK(lastFinanceEvent.paid || 0)} ={' '}
                <strong>{fmtK(lastFinanceEvent.budget_after || 0)}</strong>
                {lastFinanceEvent.insolvent && ' · INSOLVÊNCIA'}
              </div>
            )}

            {finance.wages.length > 0 && (
              <div>
                <p className="text-[10px] uppercase tracking-wider text-white/35 mb-1.5">
                  Maiores salários
                </p>
                <ul className="max-h-32 overflow-y-auto space-y-1">
                  {finance.wages.slice(0, 10).map((w) => (
                    <li
                      key={w.player_id}
                      className="flex justify-between text-[11px] font-mono text-white/60 px-1"
                    >
                      <span className="truncate mr-2">
                        {w.player_name}
                        {w.role ? <span className="text-white/30"> · {w.role}</span> : null}
                      </span>
                      <span className="text-white/80 shrink-0">{fmtK(w.monthly_salary)}/m</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[9px] text-white/30 font-mono">
              Tick financeiro a cada 28 dias (receita − folha + sponsors/facility).
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
