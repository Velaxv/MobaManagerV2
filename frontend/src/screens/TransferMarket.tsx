import { useState, useMemo, useEffect } from 'react';
import { useGameStore, type Player } from '../store/useGameStore';
import { DataGrid, type ColumnDef } from '../components/DataGrid';
import {
  SlidersHorizontal,
  UserPlus,
  ShoppingBag,
  Loader2,
  Handshake,
  X,
} from 'lucide-react';
import { RoleIcon } from '../components/RoleIcon';
import { PlayerPortrait } from '../components/PlayerPortrait';
import { ROLE_LABELS } from '../lib/champions';
import { api } from '../services/api';

type Valuation = {
  asking_fee: number;
  min_fee: number;
  desired_salary: number;
  min_salary: number;
  preferred_seasons: number;
  is_free_agent: boolean;
  current_salary: number;
  seller?: { team_name?: string; team_abbr?: string } | null;
  player_name?: string;
};

type OfferTerms = {
  transfer_fee: number;
  monthly_salary: number;
  seasons: number;
};

function fmtMoney(n: number) {
  if (n >= 1_000_000) return `€${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1000) return `€${(n / 1000).toFixed(0)}k`;
  return `€${Math.round(n)}`;
}

export function TransferMarket() {
  const { marketPlayers, signPlayer, negotiateTransfer, myBudget, myTeamName } =
    useGameStore();

  const [selectedRole, setSelectedRole] = useState<string>('ALL');
  const [ageLimitFilter, setAgeLimitFilter] = useState(false);
  const [rookieClauseFilter, setRookieClauseFilter] = useState(false);
  const [contractExpiryFilter, setContractExpiryFilter] = useState(false);

  const [offerPlayer, setOfferPlayer] = useState<Player | null>(null);
  const [valuation, setValuation] = useState<Valuation | null>(null);
  const [loadingVal, setLoadingVal] = useState(false);
  const [terms, setTerms] = useState<OfferTerms>({
    transfer_fee: 250000,
    monthly_salary: 5000,
    seasons: 2,
  });
  const [busy, setBusy] = useState(false);
  const [negResult, setNegResult] = useState<{
    status: string;
    message: string;
    counter?: OfferTerms | null;
  } | null>(null);

  const filteredPlayers = useMemo(() => {
    return marketPlayers.filter((p) => {
      if (selectedRole !== 'ALL' && p.role !== selectedRole) return false;
      if (ageLimitFilter && p.age < 18) return false;
      if (rookieClauseFilter && !p.hasRookieClause) return false;
      if (contractExpiryFilter && p.contractExpirySeasons >= 2) return false;
      return true;
    });
  }, [marketPlayers, selectedRole, ageLimitFilter, rookieClauseFilter, contractExpiryFilter]);

  useEffect(() => {
    if (!offerPlayer) {
      setValuation(null);
      setNegResult(null);
      return;
    }
    let cancelled = false;
    setLoadingVal(true);
    setNegResult(null);
    (async () => {
      try {
        const v = await api.getTransferValuation(offerPlayer.id);
        if (cancelled) return;
        setValuation(v);
        setTerms({
          transfer_fee: Math.round(v.asking_fee || 250000),
          monthly_salary: Math.round(v.desired_salary || 5000),
          seasons: v.preferred_seasons || 2,
        });
      } catch {
        if (!cancelled) setValuation(null);
      } finally {
        if (!cancelled) setLoadingVal(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [offerPlayer]);

  const openOffer = (p: Player) => {
    setOfferPlayer(p);
  };

  const closeOffer = () => {
    setOfferPlayer(null);
    setValuation(null);
    setNegResult(null);
  };

  const handleNegotiate = async () => {
    if (!offerPlayer) return;
    setBusy(true);
    setNegResult(null);
    try {
      const res = await negotiateTransfer(offerPlayer.id, terms);
      setNegResult({
        status: res.status,
        message: res.message,
        counter: res.counter || null,
      });
    } catch (e) {
      setNegResult({
        status: 'error',
        message: e instanceof Error ? e.message : 'Falha na negociação',
      });
    } finally {
      setBusy(false);
    }
  };

  const applyCounterAndAccept = async () => {
    if (!offerPlayer || !negResult?.counter) return;
    const c = { ...negResult.counter };
    setTerms(c);
    setBusy(true);
    setNegResult(null);
    try {
      // Contra-proposta costuma fechar; tenta assinar direto
      const res = await negotiateTransfer(offerPlayer.id, c);
      if (res.status === 'accepted') {
        await signPlayer(offerPlayer.id, c);
        closeOffer();
      } else {
        setNegResult({
          status: res.status,
          message: res.message,
          counter: res.counter || null,
        });
      }
    } catch (e) {
      setNegResult({
        status: 'error',
        message: e instanceof Error ? e.message : 'Falha ao aceitar contra',
      });
    } finally {
      setBusy(false);
    }
  };

  const handleConfirmSign = async () => {
    if (!offerPlayer) return;
    setBusy(true);
    try {
      await signPlayer(offerPlayer.id, terms);
      closeOffer();
    } catch {
      /* alert no store */
    } finally {
      setBusy(false);
    }
  };

  const columns = useMemo<ColumnDef<Player>[]>(
    () => [
      {
        header: 'Jogador',
        accessorKey: 'name',
        sortable: true,
        cell: (value, row) => (
          <div className="flex items-center gap-2.5">
            <PlayerPortrait name={String(value)} size="sm" />
            <div className="flex flex-col min-w-0">
              <span className="font-semibold text-white truncate">{value}</span>
              <span className="text-[10px] text-white/40 font-mono uppercase tracking-tighter">
                {row.nationality}
              </span>
            </div>
          </div>
        ),
      },
      {
        header: 'Posição',
        accessorKey: 'role',
        sortable: true,
        cell: (value) => (
          <span className="inline-flex items-center gap-1 role-pill">
            <RoleIcon role={String(value)} size={11} />
            {ROLE_LABELS[String(value)] || value}
          </span>
        ),
      },
      {
        header: 'CA',
        accessorKey: 'currentAbility',
        sortable: true,
        cell: (value) => (
          <span className="font-mono font-bold text-emerald-400">{value}</span>
        ),
      },
      {
        header: 'Idade',
        accessorKey: 'age',
        sortable: true,
        cell: (value) => (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-mono">{value}</span>
            {value < 18 ? (
              <span className="text-[9px] font-mono font-bold bg-red-950/40 text-red-400 border border-red-900/50 px-1 uppercase rounded-sm">
                Academy
              </span>
            ) : (
              <span className="text-[9px] font-mono font-bold bg-emerald-950/40 text-emerald-400 border border-emerald-900/50 px-1 uppercase rounded-sm">
                OK
              </span>
            )}
          </div>
        ),
      },
      {
        header: 'Contrato',
        accessorKey: 'contractExpirySeasons',
        sortable: true,
        cell: (value) => {
          if (value === 0) {
            return (
              <span className="text-xs font-mono font-bold text-lol-red-side uppercase bg-red-950/20 border border-red-900/30 px-1.5 py-0.5 rounded">
                Livre
              </span>
            );
          }
          return (
            <span
              className={`font-mono text-xs ${value === 1 ? 'text-amber-400' : 'text-white/50'}`}
            >
              {value} split(s)
            </span>
          );
        },
      },
      {
        header: 'Salário',
        accessorKey: 'monthlySalary',
        sortable: true,
        cell: (value) => (
          <span className="font-mono text-xs text-white/60">
            {value ? fmtMoney(Number(value)) : '—'}
          </span>
        ),
      },
      {
        header: 'Ações',
        accessorKey: 'id',
        cell: (_, row) => (
          <button
            onClick={() => openOffer(row)}
            disabled={row.age < 16}
            className="btn-lol-primary py-1 px-2.5 flex items-center gap-1 disabled:opacity-30"
          >
            <Handshake className="w-3.5 h-3.5" />
            Ofertar
          </button>
        ),
      },
    ],
    []
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="panel-lol relative overflow-hidden">
        <div className="absolute inset-0 bg-lol-header pointer-events-none" />
        <div className="relative panel-lol-header !bg-transparent">
          <div className="flex items-center gap-3 py-1">
            <div className="team-crest">
              <ShoppingBag className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display font-bold text-base text-lol-gold-soft uppercase tracking-wide">
                Mercado de transferências
              </h2>
              <p className="text-[10px] text-white/40 font-mono mt-0.5">
                CBLOL 2026 · {myTeamName} · orçamento{' '}
                <span className="text-emerald-400">€{(myBudget / 1_000_000).toFixed(2)}M</span>
                {' · '}negociação de taxa + salário + duração
              </p>
            </div>
          </div>
        </div>

        <div className="relative p-3 flex flex-col md:flex-row gap-3 items-start md:items-center border-t border-white/5 bg-black/20">
          <div className="flex items-center gap-2 text-[10px] font-semibold text-white/40 uppercase tracking-wider shrink-0">
            <SlidersHorizontal className="w-3.5 h-3.5 text-lol-gold" />
            Filtros
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {['ALL', 'TOP', 'JUNGLE', 'MID', 'BOT', 'SUPPORT'].map((role) => (
              <button
                key={role}
                onClick={() => setSelectedRole(role)}
                className={`px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide border rounded-sm transition-all flex items-center gap-1 ${
                  selectedRole === role
                    ? 'border-lol-gold bg-lol-gold/20 text-lol-gold'
                    : 'border-white/10 text-white/45 hover:border-white/25'
                }`}
              >
                {role !== 'ALL' && <RoleIcon role={role} size={11} active={selectedRole === role} />}
                {role === 'ALL' ? 'Todos' : ROLE_LABELS[role] || role}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono text-white/50">
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-white">
              <input
                type="checkbox"
                checked={ageLimitFilter}
                onChange={(e) => setAgeLimitFilter(e.target.checked)}
                className="accent-lol-gold"
              />
              Titular ≥18
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-white">
              <input
                type="checkbox"
                checked={rookieClauseFilter}
                onChange={(e) => setRookieClauseFilter(e.target.checked)}
                className="accent-lol-gold"
              />
              Rookie clause
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-white">
              <input
                type="checkbox"
                checked={contractExpiryFilter}
                onChange={(e) => setContractExpiryFilter(e.target.checked)}
                className="accent-lol-gold"
              />
              Contrato ≤1 split
            </label>
          </div>
          <div className="md:ml-auto text-[10px] font-mono text-white/30">
            {filteredPlayers.length} jogador(es)
          </div>
        </div>
      </div>

      <div className="panel-lol">
        <div className="p-2 h-[500px]">
          <DataGrid<Player>
            data={filteredPlayers}
            columns={columns}
            searchKey="name"
            searchPlaceholder="Buscar jogador…"
            rowsPerPage={10}
          />
        </div>
      </div>

      {/* Modal de oferta */}
      {offerPlayer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md panel-lol border-lol-gold/30 shadow-lol-gold max-h-[90vh] overflow-y-auto">
            <div className="panel-lol-header">
              <div className="flex items-center gap-2 min-w-0">
                <PlayerPortrait name={offerPlayer.name} size="sm" />
                <div className="min-w-0">
                  <div className="font-semibold text-sm text-white truncate">
                    {offerPlayer.name}
                  </div>
                  <div className="text-[10px] text-white/40 font-mono">
                    CA {offerPlayer.currentAbility} · {ROLE_LABELS[offerPlayer.role]} ·{' '}
                    {offerPlayer.age}a
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={closeOffer}
                className="text-white/40 hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3">
              {loadingVal ? (
                <div className="flex items-center gap-2 text-white/40 text-xs py-6 justify-center">
                  <Loader2 className="w-4 h-4 animate-spin" /> Avaliando mercado…
                </div>
              ) : (
                <>
                  {valuation && (
                    <div className="text-[11px] font-mono text-white/50 space-y-1 p-2.5 bg-black/30 border border-white/5 rounded-sm">
                      <div>
                        {valuation.is_free_agent
                          ? 'Agente livre · bônus de assinatura'
                          : `Clube: ${valuation.seller?.team_abbr || valuation.seller?.team_name || '—'}`}
                      </div>
                      <div>
                        Pedido: <span className="text-lol-gold">{fmtMoney(valuation.asking_fee)}</span>
                        {' · '}sal. {fmtMoney(valuation.desired_salary)}/m
                        {' · '}
                        {valuation.preferred_seasons} splits
                      </div>
                      <div className="text-white/30">
                        Mínimo: {fmtMoney(valuation.min_fee)} / {fmtMoney(valuation.min_salary)}
                        /m
                      </div>
                    </div>
                  )}

                  <label className="block space-y-1">
                    <span className="text-[10px] uppercase text-white/40 tracking-wider">
                      Taxa de transferência
                    </span>
                    <input
                      type="number"
                      min={0}
                      step={10000}
                      value={terms.transfer_fee}
                      onChange={(e) =>
                        setTerms((t) => ({
                          ...t,
                          transfer_fee: Number(e.target.value) || 0,
                        }))
                      }
                      className="w-full bg-black/50 border border-white/15 rounded-sm px-3 py-2 text-sm font-mono text-white focus:border-lol-gold outline-none"
                    />
                  </label>

                  <label className="block space-y-1">
                    <span className="text-[10px] uppercase text-white/40 tracking-wider">
                      Salário mensal (€)
                    </span>
                    <input
                      type="number"
                      min={0}
                      step={500}
                      value={terms.monthly_salary}
                      onChange={(e) =>
                        setTerms((t) => ({
                          ...t,
                          monthly_salary: Number(e.target.value) || 0,
                        }))
                      }
                      className="w-full bg-black/50 border border-white/15 rounded-sm px-3 py-2 text-sm font-mono text-white focus:border-lol-gold outline-none"
                    />
                  </label>

                  <label className="block space-y-1">
                    <span className="text-[10px] uppercase text-white/40 tracking-wider">
                      Duração (splits)
                    </span>
                    <div className="flex gap-1.5">
                      {[1, 2, 3, 4].map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => setTerms((t) => ({ ...t, seasons: s }))}
                          className={`flex-1 py-2 text-xs font-bold border rounded-sm ${
                            terms.seasons === s
                              ? 'border-lol-gold bg-lol-gold/15 text-lol-gold'
                              : 'border-white/10 text-white/50 hover:border-white/25'
                          }`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </label>

                  <p className="text-[10px] font-mono text-white/35">
                    Seu caixa: {fmtMoney(myBudget)} · oferta total taxa{' '}
                    <span
                      className={
                        terms.transfer_fee > myBudget
                          ? 'text-lol-red-side'
                          : 'text-emerald-400'
                      }
                    >
                      {fmtMoney(terms.transfer_fee)}
                    </span>
                  </p>

                  {negResult && (
                    <div
                      className={`text-[11px] p-2.5 rounded-sm border font-mono ${
                        negResult.status === 'accepted'
                          ? 'border-emerald-700/40 bg-emerald-950/25 text-emerald-300'
                          : negResult.status === 'counter'
                            ? 'border-amber-600/40 bg-amber-950/20 text-amber-200'
                            : 'border-lol-red-side/40 bg-red-950/20 text-lol-red-side'
                      }`}
                    >
                      {negResult.message}
                      {negResult.counter && (
                        <div className="mt-1.5 text-white/70">
                          Contra: {fmtMoney(negResult.counter.transfer_fee)} ·{' '}
                          {fmtMoney(negResult.counter.monthly_salary)}/m ·{' '}
                          {negResult.counter.seasons} splits
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex flex-col sm:flex-row gap-2 pt-1">
                    {negResult?.status === 'accepted' ? (
                      <button
                        type="button"
                        disabled={busy || terms.transfer_fee > myBudget}
                        onClick={() => void handleConfirmSign()}
                        className="btn-lol-primary flex-1 flex items-center justify-center gap-2 py-2.5"
                      >
                        {busy ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <UserPlus className="w-4 h-4" />
                        )}
                        Confirmar contratação
                      </button>
                    ) : (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void handleNegotiate()}
                        className="btn-lol-primary flex-1 flex items-center justify-center gap-2 py-2.5"
                      >
                        {busy ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Handshake className="w-4 h-4" />
                        )}
                        Enviar oferta
                      </button>
                    )}
                    {negResult?.status === 'counter' && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void applyCounterAndAccept()}
                        className="btn-lol-secondary flex-1 py-2.5 text-xs"
                      >
                        Aceitar contra-proposta
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={closeOffer}
                      className="px-4 py-2.5 text-xs text-white/40 hover:text-white border border-white/10 rounded-sm"
                    >
                      Cancelar
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
