import { useEffect } from 'react';
import { useGameStore } from '../store/useGameStore';
import { Play, Zap, Swords, Trophy, Activity, MessageSquare, AlertCircle, Calendar } from 'lucide-react';

export function MatchSimulation() {
  const { activeMatch, startSimulation, triggerCoachComm, playersCache, submitDraftAndStartMatch, syncMatchState } = useGameStore();

  // Polling mechanism
  useEffect(() => {
    let interval: number | undefined;

    if (activeMatch && activeMatch.matchId && activeMatch.currentPhase !== 'COMPLETE' && activeMatch.currentPhase !== 'DRAFT' && activeMatch.currentPhase !== 'DRAFT_COMPLETE') {
      interval = window.setInterval(() => {
        syncMatchState();
      }, 2000); // 2 segundos
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeMatch?.matchId, activeMatch?.currentPhase, syncMatchState]);

  const handleStartDraft = () => {
    startSimulation("G2 Esports", "Fnatic");
  };

  const handleStartMatch = () => {
    submitDraftAndStartMatch();
  };

  const getLogTypeColor = (type: string) => {
    switch (type) {
      case 'success': return 'text-emerald-400 border-emerald-900/60 bg-emerald-950/20';
      case 'warning': return 'text-red-400 border-red-900/60 bg-red-950/20';
      case 'alert': return 'text-amber-400 border-amber-900/60 bg-amber-950/20';
      default: return 'text-neutral-300 border-neutral-800 bg-neutral-900/40';
    }
  };

  return (
    <div className="flex flex-col gap-6 p-4">
      {/* Banner Superior */}
      <div className="p-4 bg-neutral-950 border-2 border-neutral-800 shadow-[4px_4px_0px_0px_rgba(23,23,23,1)]">
        <h2 className="text-xl font-bold font-mono tracking-tight text-white uppercase">Simulador de Partidas 2D</h2>
        <p className="text-xs text-neutral-400 font-mono">
          Estatísticas táticas ao vivo orientadas a dados e logs. Sem distrações 3D.
        </p>
      </div>

      {!activeMatch ? (
        <div className="flex flex-col items-center justify-center p-12 bg-neutral-900 border-2 border-neutral-800 rounded shadow-md text-center max-w-xl mx-auto">
          <Calendar className="w-12 h-12 text-red-500 mb-4 animate-pulse" />
          <h3 className="text-md font-bold font-mono uppercase text-neutral-200 tracking-wider">Partida Disponível no Calendário</h3>
          <p className="text-xs text-neutral-400 mt-2 mb-6 max-w-sm">
            G2 Esports está escalado para jogar contra Fnatic. Vá para o módulo de Táticas para definir seu Draft!
          </p>
          <button
            onClick={handleStartDraft}
            className="btn-brutal-active flex items-center gap-2"
          >
            <Play className="w-4 h-4 fill-black" />
            Preparar Táticas
          </button>
        </div>
      ) : activeMatch.currentPhase === 'DRAFT' ? (
        <div className="flex flex-col items-center justify-center p-12 bg-neutral-900 border-2 border-neutral-800 rounded shadow-md text-center max-w-xl mx-auto">
          <Activity className="w-12 h-12 text-sky-500 mb-4 animate-pulse" />
          <h3 className="text-md font-bold font-mono uppercase text-neutral-200 tracking-wider">Draft em Andamento</h3>
          <p className="text-xs text-neutral-400 mt-2 max-w-sm">
            Acesse a aba <strong>TÁTICAS / DRAFT</strong> no menu superior para concluir o Snake Draft antes de iniciar a simulação.
          </p>
        </div>
      ) : activeMatch.currentPhase === 'DRAFT_COMPLETE' ? (
        <div className="flex flex-col items-center justify-center p-12 bg-neutral-900 border-2 border-neutral-800 rounded shadow-md text-center max-w-xl mx-auto">
          <Swords className="w-12 h-12 text-emerald-500 mb-4 animate-bounce" />
          <h3 className="text-md font-bold font-mono uppercase text-emerald-400 tracking-wider">Táticas Definidas</h3>
          <p className="text-xs text-neutral-400 mt-2 mb-6 max-w-sm">
            O Draft foi concluído. Clique abaixo para iniciar o Motor de Partida e começar o Early Game.
          </p>
          <button
            onClick={handleStartMatch}
            className="btn-brutal-active flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400"
          >
            <Zap className="w-4 h-4 fill-black text-black" />
            INICIAR PARTIDA!
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Painel Principal de Simulação: Logs e Estatísticas */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            
            {/* Placar Brutalista */}
            <div className="panel-brutal bg-black border-neutral-700 flex flex-col gap-4">
              <div className="flex justify-between items-center text-xs font-mono text-neutral-500 uppercase tracking-widest">
                <span>Fase: <strong className="text-red-500">{activeMatch.currentPhase.replace('_', ' ')}</strong></span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-emerald-500 rounded-full animate-ping"></span>
                  AO VIVO
                </span>
              </div>
              
              <div className="grid grid-cols-3 items-center text-center">
                {/* Blue Side */}
                <div className="text-left">
                  <span className="font-mono text-xs text-sky-400 font-bold block">BLUE SIDE</span>
                  <span className="font-sans font-extrabold text-md md:text-lg text-neutral-100">{activeMatch.blueTeam}</span>
                  <div className="text-xs font-mono mt-1 text-neutral-400">
                    Ouro: <strong className="text-neutral-200">{(activeMatch.blueGold / 1000).toFixed(1)}k</strong>
                  </div>
                </div>

                {/* Score central */}
                <div className="flex flex-col items-center">
                  <span className="font-mono text-3xl font-black tracking-tighter text-white">
                    {activeMatch.blueKills} <span className="text-neutral-700 font-sans text-xl">:</span> {activeMatch.redKills}
                  </span>
                  <span className="text-[10px] font-mono bg-neutral-900 border border-neutral-800 text-neutral-400 px-2 py-0.5 rounded mt-2 uppercase">
                    Kills Totais
                  </span>
                </div>

                {/* Red Side */}
                <div className="text-right">
                  <span className="font-mono text-xs text-red-500 font-bold block">RED SIDE</span>
                  <span className="font-sans font-extrabold text-md md:text-lg text-neutral-100">{activeMatch.redTeam}</span>
                  <div className="text-xs font-mono mt-1 text-neutral-400">
                    Ouro: <strong className="text-neutral-200">{(activeMatch.redGold / 1000).toFixed(1)}k</strong>
                  </div>
                </div>
              </div>

              {/* Diferença de Ouro */}
              <div className="w-full bg-neutral-950 border border-neutral-800 h-3 rounded-sm relative overflow-hidden flex items-center justify-center">
                <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-neutral-800"></div>
                {/* Barra de vantagem de ouro */}
                <div
                  className={`h-full absolute top-0 bottom-0 ${
                    activeMatch.blueGold > activeMatch.redGold ? 'bg-sky-600 left-1/2' : 'bg-red-600 right-1/2'
                  }`}
                  style={{
                    width: `${Math.min(50, Math.abs(activeMatch.blueGold - activeMatch.redGold) / 150)}%`
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-neutral-500">
                <span>Vantagem Blue</span>
                <span>Diferença: {Math.abs(activeMatch.blueGold - activeMatch.redGold).toFixed(0)}g</span>
                <span>Vantagem Red</span>
              </div>
            </div>

            {/* Narrativa / Logs do Jogo */}
            <div className="panel-brutal flex-grow flex flex-col gap-3 min-h-[300px]">
              <h3 className="text-sm font-bold font-mono text-neutral-200 border-b border-neutral-800 pb-2 uppercase tracking-wider flex items-center gap-2">
                <Swords className="w-4 h-4 text-red-500" />
                Narrativa e Eventos de Confronto
              </h3>
              
              <div className="flex-grow overflow-y-auto max-h-[380px] bg-neutral-950 border border-neutral-800 p-3 font-mono text-xs flex flex-col gap-2 rounded-sm scroll-smooth">
                {activeMatch.logs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`p-2 border rounded-sm flex items-start gap-2.5 ${getLogTypeColor(log.type)}`}
                  >
                    <span className="text-neutral-500 shrink-0 select-none">[{log.timestamp}]</span>
                    <div>
                      <span className="font-bold uppercase text-[9px] border border-current px-1 rounded-sm mr-2 select-none tracking-tighter">
                        {log.phase}
                      </span>
                      <span className="text-neutral-200 font-sans">{log.text}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Barra Lateral: Ferramentas do Treinador e Comms */}
          <div className="lg:col-span-1 flex flex-col gap-6">
            
            {/* Coach Comms Panel */}
            <div className="panel-brutal flex flex-col gap-4">
              <h3 className="text-sm font-bold font-mono text-neutral-200 border-b border-neutral-800 pb-2 uppercase tracking-wider flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-red-500" />
                Centro de Comando do Treinador
              </h3>

              {activeMatch.currentPhase === 'EARLY_GAME' ? (
                <div className="flex flex-col gap-4">
                  <p className="text-xs text-neutral-400 font-sans leading-relaxed">
                    Você pode instruir o seu jogador Mid (*Caps*) para reverter possíveis penalidades de draft no early game.
                  </p>
                  <button
                    onClick={triggerCoachComm}
                    className="w-full btn-brutal-active flex items-center justify-center gap-2 py-3"
                  >
                    <Zap className="w-4 h-4 fill-black" />
                    Coach Comms
                  </button>
                  <span className="text-[10px] text-center text-neutral-500 font-mono block">
                    Comandos Emitidos: {activeMatch.coachCommsUsed} / 3 (Limite Seguro)
                  </span>
                </div>
              ) : activeMatch.currentPhase === 'COMPLETE' ? (
                <div className="flex flex-col gap-4">
                  <div className="p-4 bg-emerald-950/20 border border-emerald-900 text-center font-mono text-xs text-emerald-400 rounded flex flex-col items-center gap-2">
                    <Trophy className="w-8 h-8 text-emerald-400 animate-bounce" />
                    <span className="font-bold uppercase">Partida Concluída!</span>
                    <span className="text-[10px] text-neutral-500 font-sans">Todos os dados de fadiga e standings da liga foram atualizados no sistema.</span>
                  </div>
                  <button
                    onClick={() => {
                      useGameStore.setState({ activeMatch: undefined, currentScreen: 'DASHBOARD' });
                    }}
                    className="w-full btn-brutal px-4 py-3 bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border-neutral-700 uppercase tracking-widest text-xs"
                  >
                    Voltar ao Calendário
                  </button>
                </div>
              ) : (
                <div className="p-4 bg-neutral-950 border border-neutral-800 text-center font-mono text-xs text-neutral-500 rounded flex items-center gap-2 justify-center">
                  <AlertCircle className="w-4 h-4" />
                  <span>Early Game encerrado. Comandos do Coach bloqueados para o Mid/Late.</span>
                </div>
              )}

              {/* Painel de Feedback Tático de Comms */}
              {activeMatch.coachCommsFeedback && (
                <div className={`p-3 border rounded text-xs font-mono mt-2 ${
                  activeMatch.coachCommsUsed > 3 
                    ? 'bg-red-950/20 border-red-900 text-red-400' 
                    : 'bg-emerald-950/20 border-emerald-900 text-emerald-400'
                }`}>
                  {activeMatch.coachCommsFeedback}
                </div>
              )}
            </div>

            {/* Atletas em Campo Status */}
            <div className="panel-brutal flex flex-col gap-3">
              <h3 className="text-sm font-bold font-mono text-neutral-200 border-b border-neutral-800 pb-2 uppercase tracking-wider">
                Monitor Tático Individual
              </h3>
              <div className="flex flex-col gap-2">
                {playersCache.slice(0, 5).map(player => (
                  <div key={player.id} className="p-2.5 bg-neutral-950 border border-neutral-800 flex justify-between items-center text-xs font-mono">
                    <div className="flex flex-col">
                      <span className="font-bold font-sans text-neutral-200">{player.name.split(" ")[0]}</span>
                      <span className="text-[9px] text-neutral-500 uppercase">{player.role}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-neutral-500 block uppercase">Foco</span>
                      <span className={`font-bold ${player.focus > 15 ? 'text-emerald-400' : player.focus < 10 ? 'text-red-400' : 'text-neutral-200'}`}>
                        {player.focus} / 20
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>
      )}
    </div>
  );
}
