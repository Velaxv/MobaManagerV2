import { create } from 'zustand';
import { PlayerRole, Region, ChampionPoolTier, CalendarDayType, SplitPhase, DRAFT_ORDER, DraftAction, DraftTeam } from '../types/game';
import { api } from '../services/api';
import type { Champion, Team } from '../services/api';

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
  phase: 'DRAFT' | 'EARLY' | 'MID' | 'LATE';
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
  currentScreen: 'DASHBOARD' | 'MARKET' | 'DRAFT' | 'SIMULATION';
  currentWeek: number;
  currentDayIndex: number; // 0-6 (Segunda a Domingo)
  totalDaysElapsed: number;
  splitPhase: SplitPhase;
  calendar: CalendarDay[];
  
  // --- Roster do Time e Mercado ---
  isDataLoaded: boolean;
  champions: Champion[];
  teams: Team[];
  myTeamName: string;
  myBudget: number;
  playersCache: Player[]; // Cache de atributos imutáveis / mutáveis dos atletas do mercado e do time
  
  // --- Estado da Partida e Simulação ---
  activeMatch: {
    matchId?: string;
    blueTeam: string;
    redTeam: string;
    blueTeamId?: string;
    redTeamId?: string;
    blueScore: number;
    redScore: number;
    currentPhase: 'DRAFT' | 'DRAFT_COMPLETE' | 'EARLY_GAME' | 'MID_GAME' | 'LATE_GAME' | 'COMPLETE';
    logs: SimLog[];
    blueKills: number;
    redKills: number;
    blueGold: number;
    redGold: number;
    coachCommsUsed: number;
    coachCommsFeedback: string;
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
  setCurrentScreen: (screen: 'DASHBOARD' | 'MARKET' | 'DRAFT' | 'SIMULATION') => void;
  loadData: () => Promise<void>;
  setCalendarDayType: (dayIndex: number, type: CalendarDayType) => void;
  triggerCoachComm: () => void;
  startSimulation: (blueTeam: string, redTeam: string) => void;
  processDraftAction: (champion: string, role?: PlayerRole) => void;
  submitDraftAndStartMatch: () => Promise<void>;
  syncMatchState: () => Promise<void>;
  resetDraft: () => void;
  toggleRookieClause: (playerId: string) => void;
  signPlayer: (playerId: string) => void;
}

// Gerador de calendário inicial (Segunda a Domingo)
const INITIAL_CALENDAR: CalendarDay[] = [
  { dayIndex: 0, dayOfWeek: "SEG", week: 1, type: CalendarDayType.TRAINING },
  { dayIndex: 1, dayOfWeek: "TER", week: 1, type: CalendarDayType.TRAINING },
  { dayIndex: 2, dayOfWeek: "QUA", week: 1, type: CalendarDayType.MATCH_DAY, eventName: "CBLOL: paiN vs LOUD" },
  { dayIndex: 3, dayOfWeek: "QUI", week: 1, type: CalendarDayType.SCRIM },
  { dayIndex: 4, dayOfWeek: "SEX", week: 1, type: CalendarDayType.TRAINING },
  { dayIndex: 5, dayOfWeek: "SAB", week: 1, type: CalendarDayType.MATCH_DAY, eventName: "CBLOL: paiN vs RED" },
  { dayIndex: 6, dayOfWeek: "DOM", week: 1, type: CalendarDayType.REST, eventName: "Descanso Obrigatório" },
];

// Seed do cache com dados brutalistas e consistentes
const INITIAL_PLAYERS: Player[] = [
  {
    id: "png-dyruyo",
    name: "dyruyo (Mid da paiN)",
    age: 21,
    nationality: "Brazilian",
    role: PlayerRole.MID,
    region: Region.CBLOL,
    isRookie: false,
    currentAbility: 145,
    potentialAbility: 180,
    mechanics: 15,
    championPool: [
      { champion: "Azir", tier: ChampionPoolTier.MAIN },
      { champion: "Sylas", tier: ChampionPoolTier.MAIN },
      { champion: "Ahri", tier: ChampionPoolTier.SECONDARY },
    ],
    focus: 15,
    resilience: 16,
    coachability: 17,
    teamwork: 15,
    consistency: 16,
    bigMatchAptitude: 16,
    burnoutMeter: 25,
    visualFatigue: 30,
    mentalFatigue: 20,
    contractExpirySeasons: 3,
    hasRookieClause: false,
    participationRate: 1.0,
  },
  {
    id: "png-wizer",
    name: "Wizer (Choi Ui-seok)",
    age: 26,
    nationality: "Korean",
    role: PlayerRole.TOP,
    region: Region.CBLOL,
    isRookie: false,
    currentAbility: 148,
    potentialAbility: 175,
    mechanics: 16,
    championPool: [
      { champion: "Aatrox", tier: ChampionPoolTier.MAIN },
      { champion: "Jax", tier: ChampionPoolTier.MAIN },
      { champion: "Renekton", tier: ChampionPoolTier.SECONDARY },
    ],
    focus: 15,
    resilience: 15,
    coachability: 18,
    teamwork: 17,
    consistency: 16,
    bigMatchAptitude: 15,
    burnoutMeter: 20,
    visualFatigue: 25,
    mentalFatigue: 18,
    contractExpirySeasons: 3,
    hasRookieClause: false,
    participationRate: 1.0,
  },
  {
    id: "png-cariok",
    name: "Cariok (Marcos Oliveira)",
    age: 24,
    nationality: "Brazilian",
    role: PlayerRole.JUNGLE,
    region: Region.CBLOL,
    isRookie: false,
    currentAbility: 142,
    potentialAbility: 165,
    mechanics: 14,
    championPool: [
      { champion: "Lee Sin", tier: ChampionPoolTier.MAIN },
      { champion: "Maokai", tier: ChampionPoolTier.MAIN },
      { champion: "Rell", tier: ChampionPoolTier.SECONDARY },
    ],
    focus: 16,
    resilience: 14,
    coachability: 16,
    teamwork: 16,
    consistency: 15,
    bigMatchAptitude: 15,
    burnoutMeter: 30,
    visualFatigue: 35,
    mentalFatigue: 25,
    contractExpirySeasons: 3,
    hasRookieClause: false,
    participationRate: 1.0,
  },
  {
    id: "png-titan",
    name: "TitaN (Alexandre Lima)",
    age: 23,
    nationality: "Brazilian",
    role: PlayerRole.BOT,
    region: Region.CBLOL,
    isRookie: false,
    currentAbility: 150,
    potentialAbility: 185,
    mechanics: 16,
    championPool: [
      { champion: "Kai'Sa", tier: ChampionPoolTier.MAIN },
      { champion: "Aphelios", tier: ChampionPoolTier.MAIN },
    ],
    focus: 13,
    resilience: 17,
    coachability: 15,
    teamwork: 16,
    consistency: 14,
    bigMatchAptitude: 17,
    burnoutMeter: 40,
    visualFatigue: 45,
    mentalFatigue: 35,
    contractExpirySeasons: 3,
    hasRookieClause: false,
    participationRate: 1.0,
  },
  {
    id: "png-kuri",
    name: "Kuri (Choi Won-yeong)",
    age: 25,
    nationality: "Korean",
    role: PlayerRole.SUPPORT,
    region: Region.CBLOL,
    isRookie: false,
    currentAbility: 138,
    potentialAbility: 160,
    mechanics: 14,
    championPool: [
      { champion: "Thresh", tier: ChampionPoolTier.MAIN },
      { champion: "Lulu", tier: ChampionPoolTier.MAIN },
      { champion: "Rell", tier: ChampionPoolTier.SECONDARY },
    ],
    focus: 15,
    resilience: 15,
    coachability: 16,
    teamwork: 16,
    consistency: 15,
    bigMatchAptitude: 15,
    burnoutMeter: 22,
    visualFatigue: 20,
    mentalFatigue: 24,
    contractExpirySeasons: 3,
    hasRookieClause: false,
    participationRate: 1.0,
  },
  // --- Reservas e Academy da paiN Gaming ---
  {
    id: "png-reserve-1",
    name: "paiN Academy TOP",
    age: 18,
    nationality: "Brazilian",
    role: PlayerRole.TOP,
    region: Region.CBLOL,
    isRookie: true,
    currentAbility: 100,
    potentialAbility: 140,
    mechanics: 11,
    championPool: [{ champion: "Aatrox", tier: ChampionPoolTier.MAIN }],
    focus: 11,
    resilience: 12,
    coachability: 14,
    teamwork: 12,
    consistency: 11,
    bigMatchAptitude: 10,
    burnoutMeter: 10,
    visualFatigue: 8,
    mentalFatigue: 12,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  },
  {
    id: "png-rookie-1",
    name: "paiN Academy JUNGLE",
    age: 17,
    nationality: "Brazilian",
    role: PlayerRole.JUNGLE,
    region: Region.CBLOL,
    isRookie: true,
    currentAbility: 105,
    potentialAbility: 145,
    mechanics: 12,
    championPool: [{ champion: "Lee Sin", tier: ChampionPoolTier.MAIN }],
    focus: 10,
    resilience: 11,
    coachability: 15,
    teamwork: 13,
    consistency: 11,
    bigMatchAptitude: 11,
    burnoutMeter: 5,
    visualFatigue: 4,
    mentalFatigue: 6,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  },
  {
    id: "png-rookie-2",
    name: "paiN Academy MID",
    age: 17,
    nationality: "Brazilian",
    role: PlayerRole.MID,
    region: Region.CBLOL,
    isRookie: true,
    currentAbility: 110,
    potentialAbility: 150,
    mechanics: 13,
    championPool: [{ champion: "Azir", tier: ChampionPoolTier.MAIN }],
    focus: 12,
    resilience: 12,
    coachability: 15,
    teamwork: 13,
    consistency: 12,
    bigMatchAptitude: 11,
    burnoutMeter: 15,
    visualFatigue: 12,
    mentalFatigue: 18,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  },
  {
    id: "png-rookie-3",
    name: "paiN Academy BOT",
    age: 16,
    nationality: "Brazilian",
    role: PlayerRole.BOT,
    region: Region.CBLOL,
    isRookie: true,
    currentAbility: 108,
    potentialAbility: 152,
    mechanics: 12,
    championPool: [{ champion: "Kai'Sa", tier: ChampionPoolTier.MAIN }],
    focus: 11,
    resilience: 12,
    coachability: 13,
    teamwork: 12,
    consistency: 11,
    bigMatchAptitude: 11,
    burnoutMeter: 20,
    visualFatigue: 18,
    mentalFatigue: 22,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  },
  {
    id: "png-rookie-4",
    name: "paiN Academy SUPPORT",
    age: 19,
    nationality: "Brazilian",
    role: PlayerRole.SUPPORT,
    region: Region.CBLOL,
    isRookie: true,
    currentAbility: 102,
    potentialAbility: 142,
    mechanics: 11,
    championPool: [{ champion: "Thresh", tier: ChampionPoolTier.MAIN }],
    focus: 12,
    resilience: 12,
    coachability: 14,
    teamwork: 13,
    consistency: 11,
    bigMatchAptitude: 11,
    burnoutMeter: 8,
    visualFatigue: 10,
    mentalFatigue: 6,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  },
  {
    id: "png-rookie-5",
    name: "paiN Academy Reserve Extra",
    age: 18,
    nationality: "Brazilian",
    role: PlayerRole.MID,
    region: Region.CBLOL,
    isRookie: true,
    currentAbility: 98,
    potentialAbility: 135,
    mechanics: 10,
    championPool: [{ champion: "Orianna", tier: ChampionPoolTier.MAIN }],
    focus: 12,
    resilience: 11,
    coachability: 14,
    teamwork: 12,
    consistency: 11,
    bigMatchAptitude: 10,
    burnoutMeter: 12,
    visualFatigue: 15,
    mentalFatigue: 10,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  },

  // --- Mercado de Transferências (Outros Times / Agentes Livres) ---
  {
    id: "mkt-larssen",
    name: "Larssen (Emil Larsson)",
    age: 26,
    nationality: "Swedish",
    role: PlayerRole.MID,
    region: Region.LEC,
    isRookie: false,
    currentAbility: 152,
    potentialAbility: 162,
    mechanics: 15,
    championPool: [{ champion: "Azir", tier: ChampionPoolTier.MAIN }, { champion: "Viktor", tier: ChampionPoolTier.MAIN }],
    focus: 16,
    resilience: 15,
    coachability: 16,
    teamwork: 16,
    consistency: 16,
    bigMatchAptitude: 14,
    burnoutMeter: 22,
    visualFatigue: 20,
    mentalFatigue: 24,
    contractExpirySeasons: 1, // Contrato expirando!
    hasRookieClause: false,
    participationRate: 0.95,
  },
  {
    id: "mkt-elk",
    name: "Elk (Zhao Jia-Hao)",
    age: 24,
    nationality: "Chinese",
    role: PlayerRole.BOT,
    region: Region.LPL,
    isRookie: false,
    currentAbility: 175,
    potentialAbility: 182,
    mechanics: 19, // Monstro mecânico
    championPool: [{ champion: "Jinx", tier: ChampionPoolTier.MAIN }, { champion: "Kai'Sa", tier: ChampionPoolTier.MAIN }],
    focus: 17,
    resilience: 16,
    coachability: 15,
    teamwork: 15,
    consistency: 18,
    bigMatchAptitude: 18,
    burnoutMeter: 48,
    visualFatigue: 50,
    mentalFatigue: 46,
    contractExpirySeasons: 2,
    hasRookieClause: false,
    participationRate: 1.0,
  },
  {
    id: "mkt-shernfire",
    name: "Shernfire (Shern Cherng Tai)",
    age: 27,
    nationality: "Australian",
    role: PlayerRole.JUNGLE,
    region: Region.CBLOL,
    isRookie: false,
    currentAbility: 120,
    potentialAbility: 125,
    mechanics: 12,
    championPool: [{ champion: "Lee Sin", tier: ChampionPoolTier.MAIN }],
    focus: 11,
    resilience: 13,
    coachability: 14,
    teamwork: 12,
    consistency: 11,
    bigMatchAptitude: 13,
    burnoutMeter: 12,
    visualFatigue: 10,
    mentalFatigue: 14,
    contractExpirySeasons: 0, // Sem contrato (Agente Livre)
    hasRookieClause: false,
    participationRate: 0.80,
  },
  {
    id: "mkt-vlad",
    name: "Vlad (Vladimiros Kourtidis)",
    age: 17, // Menor de 18 anos -> Ilegal para LEC!
    nationality: "Greek",
    role: PlayerRole.MID,
    region: Region.ERL,
    isRookie: true,
    currentAbility: 130,
    potentialAbility: 175,
    mechanics: 16,
    championPool: [{ champion: "Viktor", tier: ChampionPoolTier.MAIN }],
    focus: 12,
    resilience: 14,
    coachability: 16,
    teamwork: 13,
    consistency: 13,
    bigMatchAptitude: 12,
    burnoutMeter: 15,
    visualFatigue: 12,
    mentalFatigue: 18,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  },
  {
    id: "mkt-mikeshore",
    name: "Mike Shore",
    age: 16, // Menor de 18 anos -> Ilegal para LEC!
    nationality: "German",
    role: PlayerRole.SUPPORT,
    region: Region.ERL,
    isRookie: true,
    currentAbility: 110,
    potentialAbility: 165,
    mechanics: 13,
    championPool: [{ champion: "Thresh", tier: ChampionPoolTier.MAIN }],
    focus: 11,
    resilience: 14,
    coachability: 15,
    teamwork: 14,
    consistency: 12,
    bigMatchAptitude: 11,
    burnoutMeter: 5,
    visualFatigue: 4,
    mentalFatigue: 6,
    contractExpirySeasons: 4,
    hasRookieClause: true,
    participationRate: 0.0,
  }
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
  myTeamName: "Moba Manager Club", // Default
  myBudget: 0,
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
    }
  },

  advanceDay: async () => {
    try {
      const advanceResponse = await api.advanceCalendar();
      const calendarData = await api.getCalendar();
      
      const { currentDayIndex, totalDaysElapsed, manager } = get();
      const nextDayIndex = (currentDayIndex + 1) % 7;
      const nextTotalDays = totalDaysElapsed + 1;
      
      set({
        currentDayIndex: nextDayIndex,
        currentWeek: calendarData.current_week,
        splitPhase: calendarData.current_phase as SplitPhase,
        totalDaysElapsed: nextTotalDays,
      });

      // Intercepta dias de jogo
      if (advanceResponse && advanceResponse.results && advanceResponse.results.length > 0) {
        const dayInfo = advanceResponse.results[0];
        if (dayInfo.is_match_day && dayInfo.scheduled_matches) {
          // Checa se o time do manager está jogando
          const myTeamId = manager?.teamId;
          if (myTeamId) {
            const myMatch = dayInfo.scheduled_matches.find(
              (m: any) => m.blue_team_id === myTeamId || m.red_team_id === myTeamId
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
                  logs: [],
                  blueKills: 0,
                  redKills: 0,
                  blueGold: 0,
                  redGold: 0,
                  coachCommsUsed: 0,
                  coachCommsFeedback: "",
                }
              });
            }
          }
        }
      }

    } catch (err) {
      console.error("Falha ao avançar calendário via API:", err);
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

  signPlayer: (playerId) => {
    const { playersCache, myBudget } = get();
    const target = playersCache.find(p => p.id === playerId);
    if (!target) return;
    
    // Contratação básica
    const updated = playersCache.map(p => {
      if (p.id === playerId) {
        return { ...p, id: `png-${p.id}`, region: Region.CBLOL }; // Muda ID para ser do time paiN
      }
      return p;
    });
    
    set({
      playersCache: updated,
      myBudget: myBudget - 250000.00, // Custo fixo simulado de compra
    });
  },

  // --- Fluxo de Simulação de Partida ---
  startSimulation: (blueTeam, redTeam) => {
    const logs: SimLog[] = [
      { phase: 'DRAFT', text: `Partida iniciada: ${blueTeam} contra ${redTeam}. Preparando Snake Draft.`, timestamp: "00:00", type: 'info' }
    ];

    set({
      activeMatch: {
        blueTeam,
        redTeam,
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
      const [teamsData, champsData, calendarData] = await Promise.all([
        api.getTeams(),
        api.getChampions(),
        api.getCalendar()
      ]);
      
      const { manager } = get();
      
      let playersData = INITIAL_PLAYERS;
      if (teamsData.length > 0) {
        // Encontra o ID do time atual do manager, ou usa o primeiro como fallback seguro
        let targetTeam = manager 
          ? teamsData.find(t => t.id === manager.teamId)
          : teamsData.find(t => t.abbreviation === 'PNG');
          
        if (!targetTeam) targetTeam = teamsData[0];

        const teamPlayers = await api.getTeamPlayers(targetTeam.id);
        
        // Mapeia para interface do Frontend
        playersData = teamPlayers.map(p => ({
          id: p.id,
          name: p.name,
          age: 20, // default temp
          nationality: "BR",
          role: p.role as PlayerRole,
          region: Region.CBLOL,
          isRookie: p.isRookie,
          currentAbility: p.currentAbility,
          potentialAbility: p.potentialAbility,
          mechanics: p.mechanics,
          championPool: [], // TODO: map champions
          focus: p.focus,
          resilience: p.resilience,
          coachability: p.coachability,
          teamwork: p.teamwork,
          consistency: p.consistency,
          bigMatchAptitude: p.bigMatchAptitude,
          burnoutMeter: p.burnoutMeter,
          visualFatigue: p.visualFatigue,
          mentalFatigue: p.mentalFatigue,
          contractExpirySeasons: 2,
          hasRookieClause: p.hasRookieClause,
          participationRate: p.participationRate,
        }));
      }

      set({ 
        teams: teamsData, 
        champions: champsData,
        playersCache: playersData.length > 0 ? playersData : INITIAL_PLAYERS,
        currentWeek: calendarData.current_week,
        splitPhase: calendarData.current_phase as SplitPhase,
        currentDayIndex: (Math.max(0, calendarData.current_day - 1)) % 7, // Converte 1-indexed para 0-indexed da semana
        isDataLoaded: true
      });
    } catch (error) {
      console.error("Failed to load game data:", error);
      // Fallback
      set({ isDataLoaded: true });
    }
  },

  submitDraftAndStartMatch: async () => {
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
        red_draft: draft.redPicks.map(p => ({ champion: p.champion, role: p.role }))
      });

      set({
        activeMatch: {
          ...activeMatch,
          matchId: response.match_id,
          currentPhase: response.state.phase,
          blueGold: response.state.blue_gold,
          redGold: response.state.red_gold,
          blueKills: response.state.blue_kills,
          redKills: response.state.red_kills,
        }
      });
    } catch (error) {
      console.error("Failed to start live match:", error);
    }
  },

  syncMatchState: async () => {
    const { activeMatch } = get();
    if (!activeMatch || !activeMatch.matchId) return;

    try {
      const state = await api.getLiveMatchState(activeMatch.matchId);
      
      // Parse logs narrativos do backend
      const newLogs = state.event_logs.map((log: any) => ({
        phase: log.phase || state.phase,
        text: log.message,
        timestamp: `${state.current_minute}:00`,
        type: log.severity === 'high' ? 'alert' : log.severity === 'medium' ? 'warning' : 'info'
      }));

      set({
        activeMatch: {
          ...activeMatch,
          currentPhase: state.phase,
          blueGold: state.blue_gold,
          redGold: state.red_gold,
          blueKills: state.blue_kills,
          redKills: state.red_kills,
          logs: newLogs
        }
      });
    } catch (error) {
      console.error("Failed to sync match state:", error);
    }
  }
}));
