import { useGameStore } from '../store/useGameStore';
import { TableProperties, Medal, TrendingUp, Trophy, Swords } from 'lucide-react';
import { SplitPhase } from '../types/game';
import { getOrgBrand, orgCrestStyle } from '../lib/orgBrands';
import { HubPageHeader } from '../components/HubPageHeader';

function seriesSideLabel(side?: {
  team_id?: string | null;
  team_abbr?: string | null;
  team_name?: string | null;
  seed?: number | null;
} | null) {
  if (!side?.team_id && !side?.team_abbr && !side?.team_name) return 'TBD';
  const tag = side.team_abbr || side.team_name || '?';
  return side.seed != null ? `#${side.seed} ${tag}` : tag;
}

export function Standings() {
  const standings = useGameStore((s) => s.standings);
  const myTeamName = useGameStore((s) => s.myTeamName);
  const currentWeek = useGameStore((s) => s.currentWeek);
  const splitPhase = useGameStore((s) => s.splitPhase);
  const myBudget = useGameStore((s) => s.myBudget);
  const playoffBracket = useGameStore((s) => s.playoffBracket);
  const startPlayoffsDev = useGameStore((s) => s.startPlayoffsDev);

  const myRank = standings.findIndex((s) => s.team_name === myTeamName) + 1;
  const myRow = standings.find((s) => s.team_name === myTeamName);
  const inPlayoffs = splitPhase === SplitPhase.PLAYOFFS;
  const champion = playoffBracket?.champion_name;

  const seriesByRound = (round: string) =>
    (playoffBracket?.series || []).filter((s) => s.round === round);

  return (
    <div className="flex flex-col gap-4">
      <HubPageHeader
        icon={TableProperties}
        eyebrow="Competition"
        title="Classificação CBLOL 2026"
        subtitle={`Semana ${currentWeek} · ${splitPhase?.replace('_', ' ') || '—'} · top 6 = playoffs`}
      />

      {myRow && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="hub-stat-card !p-2.5">
            <div className="text-[9px] uppercase tracking-hud text-white/35 flex items-center gap-1 font-mono">
              <Medal className="w-3 h-3 text-lol-hq-cyan" /> Rank
            </div>
            <div className="font-mono text-xl font-bold text-lol-hq-cyan">
              {myRow.final_placement ? `#${myRow.final_placement}` : `#${myRank}`}
            </div>
          </div>
          <div className="hub-stat-card !p-2.5">
            <div className="text-[9px] uppercase tracking-hud text-white/35 font-mono">Pontos</div>
            <div className="font-mono text-xl font-bold text-white">{myRow.points}</div>
          </div>
          <div className="hub-stat-card !p-2.5">
            <div className="text-[9px] uppercase tracking-hud text-white/35 font-mono">Campanha</div>
            <div className="font-mono text-lg font-bold">
              <span className="text-emerald-400">{myRow.wins}V</span>
              <span className="text-white/20 mx-1">-</span>
              <span className="text-lol-red-side">{myRow.losses}D</span>
            </div>
          </div>
          <div className="hub-stat-card !p-2.5">
            <div className="text-[9px] uppercase tracking-hud text-white/35 font-mono">Winrate</div>
            <div className="font-mono text-lg font-bold text-sky-300">{myRow.win_rate}</div>
          </div>
        </div>
      )}

      {/* Playoffs bracket */}
      {(inPlayoffs || playoffBracket) && (
        <div className="panel-lol">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Trophy className="w-4 h-4 text-lol-hq-cyan" />
              <span className="text-xs font-semibold uppercase tracking-wider text-white">
                Playoffs · Top 6
              </span>
            </div>
            {champion ? (
              <span className="text-[10px] font-mono text-lol-hq-cyan">
                Campeão: {champion}
              </span>
            ) : (
              <span className="text-[10px] text-white/30 font-mono">
                {playoffBracket?.current_round?.replace('_', ' ') || 'Bracket'}
              </span>
            )}
          </div>
          <div className="p-3 space-y-4">
            {playoffBracket?.series ? (
              <>
                {[
                  { key: 'QUARTERFINAL', title: 'Quartas' },
                  { key: 'SEMIFINAL', title: 'Semifinais' },
                  { key: 'FINAL', title: 'Final' },
                ].map(({ key, title }) => {
                  const rows = seriesByRound(key);
                  if (!rows.length) return null;
                  return (
                    <div key={key}>
                      <p className="text-[10px] uppercase tracking-wider text-white/35 mb-2 font-semibold">
                        {title}
                      </p>
                      <div className="grid sm:grid-cols-2 gap-2">
                        {rows.map((s) => {
                          const done = s.status === 'complete';
                          const homeWon = done && s.winner_team_id === s.home?.team_id;
                          const awayWon = done && s.winner_team_id === s.away?.team_id;
                          return (
                            <div
                              key={s.id}
                              className={`rounded-sm border px-3 py-2 ${
                                done
                                  ? 'border-lol-hq-cyan/30 bg-lol-hq-cyan/5'
                                  : s.status === 'ready'
                                    ? 'border-emerald-700/40 bg-emerald-950/20'
                                    : 'border-white/10 bg-black/20'
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2 mb-1">
                                <span className="text-[9px] text-white/40 font-mono uppercase">
                                  {s.label}
                                </span>
                                <span className="text-[9px] text-white/30">
                                  BO{s.best_of}
                                  {s.score
                                    ? ` · ${s.score.home ?? 0}-${s.score.away ?? 0}`
                                    : ''}
                                </span>
                              </div>
                              <div className="flex items-center justify-between gap-2 text-sm">
                                <span
                                  className={`font-semibold ${
                                    homeWon ? 'text-lol-hq-cyan' : 'text-white/85'
                                  }`}
                                >
                                  {seriesSideLabel(s.home)}
                                  {s.score != null && (
                                    <span className="ml-1 font-mono text-white">
                                      {s.score.home ?? 0}
                                    </span>
                                  )}
                                </span>
                                <Swords className="w-3.5 h-3.5 text-white/25 shrink-0" />
                                <span
                                  className={`font-semibold text-right ${
                                    awayWon ? 'text-lol-hq-cyan' : 'text-white/85'
                                  }`}
                                >
                                  {s.score != null && (
                                    <span className="mr-1 font-mono text-white">
                                      {s.score.away ?? 0}
                                    </span>
                                  )}
                                  {seriesSideLabel(s.away)}
                                </span>
                              </div>
                              <p className="text-[9px] mt-1 text-white/30 font-mono">
                                {done
                                  ? 'Série encerrada'
                                  : s.status === 'in_progress'
                                    ? `Em andamento · Map ${(s.maps?.length || 0) + 1}`
                                    : s.status === 'ready'
                                      ? 'Pronta'
                                      : 'Aguardando'}
                                {s.fearless_used && s.fearless_used.length > 0
                                  ? ` · Fearless ${s.fearless_used.length}`
                                  : ''}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </>
            ) : (
              <p className="text-sm text-white/40 text-center py-6 font-mono">
                Bracket ainda não gerado.
              </p>
            )}

            {!inPlayoffs && !playoffBracket && (
              <button
                type="button"
                onClick={() => void startPlayoffsDev()}
                className="btn-lol-secondary text-xs w-full sm:w-auto"
              >
                [Dev] Forçar playoffs agora
              </button>
            )}
            {!playoffBracket && inPlayoffs === false && splitPhase === SplitPhase.REGULAR_SEASON && (
              <div className="pt-2 border-t border-white/5">
                <button
                  type="button"
                  onClick={() => void startPlayoffsDev().catch(() => undefined)}
                  className="text-[10px] uppercase tracking-wide text-white/40 hover:text-lol-hq-cyan border border-white/10 hover:border-lol-hq-cyan/30 px-3 py-1.5 rounded-sm transition-colors"
                >
                  Playtest: iniciar playoffs (forçado)
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {!playoffBracket && splitPhase === SplitPhase.REGULAR_SEASON && (
        <div className="panel-lol p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <p className="text-[11px] text-white/40">
            Avance a temporada regular até o fim para gerar o bracket top 6 — ou force no playtest.
          </p>
          <button
            type="button"
            onClick={() => void startPlayoffsDev().catch(() => undefined)}
            className="text-[10px] uppercase tracking-wide text-lol-hq-cyan/80 border border-lol-hq-cyan/25 px-3 py-1.5 rounded-sm hover:bg-lol-hq-cyan/10"
          >
            Forçar playoffs
          </button>
        </div>
      )}

      {/* Table */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-lol-hq-cyan" />
            <span className="text-xs font-semibold uppercase tracking-wider text-white">
              Tabela da liga
            </span>
          </div>
          <span className="text-[10px] text-white/30 font-mono">
            Orçamento clube: €{(myBudget / 1_000_000).toFixed(2)}M
          </span>
        </div>
        <div className="p-2 sm:p-3 overflow-x-auto">
          {standings.length === 0 ? (
            <p className="text-sm text-white/40 p-10 text-center font-mono">
              Sem dados ainda. Avance o calendário e complete match days.
            </p>
          ) : (
            <>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 text-[10px] uppercase font-mono border-b border-lol-hq-cyan/20">
                    <th className="py-3 px-3 text-left">Pos</th>
                    <th className="text-left px-3">Organização</th>
                    <th className="px-3 text-center">V</th>
                    <th className="px-3 text-center">D</th>
                    <th className="px-3 text-center">Pts</th>
                    <th className="px-3 text-center">WR</th>
                    <th className="px-3 text-center hidden sm:table-cell">Zona</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {standings.map((row, idx) => {
                    const isMine = row.team_name === myTeamName;
                    const playoff =
                      row.is_in_playoffs ||
                      (row.playoff_seed != null && row.playoff_seed > 0) ||
                      (row.final_placement == null && idx < 6);
                    const seed = row.playoff_seed;
                    const place = row.final_placement;
                    const brand = getOrgBrand(row.team_name);
                    return (
                      <tr
                        key={row.team_id}
                        className={`${
                          isMine
                            ? 'hub-table-row-mine'
                            : playoff
                              ? 'hub-table-row-playoff text-white/85'
                              : 'hub-table-row-out text-white/55'
                        } hover:bg-white/[0.03] transition-colors`}
                        style={
                          isMine
                            ? { boxShadow: `inset 3px 0 0 ${brand.primary}` }
                            : undefined
                        }
                      >
                        <td className="py-3 px-3 font-mono text-white/40">
                          <span className="inline-flex items-center gap-1.5">
                            {place ?? idx + 1}
                            {(place === 1 || (!place && idx === 0)) && (
                              <span className="text-lol-hq-cyan text-[9px]">★</span>
                            )}
                          </span>
                        </td>
                        <td className="px-3 font-semibold">
                          <span className="inline-flex items-center gap-2 min-w-0">
                            <span
                              className="inline-flex items-center justify-center w-7 h-7 rounded-sm text-[9px] font-bold shrink-0"
                              style={orgCrestStyle(row.team_name)}
                              title={brand.name}
                            >
                              {brand.tag.slice(0, 3)}
                            </span>
                            <span className="truncate">{row.team_name}</span>
                          </span>
                          {seed != null && (
                            <span className="ml-2 text-[9px] text-emerald-400/90 font-mono">
                              seed {seed}
                            </span>
                          )}
                          {isMine && (
                            <span className="ml-2 text-[9px] text-lol-hq-cyan uppercase tracking-wide border border-lol-hq-cyan/30 px-1 rounded-sm">
                              Você
                            </span>
                          )}
                        </td>
                        <td className="px-3 text-center font-mono text-emerald-400">{row.wins}</td>
                        <td className="px-3 text-center font-mono text-lol-red-side">{row.losses}</td>
                        <td className="px-3 text-center font-mono font-bold text-base sm:text-lg">
                          {row.points}
                        </td>
                        <td className="px-3 text-center font-mono text-white/45">{row.win_rate}</td>
                        <td className="px-3 text-center hidden sm:table-cell">
                          {place === 1 ? (
                            <span className="text-[9px] uppercase tracking-wide text-lol-hq-cyan border border-lol-hq-cyan/40 bg-lol-hq-cyan/10 px-1.5 py-0.5 rounded-sm">
                              Campeão
                            </span>
                          ) : playoff ? (
                            <span className="text-[9px] uppercase tracking-wide text-emerald-400 border border-emerald-700/40 bg-emerald-950/30 px-1.5 py-0.5 rounded-sm">
                              Playoffs
                            </span>
                          ) : (
                            <span className="text-[9px] uppercase tracking-wide text-white/25 border border-white/10 px-1.5 py-0.5 rounded-sm">
                              Fora
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="flex flex-wrap gap-4 mt-4 px-2 text-[10px] text-white/30 font-mono">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-sm bg-emerald-600/60" /> Top 6 — Playoffs
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-sm bg-lol-hq-cyan/50" /> Seu time
                </span>
                <span>3 pts por vitória na regular · playoffs eliminatórios</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
