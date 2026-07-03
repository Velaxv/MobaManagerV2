import { useGameStore } from '../store/useGameStore';
import { Trophy, Activity, Users } from 'lucide-react';

export function MainMenu() {
  const { setGameState, isDataLoaded } = useGameStore();

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background brutalist elements */}
      <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none flex flex-col justify-between">
        <div className="text-[20vw] font-black font-mono leading-none tracking-tighter text-white rotate-12 -ml-32">MOBA</div>
        <div className="text-[20vw] font-black font-mono leading-none tracking-tighter text-red-500 -rotate-12 -mr-32 text-right">MANAGER</div>
      </div>

      <div className="z-10 w-full max-w-2xl flex flex-col gap-12">
        {/* Title Block */}
        <div className="border-4 border-white p-8 bg-black shadow-[16px_16px_0px_0px_rgba(239,68,68,1)]">
          <h1 className="text-6xl md:text-8xl font-black font-mono text-white tracking-tighter uppercase mb-4">
            Moba<br/><span className="text-red-500">Manager</span><br/>2026
          </h1>
          <p className="text-neutral-400 font-mono uppercase tracking-widest text-sm border-t-2 border-neutral-800 pt-4">
            Simulador de Gestão de Esports // Tático & Brutal
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-4">
          <button
            disabled={!isDataLoaded}
            onClick={() => setGameState('NEW_GAME_SETUP')}
            className="group relative border-2 border-white bg-white text-black p-6 font-bold font-mono text-xl uppercase tracking-widest hover:bg-black hover:text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-between"
          >
            <span>Nova Carreira</span>
            <Trophy className="w-8 h-8 group-hover:scale-110 transition-transform" />
          </button>

          <button
            disabled
            className="border-2 border-neutral-700 bg-neutral-900 text-neutral-500 p-6 font-bold font-mono text-xl uppercase tracking-widest cursor-not-allowed flex items-center justify-between"
          >
            <span>Carregar Jogo (Em Breve)</span>
            <Activity className="w-8 h-8 opacity-50" />
          </button>
          
          <button
            disabled
            className="border-2 border-neutral-700 bg-neutral-900 text-neutral-500 p-6 font-bold font-mono text-xl uppercase tracking-widest cursor-not-allowed flex items-center justify-between"
          >
            <span>Multijogador (Em Breve)</span>
            <Users className="w-8 h-8 opacity-50" />
          </button>
        </div>
      </div>
      
      {/* Footer info */}
      <div className="absolute bottom-6 left-6 font-mono text-xs text-neutral-600 uppercase">
        {isDataLoaded ? 'Banco de Dados Carregado. Pronto.' : 'Conectando ao Motor Backend...'}
      </div>
      <div className="absolute bottom-6 right-6 font-mono text-xs text-neutral-600 uppercase">
        v1.0.0
      </div>
    </div>
  );
}
