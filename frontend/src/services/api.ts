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

  getTeamFinance: async (teamId: string): Promise<{
    team_id: string;
    team_name: string;
    budget: number;
    monthly_revenue: number;
    monthly_payroll: number;
    monthly_net: number;
    runway_months: number | null;
    health: string;
    wages: {
      player_id: string;
      player_name: string;
      role?: string;
      monthly_salary: number;
    }[];
    player_count: number;
  }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/finance`);
    return parseJsonOrThrow(response, 'Failed to fetch team finance');
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

  getDraftAiDecision: async (payload: {
    blue_team_id: string;
    red_team_id: string;
    acting_side: 'BLUE' | 'RED';
    current_turn: number;
    blue_bans: string[];
    red_bans: string[];
    blue_picks: { champion: string; role: string }[];
    red_picks: { champion: string; role: string }[];
  }): Promise<{
    champion: string;
    role?: string | null;
    action: string;
    team: string;
    current_turn: number;
    source?: string;
  }> => {
    const response = await fetch(`${API_BASE}/draft/ai-decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to get draft AI decision');
  },

  getOffseasonStatus: async (managedTeamId?: string) => {
    const qs = managedTeamId
      ? `?managed_team_id=${encodeURIComponent(managedTeamId)}`
      : '';
    const response = await fetch(`${API_BASE}/offseason/status${qs}`);
    return parseJsonOrThrow(response, 'Failed to fetch offseason status');
  },

  startOffseason: async () => {
    const response = await fetch(`${API_BASE}/offseason/start`, { method: 'POST' });
    return parseJsonOrThrow(response, 'Failed to start offseason');
  },

  getOffseasonContracts: async (teamId: string) => {
    const response = await fetch(
      `${API_BASE}/offseason/contracts?team_id=${encodeURIComponent(teamId)}`
    );
    return parseJsonOrThrow(response, 'Failed to fetch contracts');
  },

  renewContract: async (payload: {
    team_id: string;
    player_id: string;
    seasons?: number;
    monthly_salary?: number;
  }) => {
    const response = await fetch(`${API_BASE}/offseason/renew`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to renew contract');
  },

  releasePlayer: async (payload: { team_id: string; player_id: string }) => {
    const response = await fetch(`${API_BASE}/offseason/release`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to release player');
  },

  startNewSplit: async () => {
    const response = await fetch(`${API_BASE}/offseason/new-split`, { method: 'POST' });
    return parseJsonOrThrow(response, 'Failed to start new split');
  },

  listCareerSaves: async (): Promise<{
    saves: {
      slot: string;
      manager_name?: string;
      team_id?: string;
      team_name?: string;
      team_abbr?: string;
      saved_at?: string;
      phase?: string;
      week?: number;
      day?: number;
      error?: string;
    }[];
  }> => {
    const response = await fetch(`${API_BASE}/career/saves`);
    return parseJsonOrThrow(response, 'Failed to list saves');
  },

  saveCareer: async (payload: {
    slot: string;
    manager_name: string;
    team_id: string;
    label?: string;
  }) => {
    const response = await fetch(`${API_BASE}/career/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to save career');
  },

  loadCareer: async (slot: string) => {
    const response = await fetch(`${API_BASE}/career/load/${encodeURIComponent(slot)}`, {
      method: 'POST',
    });
    return parseJsonOrThrow(response, 'Failed to load career');
  },

  deleteCareerSave: async (slot: string) => {
    const response = await fetch(`${API_BASE}/career/saves/${encodeURIComponent(slot)}`, {
      method: 'DELETE',
    });
    return parseJsonOrThrow(response, 'Failed to delete save');
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

  getTransferValuation: async (playerId: string) => {
    const response = await fetch(`${API_BASE}/transfers/valuation/${playerId}`);
    return parseJsonOrThrow(response, 'Failed to fetch valuation');
  },

  negotiateTransfer: async (payload: {
    team_id: string;
    player_id: string;
    transfer_fee: number;
    monthly_salary: number;
    seasons: number;
  }) => {
    const response = await fetch(`${API_BASE}/transfers/negotiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to negotiate transfer');
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
    managed_team_id?: string;
    game_style?: 'BALANCED' | 'EARLY' | 'MID' | 'LATE';
    coach_comms?: number;
    starter_ids?: string[];
  }) => {
    const response = await fetch(`${API_BASE}/matches/live/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed: '2x', game_style: 'BALANCED', coach_comms: 3, ...payload }),
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
