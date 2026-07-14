import { useGameStore } from '../store/useGameStore';
import { TableProperties, Medal, TrendingUp } from 'lucide-react';

export function Standings() {
  const standings = useGameStore((s) => s.standings);
  const myTeamName = useGameStore((s) => s.myTeamName);
  const currentWeek = useGameStore((s) => s.currentWeek);
  const splitPhase = useGameStore((s) => s.splitPhase);
  const myBudget = useGameStore((s) => s.myBudget);

  const myRank = standings.findIndex((s) => s.team_name === myTeamName) + 1;
  const myRow = standings.find((s) => s.team_name === myTeamName);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="panel-lol relative overflow-hidden">
        <div className="absolute inset-0 bg-lol-header pointer-events-none" />
        <div className="relative panel-lol-header !bg-transparent border-b border-lol-gold/15">
          <div className="flex items-center gap-3 py-1">
            <div className="team-crest">
              <TableProperties className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display font-bold text-base text-lol-gold-soft uppercase tracking-wide">
                Classificação CBLOL 2026
              </h2>
              <p className="text-[10px] text-white/40 font-mono">
                Semana {currentWeek} · {splitPhase?.replace('_', ' ')} · top 6 = playoffs
              </p>
            </div>
          </div>
        </div>

        {myRow && (
          <div className="relative grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 border-b border-white/5 bg-black/20">
            <div className="hub-stat-card !p-2.5">
              <div className="text-[9px] uppercase text-white/35 flex items-center gap-1">
                <Medal className="w-3 h-3 text-lol-gold" /> Sua posição
              </div>
              <div className="font-mono text-xl font-bold text-lol-gold">#{myRank}</div>
            </div>
            <div className="hub-stat-card !p-2.5">
              <div className="text-[9px] uppercase text-white/35">Pontos</div>
              <div className="font-mono text-xl font-bold text-white">{myRow.points}</div>
            </div>
            <div className="hub-stat-card !p-2.5">
              <div className="text-[9px] uppercase text-white/35">Campanha</div>
              <div className="font-mono text-lg font-bold">
                <span className="text-emerald-400">{myRow.wins}V</span>
                <span className="text-white/20 mx-1">-</span>
                <span className="text-lol-red-side">{myRow.losses}D</span>
              </div>
            </div>
            <div className="hub-stat-card !p-2.5">
              <div className="text-[9px] uppercase text-white/35">Winrate</div>
              <div className="font-mono text-lg font-bold text-sky-300">{myRow.win_rate}</div>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-lol-gold" />
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
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
                  <tr className="text-white/40 text-[10px] uppercase font-mono border-b border-lol-gold/20">
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
                    const playoff = idx < 6;
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
                      >
                        <td className="py-3 px-3 font-mono text-white/40">
                          <span className="inline-flex items-center gap-1.5">
                            {idx + 1}
                            {idx === 0 && <span className="text-lol-gold text-[9px]">★</span>}
                          </span>
                        </td>
                        <td className="px-3 font-semibold">
                          {row.team_name}
                          {isMine && (
                            <span className="ml-2 text-[9px] text-lol-gold uppercase tracking-wide border border-lol-gold/30 px-1 rounded-sm">
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
                          {playoff ? (
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
                  <span className="w-2 h-2 rounded-sm bg-lol-gold/50" /> Seu time
                </span>
                <span>3 pts por vitória de série</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
