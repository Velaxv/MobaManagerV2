import { useState, useMemo } from 'react';
import { useGameStore, type Player } from '../store/useGameStore';
import { DataGrid, type ColumnDef } from '../components/DataGrid';
import { SlidersHorizontal, UserPlus, ShoppingBag } from 'lucide-react';
import { RoleIcon } from '../components/RoleIcon';
import { ChampionImage } from '../components/ChampionImage';
import { ROLE_LABELS } from '../lib/champions';

export function TransferMarket() {
  const { marketPlayers, signPlayer, myBudget, myTeamName } = useGameStore();

  const [selectedRole, setSelectedRole] = useState<string>('ALL');
  const [ageLimitFilter, setAgeLimitFilter] = useState(false);
  const [rookieClauseFilter, setRookieClauseFilter] = useState(false);
  const [contractExpiryFilter, setContractExpiryFilter] = useState(false);
  const [signingId, setSigningId] = useState<string | null>(null);

  const filteredPlayers = useMemo(() => {
    return marketPlayers.filter((p) => {
      if (selectedRole !== 'ALL' && p.role !== selectedRole) return false;
      if (ageLimitFilter && p.age < 18) return false;
      if (rookieClauseFilter && !p.hasRookieClause) return false;
      if (contractExpiryFilter && p.contractExpirySeasons >= 2) return false;
      return true;
    });
  }, [marketPlayers, selectedRole, ageLimitFilter, rookieClauseFilter, contractExpiryFilter]);

  const columns = useMemo<ColumnDef<Player>[]>(
    () => [
      {
        header: 'Jogador',
        accessorKey: 'name',
        sortable: true,
        cell: (value, row) => (
          <div className="flex items-center gap-2.5">
            <ChampionImage
              name={row.championPool?.[0]?.champion}
              variant="ban"
              className="!w-9 !h-9"
            />
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
        header: 'Rookie',
        accessorKey: 'hasRookieClause',
        sortable: true,
        cell: (value) => (
          <span
            className={`text-[10px] font-mono px-1.5 py-0.5 border rounded-sm ${
              value
                ? 'text-sky-400 bg-sky-950/20 border-sky-900/50'
                : 'text-white/25 bg-black/20 border-white/5'
            }`}
          >
            {value ? 'CLÁUSULA' : '—'}
          </span>
        ),
      },
      {
        header: 'Mec',
        accessorKey: 'mechanics',
        sortable: true,
      },
      {
        header: 'Ações',
        accessorKey: 'id',
        cell: (_, row) => (
          <button
            onClick={async () => {
              setSigningId(row.id);
              try {
                await signPlayer(row.id);
              } finally {
                setSigningId(null);
              }
            }}
            disabled={row.age < 16 || signingId === row.id || myBudget < 250000}
            className="btn-lol-primary py-1 px-2.5 flex items-center gap-1 disabled:opacity-30"
          >
            <UserPlus className="w-3.5 h-3.5" />
            {signingId === row.id ? '…' : 'Contratar'}
          </button>
        ),
      },
    ],
    [signPlayer, signingId, myBudget]
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
                {' · '}taxa base €250k
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
    </div>
  );
}
