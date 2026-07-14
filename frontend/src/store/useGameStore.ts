import { create } from 'zustand';
import { PlayerRole, Region, ChampionPoolTier, CalendarDayType, SplitPhase, DRAFT_ORDER, DraftAction, DraftTeam } from '../types/game';
import { api } from '../services/api';
import type { ApiPlayer, Champion, StandingRow, Team } from '../services/api';

function mapApiPlayer(p: ApiPlayer): Player {
  return {
    id: p.id,
    name: p.name,
    age: p.age ?? 20,
    nationality: p.nationality || 'BR',
    role: p.role as PlayerRole,
    region: (p.region as Region) || Region.CBLOL,
    isRookie: !!p.isRookie,
    currentAbility: p.currentAbility,
    potentialAbility: p.potentialAbility,
    mechanics: p.mechanics,
    championPool: (p.championPool || []).map((c) => ({
      champion: c.champion,
      tier: (c.tier as ChampionPoolTier) || ChampionPoolTier.SECONDARY,
    })),
    focus: p.focus,
    resilience: p.resilience,
    coachability: p.coachability,
    teamwork: p.teamwork,
    consistency: p.consistency,
    bigMatchAptitude: p.bigMatchAptitude,
    burnoutMeter: p.burnoutMeter,
    visualFatigue: p.visualFatigue,
    mentalFatigue: p.mentalFatigue,
    contractExpirySeasons: p.contractExpirySeasons ?? 0,
    hasRookieClause: !!p.hasRookieClause,
    participationRate: p.participationRate ?? 0,
    teamId: p.teamId ?? null,
  };
}

function mapWeekCalendar(
  days: {
    dayIndex: number;
    dayOfWeek: string;
    week: number;
    type: string;
    eventName?: string | null;
  }[]
): CalendarDay[] {
  return days.map((d) => ({
    dayIndex: d.dayIndex,
    dayOfWeek: d.dayOfWeek,
    week: d.week,
    type: (d.type as CalendarDayType) || CalendarDayType.TRAINING,
    eventName: d.eventName || undefined,
  }));
}

// Interface do Jogador no Frontend
export interface Player {
  id: string;
  name: string;
  age: number;
  nationality: string;
  role: PlayerRole;
  region: Region;
  isRookie: boolean;
  currentAbility: number; // CA 0-200
  potentialAbility: number; // PA 0-200
  mechanics: number; // 1-20
  championPool: { champion: string; tier: ChampionPoolTier }[];
  focus: number; // 1-20
  resilience: number; // 1-20
  coachability: number; // 1-20
  teamwork: number; // 1-20
  consistency: number; // 1-20
  bigMatchAptitude: number; // 1-20
  burnoutMeter: number; // 0-100
  visualFatigue: number; // 0-100
  mentalFatigue: number; // 0-100
  contractExpirySeasons: number; // Duração restante em temporadas
  hasRookieClause: boolean;
  participationRate: number; // Participação de partidas (0.0 - 1.0)
  teamId?: string | null;
}

// Evento do calendário
export interface CalendarDay {
  dayIndex: number;
  dayOfWeek: string;
  week: number;
  type: CalendarDayType;
  eventName?: string;
}

// Log de simulação de partida
export interface SimLog {
  phase: string;
  text: string;
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'alert';
}

interface GameState {
  // --- Estado Global e Carreira ---
  gameState: 'MAIN_MENU' | 'NEW_GAME_SETUP' | 'PLAYING';
  manager: {
    name: string;
    teamId: string;
  } | null;

  // --- Calendário e Estado do Jogo ---
  currentScreen: 'DASHBOARD' | 'SQUAD' | 'MARKET' | 'DRAFT' | 'SIMULATION' | 'STANDINGS';
  currentWeek: number;
  currentDayIndex: number; // 0-6 (Segunda a Domingo)
  totalDaysElapsed: number;
  splitPhase: SplitPhase;
  calendar: CalendarDay[];
  
  // --- Roster do Time e Mercado ---
  isDataLoaded: boolean;
  champions: Champion[];
  teams: Team[];
  leagueId: string | null;
  standings: StandingRow[];
  lastAutoResults: { winner_name?: string; blue_team_name?: string; red_team_name?: string }[];
  myTeamName: string;
  myBudget: number;
  myPlayers: Player[];
  marketPlayers: Player[];
  playersCache: Player[]; // Compat: myPlayers + market (legado de telas)
  
  // --- Estado da Partida e Simulação ---
  activeMatch: {
    matchId?: string;
    blueTeam: string;
    redTeam: string;
    blueTeamId?: string;
    redTeamId?: string;
    blueScore: number;
    redScore: number;
    currentPhase: 'DRAFT' | 'DRAFT_COMPLETE' | 'EARLY_GAME' | 'MID_GAME' | 'LATE_GAME' | 'COMPLETE' | 'FINISHED' | 'SETUP';
    logs: SimLog[];
    blueKills: number;
    redKills: number;
    blueGold: number;
    redGold: number;
    blueDragons?: number;
    redDragons?: number;
    blueBarons?: number;
    redBarons?: number;
    currentMinute?: number;
    coachCommsUsed: number;
    coachCommsFeedback: string;
    winnerSide?: string | null;
    speed?: '1x' | '2x' | '4x' | 'instant';
  } | null;
  
  // --- Estado do Draft ---
  draft: {
    currentTurn: number; // 0-19
    blueBans: string[];
    redBans: string[];
    bluePicks: { champion: string; role: PlayerRole }[];
    redPicks: { champion: string; role: PlayerRole }[];
    isComplete: boolean;
    narrative: string[];
  };

  // --- Ações ---
  setGameState: (state: 'MAIN_MENU' | 'NEW_GAME_SETUP' | 'PLAYING') => void;
  setManager: (name: string, teamId: string) => void;
  advanceDay: () => Promise<void>;
  setCurrentScreen: (screen: 'DASHBOARD' | 'SQUAD' | 'MARKET' | 'DRAFT' | 'SIMULATION' | 'STANDINGS') => void;
  loadData: () => Promise<void>;
  refreshRosterAndMarket: () => Promise<void>;
  setCalendarDayType: (dayIndex: number, type: CalendarDayType) => void;
  triggerCoachComm: () => void;
  startSimulation: (blueTeam: string, redTeam: string, blueTeamId?: string, redTeamId?: string) => void;
  processDraftAction: (champion: string, role?: PlayerRole) => void;
  submitDraftAndStartMatch: (speed?: '1x' | '2x' | '4x' | 'instant') => Promise<void>;
  setLiveSpeed: (speed: '1x' | '2x' | '4x' | 'instant') => Promise<void>;
  syncMatchState: () => Promise<void>;
  clearActiveMatch: () => void;
  resetDraft: () => void;
  toggleRookieClause: (playerId: string) => void;
  signPlayer: (playerId: string) => Promise<void>;
}

// Calendário fallback (API sobrescreve)
const INITIAL_CALENDAR: CalendarDay[] = [
  { dayIndex: 0, dayOfWeek: 'SEG', week: 1, type: CalendarDayType.TRAINING },
  { dayIndex: 1, dayOfWeek: 'TER', week: 1, type: CalendarDayType.TRAINING },
  { dayIndex: 2, dayOfWeek: 'QUA', week: 1, type: CalendarDayType.MATCH_DAY, eventName: 'CBLOL: FURIA vs RED' },
  { dayIndex: 3, dayOfWeek: 'QUI', week: 1, type: CalendarDayType.SCRIM },
  { dayIndex: 4, dayOfWeek: 'SEX', week: 1, type: CalendarDayType.TRAINING },
  { dayIndex: 5, dayOfWeek: 'SAB', week: 1, type: CalendarDayType.MATCH_DAY, eventName: 'CBLOL: paiN vs LOUD' },
  { dayIndex: 6, dayOfWeek: 'DOM', week: 1, type: CalendarDayType.REST, eventName: 'Descanso Obrigatório' },
];

/** Fallback offline — só CBLOL 2026 (sem G2/T1/LEC/LPL). Prefira dados da API. */
function mkPlayer(
  id: string,
  name: string,
  role: PlayerRole,
  ca: number,
  age: number,
  nationality: string,
  opts?: Partial<Player>
): Player {
  return {
    id,
    name,
    age,
    nationality,
    role,
    region: Region.CBLOL,
    isRookie: false,
    currentAbility: ca,
    potentialAbility: ca + 20,
    mechanics: 14,
    championPool: [],
    focus: 14,
    resilience: 14,
    coachability: 14,
    teamwork: 14,
    consistency: 14,
    bigMatchAptitude: 14,
    burnoutMeter: 15,
    visualFatigue: 10,
    mentalFatigue: 12,
    contractExpirySeasons: 3,
    hasRookieClause: false,
    participationRate: 1.0,
    ...opts,
  };
}

const INITIAL_PLAYERS: Player[] = [
  // paiN 2026
  mkPlayer('png-robo', 'Robo', PlayerRole.TOP, 151, 28, 'Brazil'),
  mkPlayer('png-cariok', 'CarioK', PlayerRole.JUNGLE, 145, 26, 'Brazil'),
  mkPlayer('png-keine', 'Keine', PlayerRole.MID, 148, 24, 'South Korea'),
  mkPlayer('png-trigger', 'Trigger', PlayerRole.BOT, 147, 23, 'South Korea'),
  mkPlayer('png-kuri', 'Kuri', PlayerRole.SUPPORT, 146, 25, 'South Korea'),
  // Mercado CBLOL (outros times do circuito)
  mkPlayer('mkt-tatu', 'Tatu', PlayerRole.JUNGLE, 155, 22, 'Brazil', { contractExpirySeasons: 1 }),
  mkPlayer('mkt-kaze', 'Kaze', PlayerRole.MID, 152, 24, 'Argentina', { contractExpirySeasons: 1 }),
  mkPlayer('mkt-zest', 'Zest', PlayerRole.TOP, 153, 25, 'South Korea', { contractExpirySeasons: 2 }),
  mkPlayer('mkt-ayu', 'Ayu', PlayerRole.BOT, 154, 23, 'Brazil', { contractExpirySeasons: 2 }),
  mkPlayer('mkt-jojo', 'JoJo', PlayerRole.SUPPORT, 151, 26, 'Brazil', { contractExpirySeasons: 1 }),
  mkPlayer('mkt-wizer', 'Wizer', PlayerRole.TOP, 150, 27, 'South Korea', { contractExpirySeasons: 2 }),
  mkPlayer('mkt-envy', 'Envy', PlayerRole.MID, 149, 28, 'Brazil', { contractExpirySeasons: 1 }),
];

export const useGameStore = create<GameState>((set, get) => ({
  // --- Estado Global e Carreira ---
  gameState: 'MAIN_MENU',
  manager: null,

  // --- Calendário e Estado do Jogo ---
  currentScreen: 'DASHBOARD',
  currentWeek: 1,
  currentDayIndex: 0,
  totalDaysElapsed: 0,
  splitPhase: SplitPhase.OFFSEASON,
  calendar: INITIAL_CALENDAR,
  
  // --- Roster do Time e Mercado ---
  isDataLoaded: false,
  champions: [],
  teams: [],
  leagueId: null,
  standings: [],
  lastAutoResults: [],
  myTeamName: "Moba Manager Club", // Default
  myBudget: 0,
  myPlayers: [],
  marketPlayers: [],
  playersCache: [],

  // --- Estado da Partida e Simulação ---
  activeMatch: null,
  
  // --- Estado do Draft ---
  draft: {
    currentTurn: 0,
    blueBans: [],
    redBans: [],
    bluePicks: [],
    redPicks: [],
    isComplete: false,
    narrative: ["Draft da Partida Iniciado."],
  },

  // --- Ações ---
  setGameState: (state) => set({ gameState: state }),
  
  setManager: (name, teamId) => {
    const teams = get().teams;
    const selectedTeam = teams.find(t => t.id === teamId);
    if (selectedTeam) {
      set({ 
        manager: { name, teamId },
        myTeamName: selectedTeam.name,
        myBudget: selectedTeam.budget
      });
      // Carrega elenco real do time escolhido + mercado
      void get().refreshRosterAndMarket();
    }
  },

  advanceDay: async () => {
    try {
      const { manager, totalDaysElapsed, leagueId } = get();
      const myTeamId = manager?.teamId;
      const advanceResponse = await api.advanceCalendar(myTeamId);
      const calendarData = await api.getCalendar();

      const weekCalendar = calendarData.week_calendar
        ? mapWeekCalendar(calendarData.week_calendar)
        : get().calendar;

      set({
        currentDayIndex: calendarData.day_of_week ?? ((calendarData.current_day - 1) % 7),
        currentWeek: calendarData.current_week,
        splitPhase: calendarData.current_phase as SplitPhase,
        totalDaysElapsed: totalDaysElapsed + 1,
        calendar: weekCalendar,
        leagueId: calendarData.league_id || leagueId,
      });

      // Atualiza standings e elenco (burnout do dia)
      await get().refreshRosterAndMarket();
      const activeLeagueId = get().leagueId || calendarData.league_id;
      if (activeLeagueId) {
        try {
          const standings = await api.getStandings(activeLeagueId);
          set({ standings });
        } catch (e) {
          console.warn('Standings indisponíveis:', e);
        }
      }

      // Intercepta dias de jogo do manager + resultados auto-simulados
      if (advanceResponse?.results?.length > 0) {
        const dayInfo = advanceResponse.results[0];
        const autoResults = dayInfo.auto_simulated_matches || [];
        if (autoResults.length) {
          set({ lastAutoResults: autoResults });
        }

        if (dayInfo.is_match_day && dayInfo.scheduled_matches?.length) {
          const myMatch = dayInfo.scheduled_matches.find(
            (m: { blue_team_id: string; red_team_id: string }) =>
              myTeamId && (m.blue_team_id === myTeamId || m.red_team_id === myTeamId)
          );

          if (myMatch) {
            set({
              activeMatch: {
                matchId: undefined,
                blueTeam: myMatch.blue_team_name,
                redTeam: myMatch.red_team_name,
                blueTeamId: myMatch.blue_team_id,
                redTeamId: myMatch.red_team_id,
                blueScore: 0,
                redScore: 0,
                currentPhase: 'DRAFT',
                logs: [
                  {
                    phase: 'DRAFT',
                    text: `Match day: ${myMatch.blue_team_name} vs ${myMatch.red_team_name}. Vá para Táticas/Draft.`,
                    timestamp: '00:00',
                    type: 'alert',
                  },
                ],
                blueKills: 0,
                redKills: 0,
                blueGold: 500,
                redGold: 500,
                coachCommsUsed: 0,
                coachCommsFeedback: '',
              },
              draft: {
                currentTurn: 0,
                blueBans: [],
                redBans: [],
                bluePicks: [],
                redPicks: [],
                isComplete: false,
                narrative: [`Draft: ${myMatch.blue_team_name} (BLUE) vs ${myMatch.red_team_name} (RED).`],
              },
            });
          }
        }
      }
    } catch (err) {
      console.error('Falha ao avançar calendário via API:', err);
    }
  },

  setCalendarDayType: (dayIndex, type) => {
    const { calendar } = get();
    const updated = calendar.map(d => d.dayIndex === dayIndex ? { ...d, type } : d);
    set({ calendar: updated });
  },

  toggleRookieClause: (playerId) => {
    const { playersCache } = get();
    const updated = playersCache.map(p => p.id === playerId ? { ...p, hasRookieClause: !p.hasRookieClause } : p);
    set({ playersCache: updated });
  },

  signPlayer: async (playerId) => {
    const { manager, marketPlayers } = get();
    if (!manager?.teamId) {
      console.error('Sem time gerenciado para contratar.');
      return;
    }
    const target = marketPlayers.find((p) => p.id === playerId);
    if (!target) return;

    try {
      const response = await api.signPlayer({
        team_id: manager.teamId,
        player_id: playerId,
        transfer_fee: 250000,
        monthly_salary: 5000,
        seasons: 2,
      });
      set({ myBudget: response.team_budget });
      await get().refreshRosterAndMarket();
    } catch (err) {
      console.error('Falha na contratação:', err);
      alert(err instanceof Error ? err.message : 'Falha na contratação');
    }
  },

  // --- Fluxo de Simulação de Partida ---
  startSimulation: (blueTeam, redTeam, blueTeamId, redTeamId) => {
    const logs: SimLog[] = [
      { phase: 'DRAFT', text: `Partida iniciada: ${blueTeam} contra ${redTeam}. Preparando Snake Draft.`, timestamp: "00:00", type: 'info' }
    ];

    set({
      activeMatch: {
        blueTeam,
        redTeam,
        blueTeamId,
        redTeamId,
        blueScore: 0,
        redScore: 0,
        currentPhase: 'DRAFT',
        logs,
        blueKills: 0,
        redKills: 0,
        blueGold: 500,
        redGold: 500,
        coachCommsUsed: 0,
        coachCommsFeedback: "",
      },
      draft: {
        currentTurn: 0,
        blueBans: [],
        redBans: [],
        bluePicks: [],
        redPicks: [],
        isComplete: false,
        narrative: ["Fase de Draft Iniciada. BLUE bane primeiro (BAN 1)."],
      }
    });
  },

  clearActiveMatch: () => {
    set({
      activeMatch: null,
      currentScreen: 'DASHBOARD',
      draft: {
        currentTurn: 0,
        blueBans: [],
        redBans: [],
        bluePicks: [],
        redPicks: [],
        isComplete: false,
        narrative: ['Draft reiniciado.'],
      },
    });
    // Atualiza standings/elenco após partida
    void get().refreshRosterAndMarket();
    const leagueId = get().leagueId;
    if (leagueId) {
      void api.getStandings(leagueId).then((standings) => set({ standings })).catch(() => undefined);
    }
  },

  processDraftAction: (champion, role) => {
    const { draft, activeMatch } = get();
    if (!activeMatch || draft.isComplete) return;

    // Ordem das 20 ações
    const currentAction = DRAFT_ORDER[draft.currentTurn];
    const [phase, side, actionType] = currentAction;
    
    const newBlueBans = [...draft.blueBans];
    const newRedBans = [...draft.redBans];
    const newBluePicks = [...draft.bluePicks];
    const newRedPicks = [...draft.redPicks];
    const newNarrative = [...draft.narrative];

    if (actionType === DraftAction.BAN) {
      if (side === DraftTeam.BLUE) newBlueBans.push(champion);
      else newRedBans.push(champion);
      newNarrative.push(`[${phase}] ${side} banhou ${champion}`);
    } else {
      const pickRole = role || PlayerRole.MID;
      if (side === DraftTeam.BLUE) newBluePicks.push({ champion, role: pickRole });
      else newRedPicks.push({ champion, role: pickRole });
      
      // Exemplo de counter-pick alert na UI:
      // Se Red pickar Viktor contra Azir (Mid)
      let alertMsg = "";
      if (pickRole === PlayerRole.MID && champion === "Viktor" && newBluePicks.some(p => p.champion === "Azir")) {
        alertMsg = `⚠️ COUNTER-PICK! Viktor foi escolhido contra Azir. Atributo Mental do Mid do Blue foi afetado!`;
        newNarrative.push(alertMsg);
      }
      
      newNarrative.push(`[${phase}] ${side} escolheu ${champion} (${pickRole})`);
    }

    const nextTurn = draft.currentTurn + 1;
    const isComplete = nextTurn >= 20;

    const updatedDraft = {
      ...draft,
      currentTurn: nextTurn,
      blueBans: newBlueBans,
      redBans: newRedBans,
      bluePicks: newBluePicks,
      redPicks: newRedPicks,
      isComplete,
      narrative: newNarrative,
    };

    let updatedMatch = { ...activeMatch };
    if (isComplete) {
      updatedMatch.currentPhase = 'DRAFT_COMPLETE';
      updatedMatch.logs.push({
        phase: 'DRAFT',
        text: `Draft Concluído. Prossiga para a tela de Simulação para acionar o motor de partida.`,
        timestamp: "00:00",
        type: 'info',
      });
    }

    set({
      draft: updatedDraft,
      activeMatch: updatedMatch,
    });
  },

  resetDraft: () => {
    set({
      draft: {
        currentTurn: 0,
        blueBans: [],
        redBans: [],
        bluePicks: [],
        redPicks: [],
        isComplete: false,
        narrative: ["Draft reiniciado."],
      }
    });
  },

  // Botão de Ação "Coach Comms"
  triggerCoachComm: async () => {
    const { activeMatch, syncMatchState } = get();
    if (!activeMatch || !activeMatch.matchId || activeMatch.currentPhase !== 'EARLY_GAME') return;

    try {
      const response = await api.sendCoachComm(activeMatch.matchId, 'BLUE');
      
      set({
        activeMatch: {
          ...activeMatch,
          coachCommsUsed: activeMatch.coachCommsUsed + 1,
          coachCommsFeedback: response.message
        }
      });
      
      // Força um sync para pegar os novos logs e debuffs gerados pela action
      await syncMatchState();
    } catch (error: any) {
      set({
        activeMatch: {
          ...activeMatch,
          coachCommsFeedback: `⚠️ Erro: ${error.message || 'Falha ao enviar comms'}`
        }
      });
    }
  },

  setCurrentScreen: (screen) => set({ currentScreen: screen }),

  loadData: async () => {
    try {
      const [teamsData, champsData, calendarData, leagues] = await Promise.all([
        api.getTeams(),
        api.getChampions(),
        api.getCalendar(),
        api.getLeagues().catch(() => []),
      ]);

      const { manager } = get();
      const leagueId = calendarData.league_id || leagues[0]?.id || null;

      let targetTeam = manager
        ? teamsData.find((t) => t.id === manager.teamId)
        : teamsData.find((t) => t.abbreviation === 'PNG');
      if (!targetTeam) targetTeam = teamsData[0];

      let myPlayers: Player[] = [];
      let marketPlayers: Player[] = [];

      if (targetTeam) {
        const [teamPlayers, market] = await Promise.all([
          api.getTeamPlayers(targetTeam.id),
          api.getMarketPlayers(targetTeam.id).catch(() => [] as ApiPlayer[]),
        ]);
        myPlayers = teamPlayers.map(mapApiPlayer);
        marketPlayers = market.map(mapApiPlayer);
      }

      let standings: StandingRow[] = [];
      if (leagueId) {
        standings = await api.getStandings(leagueId).catch(() => []);
      }

      const weekCalendar = calendarData.week_calendar
        ? mapWeekCalendar(calendarData.week_calendar)
        : INITIAL_CALENDAR;

      set({
        teams: teamsData,
        champions: champsData,
        leagueId,
        standings,
        myPlayers,
        marketPlayers,
        playersCache: [...myPlayers, ...marketPlayers],
        myTeamName: targetTeam?.name || get().myTeamName,
        myBudget: targetTeam?.budget ?? get().myBudget,
        currentWeek: calendarData.current_week,
        splitPhase: calendarData.current_phase as SplitPhase,
        currentDayIndex: calendarData.day_of_week ?? (Math.max(0, calendarData.current_day - 1) % 7),
        calendar: weekCalendar,
        isDataLoaded: true,
      });
    } catch (error) {
      console.error('Failed to load game data:', error);
      // Fallback offline
      set({
        isDataLoaded: true,
        myPlayers: INITIAL_PLAYERS.filter((p) => p.id.startsWith('png-')),
        marketPlayers: INITIAL_PLAYERS.filter((p) => p.id.startsWith('mkt-')),
        playersCache: INITIAL_PLAYERS,
      });
    }
  },

  refreshRosterAndMarket: async () => {
    const { manager, teams } = get();
    const teamId = manager?.teamId || teams.find((t) => t.abbreviation === 'PNG')?.id;
    if (!teamId) return;

    try {
      const [teamPlayers, market, teamList] = await Promise.all([
        api.getTeamPlayers(teamId),
        api.getMarketPlayers(teamId),
        api.getTeams(),
      ]);
      const myPlayers = teamPlayers.map(mapApiPlayer);
      const marketPlayers = market.map(mapApiPlayer);
      const myTeam = teamList.find((t) => t.id === teamId);

      set({
        teams: teamList,
        myPlayers,
        marketPlayers,
        playersCache: [...myPlayers, ...marketPlayers],
        myBudget: myTeam?.budget ?? get().myBudget,
        myTeamName: myTeam?.name ?? get().myTeamName,
      });
    } catch (err) {
      console.error('Falha ao atualizar elenco/mercado:', err);
    }
  },

  submitDraftAndStartMatch: async (speed = '2x') => {
    const { draft, activeMatch, teams } = get();
    if (!activeMatch) return;

    try {
      // Pega IDs reais que já estão salvos no activeMatch, ou faz fallback se por algum motivo for antigo
      const blueTeamId = activeMatch.blueTeamId || teams.find(t => activeMatch.blueTeam.includes(t.name))?.id || teams[0].id;
      const redTeamId = activeMatch.redTeamId || teams.find(t => activeMatch.redTeam.includes(t.name))?.id || teams[1].id;

      const response = await api.startLiveMatch({
        blue_team_id: blueTeamId,
        red_team_id: redTeamId,
        is_playoff: false,
        split_week: get().currentWeek,
        blue_draft: draft.bluePicks.map(p => ({ champion: p.champion, role: p.role })),
        red_draft: draft.redPicks.map(p => ({ champion: p.champion, role: p.role })),
        speed,
      });

      const phase = response.state?.phase === 'FINISHED' ? 'COMPLETE' : (response.state?.phase || 'EARLY_GAME');
      set({
        activeMatch: {
          ...activeMatch,
          matchId: response.match_id,
          blueTeamId,
          redTeamId,
          currentPhase: phase,
          blueGold: response.state.blue_gold ?? 15000,
          redGold: response.state.red_gold ?? 15000,
          blueKills: response.state.blue_kills ?? 0,
          redKills: response.state.red_kills ?? 0,
          blueDragons: response.state.blue_dragons ?? 0,
          redDragons: response.state.red_dragons ?? 0,
          blueBarons: response.state.blue_barons ?? 0,
          redBarons: response.state.red_barons ?? 0,
          currentMinute: response.state.current_minute ?? 0,
          speed: (response.state?.speed_label as '1x' | '2x' | '4x' | 'instant') || speed,
        },
        currentScreen: 'SIMULATION',
      });
    } catch (error) {
      console.error("Failed to start live match:", error);
      alert(error instanceof Error ? error.message : 'Falha ao iniciar partida');
    }
  },

  setLiveSpeed: async (speed) => {
    const { activeMatch } = get();
    if (!activeMatch?.matchId) return;
    try {
      await api.setLiveMatchSpeed(activeMatch.matchId, speed);
      set({
        activeMatch: { ...activeMatch, speed },
      });
    } catch (err) {
      console.error('Falha ao alterar velocidade:', err);
    }
  },

  syncMatchState: async () => {
    const { activeMatch } = get();
    if (!activeMatch || !activeMatch.matchId) return;

    try {
      const state = await api.getLiveMatchState(activeMatch.matchId);
      
      // Parse logs narrativos do backend
      const newLogs = (state.event_logs || []).map((log: {
        phase?: string;
        message?: string;
        description?: string;
        timestamp?: string;
        severity?: string;
      }) => ({
        phase: (log.phase || state.phase || 'EARLY') as SimLog['phase'],
        text: log.message || log.description || '',
        timestamp: log.timestamp || `${state.current_minute}:00`,
        type: (log.severity === 'high' ? 'alert' : log.severity === 'medium' ? 'warning' : 'info') as SimLog['type'],
      }));

      let phase = state.phase as typeof activeMatch.currentPhase;
      if (state.is_complete || phase === 'FINISHED') {
        phase = 'COMPLETE';
      }

      set({
        activeMatch: {
          ...activeMatch,
          currentPhase: phase,
          blueGold: state.blue_gold ?? activeMatch.blueGold,
          redGold: state.red_gold ?? activeMatch.redGold,
          blueKills: state.blue_kills ?? activeMatch.blueKills,
          redKills: state.red_kills ?? activeMatch.redKills,
          blueDragons: state.blue_dragons ?? activeMatch.blueDragons ?? 0,
          redDragons: state.red_dragons ?? activeMatch.redDragons ?? 0,
          blueBarons: state.blue_barons ?? activeMatch.blueBarons ?? 0,
          redBarons: state.red_barons ?? activeMatch.redBarons ?? 0,
          currentMinute: state.current_minute ?? activeMatch.currentMinute ?? 0,
          logs: newLogs,
          winnerSide: state.winner_side,
          coachCommsUsed: state.blue_coach_comms_used ?? activeMatch.coachCommsUsed,
          speed: (state.speed_label as typeof activeMatch.speed) || activeMatch.speed,
        }
      });

      // Partida acabou: recarrega elenco (burnout aplicado no backend)
      if (phase === 'COMPLETE') {
        void get().refreshRosterAndMarket();
        const leagueId = get().leagueId;
        if (leagueId) {
          void api.getStandings(leagueId).then((standings) => set({ standings })).catch(() => undefined);
        }
      }
    } catch (error) {
      console.error("Failed to sync match state:", error);
    }
  }
}));
