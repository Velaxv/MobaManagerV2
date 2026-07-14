import { useMemo, useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { ROLE_LABELS, championSplashUrl } from '../lib/champions';
import { ChampionImage } from '../components/ChampionImage';
import { RoleIcon } from '../components/RoleIcon';
import { Users, Search } from 'lucide-react';
import { PlayerRole } from '../types/game';

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
  const [filterRole, setFilterRole] = useState<string>('ALL');
  const [search, setSearch] = useState('');

  const starters = useMemo(() => {
    return ROLE_ORDER.map((role) => myPlayers.find((p) => p.role === role)).filter(Boolean) as typeof myPlayers;
  }, [myPlayers]);

  const bench = useMemo(() => {
    const starterIds = new Set(starters.map((p) => p.id));
    return myPlayers.filter((p) => !starterIds.has(p.id));
  }, [myPlayers, starters]);

  const filteredBench = useMemo(() => {
    return bench.filter((p) => {
      if (filterRole !== 'ALL' && p.role !== filterRole) return false;
      if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [bench, filterRole, search]);

  const heroChamp = starters[2]?.championPool?.[0]?.champion || starters[0]?.championPool?.[0]?.champion;

  return (
    <div className="flex flex-col gap-4">
      {/* Hero */}
      <div className="panel-lol relative overflow-hidden min-h-[120px]">
        {heroChamp && (
          <div
            className="absolute inset-0 bg-cover bg-center opacity-30"
            style={{ backgroundImage: `url(${championSplashUrl(heroChamp)})` }}
          />
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
                {myPlayers.length} atletas · {starters.length} titulares · {bench.length} reservas
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
            const mainChamp = p.championPool?.[0]?.champion;
            return (
              <div key={p.id} className="hub-player-card">
                {/* Splash header */}
                <div className="relative h-16 overflow-hidden">
                  {mainChamp && (
                    <div
                      className="absolute inset-0 bg-cover bg-center"
                      style={{ backgroundImage: `url(${championSplashUrl(mainChamp)})` }}
                    />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-[#060d18] via-black/40 to-transparent" />
                  <div className="absolute bottom-2 left-2 right-2 flex items-end justify-between">
                    <ChampionImage name={mainChamp} variant="portrait" locked className="!w-11 !h-11" />
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
                      <div className="text-white/70 text-sm">{p.potentialAbility}</div>
                    </div>
                    <div>
                      <div className="text-white/35">Mec</div>
                      <div className="text-lol-gold-soft text-sm">{p.mechanics}</div>
                    </div>
                  </div>

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

      {/* Bench */}
      <div className="panel-lol">
        <div className="panel-lol-header flex-wrap gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-white/70">
            Reservas / Academy
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
            <p className="text-xs text-white/35 p-6 text-center font-mono">Nenhuma reserva neste filtro.</p>
          ) : (
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="text-white/35 font-mono text-[10px] uppercase border-b border-white/5">
                  <th className="py-2 px-2">Jogador</th>
                  <th className="px-2">Role</th>
                  <th className="px-2">Idade</th>
                  <th className="px-2">CA</th>
                  <th className="px-2">PA</th>
                  <th className="px-2">Pool</th>
                  <th className="px-2">Rookie</th>
                  <th className="px-2">Contrato</th>
                  <th className="px-2 min-w-[70px]">Burnout</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredBench.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.03]">
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <ChampionImage
                          name={p.championPool?.[0]?.champion}
                          variant="ban"
                          className="!w-8 !h-8"
                        />
                        <span className="font-semibold">{p.name}</span>
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
                    <td className="px-2 font-mono text-white/50">{p.potentialAbility}</td>
                    <td className="px-2">
                      <div className="flex gap-0.5">
                        {(p.championPool || []).slice(0, 3).map((c) => (
                          <ChampionImage
                            key={c.champion}
                            name={c.champion}
                            variant="ban"
                            className="!w-6 !h-6"
                          />
                        ))}
                      </div>
                    </td>
                    <td className="px-2">
                      {p.isRookie ? (
                        <span className="text-sky-400 text-[10px] font-bold">Sim</span>
                      ) : (
                        <span className="text-white/25">—</span>
                      )}
                    </td>
                    <td className="px-2 font-mono text-white/50">{p.contractExpirySeasons}s</td>
                    <td className="px-2">
                      <div className="stat-bar">
                        <div
                          className={`stat-bar-fill ${
                            p.burnoutMeter > 70 ? 'bg-lol-red-side' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${p.burnoutMeter}%` }}
                        />
                      </div>
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
