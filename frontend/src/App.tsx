import { useEffect } from 'react';
import { Dashboard } from './screens/Dashboard';
import { TransferMarket } from './screens/TransferMarket';
import { TacticsDraft } from './screens/TacticsDraft';
import { MatchSimulation } from './screens/MatchSimulation';
import { MainMenu } from './screens/MainMenu';
import { NewGameWizard } from './screens/NewGameWizard';
import { LayoutDashboard, Users, Trophy, Swords } from 'lucide-react';
import { useGameStore } from './store/useGameStore';

function App() {
  const currentScreen = useGameStore(state => state.currentScreen);
  const setCurrentScreen = useGameStore(state => state.setCurrentScreen);
  const loadData = useGameStore(state => state.loadData);
  const gameState = useGameStore(state => state.gameState);
  const manager = useGameStore(state => state.manager);
  const myTeamName = useGameStore(state => state.myTeamName);
  
  useEffect(() => {
    loadData();
  }, [loadData]);

  if (gameState === 'MAIN_MENU') {
    return <MainMenu />;
  }

  if (gameState === 'NEW_GAME_SETUP') {
    return <NewGameWizard />;
  }

  const renderActiveScreen = () => {
    switch (currentScreen) {
      case 'DASHBOARD':
        return <Dashboard />;
      case 'MARKET':
        return <TransferMarket />;
      case 'DRAFT':
        return <TacticsDraft />;
      case 'SIMULATION':
        return <MatchSimulation />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col">
      {/* Header / Barra de Navegação Superior Brutalista */}
      <header className="bg-black border-b-4 border-neutral-800 p-4 sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          
          {/* Logo / Título */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="bg-red-500 text-black px-2 py-1 font-mono font-black text-md tracking-tighter uppercase select-none rounded-sm">
                LOL.MGR
              </div>
              <h1 className="text-sm font-mono font-bold tracking-wider text-neutral-300 uppercase hidden sm:block">
                Manager <span className="text-[10px] text-red-500 font-bold ml-1.5 bg-neutral-900 border border-neutral-800 px-1 rounded-sm">v1.0</span>
              </h1>
            </div>
            
            {manager && (
              <div className="flex items-center gap-2 border-l-2 border-neutral-800 pl-4">
                <span className="text-xs font-mono font-bold text-neutral-400 uppercase">Treinador:</span>
                <span className="text-sm font-mono font-bold text-white uppercase">{manager.name}</span>
                <span className="text-xs font-mono text-neutral-500 mx-1">|</span>
                <span className="text-sm font-mono font-bold text-red-400 uppercase">{myTeamName}</span>
              </div>
            )}
          </div>

          {/* Menus brutalistas */}
          <nav className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setCurrentScreen('DASHBOARD')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-mono font-bold uppercase transition-all border-2 rounded ${
                currentScreen === 'DASHBOARD'
                  ? 'bg-red-500 text-black border-black shadow-[2px_2px_0px_0px_rgba(255,255,255,0.1)]'
                  : 'bg-neutral-900 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-white'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              Painel
            </button>
            <button
              onClick={() => setCurrentScreen('MARKET')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-mono font-bold uppercase transition-all border-2 rounded ${
                currentScreen === 'MARKET'
                  ? 'bg-red-500 text-black border-black shadow-[2px_2px_0px_0px_rgba(255,255,255,0.1)]'
                  : 'bg-neutral-900 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-white'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Transferências
            </button>
            <button
              onClick={() => setCurrentScreen('DRAFT')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-mono font-bold uppercase transition-all border-2 rounded ${
                currentScreen === 'DRAFT'
                  ? 'bg-red-500 text-black border-black shadow-[2px_2px_0px_0px_rgba(255,255,255,0.1)]'
                  : 'bg-neutral-900 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-white'
              }`}
            >
              <Swords className="w-3.5 h-3.5" />
              Táticas / Draft
            </button>
            <button
              onClick={() => setCurrentScreen('SIMULATION')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-mono font-bold uppercase transition-all border-2 rounded ${
                currentScreen === 'SIMULATION'
                  ? 'bg-red-500 text-black border-black shadow-[2px_2px_0px_0px_rgba(255,255,255,0.1)]'
                  : 'bg-neutral-900 text-neutral-400 border-neutral-800 hover:border-neutral-700 hover:text-white'
              }`}
            >
              <Trophy className="w-3.5 h-3.5" />
              Simulação
            </button>
          </nav>

        </div>
      </header>

      {/* Conteúdo Principal */}
      <main className="max-w-7xl w-full mx-auto flex-grow p-2 sm:p-4">
        <div className="bg-neutral-900/40 border-2 border-neutral-950 min-h-[580px]">
          {renderActiveScreen()}
        </div>
      </main>

      {/* Rodapé Brutalista */}
      <footer className="bg-black border-t-2 border-neutral-900 p-3 text-center text-[10px] font-mono text-neutral-600">
        LOL MANAGER CODESPACE — 2026. SEM CRAP OU GACHA. APENAS DADOS E SIMULAÇÃO.
      </footer>
    </div>
  );
}

export default App;
