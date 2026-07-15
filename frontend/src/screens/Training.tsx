import { useState } from 'react';
import {
  Dumbbell,
  Heart,
  Target,
  Clapperboard,
  Binoculars,
} from 'lucide-react';
import { useGameStore } from '../store/useGameStore';
import { HubPageHeader } from '../components/HubPageHeader';

/**
 * Treino, moral/prática e scouting — área de “preparação do plantel”.
 * Separada do Painel (overview) no estilo FM.
 */
export function Training() {
  const {
    training,
    lastTrainingEvent,
    setTrainingPlan,
    practice,
    lastPracticeEvent,
    refreshPractice,
    scouting,
    lastScoutingEvent,
    clearScout,
    setCurrentScreen,
    manager,
  } = useGameStore();

  const [trainingBusy, setTrainingBusy] = useState(false);
  const [trainingMsg, setTrainingMsg] = useState<string | null>(null);
  const myTeamId = manager?.teamId;

  return (
    <div className="flex flex-col gap-4">
      <HubPageHeader
        icon={Dumbbell}
        title="Treino & preparação"
        subtitle="Plano de treino, moral, scrims, VOD e scouting — o que o plantel faz entre os match days."
        actions={
          myTeamId ? (
            <button
              type="button"
              onClick={() => void refreshPractice?.()}
              className="text-[10px] uppercase tracking-wide text-white/50 border border-white/10 px-3 py-1.5 rounded-sm hover:border-lol-gold/30 hover:text-lol-gold"
            >
              Atualizar prática
            </button>
          ) : null
        }
      />

      {/* Treino / desenvolvimento */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <div className="flex items-center gap-2">
            <Dumbbell className="w-4 h-4 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-lol-gold-soft">
              Plano de treino · CA → PA
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
                +{lastTrainingEvent?.ca_gains ?? training?.last_session?.ca_gains ?? 0} CA ·{' '}
                {lastTrainingEvent?.attr_gains ?? training?.last_session?.attr_gains ?? 0} attrs ·{' '}
                {lastTrainingEvent?.players_trained ??
                  training?.last_session?.players_trained ??
                  0}{' '}
                atletas
              </p>
              <ul className="mt-1.5 space-y-0.5 max-h-28 overflow-y-auto">
                {(lastTrainingEvent?.gains || training?.last_session?.gains || [])
                  .slice(0, 10)
                  .map((g, i) => (
                    <li key={`${g.player_name}-${i}`} className="text-[10px] font-mono text-white/50">
                      <span className="text-white/75">{g.player_name}</span>
                      {g.ca_delta ? (
                        <span className="text-emerald-400">
                          {' '}
                          CA {g.ca_before}→{g.ca_after}
                        </span>
                      ) : null}
                      {g.attr_deltas && Object.keys(g.attr_deltas).length > 0 && (
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

      {/* Moral + scrim + VOD */}
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
                {practice?.morale?.morale_label || '—'} / {practice?.morale?.chemistry_label || '—'}
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
              <ul className="space-y-1 max-h-[80px] overflow-y-auto">
                {(practice?.morale?.last_events || []).slice(-4).map((e, i) => (
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
                  Prática atualizada no último advance day.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

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
            Consistência, BMA e PA começam ocultos. Atribua o scout no{' '}
            <button
              type="button"
              className="text-lol-gold underline-offset-2 hover:underline"
              onClick={() => setCurrentScreen('SQUAD')}
            >
              Elenco
            </button>{' '}
            ou{' '}
            <button
              type="button"
              className="text-lol-gold underline-offset-2 hover:underline"
              onClick={() => setCurrentScreen('MARKET')}
            >
              Mercado
            </button>
            ; o progresso sobe ao avançar o dia.
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
                  {scouting.assignment.focus || 'ALL'} · {scouting.assignment.days_invested || 0}{' '}
                  dia(s)
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
              {lastScoutingEvent.events.slice(0, 5).map((e, i) => (
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
    </div>
  );
}
