import { useEffect, useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { FileCode2, TrendingUp, TrendingDown, Clock, Loader2, Sparkles } from 'lucide-react';
import { ChampionImage } from '../components/ChampionImage';
import { RoleIcon } from '../components/RoleIcon';
import { ROLE_LABELS } from '../lib/champions';

export function PatchNotes() {
  const patch = useGameStore((s) => s.patchStatus);
  const refreshPatch = useGameStore((s) => s.refreshPatch);
  const totalDaysElapsed = useGameStore((s) => s.totalDaysElapsed);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    void refreshPatch().finally(() => setLoading(false));
  }, [refreshPatch, totalDaysElapsed]);

  const active = patch?.active;
  const upcoming = patch?.upcoming;

  return (
    <div className="flex flex-col gap-4">
      <div className="panel-lol relative overflow-hidden">
        <div className="absolute inset-0 bg-lol-header pointer-events-none" />
        <div className="relative panel-lol-header !bg-transparent">
          <div className="flex items-center gap-3 py-1">
            <div className="team-crest">
              <FileCode2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display font-bold text-base text-lol-gold-soft uppercase tracking-wide">
                Patch notes · Meta CBLOL
              </h2>
              <p className="text-[10px] text-white/40 font-mono mt-0.5">
                Buffs/nerfs afetam o motor de partida e a IA de draft
                {patch?.calendar_date ? ` · data jogo ${patch.calendar_date}` : ''}
              </p>
            </div>
            {loading && <Loader2 className="w-4 h-4 animate-spin text-white/40 ml-auto" />}
          </div>
        </div>
      </div>

      {/* Active */}
      <div className="panel-lol border-emerald-500/20">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-200">
              Patch ativo
            </span>
          </div>
          <span className="font-mono text-sm text-lol-gold-soft font-bold">
            {active?.version ? `v${active.version}` : '—'}
          </span>
        </div>
        <div className="p-3 space-y-3">
          {!active ? (
            <p className="text-xs text-white/40 font-mono">
              Nenhum patch em vigor. Avance o calendário ou rode o seed.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-3 text-[10px] font-mono text-white/45">
                <span>Lançamento {active.release_date}</span>
                <span>· Vigor {active.effective_date}</span>
                <span className="text-emerald-400">· {active.buff_count ?? 0} buffs</span>
                <span className="text-lol-red-side">· {active.nerf_count ?? 0} nerfs</span>
              </div>
              <ul className="space-y-1.5 max-h-[360px] overflow-y-auto">
                {(active.changes || []).map((c, i) => (
                  <li
                    key={`${c.champion}-${c.role}-${i}`}
                    className={`flex flex-wrap items-center gap-2 px-2.5 py-2 rounded-sm border text-[11px] ${
                      c.kind === 'BUFF'
                        ? 'border-emerald-700/35 bg-emerald-950/20'
                        : 'border-red-900/35 bg-red-950/20'
                    }`}
                  >
                    <ChampionImage name={c.champion} variant="ban" className="!w-8 !h-8" />
                    <div className="min-w-[7rem]">
                      <div className="font-semibold text-white">{c.champion}</div>
                      <div className="flex items-center gap-1 text-[9px] text-white/40">
                        <RoleIcon role={c.role} size={10} />
                        {ROLE_LABELS[c.role] || c.role}
                      </div>
                    </div>
                    <span
                      className={`inline-flex items-center gap-1 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-sm border ${
                        c.kind === 'BUFF'
                          ? 'text-emerald-300 border-emerald-600/40'
                          : 'text-red-300 border-red-700/40'
                      }`}
                    >
                      {c.kind === 'BUFF' ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {c.kind}
                    </span>
                    <span className="font-mono text-white/55 flex-1 min-w-[10rem]">
                      {c.summary}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Upcoming */}
      <div className="panel-lol border-sky-500/20">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-sky-200">
              Próximo patch
            </span>
          </div>
          <span className="font-mono text-sm text-white/70">
            {upcoming?.version ? `v${upcoming.version}` : '—'}
          </span>
        </div>
        <div className="p-3 space-y-2">
          {!upcoming ? (
            <p className="text-xs text-white/40 font-mono">Nenhum patch agendado.</p>
          ) : (
            <>
              <p className="text-[11px] text-white/50 font-mono">
                Entra em vigor em <span className="text-sky-300 font-bold">{upcoming.days_until}</span>{' '}
                dia(s) · {upcoming.effective_date}
              </p>
              <ul className="space-y-1 max-h-[200px] overflow-y-auto">
                {(upcoming.changes || []).slice(0, 12).map((c, i) => (
                  <li
                    key={`up-${c.champion}-${i}`}
                    className="flex items-center gap-2 text-[10px] font-mono text-white/50 px-2 py-1 border border-white/5 rounded-sm"
                  >
                    <span
                      className={
                        c.kind === 'BUFF' ? 'text-emerald-400' : 'text-red-400'
                      }
                    >
                      {c.kind}
                    </span>
                    <span className="text-white/75">{c.champion}</span>
                    <span className="text-white/35">{c.role}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* Timeline */}
      {patch?.patches && patch.patches.length > 0 && (
        <div className="panel-lol">
          <div className="panel-lol-header">
            <span className="text-xs font-semibold uppercase tracking-wider text-white/70">
              Linha do tempo
            </span>
          </div>
          <div className="p-3 flex flex-wrap gap-2">
            {patch.patches.map((p) => (
              <div
                key={p.version}
                className={`px-3 py-2 rounded-sm border text-[10px] font-mono ${
                  p.status === 'active'
                    ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-200'
                    : p.status === 'upcoming'
                      ? 'border-sky-500/30 bg-sky-950/20 text-sky-200'
                      : 'border-white/10 text-white/35'
                }`}
              >
                <div className="font-bold">v{p.version}</div>
                <div>{p.status}</div>
                <div className="text-white/40">{p.effective_date}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
