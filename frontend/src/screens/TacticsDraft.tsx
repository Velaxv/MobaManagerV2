import { useState, useEffect } from 'react';
import { useGameStore } from '../store/useGameStore';
import { Sparkles, Ban, RotateCcw } from 'lucide-react';
import { PlayerRole, ChampionPoolTier, DraftTeam, DraftAction } from '../types/game';

export function TacticsDraft() {
  const { draft, playersCache, processDraftAction, resetDraft, champions, submitDraftAndStartMatch } = useGameStore();

  const [selectedRole, setSelectedRole] = useState<PlayerRole>(PlayerRole.MID);
  const [selectedChamp, setSelectedChamp] = useState<string>("");

  // Pega os jogadores titulares
  const myPlayers = playersCache.slice(0, 5);

  // Mapeamento de ações do draft
  const currentActionIndex = draft.currentTurn;
  const isComplete = draft.isComplete;
  
  // Ordem de ações oficiais
  const DRAFT_SEQUENCES = [
    // Bans 1
    { team: DraftTeam.BLUE, action: DraftAction.BAN },
    { team: DraftTeam.RED, action: DraftAction.BAN },
    { team: DraftTeam.BLUE, action: DraftAction.BAN },
    { team: DraftTeam.RED, action: DraftAction.BAN },
    { team: DraftTeam.BLUE, action: DraftAction.BAN },
    { team: DraftTeam.RED, action: DraftAction.BAN },
    // Picks 1
    { team: DraftTeam.BLUE, action: DraftAction.PICK },
    { team: DraftTeam.RED, action: DraftAction.PICK },
    { team: DraftTeam.RED, action: DraftAction.PICK },
    { team: DraftTeam.BLUE, action: DraftAction.PICK },
    { team: DraftTeam.BLUE, action: DraftAction.PICK },
    { team: DraftTeam.RED, action: DraftAction.PICK },
    // Bans 2
    { team: DraftTeam.RED, action: DraftAction.BAN },
    { team: DraftTeam.BLUE, action: DraftAction.BAN },
    { team: DraftTeam.RED, action: DraftAction.BAN },
    { team: DraftTeam.BLUE, action: DraftAction.BAN },
    // Picks 2
    { team: DraftTeam.RED, action: DraftAction.PICK },
    { team: DraftTeam.BLUE, action: DraftAction.PICK },
    { team: DraftTeam.BLUE, action: DraftAction.PICK },
    { team: DraftTeam.RED, action: DraftAction.PICK },
  ];

  const currentStep = !isComplete && currentActionIndex < 20 ? DRAFT_SEQUENCES[currentActionIndex] : null;

  const myTeamName = useGameStore(state => state.myTeamName);
  const activeMatch = useGameStore(state => state.activeMatch);
  
  // Determina o lado do jogador
  const myTeamSide = activeMatch?.blueTeam === myTeamName ? DraftTeam.BLUE : DraftTeam.RED;
  const isMyTurn = currentStep && currentStep.team === myTeamSide;

  // Lista de campeões disponíveis para a role selecionada da base real
  const championsList = champions
    .filter(c => c.primary_role === selectedRole || c.secondary_role === selectedRole)
    .map(c => c.name)
    .sort();

  // Verifica o nível de conforto do jogador titular da role com o campeão selecionado
  const getComfortLevel = (championName: string, role: PlayerRole) => {
    const player = myPlayers.find(p => p.role === role);
    if (!player) return ChampionPoolTier.OFF_POOL;
    
    const pool = player.championPool || [];
    const entry = pool.find(c => c.champion.toLowerCase() === championName.toLowerCase());
    return entry ? entry.tier : ChampionPoolTier.OFF_POOL;
  };

  const handleApplyAction = () => {
    if (!selectedChamp || isComplete || !isMyTurn) return;
    
    // Executa a ação do draft no Zustand store
    processDraftAction(selectedChamp, selectedRole);
    setSelectedChamp("");
  };

  // --- IA de Draft Básica (Frontend-Heavy) ---
  
  useEffect(() => {
    if (!isComplete && currentStep && !isMyTurn) {
      // Turno da IA
      const timer = setTimeout(() => {
        // Lógica burra de IA (pega qualquer campeão disponível que não foi banido/pickado)
        const allUsed = [...draft.blueBans, ...draft.redBans, ...draft.bluePicks.map(p => p.champion), ...draft.redPicks.map(p => p.champion)];
        const availableChamps = champions.filter(c => !allUsed.includes(c.name));
        
        if (currentStep.action === DraftAction.BAN) {
          const randomChamp = availableChamps[Math.floor(Math.random() * availableChamps.length)].name;
          processDraftAction(randomChamp, PlayerRole.MID);
        } else {
          // Achar uma role que a IA ainda não pickou
          const aiPicks = currentStep.team === DraftTeam.BLUE ? draft.bluePicks : draft.redPicks;
          const rolesPicked = aiPicks.map(p => p.role);
          const allRoles = Object.values(PlayerRole);
          const availableRole = allRoles.find(r => !rolesPicked.includes(r)) || PlayerRole.MID;
          
          const roleChamps = availableChamps.filter(c => c.primary_role === availableRole || c.secondary_role === availableRole);
          const champToPick = roleChamps.length > 0 ? roleChamps[Math.floor(Math.random() * roleChamps.length)].name : availableChamps[0].name;
          
          processDraftAction(champToPick, availableRole);
        }
      }, 1500); // Delay de 1.5s para simular pensamento
      return () => clearTimeout(timer);
    }
  }, [draft.currentTurn, isComplete, currentStep, isMyTurn]);

  return (
    <div className="flex flex-col gap-6 p-4">
      {/* Top Banner */}
      <div className="p-4 bg-neutral-950 border-2 border-neutral-800 flex justify-between items-center shadow-[4px_4px_0px_0px_rgba(23,23,23,1)]">
        <div>
          <h2 className="text-xl font-bold font-mono tracking-tight text-white uppercase">Módulo de Táticas e Snake Draft</h2>
          <p className="text-xs text-neutral-400 font-mono">
            Execute os banimentos e seleções táticas de acordo com a sequência competitiva oficial do LoL.
          </p>
        </div>
        <button
          onClick={resetDraft}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-900 border border-neutral-700 hover:border-red-500 hover:text-red-500 font-mono font-bold text-xs uppercase tracking-wider rounded transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reiniciar
        </button>
      </div>

      {/* Interface de Draft */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Lado Esquerdo: Blue Side Picks e Bans */}
        <div className="lg:col-span-1 panel-brutal border-sky-950 bg-sky-950/5 flex flex-col gap-4">
          <h3 className="text-md font-bold font-mono text-sky-400 border-b border-sky-950 pb-2 uppercase tracking-wider flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-sky-500 rounded-sm"></span>
            Blue Side Picks
          </h3>
          
          <div className="flex flex-col gap-2">
            {myPlayers.map((player) => {
              const pick = draft.bluePicks.find(p => p.role === player.role);
              return (
                <div key={player.id} className="p-3 bg-neutral-950 border border-neutral-800 flex flex-col gap-1.5 rounded-sm">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-neutral-300">{player.name}</span>
                    <span className="font-mono text-neutral-500 font-semibold">{player.role}</span>
                  </div>
                  {pick ? (
                    <div className="flex justify-between items-center mt-1">
                      <span className="font-mono text-sm text-sky-400 font-bold">{pick.champion}</span>
                      <span className="text-[10px] font-mono font-bold px-1 bg-sky-950/40 text-sky-400 border border-sky-900/50 rounded uppercase">
                        {getComfortLevel(pick.champion, player.role)}
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs text-neutral-600 font-mono italic mt-1">Aguardando Pick...</span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-4 border-t border-sky-950/40 pt-2 flex flex-col gap-2">
            <span className="text-xs font-mono text-neutral-500 uppercase">Blue Bans</span>
            <div className="flex flex-wrap gap-1.5">
              {draft.blueBans.map((b, i) => (
                <span key={i} className="text-xs font-mono bg-neutral-950 border border-neutral-800 text-neutral-400 px-2 py-0.5 rounded-sm flex items-center gap-1">
                  <Ban className="w-3 h-3 text-red-500/80" />
                  {b}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Centro: Controle do Draft */}
        <div className="lg:col-span-2 panel-brutal flex flex-col gap-6">
          <div className="border-b border-neutral-800 pb-3 flex justify-between items-center">
            <h3 className="text-md font-bold font-mono uppercase tracking-wider text-neutral-200">
              {isComplete ? "Draft Concluído!" : `Ação Tática #${draft.currentTurn + 1}`}
            </h3>
            {currentStep && (
              <span className={`px-2 py-1 text-xs font-mono font-bold rounded-sm border ${
                currentStep.team === DraftTeam.BLUE 
                  ? 'bg-sky-950 text-sky-400 border-sky-900' 
                  : 'bg-red-950 text-red-400 border-red-900'
              }`}>
                {currentStep.team} Side — {currentStep.action}
              </span>
            )}
          </div>

          {!isComplete && currentStep ? (
            <div className="flex flex-col gap-4 bg-neutral-950 p-4 border border-neutral-800">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-neutral-500 font-mono uppercase block mb-1">Lane / Posição</label>
                  <select
                    value={selectedRole}
                    onChange={(e) => {
                      setSelectedRole(e.target.value as PlayerRole);
                      setSelectedChamp("");
                    }}
                    className="w-full bg-neutral-900 border border-neutral-800 focus:border-red-500 focus:outline-none px-3 py-1.5 font-mono text-sm rounded"
                  >
                    {Object.values(PlayerRole).map(role => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-neutral-500 font-mono uppercase block mb-1">Campeão</label>
                  <select
                    value={selectedChamp}
                    onChange={(e) => setSelectedChamp(e.target.value)}
                    className="w-full bg-neutral-900 border border-neutral-800 focus:border-red-500 focus:outline-none px-3 py-1.5 font-mono text-sm rounded"
                  >
                    <option value="">Selecione o Campeão</option>
                    {championsList.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>

              {selectedChamp && currentStep.action === DraftAction.PICK && (
                <div className="p-3 bg-neutral-900 border border-neutral-800 flex flex-col gap-1.5 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-neutral-500 uppercase">Conforto do Jogador:</span>
                    <span className={`font-bold ${
                      getComfortLevel(selectedChamp, selectedRole) === ChampionPoolTier.MAIN ? 'text-emerald-400' :
                      getComfortLevel(selectedChamp, selectedRole) === ChampionPoolTier.SECONDARY ? 'text-sky-400' : 'text-red-400'
                    }`}>
                      {getComfortLevel(selectedChamp, selectedRole)}
                    </span>
                  </div>
                  {getComfortLevel(selectedChamp, selectedRole) === ChampionPoolTier.OFF_POOL && (
                    <p className="text-[10px] text-red-400 bg-red-950/20 border border-red-900/40 p-1.5 rounded font-sans">
                      ⚠️ **Debuff de Champion Pool Ativo (-45% de Mecânica)**: O atleta selecionado não domina este campeão.
                    </p>
                  )}
                </div>
              )}

              <button
                onClick={handleApplyAction}
                disabled={!selectedChamp}
                className="w-full btn-brutal-active flex items-center justify-center gap-2"
              >
                Confirmar {currentStep.action === DraftAction.BAN ? "Banimento" : "Escolha"}
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-8 bg-neutral-950 border border-neutral-800 text-center font-mono">
              <Sparkles className="w-10 h-10 text-emerald-400 mb-2 animate-bounce" />
              <span className="text-sm font-bold text-emerald-400 uppercase mb-4">Draft Concluído com Sucesso!</span>
              
              <button 
                className="btn-brutal px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold tracking-wider"
                onClick={async () => {
                  try {
                    await submitDraftAndStartMatch();
                    useGameStore.getState().setCurrentScreen('SIMULATION');
                  } catch (e) {
                    console.error("Erro ao iniciar partida:", e);
                    alert("Erro ao conectar com o motor de partida!");
                  }
                }}
              >
                IR PARA A PARTIDA
              </button>
            </div>
          )}

          {/* Narrativa do Draft */}
          <div className="flex-grow flex flex-col gap-2">
            <span className="text-xs font-mono text-neutral-500 uppercase">Histórico do Log de Draft</span>
            <div className="h-[200px] overflow-y-auto bg-neutral-950 border border-neutral-800 p-3 font-mono text-xs text-neutral-400 flex flex-col gap-1.5 scroll-smooth">
              {draft.narrative.map((log, i) => (
                <div key={i} className={`p-1.5 rounded-sm ${
                  log.includes("⚠️") ? "bg-red-950/20 border border-red-900/40 text-red-400" : "bg-neutral-900/50"
                }`}>
                  {log}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Lado Direito: Red Side Picks e Bans */}
        <div className="lg:col-span-1 panel-brutal border-red-950 bg-red-950/5 flex flex-col gap-4">
          <h3 className="text-md font-bold font-mono text-red-500 border-b border-red-950 pb-2 uppercase tracking-wider flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-red-500 rounded-sm"></span>
            Red Side Picks
          </h3>
          
          <div className="flex flex-col gap-2">
            {myPlayers.map((player, idx) => {
              const pick = draft.redPicks.find(p => p.role === player.role);
              return (
                <div key={player.id} className="p-3 bg-neutral-950 border border-neutral-800 flex flex-col gap-1.5 rounded-sm">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-neutral-300">Red Player {idx+1}</span>
                    <span className="font-mono text-neutral-500 font-semibold">{player.role}</span>
                  </div>
                  {pick ? (
                    <div className="flex justify-between items-center mt-1">
                      <span className="font-mono text-sm text-red-400 font-bold">{pick.champion}</span>
                    </div>
                  ) : (
                    <span className="text-xs text-neutral-600 font-mono italic mt-1">Aguardando Pick...</span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-4 border-t border-red-950/40 pt-2 flex flex-col gap-2">
            <span className="text-xs font-mono text-neutral-500 uppercase">Red Bans</span>
            <div className="flex flex-wrap gap-1.5">
              {draft.redBans.map((b, i) => (
                <span key={i} className="text-xs font-mono bg-neutral-950 border border-neutral-800 text-neutral-400 px-2 py-0.5 rounded-sm flex items-center gap-1">
                  <Ban className="w-3 h-3 text-red-500/80" />
                  {b}
                </span>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
