import { PlayerRole } from '../types/game';

const API_BASE = 'http://127.0.0.1:8000';

export interface Champion {
  id: string;
  name: string;
  primary_role: PlayerRole;
  secondary_role: PlayerRole | null;
  class_type: string;
  damage_type: string;
  early_game_power: number;
  late_game_scaling: number;
  mechanical_difficulty: number;
  utility: number;
}

export interface Team {
  id: string;
  name: string;
  abbreviation: string;
  budget: number;
  monthlyRevenue: number;
  region: string;
}

export interface LeagueInfo {
  id: string;
  name: string;
  abbreviation: string;
  region: string | null;
  current_phase: string | null;
  current_week: number;
  current_day: number;
}

export interface ApiPlayer {
  id: string;
  name: string;
  age: number;
  nationality: string;
  role: string;
  region: string | null;
  teamId: string | null;
  isRookie: boolean;
  currentAbility: number;
  potentialAbility: number;
  mechanics: number;
  championPool: { champion: string; tier: string }[];
  focus: number;
  resilience: number;
  coachability: number;
  teamwork: number;
  consistency: number;
  bigMatchAptitude: number;
  burnoutMeter: number;
  visualFatigue: number;
  mentalFatigue: number;
  gamesPlayedThisSplit: number;
  hasRookieClause: boolean;
  participationRate: number;
  contractExpirySeasons: number;
  monthlySalary: number;
}

export interface CalendarState {
  current_day: number;
  current_week: number;
  current_phase: string;
  day_of_week: number;
  league_id: string | null;
  league_name?: string;
  week_calendar: {
    dayIndex: number;
    dayOfWeek: string;
    week: number;
    type: string;
    eventName?: string | null;
    isToday?: boolean;
    phase?: string;
  }[];
}

export interface StandingRow {
  team_id: string;
  team_name: string;
  wins: number;
  losses: number;
  points: number;
  win_rate: string;
}

async function parseJsonOrThrow(response: Response, fallback: string) {
  if (!response.ok) {
    let detail = fallback;
    try {
      const body = await response.json();
      detail = body.detail || body.message || fallback;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : fallback);
  }
  return response.json();
}

export const api = {
  getTeams: async (): Promise<Team[]> => {
    const response = await fetch(`${API_BASE}/teams`);
    return parseJsonOrThrow(response, 'Failed to fetch teams');
  },

  getTeamPlayers: async (teamId: string): Promise<ApiPlayer[]> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/players`);
    return parseJsonOrThrow(response, 'Failed to fetch players');
  },

  getChampions: async (): Promise<Champion[]> => {
    const response = await fetch(`${API_BASE}/champions`);
    return parseJsonOrThrow(response, 'Failed to fetch champions');
  },

  getLeagues: async (): Promise<LeagueInfo[]> => {
    const response = await fetch(`${API_BASE}/leagues`);
    return parseJsonOrThrow(response, 'Failed to fetch leagues');
  },

  getStandings: async (leagueId: string): Promise<StandingRow[]> => {
    const response = await fetch(`${API_BASE}/leagues/${leagueId}/standings`);
    return parseJsonOrThrow(response, 'Failed to fetch standings');
  },

  getMarketPlayers: async (excludeTeamId?: string): Promise<ApiPlayer[]> => {
    const qs = excludeTeamId ? `?exclude_team_id=${excludeTeamId}` : '';
    const response = await fetch(`${API_BASE}/market/players${qs}`);
    return parseJsonOrThrow(response, 'Failed to fetch market players');
  },

  signPlayer: async (payload: {
    team_id: string;
    player_id: string;
    transfer_fee?: number;
    monthly_salary?: number;
    seasons?: number;
  }) => {
    const response = await fetch(`${API_BASE}/transfers/sign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to sign player');
  },

  startLiveMatch: async (payload: {
    blue_team_id: string;
    red_team_id: string;
    is_playoff: boolean;
    split_week: number;
    blue_draft: { champion: string; role: string }[];
    red_draft: { champion: string; role: string }[];
    speed?: '1x' | '2x' | '4x' | 'instant';
  }) => {
    const response = await fetch(`${API_BASE}/matches/live/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed: '2x', ...payload }),
    });
    return parseJsonOrThrow(response, 'Failed to start live match');
  },

  getLiveMatchState: async (matchId: string) => {
    const response = await fetch(`${API_BASE}/matches/live/${matchId}/state`);
    return parseJsonOrThrow(response, 'Failed to fetch match state');
  },

  setLiveMatchSpeed: async (matchId: string, speed: '1x' | '2x' | '4x' | 'instant') => {
    const response = await fetch(`${API_BASE}/matches/live/${matchId}/speed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed }),
    });
    return parseJsonOrThrow(response, 'Failed to set match speed');
  },

  sendCoachComm: async (matchId: string, teamSide: 'BLUE' | 'RED') => {
    const response = await fetch(`${API_BASE}/matches/live/${matchId}/coach-comm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_side: teamSide }),
    });
    return parseJsonOrThrow(response, 'Failed to send coach comms');
  },

  getCalendar: async (): Promise<CalendarState> => {
    const response = await fetch(`${API_BASE}/calendar`);
    return parseJsonOrThrow(response, 'Failed to fetch calendar');
  },

  advanceCalendar: async (managedTeamId?: string) => {
    const qs = managedTeamId ? `?managed_team_id=${managedTeamId}` : '';
    const response = await fetch(`${API_BASE}/calendar/advance${qs}`, {
      method: 'POST',
    });
    return parseJsonOrThrow(response, 'Failed to advance calendar');
  },
};
