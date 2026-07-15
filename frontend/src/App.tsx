import { useEffect } from 'react';
import { Dashboard } from './screens/Dashboard';
import { Training } from './screens/Training';
import { Staff } from './screens/Staff';
import { Organization } from './screens/Organization';
import { TransferMarket } from './screens/TransferMarket';
import { TacticsDraft } from './screens/TacticsDraft';
import { MatchSimulation } from './screens/MatchSimulation';
import { MainMenu } from './screens/MainMenu';
import { NewGameWizard } from './screens/NewGameWizard';
import { Squad } from './screens/Squad';
import { Standings } from './screens/Standings';
import { PatchNotes } from './screens/PatchNotes';
import { GameShell } from './components/GameShell';
import { useGameStore } from './store/useGameStore';

function App() {
  const currentScreen = useGameStore((state) => state.currentScreen);
  const loadData = useGameStore((state) => state.loadData);
  const gameState = useGameStore((state) => state.gameState);

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
      case 'TRAINING':
        return <Training />;
      case 'STAFF':
        return <Staff />;
      case 'ORG':
        return <Organization />;
      case 'SQUAD':
        return <Squad />;
      case 'STANDINGS':
        return <Standings />;
      case 'MARKET':
        return <TransferMarket />;
      case 'PATCH':
        return <PatchNotes />;
      case 'DRAFT':
        return <TacticsDraft />;
      case 'SIMULATION':
        return <MatchSimulation />;
      default:
        return <Dashboard />;
    }
  };

  return <GameShell>{renderActiveScreen()}</GameShell>;
}

export default App;
