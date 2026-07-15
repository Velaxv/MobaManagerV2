import { useEffect, useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { Trophy, Activity, Users, Swords, Loader2, FolderOpen } from 'lucide-react';

/** Key art HQ — ver docs/STYLE_BIBLE.md (arte sem texto; UI em React). */
const MENU_HQ_BG = '/art/menu-hq-bg.jpg';

type SaveMeta = {
  slot: string;
  manager_name?: string;
  team_name?: string;
  team_abbr?: string;
  saved_at?: string;
  phase?: string;
  week?: number;
  error?: string;
};

export function MainMenu() {
  const { setGameState, isDataLoaded, loadCareer, listCareerSaves } = useGameStore();
  const [saves, setSaves] = useState<SaveMeta[]>([]);
  const [loadingSaves, setLoadingSaves] = useState(true);
  const [loadingSlot, setLoadingSlot] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showLoad, setShowLoad] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await listCareerSaves();
        if (!cancelled) setSaves(list);
      } catch {
        if (!cancelled) setSaves([]);
      } finally {
        if (!cancelled) setLoadingSaves(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [listCareerSaves]);

  const handleLoad = async (slot: string) => {
    setLoadError(null);
    setLoadingSlot(slot);
    try {
      await loadCareer(slot);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Falha ao carregar save');
    } finally {
      setLoadingSlot(null);
    }
  };

  const validSaves = saves.filter((s) => !s.error && s.manager_name);

  return (
    <div className="min-h-screen relative flex flex-col items-center justify-center p-6 overflow-hidden bg-lol-void">
      {/* Layer 1: production key art (no text — STYLE_BIBLE) */}
      <div
        className="absolute inset-0 bg-cover bg-center scale-105"
        style={{
          backgroundImage: `url(${MENU_HQ_BG})`,
          backgroundPosition: '55% 40%',
        }}
        aria-hidden
      />
      {/* Layer 2: readability vignette — left-center for menu column */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 70% 80% at 45% 50%, rgba(1,10,19,0.55) 0%, rgba(1,10,19,0.72) 55%, rgba(1,10,19,0.88) 100%)',
        }}
        aria-hidden
      />
      <div className="absolute inset-0 bg-hq-ambient opacity-60 pointer-events-none" aria-hidden />
      <div
        className="absolute inset-0 opacity-25 pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(rgba(34,211,238,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.035) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
        aria-hidden
      />
      <div
        className="absolute inset-0 bg-gradient-to-b from-lol-void/40 via-transparent to-lol-void/90 pointer-events-none"
        aria-hidden
      />
      <div
        className="absolute inset-y-0 left-0 w-full max-w-3xl bg-gradient-to-r from-lol-void/75 via-lol-void/35 to-transparent pointer-events-none"
        aria-hidden
      />

      <div className="z-10 w-full max-w-xl flex flex-col gap-8 animate-fade-in">
        <div className="hq-frame border border-lol-hq-cyan/30 bg-gradient-to-b from-[#0a1e32]/88 to-black/85 p-8 sm:p-10 shadow-hq-glass rounded-sm relative overflow-hidden backdrop-blur-md">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-lol-hq-cyan to-lol-hq-orange/50" />
          <div className="flex items-center gap-2 mb-4">
            <div className="team-crest !w-8 !h-8 text-[10px]">LM</div>
            <p className="text-[10px] uppercase tracking-[0.35em] text-lol-hq-cyan/80 font-semibold font-mono">
              CBLOL 2026 · War Room
            </p>
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-bold text-white tracking-wide leading-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.65)]">
            Moba Manager
            <span className="block text-lol-hq-cyan mt-1 text-2xl sm:text-3xl font-semibold tracking-[0.12em] uppercase">
              League Ops
            </span>
          </h1>
          <p className="mt-4 text-sm text-white/55 leading-relaxed border-t border-lol-hq-cyan/15 pt-4">
            Mesa de guerra digital — draft tático, live Rift e gestão de elenco com analytics de
            performance. Tech-noir, data-rich, sem gacha.
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-[10px] font-mono text-white/40">
            <span className="flex items-center gap-1 border border-lol-hq-cyan/20 px-2 py-0.5 rounded-sm bg-black/40">
              <Swords className="w-3 h-3 text-lol-hq-cyan" /> Draft flex
            </span>
            <span className="flex items-center gap-1 border border-lol-hq-cyan/20 px-2 py-0.5 rounded-sm bg-black/40">
              <Trophy className="w-3 h-3 text-lol-hq-orange" /> Live match
            </span>
            <span className="flex items-center gap-1 border border-lol-hq-cyan/20 px-2 py-0.5 rounded-sm bg-black/40">
              <Users className="w-3 h-3 text-lol-hq-cyan" /> Roster analytics
            </span>
            <span className="flex items-center gap-1 border border-lol-hq-cyan/20 px-2 py-0.5 rounded-sm bg-black/40">
              <FolderOpen className="w-3 h-3 text-lol-hq-cyan" /> Save / Load
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <button
            disabled={!isDataLoaded}
            onClick={() => setGameState('NEW_GAME_SETUP')}
            className="group flex items-center justify-between p-5 border border-lol-hq-cyan/45 bg-gradient-to-r from-lol-hq-cyan/20 to-black/50 hover:from-lol-hq-cyan/30 hover:shadow-hq-cyan-sm transition-all disabled:opacity-40 rounded-sm backdrop-blur-sm"
          >
            <div className="text-left">
              <div className="font-display font-bold text-lol-hq-cyan-bright uppercase tracking-wide">
                Nova carreira
              </div>
              <div className="text-[11px] text-white/45 mt-0.5">Assuma um time do CBLOL 2026</div>
            </div>
            <Trophy className="w-7 h-7 text-lol-hq-cyan group-hover:scale-110 transition-transform" />
          </button>

          <button
            disabled={!isDataLoaded || loadingSaves}
            onClick={() => setShowLoad((v) => !v)}
            className="group flex items-center justify-between p-5 border border-white/12 bg-black/45 hover:border-lol-hq-cyan/35 hover:bg-lol-hq-cyan/10 transition-all disabled:opacity-40 rounded-sm backdrop-blur-sm"
          >
            <div className="text-left">
              <div className="font-display font-bold uppercase tracking-wide text-white/90">
                Carregar jogo
              </div>
              <div className="text-[11px] mt-0.5 text-white/45">
                {loadingSaves
                  ? 'Buscando saves…'
                  : validSaves.length
                    ? `${validSaves.length} save(s) disponível(is)`
                    : 'Nenhum save ainda — jogue e salve no hub'}
              </div>
            </div>
            {loadingSaves ? (
              <Loader2 className="w-7 h-7 animate-spin text-white/40" />
            ) : (
              <Activity className="w-7 h-7 text-lol-hq-cyan/70 group-hover:scale-110 transition-transform" />
            )}
          </button>

          {showLoad && (
            <div className="border border-lol-hq-cyan/15 bg-black/70 rounded-sm p-3 space-y-2 backdrop-blur-md">
              {validSaves.length === 0 ? (
                <p className="text-xs text-white/40 font-mono p-2">
                  Pasta <code className="text-lol-hq-cyan/80">saves/</code> vazia. Durante a carreira,
                  use <strong className="text-white/60">Salvar</strong> no painel.
                </p>
              ) : (
                validSaves.map((s) => (
                  <button
                    key={s.slot}
                    type="button"
                    disabled={!!loadingSlot}
                    onClick={() => void handleLoad(s.slot)}
                    className="w-full text-left p-3 border border-white/10 hover:border-lol-hq-cyan/35 bg-black/40 rounded-sm flex items-center justify-between gap-2 transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-white truncate">
                        {s.manager_name}
                        <span className="text-white/30 font-normal"> · </span>
                        <span className="text-lol-hq-cyan">{s.team_abbr || s.team_name}</span>
                      </div>
                      <div className="text-[10px] text-white/35 font-mono mt-0.5">
                        {s.slot}
                        {s.phase ? ` · ${s.phase.replace(/_/g, ' ')}` : ''}
                        {s.week != null ? ` · sem ${s.week}` : ''}
                        {s.saved_at
                          ? ` · ${new Date(s.saved_at).toLocaleString('pt-BR', {
                              dateStyle: 'short',
                              timeStyle: 'short',
                            })}`
                          : ''}
                      </div>
                    </div>
                    {loadingSlot === s.slot ? (
                      <Loader2 className="w-4 h-4 animate-spin text-lol-hq-cyan shrink-0" />
                    ) : (
                      <FolderOpen className="w-4 h-4 text-lol-hq-cyan/60 shrink-0" />
                    )}
                  </button>
                ))
              )}
              {loadError && (
                <p className="text-[11px] text-lol-red-side font-mono px-1">{loadError}</p>
              )}
            </div>
          )}

          <button
            disabled
            className="flex items-center justify-between p-5 border border-white/10 bg-black/40 text-white/30 cursor-not-allowed rounded-sm backdrop-blur-sm"
          >
            <div className="text-left">
              <div className="font-display font-bold uppercase tracking-wide">Multijogador</div>
              <div className="text-[11px] mt-0.5">Em breve</div>
            </div>
            <Users className="w-7 h-7 opacity-40" />
          </button>
        </div>
      </div>
    </div>
  );
}
