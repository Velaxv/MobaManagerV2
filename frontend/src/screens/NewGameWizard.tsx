import { useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { ArrowRight, ArrowLeft } from 'lucide-react';


export function NewGameWizard() {
  const { teams, setManager, setGameState, loadData } = useGameStore();
  const [managerName, setManagerName] = useState('');
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');
  const [isStarting, setIsStarting] = useState(false);

  const selectedTeam = teams.find(t => t.id === selectedTeamId);

  const handleStartCareer = async () => {
    if (!managerName || !selectedTeamId) return;
    
    setIsStarting(true);
    setManager(managerName, selectedTeamId);
    
    // Recarrega os dados para garantir que a store puxe o time correto 
    // Em uma versão mais complexa, o backend geraria a "Career" aqui
    await loadData();
    
    setGameState('PLAYING');
    setIsStarting(false);
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-6 text-white font-mono">
      <div className="w-full max-w-4xl flex flex-col gap-8">
        
        {/* Header */}
        <div className="border-b-2 border-white pb-6 flex justify-between items-end">
          <div>
            <h2 className="text-4xl font-black uppercase tracking-tighter">Setup de Carreira</h2>
            <p className="text-neutral-400 mt-2">Configure seu perfil de treinador e assuma um time.</p>
          </div>
          <button 
            onClick={() => setGameState('MAIN_MENU')}
            className="text-neutral-500 hover:text-white uppercase text-sm tracking-widest flex items-center gap-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
          
          {/* Left Column - Forms */}
          <div className="flex flex-col gap-8">
            <div className="flex flex-col gap-4">
              <label className="text-xl font-bold uppercase tracking-widest">1. Nome do Treinador</label>
              <input 
                type="text" 
                value={managerName}
                onChange={(e) => setManagerName(e.target.value)}
                placeholder="Ex: Tockers"
                className="bg-transparent border-2 border-neutral-700 p-4 text-xl focus:border-red-500 focus:outline-none transition-colors w-full"
              />
            </div>

            <div className="flex flex-col gap-4">
              <label className="text-xl font-bold uppercase tracking-widest">2. Selecione sua Organização</label>
              <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                {teams.map(team => (
                  <button
                    key={team.id}
                    onClick={() => setSelectedTeamId(team.id)}
                    className={`text-left p-4 border-2 transition-all flex items-center justify-between ${
                      selectedTeamId === team.id 
                        ? 'border-red-500 bg-red-500/10 text-white' 
                        : 'border-neutral-800 bg-neutral-900 text-neutral-400 hover:border-neutral-600'
                    }`}
                  >
                    <span className="font-bold">{team.name}</span>
                    <span className="text-sm font-mono opacity-50">{team.abbreviation}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column - Team Preview */}
          <div className="bg-neutral-900 border-2 border-neutral-800 p-8 flex flex-col justify-between">
            {selectedTeam ? (
              <div>
                <h3 className="text-3xl font-black uppercase tracking-tighter mb-2">{selectedTeam.name}</h3>
                <div className="inline-block bg-red-500 text-black font-bold px-2 py-1 text-sm mb-6">
                  {selectedTeam.abbreviation}
                </div>
                
                <div className="space-y-4">
                  <div className="flex justify-between border-b border-neutral-800 pb-2">
                    <span className="text-neutral-500 uppercase">Orçamento Anual</span>
                    <span className="font-bold text-green-400">
                      R$ {selectedTeam.budget.toLocaleString('pt-BR')}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-neutral-800 pb-2">
                    <span className="text-neutral-500 uppercase">Receita Mensal</span>
                    <span className="font-bold">
                      R$ {selectedTeam.monthlyRevenue.toLocaleString('pt-BR')}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-neutral-800 pb-2">
                    <span className="text-neutral-500 uppercase">Região</span>
                    <span className="font-bold">{selectedTeam.region}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-neutral-600 uppercase text-center border-2 border-dashed border-neutral-800 p-8">
                Selecione um time na lista para ver os detalhes da franquia.
              </div>
            )}

            <button
              disabled={!managerName || !selectedTeamId || isStarting}
              onClick={handleStartCareer}
              className="w-full mt-8 bg-white text-black p-4 font-bold uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isStarting ? 'Iniciando Carreira...' : 'Assinar Contrato'}
              {!isStarting && <ArrowRight className="w-5 h-5" />}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
