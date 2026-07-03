import { useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { Calendar, AlertTriangle, Play, ShieldAlert, Loader2, Swords } from 'lucide-react';
import { CalendarDayType } from '../types/game';

export function Dashboard() {
  const [isAdvancing, setIsAdvancing] = useState(false);
  const {
    currentWeek,
    currentDayIndex,
    calendar,
    playersCache,
    myTeamName,
    myBudget,
    advanceDay,
    activeMatch,
    setCurrentScreen,
  } = useGameStore();

  // Usa o cache completo que já foi filtrado no loadData (são os jogadores do time atual)
  const myPlayers = playersCache;

  // Detecta jogadores sob alerta de burnout crítico (> 70)
  const burnoutAlerts = myPlayers.filter(p => p.burnoutMeter > 70 || p.visualFatigue > 70);

  const getDayTypeStyles = (type: CalendarDayType) => {
    switch (type) {
      case CalendarDayType.REST:
        return "bg-emerald-950/40 text-emerald-400 border-emerald-800/80";
      case CalendarDayType.MATCH_DAY:
        return "bg-red-950/40 text-red-500 border-red-800/80";
      case CalendarDayType.TRAINING:
        return "bg-neutral-900 text-neutral-300 border-neutral-700";
      case CalendarDayType.SCRIM:
        return "bg-sky-950/40 text-sky-400 border-sky-850";
      default:
        return "bg-neutral-900 border-neutral-700";
    }
  };

  return (
    <div className="flex flex-col gap-6 p-4">
      {/* Top Status Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-neutral-950 border-2 border-neutral-800 shadow-[4px_4px_0px_0px_rgba(23,23,23,1)]">
        <div>
          <h2 className="text-xl font-bold font-mono tracking-tight text-white uppercase">{myTeamName}</h2>
          <p className="text-xs text-neutral-400 font-mono">
            Orçamento: <span className="text-emerald-400 font-bold">€{(myBudget / 1000000).toFixed(2)}M</span>
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-xs text-neutral-500 font-mono uppercase block">Tempo de Jogo</span>
            <span className="font-mono text-sm font-bold text-neutral-200">
              SEMANA {currentWeek} — {calendar[currentDayIndex].dayOfWeek}
            </span>
          </div>
          {activeMatch && activeMatch.currentPhase === 'DRAFT' ? (
            <button
              onClick={() => setCurrentScreen('DRAFT')}
              className="flex items-center gap-2 px-4 py-2.5 bg-amber-500 text-black border-2 border-black font-mono font-bold text-sm tracking-wider uppercase shadow-[3px_3px_0px_0px_rgba(255,255,255,0.15)] hover:bg-amber-400 active:translate-x-0.5 active:translate-y-0.5 transition-all"
            >
              <Swords className="w-4 h-4 fill-black" />
              Iniciar Partida
            </button>
          ) : (
            <button
              disabled={isAdvancing}
              onClick={async () => {
                setIsAdvancing(true);
                await advanceDay();
                setIsAdvancing(false);
              }}
              className="flex items-center gap-2 px-4 py-2.5 bg-red-500 text-black border-2 border-black font-mono font-bold text-sm tracking-wider uppercase shadow-[3px_3px_0px_0px_rgba(255,255,255,0.15)] hover:bg-red-400 active:translate-x-0.5 active:translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-wait"
            >
              {isAdvancing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-black" />}
              {isAdvancing ? 'Avançando...' : 'Avançar Dia'}
            </button>
          )}
        </div>
      </div>

      {/* Calendário Progressivo */}
      <div className="panel-brutal">
        <div className="flex items-center gap-2 mb-4 border-b border-neutral-800 pb-2">
          <Calendar className="w-5 h-5 text-red-500" />
          <h3 className="text-md font-bold font-mono uppercase tracking-wider text-neutral-200">Calendário de Progresso Semanal</h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {calendar.map((day, idx) => {
            const isToday = idx === currentDayIndex;
            return (
              <div
                key={day.dayIndex}
                className={`flex flex-col p-3 border-2 transition-all relative ${
                  isToday ? "border-red-500 ring-1 ring-red-500 shadow-[2px_2px_0px_0px_rgba(239,68,68,1)]" : "border-neutral-800"
                } ${getDayTypeStyles(day.type)}`}
              >
                {isToday && (
                  <span className="absolute top-1.5 right-1.5 text-[9px] font-mono font-bold bg-red-500 text-black px-1 uppercase rounded-sm">
                    HOJE
                  </span>
                )}
                <span className="font-mono font-bold text-xs text-neutral-400">{day.dayOfWeek}</span>
                <span className="font-mono text-[10px] font-semibold mt-1 tracking-wider uppercase opacity-80">
                  {day.type.replace('_', ' ')}
                </span>
                <p className="text-[11px] font-sans mt-2 line-clamp-1 opacity-70">
                  {day.eventName || "Treino diário"}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Grid Principal - Alertas de Burnout e Elenco */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Painel de Alerta de Burnout */}
        <div className="lg:col-span-1 panel-brutal-alert border-red-900/60 bg-red-950/10 flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-red-900/40 pb-2">
            <AlertTriangle className="w-5 h-5 text-red-400 animate-pulse" />
            <h3 className="text-md font-bold font-mono uppercase tracking-wider text-red-400">Alertas de Burnout e Fadiga</h3>
          </div>
          
          {burnoutAlerts.length > 0 ? (
            <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-1">
              {burnoutAlerts.map(player => {
                const isVisualAlert = player.visualFatigue > 70;
                return (
                  <div
                    key={player.id}
                    className="p-3 bg-neutral-950/80 border border-red-900/60 flex flex-col gap-1.5"
                  >
                    <div className="flex justify-between items-start">
                      <span className="font-bold text-neutral-200 text-sm">{player.name}</span>
                      <span className="text-[10px] font-mono bg-red-900/40 text-red-400 border border-red-700/50 px-1 rounded uppercase">
                        {player.role}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                      <div>
                        <span className="text-neutral-500 uppercase text-[10px] block">Burnout Geral</span>
                        <span className={`font-bold ${player.burnoutMeter > 80 ? 'text-red-400' : 'text-amber-400'}`}>
                          {player.burnoutMeter}%
                        </span>
                      </div>
                      <div>
                        <span className="text-neutral-500 uppercase text-[10px] block">Fadiga Visual</span>
                        <span className={`font-bold ${player.visualFatigue > 70 ? 'text-red-400' : 'text-neutral-400'}`}>
                          {player.visualFatigue}%
                        </span>
                      </div>
                    </div>

                    {isVisualAlert && (
                      <p className="text-[10px] text-red-400 bg-red-950/30 border border-red-900/40 p-1.5 rounded mt-1 font-sans">
                        ⚠️ **Debuff de Mecânica Ativo (-25%)**: A fadiga visual está muito elevada. Alocar descanso urgente!
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-8 text-neutral-600 text-center flex-grow font-mono">
              <ShieldAlert className="w-10 h-10 text-neutral-700 mb-2" />
              <span>Sem alertas críticos. Todo o elenco em condições físicas e visuais estáveis.</span>
            </div>
          )}
        </div>

        {/* Resumo do Elenco Ativo */}
        <div className="lg:col-span-2 panel-brutal flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
            <h3 className="text-md font-bold font-mono uppercase tracking-wider text-neutral-200">Elenco Principal G2 Esports</h3>
            <span className="text-xs text-neutral-500 font-mono uppercase">
              Tamanho: {myPlayers.length} / 11 Atletas
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono text-xs select-none">
              <thead>
                <tr className="border-b border-neutral-800 text-neutral-500">
                  <th className="py-2">Jogador</th>
                  <th>Role</th>
                  <th>Idade</th>
                  <th>CA</th>
                  <th>PA</th>
                  <th>Mecânica</th>
                  <th>Foco</th>
                  <th>Fadiga Geral</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-900 text-neutral-300">
                {myPlayers.slice(0, 5).map(player => (
                  <tr key={player.id} className="hover:bg-neutral-800/40">
                    <td className="py-2.5 font-bold font-sans text-neutral-200">{player.name}</td>
                    <td>
                      <span className="bg-neutral-800 px-1.5 py-0.5 rounded text-[10px] text-neutral-400">
                        {player.role}
                      </span>
                    </td>
                    <td>{player.age} anos</td>
                    <td>
                      <span className="text-emerald-400 font-bold">{player.currentAbility}</span>
                    </td>
                    <td className="text-neutral-500">{player.potentialAbility}</td>
                    <td>
                      <span className={`px-1.5 py-0.5 rounded ${player.mechanics >= 16 ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-900/50' : 'text-neutral-300'}`}>
                        {player.mechanics}
                      </span>
                    </td>
                    <td>{player.focus}</td>
                    <td>
                      <div className="w-full max-w-[80px] bg-neutral-950 border border-neutral-800 h-2.5 rounded-sm relative overflow-hidden">
                        <div
                          className={`h-full ${
                            player.burnoutMeter > 70 ? 'bg-red-500' : player.burnoutMeter > 40 ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${player.burnoutMeter}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="text-[11px] text-neutral-500 font-sans border-t border-neutral-800/60 pt-2">
            💡 *Avançar o dia simula a rotina física dos atletas. Dias de MATCH_DAY e TRAINING aumentam o estresse visual/mental, e dias de REST reduzem burnout de forma integrada.*
          </div>
        </div>

      </div>
    </div>
  );
}
