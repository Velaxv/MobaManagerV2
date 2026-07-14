import { useGameStore } from '../store/useGameStore';
import { Trophy, Activity, Users, Swords } from 'lucide-react';
import { championSplashUrl } from '../lib/champions';

export function MainMenu() {
  const { setGameState, isDataLoaded } = useGameStore();

  return (
    <div className="min-h-screen relative flex flex-col items-center justify-center p-6 overflow-hidden bg-lol-void">
      <div
        className="absolute inset-0 bg-cover bg-center opacity-25 scale-105"
        style={{ backgroundImage: `url(${championSplashUrl('Aatrox')})` }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(200,155,60,0.15)_0%,_transparent_50%),linear-gradient(180deg,rgba(1,10,19,0.7)_0%,rgba(1,10,19,0.95)_100%)]" />

      <div className="z-10 w-full max-w-xl flex flex-col gap-8 animate-fade-in">
        <div className="border border-lol-gold/40 bg-gradient-to-b from-[#0a1428]/95 to-black/90 p-8 sm:p-10 shadow-lol-gold rounded-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-lol-gold to-transparent" />
          <div className="flex items-center gap-2 mb-4">
            <div className="team-crest !w-8 !h-8 text-[10px]">LM</div>
            <p className="text-[10px] uppercase tracking-[0.35em] text-lol-gold/70 font-semibold">
              CBLOL 2026
            </p>
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-bold text-lol-gold-soft tracking-wide leading-tight">
            League of Legends
            <span className="block text-white mt-1">Manager</span>
          </h1>
          <p className="mt-4 text-sm text-white/45 leading-relaxed border-t border-white/10 pt-4">
            Hub de gestão estilo Football Manager, draft e partida ao vivo no visual do cliente de
            League — imersão tática, sem gacha.
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-[10px] font-mono text-white/30">
            <span className="flex items-center gap-1 border border-white/10 px-2 py-0.5 rounded-sm">
              <Swords className="w-3 h-3 text-lol-gold" /> Draft
            </span>
            <span className="flex items-center gap-1 border border-white/10 px-2 py-0.5 rounded-sm">
              <Trophy className="w-3 h-3 text-lol-gold" /> Live match
            </span>
            <span className="flex items-center gap-1 border border-white/10 px-2 py-0.5 rounded-sm">
              <Users className="w-3 h-3 text-lol-gold" /> Elenco & mercado
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <button
            disabled={!isDataLoaded}
            onClick={() => setGameState('NEW_GAME_SETUP')}
            className="group flex items-center justify-between p-5 border border-lol-gold/50 bg-gradient-to-r from-lol-gold/20 to-transparent hover:from-lol-gold/35 transition-all disabled:opacity-40 rounded-sm"
          >
            <div className="text-left">
              <div className="font-display font-bold text-lol-gold-soft uppercase tracking-wide">
                Nova carreira
              </div>
              <div className="text-[11px] text-white/40 mt-0.5">Assuma um time do CBLOL 2026</div>
            </div>
            <Trophy className="w-7 h-7 text-lol-gold group-hover:scale-110 transition-transform" />
          </button>

          <button
            disabled
            className="flex items-center justify-between p-5 border border-white/10 bg-white/[0.02] text-white/30 cursor-not-allowed rounded-sm"
          >
            <div className="text-left">
              <div className="font-display font-bold uppercase tracking-wide">Carregar jogo</div>
              <div className="text-[11px] mt-0.5">Em breve</div>
            </div>
            <Activity className="w-7 h-7 opacity-40" />
          </button>

          <button
            disabled
            className="flex items-center justify-between p-5 border border-white/10 bg-white/[0.02] text-white/30 cursor-not-allowed rounded-sm"
          >
            <div className="text-left">
              <div className="font-display font-bold uppercase tracking-wide">Multijogador</div>
              <div className="text-[11px] mt-0.5">Em breve</div>
            </div>
            <Users className="w-7 h-7 opacity-40" />
          </button>
        </div>
      </div>

      <div className="absolute bottom-5 left-5 right-5 flex justify-between text-[10px] font-mono text-white/25 uppercase tracking-wider">
        <span>{isDataLoaded ? 'Motor online · seed CBLOL 2026' : 'Conectando ao backend…'}</span>
        <span>v1.2 hub</span>
      </div>
    </div>
  );
}
