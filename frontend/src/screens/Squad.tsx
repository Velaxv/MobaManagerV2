import { useMemo, useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { ROLE_LABELS } from '../lib/champions';
import { ChampionImage } from '../components/ChampionImage';
import { PlayerPortrait } from '../components/PlayerPortrait';
import { RoleIcon } from '../components/RoleIcon';
import { Users, Search, Binoculars, ArrowUpCircle, ArrowDownCircle, GraduationCap } from 'lucide-react';
import { PlayerRole } from '../types/game';
import { getPlayerPhotoUrl } from '../lib/playerPhotoMap';
import type { Player } from '../store/useGameStore';

function formatHiddenAttr(
  known: boolean | undefined,
  value: number | null | undefined,
  min: number | null | undefined,
  max: number | null | undefined,
  digits = 0
): string {
  if (known && value != null) {
    return digits > 0 ? Number(value).toFixed(digits) : String(Math.round(Number(value)));
  }
  if (min != null && max != null) {
    const a = digits > 0 ? Number(min).toFixed(digits) : String(Math.round(Number(min)));
    const b = digits > 0 ? Number(max).toFixed(digits) : String(Math.round(Number(max)));
    return `${a}–${b}`;
  }
  return '???';
}

function formatPa(p: Player): string {
  return formatHiddenAttr(
    p.potentialAbilityKnown,
    p.potentialAbility,
    p.potentialAbilityMin,
    p.potentialAbilityMax
  );
}

const ROLE_ORDER = [
  PlayerRole.TOP,
  PlayerRole.JUNGLE,
  PlayerRole.MID,
  PlayerRole.BOT,
  PlayerRole.SUPPORT,
];

export function Squad() {
  const myPlayers = useGameStore((s) => s.myPlayers);
  const myTeamName = useGameStore((s) => s.myTeamName);
  const scouting = useGameStore((s) => s.scouting);
  const assignScout = useGameStore((s) => s.assignScout);
  const clearScout = useGameStore((s) => s.clearScout);
  const promotePlayer = useGameStore((s) => s.promotePlayer);
  const demotePlayer = useGameStore((s) => s.demotePlayer);
  const [filterRole, setFilterRole] = useState<string>('ALL');
  const [search, setSearch] = useState('');
  const [scoutBusy, setScoutBusy] = useState<string | null>(null);
  const [lineupBusy, setLineupBusy] = useState<string | null>(null);
  const [lineupMsg, setLineupMsg] = useState<string | null>(null);

  const starters = useMemo(() => {
    return ROLE_ORDER.map((role) => {
      const marked = myPlayers.find((p) => p.role === role && p.isStarter);
      if (marked) return marked;
      return myPlayers.find((p) => p.role === role);
    }).filter(Boolean) as typeof myPlayers;
  }, [myPlayers]);

  const starterIds = useMemo(() => new Set(starters.map((p) => p.id)), [starters]);

  const bench = useMemo(() => {
    return myPlayers.filter(
      (p) => !starterIds.has(p.id) && !p.isRookie && !p.name.includes('Academy')
    );
  }, [myPlayers, starterIds]);

  const academy = useMemo(() => {
    return myPlayers.filter(
      (p) => !starterIds.has(p.id) && (p.isRookie || p.name.includes('Academy'))
    );
  }, [myPlayers, starterIds]);

  const filteredBench = useMemo(() => {
    return bench.filter((p) => {
      if (filterRole !== 'ALL' && p.role !== filterRole) return false;
      if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [bench, filterRole, search]);

  const filteredAcademy = useMemo(() => {
    return academy.filter((p) => {
      if (filterRole !== 'ALL' && p.role !== filterRole) return false;
      if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [academy, filterRole, search]);

  const rookieClauses = useMemo(
    () => myPlayers.filter((p) => p.hasRookieClause),
    [myPlayers]
  );

  const runPromote = async (p: Player) => {
    setLineupBusy(p.id);
    setLineupMsg(null);
    try {
      await promotePlayer(p.id);
      setLineupMsg(`${p.name} promovido a titular.`);
    } catch (e) {
      setLineupMsg(e instanceof Error ? e.message : 'Erro ao promover');
    } finally {
      setLineupBusy(null);
    }
  };

  const runDemote = async (p: Player) => {
    setLineupBusy(p.id);
    setLineupMsg(null);
    try {
      await demotePlayer(p.id);
      setLineupMsg(`${p.name} rebaixado da lineup.`);
    } catch (e) {
      setLineupMsg(e instanceof Error ? e.message : 'Erro ao rebaixar');
    } finally {
      setLineupBusy(null);
    }
  };

  const heroPhoto =
    getPlayerPhotoUrl(starters[2]?.name) ||
    getPlayerPhotoUrl(starters[0]?.name) ||
    null;

  return (
    <div className="flex flex-col gap-4">
      {/* Hero */}
      <div className="panel-lol relative overflow-hidden min-h-[120px]">
        {heroPhoto ? (
          <div
            className="absolute inset-0 bg-cover bg-top opacity-35"
            style={{ backgroundImage: `url(${heroPhoto})` }}
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-[#121a28] to-lol-void" />
        )}
        <div className="absolute inset-0 bg-gradient-to-r from-lol-void via-lol-void/90 to-lol-void/70" />
        <div className="relative panel-lol-header !border-0 !bg-transparent">
          <div className="flex items-center gap-3 py-2">
            <div className="team-crest">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display font-bold text-base sm:text-lg text-lol-gold-soft uppercase tracking-wide">
                Elenco — {myTeamName}
              </h2>
              <p className="text-[10px] text-white/45 font-mono">
                {myPlayers.length} atletas · {starters.length} titulares · {bench.length} reservas ·{' '}
                {academy.length} academy
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Lineup cards */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
            Lineup principal
          </span>
        </div>
        <div className="p-3 sm:p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {starters.map((p) => {
            const photo = getPlayerPhotoUrl(p.name);
            return (
              <div key={p.id} className="hub-player-card">
                {/* Foto real / silhueta (não usa splash de campeão) */}
                <div className="relative h-20 overflow-hidden bg-[#0a1018]">
                  {photo ? (
                    <div
                      className="absolute inset-0 bg-cover bg-top opacity-80"
                      style={{ backgroundImage: `url(${photo})` }}
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center opacity-80">
                      <PlayerPortrait name={p.name} size="lg" className="!w-14 !h-14" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-[#060d18] via-black/40 to-transparent" />
                  <div className="absolute bottom-2 left-2 right-2 flex items-end justify-between">
                    <PlayerPortrait name={p.name} size="md" className="!w-11 !h-11 ring-1 ring-black/40" />
                    <span className="flex items-center gap-1 text-[9px] uppercase tracking-wide text-lol-gold bg-black/60 border border-lol-gold/30 px-1.5 py-0.5 rounded-sm">
                      <RoleIcon role={p.role} size={11} active />
                      {ROLE_LABELS[p.role]}
                    </span>
                  </div>
                </div>

                <div className="p-3 flex flex-col gap-2 flex-1">
                  <div>
                    <div className="font-semibold text-sm text-white leading-tight">{p.name}</div>
                    <div className="text-[10px] text-white/40 font-mono">
                      {p.age}a · {p.nationality}
                      {p.isRookie && <span className="text-sky-400 ml-1">· Rookie</span>}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-1 text-center text-[10px] font-mono pt-1 border-t border-white/5">
                    <div>
                      <div className="text-white/35">CA</div>
                      <div className="text-emerald-400 font-bold text-sm">{p.currentAbility}</div>
                    </div>
                    <div>
                      <div className="text-white/35">PA</div>
                      <div
                        className={`text-sm ${
                          p.potentialAbilityKnown ? 'text-white/70' : 'text-amber-300/80'
                        }`}
                      >
                        {formatPa(p)}
                      </div>
                    </div>
                    <div>
                      <div className="text-white/35">Mec</div>
                      <div className="text-lol-gold-soft text-sm">{p.mechanics}</div>
                    </div>
                  </div>
                  {/* Forma recente (TR-1) */}
                  <div className="flex items-center justify-between text-[9px] font-mono border border-white/5 rounded-sm px-1.5 py-1 bg-black/30">
                    <span className="text-white/40">Forma</span>
                    <span
                      className={
                        (p.formAvg ?? 0) >= 7.5
                          ? 'text-emerald-400 font-bold'
                          : (p.formAvg ?? 0) >= 6
                            ? 'text-white/80'
                            : (p.formDiscontent ?? 0) >= 40
                              ? 'text-amber-400'
                              : 'text-white/45'
                      }
                      title={p.formLabel || ''}
                    >
                      {p.formAvg != null ? p.formAvg.toFixed(1) : '—'}
                      {p.formTrend === 'UP' ? ' ↑' : p.formTrend === 'DOWN' ? ' ↓' : ''}
                      {(p.formDiscontent ?? 0) >= 40 ? ' · ⚠' : ''}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[9px] font-mono">
                    <div>
                      <span className="text-white/35">Consist. </span>
                      <span className={p.consistencyKnown ? 'text-white/70' : 'text-amber-300/80'}>
                        {formatHiddenAttr(
                          p.consistencyKnown,
                          p.consistency,
                          p.consistencyMin,
                          p.consistencyMax,
                          1
                        )}
                      </span>
                    </div>
                    <div>
                      <span className="text-white/35">BMA </span>
                      <span
                        className={p.bigMatchAptitudeKnown ? 'text-white/70' : 'text-amber-300/80'}
                      >
                        {formatHiddenAttr(
                          p.bigMatchAptitudeKnown,
                          p.bigMatchAptitude,
                          p.bigMatchAptitudeMin,
                          p.bigMatchAptitudeMax,
                          1
                        )}
                      </span>
                    </div>
                  </div>
                  {/* Barra de progresso CA→PA (se PA conhecido) */}
                  <div>
                    <div className="flex justify-between text-[9px] text-white/35 mb-0.5">
                      <span>Progresso / Scout</span>
                      <span>
                        {p.potentialAbilityKnown && p.potentialAbility
                          ? `${Math.min(
                              100,
                              Math.round((p.currentAbility / p.potentialAbility) * 100)
                            )}% CA`
                          : `${Math.round(p.scoutingProgress || 0)}% scout`}
                      </span>
                    </div>
                    <div className="stat-bar">
                      <div
                        className="stat-bar-fill bg-sky-500/80"
                        style={{
                          width: `${
                            p.potentialAbilityKnown && p.potentialAbility
                              ? Math.min(100, (p.currentAbility / p.potentialAbility) * 100)
                              : Math.min(100, p.scoutingProgress || 0)
                          }%`,
                        }}
                      />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1 mt-1">
                    <button
                      type="button"
                      disabled={!!lineupBusy}
                      onClick={() => void runDemote(p)}
                      className="flex items-center justify-center gap-1 text-[9px] uppercase tracking-wide px-2 py-1 rounded-sm border border-amber-600/30 text-amber-300/80 hover:bg-amber-950/30 disabled:opacity-40"
                    >
                      <ArrowDownCircle className="w-3 h-3" />
                      {lineupBusy === p.id ? '…' : 'Rebaixar'}
                    </button>
                    <button
                      type="button"
                      disabled={!!scoutBusy || p.scoutingFullyScouted}
                      onClick={async () => {
                        setScoutBusy(p.id);
                        try {
                          if (scouting?.assignment?.player_id === p.id) {
                            await clearScout();
                          } else {
                            await assignScout(p.id, 'ALL');
                          }
                        } finally {
                          setScoutBusy(null);
                        }
                      }}
                      className={`flex items-center justify-center gap-1 text-[9px] uppercase tracking-wide px-2 py-1 rounded-sm border ${
                        scouting?.assignment?.player_id === p.id
                          ? 'border-violet-400/50 bg-violet-950/40 text-violet-200'
                          : p.scoutingFullyScouted
                            ? 'border-emerald-700/30 text-emerald-500/60 opacity-60'
                            : 'border-white/10 text-white/45 hover:border-violet-400/40 hover:text-violet-200'
                      }`}
                    >
                      <Binoculars className="w-3 h-3" />
                      {p.scoutingFullyScouted
                        ? 'Scout completo'
                        : scouting?.assignment?.player_id === p.id
                          ? 'Cancelar scout'
                          : 'Scoutar'}
                    </button>
                  </div>
                  {p.hasRookieClause && (
                    <div className="text-[9px] font-mono text-sky-300/80 border border-sky-700/30 rounded-sm px-1.5 py-1 mt-1">
                      Cláusula rookie ·{' '}
                      {Math.round((p.participationRate || 0) * 100)}% jogos
                      {(p.participationRate || 0) >= (p.rookieClauseThreshold || 0.25)
                        ? ' · no ritmo'
                        : ` · meta ${Math.round((p.rookieClauseThreshold || 0.25) * 100)}%`}
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                    <div>
                      <div className="text-white/35">Foco</div>
                      <div className="text-white/80">{p.focus}</div>
                    </div>
                    <div>
                      <div className="text-white/35">Contrato</div>
                      <div className="text-white/80">{p.contractExpirySeasons} split(s)</div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[9px] text-white/35 mb-0.5">
                      <span>Burnout</span>
                      <span>{Math.round(p.burnoutMeter)}%</span>
                    </div>
                    <div className="stat-bar">
                      <div
                        className={`stat-bar-fill ${
                          p.burnoutMeter > 70
                            ? 'bg-lol-red-side'
                            : p.burnoutMeter > 40
                              ? 'bg-amber-500'
                              : 'bg-emerald-500'
                        }`}
                        style={{ width: `${p.burnoutMeter}%` }}
                      />
                    </div>
                  </div>

                  {p.championPool?.length > 0 && (
                    <div className="flex gap-1 flex-wrap pt-1 border-t border-white/5">
                      {p.championPool.slice(0, 5).map((c) => (
                        <ChampionImage
                          key={c.champion}
                          name={c.champion}
                          variant="ban"
                          className="!w-7 !h-7"
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {starters.length === 0 && (
            <p className="col-span-full text-xs text-white/40 p-6 text-center font-mono">
              Nenhum titular carregado.
            </p>
          )}
        </div>
      </div>

      {lineupMsg && (
        <p className="text-[11px] font-mono text-sky-300/90 px-1">{lineupMsg}</p>
      )}

      {/* Cláusulas rookie */}
      {rookieClauses.length > 0 && (
        <div className="panel-lol border-sky-500/20">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-sky-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-sky-200">
                Cláusulas rookie
              </span>
            </div>
            <span className="text-[10px] text-white/35 font-mono">
              Meta {Math.round((rookieClauses[0]?.rookieClauseThreshold || 0.25) * 100)}% dos jogos
            </span>
          </div>
          <ul className="p-3 space-y-1.5">
            {rookieClauses.map((p) => {
              const pct = Math.round((p.participationRate || 0) * 100);
              const thr = Math.round((p.rookieClauseThreshold || 0.25) * 100);
              const onTrack = (p.participationRate || 0) >= (p.rookieClauseThreshold || 0.25);
              return (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center gap-2 text-[11px] border border-white/5 rounded-sm px-2.5 py-2 bg-black/25"
                >
                  <PlayerPortrait name={p.name} size="xs" />
                  <span className="font-semibold text-white min-w-[6rem]">{p.name}</span>
                  <span className="text-white/40 font-mono">
                    {ROLE_LABELS[p.role] || p.role} · CA {p.currentAbility}
                  </span>
                  <span className="text-white/40 font-mono">
                    {p.rookieGamesPlayed || 0}/{p.rookieTotalLeagueGames || 0} jogos
                  </span>
                  <span
                    className={`font-mono font-bold ${
                      onTrack ? 'text-emerald-400' : 'text-amber-300'
                    }`}
                  >
                    {pct}% {onTrack ? '· no ritmo' : `· meta ${thr}%`}
                  </span>
                  {p.rookieExtensionTriggered && (
                    <span className="text-[9px] uppercase text-emerald-400 border border-emerald-700/40 px-1 rounded-sm">
                      Extensão OK
                    </span>
                  )}
                  {p.isStarter && (
                    <span className="text-[9px] uppercase text-lol-gold border border-lol-gold/30 px-1 rounded-sm">
                      Titular
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Bench */}
      <div className="panel-lol">
        <div className="panel-lol-header flex-wrap gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-white/70">
            Reservas (1º time)
          </span>
          <div className="flex items-center gap-2 flex-wrap ml-auto">
            <div className="flex gap-1">
              {['ALL', ...ROLE_ORDER].map((role) => (
                <button
                  key={role}
                  onClick={() => setFilterRole(role)}
                  className={`px-2 py-1 text-[9px] font-bold uppercase border rounded-sm ${
                    filterRole === role
                      ? 'border-lol-gold bg-lol-gold/15 text-lol-gold'
                      : 'border-white/10 text-white/40 hover:border-white/25'
                  }`}
                >
                  {role === 'ALL' ? 'All' : (
                    <span className="flex items-center gap-0.5">
                      <RoleIcon role={role} size={10} />
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-white/30" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar…"
                className="pl-7 pr-2 py-1 text-[11px] bg-black/40 border border-white/10 rounded-sm focus:border-lol-gold focus:outline-none w-28 sm:w-36"
              />
            </div>
          </div>
        </div>
        <div className="overflow-x-auto p-2">
          {filteredBench.length === 0 ? (
            <p className="text-xs text-white/35 p-6 text-center font-mono">
              Nenhuma reserva neste filtro.
            </p>
          ) : (
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="text-white/35 font-mono text-[10px] uppercase border-b border-white/5">
                  <th className="py-2 px-2">Jogador</th>
                  <th className="px-2">Role</th>
                  <th className="px-2">CA</th>
                  <th className="px-2">PA</th>
                  <th className="px-2">Contrato</th>
                  <th className="px-2">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredBench.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.03]">
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <PlayerPortrait name={p.name} size="xs" />
                        <span className="font-semibold">{p.name}</span>
                      </div>
                    </td>
                    <td className="px-2">
                      <span className="inline-flex items-center gap-1 role-pill">
                        <RoleIcon role={p.role} size={10} />
                        {ROLE_LABELS[p.role] || p.role}
                      </span>
                    </td>
                    <td className="px-2 font-mono text-emerald-400 font-bold">{p.currentAbility}</td>
                    <td className="px-2 font-mono text-white/50">{formatPa(p)}</td>
                    <td className="px-2 font-mono text-white/50">{p.contractExpirySeasons}s</td>
                    <td className="px-2">
                      <button
                        type="button"
                        disabled={!!lineupBusy}
                        onClick={() => void runPromote(p)}
                        className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wide px-2 py-1 rounded-sm border border-emerald-600/40 text-emerald-300 hover:bg-emerald-950/40 disabled:opacity-40"
                      >
                        <ArrowUpCircle className="w-3 h-3" />
                        {lineupBusy === p.id ? '…' : 'Promover'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Academy */}
      <div className="panel-lol border-sky-500/15">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-4 h-4 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-sky-200">
              Academy / rookies
            </span>
          </div>
          <span className="text-[10px] text-white/35 font-mono">{filteredAcademy.length} atletas</span>
        </div>
        <div className="overflow-x-auto p-2">
          {filteredAcademy.length === 0 ? (
            <p className="text-xs text-white/35 p-6 text-center font-mono">
              Nenhum jogador de academy neste filtro.
            </p>
          ) : (
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="text-white/35 font-mono text-[10px] uppercase border-b border-white/5">
                  <th className="py-2 px-2">Jogador</th>
                  <th className="px-2">Role</th>
                  <th className="px-2">Idade</th>
                  <th className="px-2">CA</th>
                  <th className="px-2">Cláusula</th>
                  <th className="px-2">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredAcademy.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.03]">
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <PlayerPortrait name={p.name} size="xs" />
                        <span className="font-semibold">{p.name}</span>
                        {p.isRookie && (
                          <span className="text-[9px] text-sky-400 uppercase">Rookie</span>
                        )}
                      </div>
                    </td>
                    <td className="px-2">
                      <span className="inline-flex items-center gap-1 role-pill">
                        <RoleIcon role={p.role} size={10} />
                        {ROLE_LABELS[p.role] || p.role}
                      </span>
                    </td>
                    <td className="px-2 font-mono">{p.age}</td>
                    <td className="px-2 font-mono text-emerald-400 font-bold">{p.currentAbility}</td>
                    <td className="px-2 font-mono text-[10px] text-white/50">
                      {p.hasRookieClause
                        ? `${Math.round((p.participationRate || 0) * 100)}% jogos`
                        : '—'}
                    </td>
                    <td className="px-2">
                      <button
                        type="button"
                        disabled={!!lineupBusy}
                        onClick={() => void runPromote(p)}
                        className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wide px-2 py-1 rounded-sm border border-sky-500/40 text-sky-300 hover:bg-sky-950/40 disabled:opacity-40"
                      >
                        <ArrowUpCircle className="w-3 h-3" />
                        {lineupBusy === p.id ? '…' : 'Subir pro main'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
