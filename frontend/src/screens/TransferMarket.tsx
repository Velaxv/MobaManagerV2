import { useState, useMemo } from 'react';
import { useGameStore, type Player } from '../store/useGameStore';
import { DataGrid, type ColumnDef } from '../components/DataGrid';
import { SlidersHorizontal, UserPlus } from 'lucide-react';

export function TransferMarket() {
  const { playersCache, signPlayer } = useGameStore();

  // Estados dos filtros
  const [selectedRole, setSelectedRole] = useState<string>("ALL");
  const [ageLimitFilter, setAgeLimitFilter] = useState<boolean>(false); // Filtrar apenas legais para LEC (>= 18)
  const [rookieClauseFilter, setRookieClauseFilter] = useState<boolean>(false); // Apenas com Rookie Clause
  const [contractExpiryFilter, setContractExpiryFilter] = useState<boolean>(false); // Apenas com contrato prestes a vencer (< 2 temporadas)

  // Filtra apenas jogadores que NÃO são do nosso time (ou seja, IDs que não começam com "g2-")
  const marketPlayers = useMemo(() => {
    return playersCache.filter(p => !p.id.startsWith("g2-"));
  }, [playersCache]);

  // Aplicação dos filtros do mercado
  const filteredPlayers = useMemo(() => {
    return marketPlayers.filter(p => {
      // Filtro de Role
      if (selectedRole !== "ALL" && p.role !== selectedRole) return false;
      
      // Filtro de Idade (Maior de 18 anos = Legal para LEC)
      if (ageLimitFilter && p.age < 18) return false;

      // Filtro de Rookie Clause
      if (rookieClauseFilter && !p.hasRookieClause) return false;

      // Filtro de expiração de contrato (Agente Livre ou < 2 splits)
      if (contractExpiryFilter && p.contractExpirySeasons >= 2) return false;

      return true;
    });
  }, [marketPlayers, selectedRole, ageLimitFilter, rookieClauseFilter, contractExpiryFilter]);

  // Definição das colunas da tabela DataGrid
  const columns = useMemo<ColumnDef<Player>[]>(() => [
    {
      header: "Jogador",
      accessorKey: "name",
      sortable: true,
      cell: (value, row) => (
        <div className="flex flex-col">
          <span className="font-bold text-neutral-100 font-sans">{value}</span>
          <span className="text-[10px] text-neutral-500 font-mono tracking-tighter uppercase">{row.nationality}</span>
        </div>
      )
    },
    {
      header: "Posição",
      accessorKey: "role",
      sortable: true,
      cell: (value) => (
        <span className="px-1.5 py-0.5 bg-neutral-900 border border-neutral-800 text-xs font-mono font-bold text-neutral-400 rounded-sm">
          {value}
        </span>
      )
    },
    {
      header: "Região",
      accessorKey: "region",
      sortable: true,
    },
    {
      header: "Idade",
      accessorKey: "age",
      sortable: true,
      cell: (value) => (
        <div className="flex items-center gap-1.5">
          <span className="font-mono">{value} anos</span>
          {value < 18 ? (
            <span className="text-[9px] font-mono font-bold bg-red-950/40 text-red-500 border border-red-900/60 px-1 uppercase rounded-sm">
              Ilegal para LEC (menor de 18)
            </span>
          ) : (
            <span className="text-[9px] font-mono font-bold bg-emerald-950/40 text-emerald-400 border border-emerald-900/60 px-1 uppercase rounded-sm">
              LEC OK
            </span>
          )}
        </div>
      )
    },
    {
      header: "Contrato",
      accessorKey: "contractExpirySeasons",
      sortable: true,
      cell: (value) => {
        if (value === 0) {
          return (
            <span className="text-xs font-mono font-bold text-red-500 uppercase bg-red-950/20 border border-red-900/30 px-1.5 py-0.5 rounded">
              Agente Livre
            </span>
          );
        }
        return (
          <span className={`font-mono text-xs ${value === 1 ? 'text-amber-500' : 'text-neutral-400'}`}>
            {value} split(s) restante(s)
          </span>
        );
      }
    },
    {
      header: "Cláusula Rookie",
      accessorKey: "hasRookieClause",
      sortable: true,
      cell: (value) => (
        <span className={`text-xs font-mono px-1.5 py-0.5 border rounded-sm ${value ? 'text-sky-400 bg-sky-950/20 border-sky-900/50' : 'text-neutral-600 bg-neutral-950 border-neutral-900'}`}>
          {value ? "ROOKIE CL." : "N/A"}
        </span>
      )
    },
    {
      header: "Mecânica",
      accessorKey: "mechanics",
      sortable: true,
    },
    {
      header: "Foco",
      accessorKey: "focus",
      sortable: true,
    },
    {
      header: "Ações",
      accessorKey: "id",
      cell: (_, row) => (
        <button
          onClick={() => signPlayer(row.id)}
          disabled={row.age < 18}
          className="flex items-center gap-1 px-3 py-1 bg-neutral-900 border-2 border-neutral-700 hover:border-emerald-500 hover:bg-neutral-800 disabled:opacity-30 disabled:hover:border-neutral-700 disabled:hover:bg-neutral-900 font-mono font-bold text-xs tracking-wider uppercase text-neutral-300 hover:text-emerald-400 transition-all rounded"
        >
          <UserPlus className="w-3.5 h-3.5" />
          Contratar
        </button>
      )
    }
  ], [signPlayer]);

  return (
    <div className="flex flex-col gap-6 p-4">
      {/* Top Banner */}
      <div className="p-4 bg-neutral-950 border-2 border-neutral-800 shadow-[4px_4px_0px_0px_rgba(23,23,23,1)]">
        <h2 className="text-xl font-bold font-mono tracking-tight text-white uppercase">Mercado Global de Transferências</h2>
        <p className="text-xs text-neutral-400 font-mono">
          Pesquise e contrate atletas do meta internacional para a sua equipe do LEC ou Academy.
        </p>
      </div>

      {/* Painel de Filtros Brutalista */}
      <div className="panel-brutal flex flex-col md:flex-row gap-4 items-start md:items-center">
        <div className="flex items-center gap-2 text-xs font-mono font-bold text-neutral-400 uppercase">
          <SlidersHorizontal className="w-4 h-4 text-red-500" />
          <span>Filtros Rápidos</span>
        </div>

        {/* Seleção de Posição */}
        <div className="flex flex-wrap items-center gap-2">
          {["ALL", "TOP", "JUNGLE", "MID", "BOT", "SUPPORT"].map(role => (
            <button
              key={role}
              onClick={() => setSelectedRole(role)}
              className={`px-3 py-1.5 text-xs font-mono font-bold uppercase border-2 transition-all rounded ${
                selectedRole === role
                  ? "bg-red-500 text-black border-black shadow-[2px_2px_0px_0px_rgba(255,255,255,0.15)]"
                  : "bg-neutral-900 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-white"
              }`}
            >
              {role}
            </button>
          ))}
        </div>

        {/* Checkbox Toggles */}
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono font-semibold select-none">
          <label className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={ageLimitFilter}
              onChange={(e) => setAgeLimitFilter(e.target.checked)}
              className="accent-red-500 h-4 w-4 bg-neutral-950 border-2 border-neutral-800 rounded"
            />
            <span>Apenas LEC OK (≥ 18)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={rookieClauseFilter}
              onChange={(e) => setRookieClauseFilter(e.target.checked)}
              className="accent-red-500 h-4 w-4 bg-neutral-950 border-2 border-neutral-800 rounded"
            />
            <span>Apenas Cláusulas Rookie</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer hover:text-white transition-colors">
            <input
              type="checkbox"
              checked={contractExpiryFilter}
              onChange={(e) => setContractExpiryFilter(e.target.checked)}
              className="accent-red-500 h-4 w-4 bg-neutral-950 border-2 border-neutral-800 rounded"
            />
            <span>Vencendo / Livre (≤ 1 split)</span>
          </label>
        </div>
      </div>

      {/* Grid de Jogadores */}
      <div className="h-[480px]">
        <DataGrid<Player>
          data={filteredPlayers}
          columns={columns}
          searchKey="name"
          searchPlaceholder="Buscar jogador pelo nome..."
          rowsPerPage={10}
        />
      </div>
    </div>
  );
}
