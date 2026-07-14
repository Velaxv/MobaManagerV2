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

export interface WeekCalendarDay {
  dayIndex: number;
  dayOfWeek: string;
  week: number;
  type: string;
  eventName?: string | null;
  isToday?: boolean;
  phase?: string;
  opponentId?: string | null;
  opponentName?: string | null;
  opponentAbbr?: string | null;
  isHome?: boolean | null;
  sideLabel?: string | null;
  homeTeamId?: string | null;
  awayTeamId?: string | null;
  homeTeamAbbr?: string | null;
  awayTeamAbbr?: string | null;
  roundIndex?: number | null;
  allMatches?: {
    homeTeamId: string;
    awayTeamId: string;
    homeTeamAbbr?: string;
    awayTeamAbbr?: string;
  }[];
}

export interface CalendarState {
  current_day: number;
  current_week: number;
  current_phase: string;
  day_of_week: number;
  league_id: string | null;
  league_name?: string;
  week_calendar: WeekCalendarDay[];
  next_match?: {
    dayIndex: number;
    dayOfWeek: string;
    eventName?: string | null;
    opponentAbbr?: string | null;
    opponentName?: string | null;
    isHome?: boolean | null;
    roundIndex?: number | null;
  } | null;
}

export interface StandingRow {
  team_id: string;
  team_name: string;
  wins: number;
  losses: number;
  points: number;
  win_rate: string;
  is_in_playoffs?: boolean;
  playoff_seed?: number | null;
  final_placement?: number | null;
  prize_earned?: number;
}

export interface RoundMatchResult {
  match_id?: string | null;
  blue_team_id?: string;
  blue_team_name?: string;
  blue_team_abbr?: string;
  red_team_id?: string;
  red_team_name?: string;
  red_team_abbr?: string;
  winner_team_id?: string | null;
  winner_name?: string | null;
  duration?: number | null;
  split_week?: number;
  is_playoff?: boolean;
  status?: string;
  auto_simulated?: boolean;
  series_label?: string;
}

export interface PlayoffSeriesSide {
  team_id?: string | null;
  team_name?: string | null;
  team_abbr?: string | null;
  seed?: number | null;
}

export interface PlayoffSeries {
  id: string;
  round: string;
  label: string;
  best_of: number;
  home: PlayoffSeriesSide;
  away: PlayoffSeriesSide;
  winner_team_id?: string | null;
  status: string;
  feeds_into?: string | null;
  feeds_slot?: string | null;
}

export interface PlayoffBracket {
  status: string;
  format?: string;
  champion_team_id?: string | null;
  champion_name?: string | null;
  seeds?: {
    seed: number;
    team_id: string;
    team_name: string;
    team_abbr: string;
  }[];
  series?: PlayoffSeries[];
  current_round?: string;
  eliminated?: { team_id: string; team_name?: string; eliminated_in?: string }[];
}

export interface PlayoffsResponse {
  status: string;
  message?: string;
  bracket: PlayoffBracket | null;
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

  getLeagueMatches: async (
    leagueId: string,
    opts?: { latest_round?: boolean; week?: number; limit?: number }
  ): Promise<{
    league_id: string;
    count: number;
    week: number | null;
    matches: RoundMatchResult[];
  }> => {
    const params = new URLSearchParams();
    if (opts?.latest_round === false) params.set('latest_round', 'false');
    if (opts?.week != null) params.set('week', String(opts.week));
    if (opts?.limit != null) params.set('limit', String(opts.limit));
    const qs = params.toString() ? `?${params}` : '';
    const response = await fetch(`${API_BASE}/leagues/${leagueId}/matches${qs}`);
    return parseJsonOrThrow(response, 'Failed to fetch league matches');
  },

  getMatchDetails: async (matchId: string) => {
    const response = await fetch(`${API_BASE}/matches/${matchId}`);
    return parseJsonOrThrow(response, 'Failed to fetch match details');
  },

  getPlayoffs: async (leagueId: string): Promise<PlayoffsResponse> => {
    const response = await fetch(`${API_BASE}/leagues/${leagueId}/playoffs`);
    return parseJsonOrThrow(response, 'Failed to fetch playoffs');
  },

  startPlayoffs: async (leagueId: string): Promise<{ bracket: PlayoffBracket; message: string }> => {
    const response = await fetch(`${API_BASE}/leagues/${leagueId}/playoffs/start`, {
      method: 'POST',
    });
    return parseJsonOrThrow(response, 'Failed to start playoffs');
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

  getCalendar: async (managedTeamId?: string): Promise<CalendarState> => {
    const qs = managedTeamId ? `?managed_team_id=${encodeURIComponent(managedTeamId)}` : '';
    const response = await fetch(`${API_BASE}/calendar${qs}`);
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
