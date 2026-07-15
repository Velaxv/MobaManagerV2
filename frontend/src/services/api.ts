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
  isStarter?: boolean;
  squadStatus?: string;
  currentAbility: number;
  potentialAbility: number | null;
  mechanics: number;
  championPool: { champion: string; tier: string }[];
  focus: number;
  resilience: number;
  coachability: number;
  teamwork: number;
  consistency: number | null;
  bigMatchAptitude: number | null;
  burnoutMeter: number;
  visualFatigue: number;
  mentalFatigue: number;
  gamesPlayedThisSplit: number;
  hasRookieClause: boolean;
  participationRate: number;
  rookieGamesPlayed?: number;
  rookieTotalLeagueGames?: number;
  rookieExtensionTriggered?: boolean;
  rookieClauseThreshold?: number;
  contractExpirySeasons: number;
  monthlySalary: number;
  // Scouting mask
  consistencyKnown?: boolean;
  bigMatchAptitudeKnown?: boolean;
  potentialAbilityKnown?: boolean;
  consistencyMin?: number | null;
  consistencyMax?: number | null;
  bigMatchAptitudeMin?: number | null;
  bigMatchAptitudeMax?: number | null;
  potentialAbilityMin?: number | null;
  potentialAbilityMax?: number | null;
  scoutingProgress?: number;
  scoutingFullyScouted?: boolean;
  scoutingDaysInvested?: number;
  isFreeAgent?: boolean;
  formAvg?: number | null;
  formTrend?: string | null;
  formLabel?: string | null;
  formLast?: number | null;
  formGames?: number;
  formDiscontent?: number;
  formRatings?: Array<{ rating?: number; note?: string }>;
}

export interface MarketWindowStatus {
  phase: string;
  mode: 'OPEN_FULL' | 'OPEN_FA_ONLY' | 'CLOSED' | string;
  label: string;
  can_buy_from_clubs: boolean;
  can_sign_free_agents: boolean;
  is_open: boolean;
  week?: number;
}

export interface StaffMember {
  id: string;
  name: string;
  role: string;
  role_label?: string;
  role_hint?: string;
  meta_reading: number;
  communication: number;
  monthly_cost: number;
  signing_fee?: number;
}

export interface StaffCandidate {
  candidate_id: string;
  name: string;
  role: string;
  role_label?: string;
  role_hint?: string;
  meta_reading: number;
  communication: number;
  monthly_cost: number;
  signing_fee: number;
  slot_available: boolean;
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
  score?: { home: number; away: number };
  maps?: { map_index: number; winner_team_id?: string }[];
  fearless_used?: string[];
  momentum_team_id?: string | null;
  current_map?: number;
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

export interface DraftScoutReason {
  code: string;
  label: string;
  weight: number;
}

export interface DraftScoutRecommendation {
  champion: string;
  role?: string | null;
  score: number;
  confidence: number;
  priority: number;
  action?: string;
  summary: string;
  reasons: DraftScoutReason[];
  factors?: Record<string, number>;
  global_meta?: {
    games_played_world: number;
    presence_score: number;
    tier: string;
    pick_rate_proxy?: number;
    win_rate_proxy?: number;
  };
  for_player?: string | null;
  pool_tier?: string | null;
}

export interface DraftScoutAdviceResponse {
  action?: string | null;
  team?: string | null;
  current_turn?: number | null;
  scout?: {
    name: string;
    role: string;
    meta_reading: number;
    communication?: number;
  } | null;
  patch?: {
    version?: string;
    bias_applied?: boolean;
  };
  recommendations: DraftScoutRecommendation[];
  intel_note?: string;
  factors?: string[];
  source?: string;
  error?: string;
  session_id?: string;
  opponent_stars?: {
    player_id: string;
    player_name: string;
    star_score: number;
    label: string;
    scouting_progress: number;
  }[];
}

export interface ScoutEvaluation {
  session_id?: string;
  scout_name?: string;
  patch_version?: string;
  hits?: number;
  misses?: number;
  partials?: number;
  accuracy?: number | null;
  follow_rate?: number | null;
  grade?: string;
  summary?: string;
  managed_won?: boolean | null;
  verdicts?: {
    turn: number;
    action: string;
    champion: string;
    status: string;
    detail: string;
    followed?: boolean;
  }[];
  evaluated_at?: string;
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

  getTeamTraining: async (teamId: string): Promise<{
    team_id: string;
    team_name?: string;
    focus: string;
    intensity: string;
    source?: string;
    focuses?: string[];
    intensities?: string[];
    last_session?: {
      day_type?: string;
      focus?: string;
      intensity?: string;
      ca_gains?: number;
      attr_gains?: number;
      players_trained?: number;
      gains?: {
        player_name?: string;
        role?: string;
        ca_delta?: number;
        ca_before?: number;
        ca_after?: number;
        attr_deltas?: Record<string, number>;
      }[];
    } | null;
  }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/training`);
    return parseJsonOrThrow(response, 'Failed to fetch training plan');
  },

  setTeamTraining: async (
    teamId: string,
    focus: string,
    intensity: string
  ): Promise<{ focus: string; intensity: string; message?: string }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/training`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ focus, intensity }),
    });
    return parseJsonOrThrow(response, 'Failed to set training plan');
  },

  getTeamScouting: async (teamId: string): Promise<{
    team_id: string;
    team_name?: string;
    assignment: {
      player_id?: string;
      player_name?: string;
      player_role?: string;
      focus?: string;
      progress?: number;
      days_invested?: number;
      fully_scouted?: boolean;
    } | null;
    staff_power?: {
      staff_count: number;
      avg_meta_reading: number;
      power_mult: number;
      staff?: { name: string; role: string; meta_reading: number }[];
    };
    knowledge_count?: number;
    knowledge_summary?: {
      player_id: string;
      progress: number;
      fully_scouted: boolean;
    }[];
    focuses?: string[];
  }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/scouting`);
    return parseJsonOrThrow(response, 'Failed to fetch scouting status');
  },

  assignScout: async (
    teamId: string,
    playerId: string,
    focus: string = 'ALL'
  ): Promise<{ message?: string; assignment?: Record<string, unknown> }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/scouting/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId, focus }),
    });
    return parseJsonOrThrow(response, 'Failed to assign scout');
  },

  clearScout: async (teamId: string): Promise<{ cleared?: boolean }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/scouting/clear`, {
      method: 'POST',
    });
    return parseJsonOrThrow(response, 'Failed to clear scout assignment');
  },

  getTeamAcademy: async (teamId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/academy`);
    return parseJsonOrThrow(response, 'Failed to fetch academy roster');
  },

  promotePlayer: async (teamId: string, playerId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/academy/promote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId }),
    });
    return parseJsonOrThrow(response, 'Failed to promote player');
  },

  demotePlayer: async (teamId: string, playerId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/academy/demote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId }),
    });
    return parseJsonOrThrow(response, 'Failed to demote player');
  },

  getPatches: async (daysElapsed?: number) => {
    const qs =
      daysElapsed != null ? `?days_elapsed=${encodeURIComponent(String(daysElapsed))}` : '';
    const response = await fetch(`${API_BASE}/patches${qs}`);
    return parseJsonOrThrow(response, 'Failed to fetch patches');
  },

  getCurrentPatch: async (daysElapsed?: number) => {
    const qs =
      daysElapsed != null ? `?days_elapsed=${encodeURIComponent(String(daysElapsed))}` : '';
    const response = await fetch(`${API_BASE}/patches/current${qs}`);
    return parseJsonOrThrow(response, 'Failed to fetch current patch');
  },

  getPatchBadges: async (): Promise<{
    version: string | null;
    badges: Record<string, string>;
    changes: {
      champion: string;
      role: string;
      kind: string;
      summary?: string;
    }[];
  }> => {
    const response = await fetch(`${API_BASE}/patches/badges`);
    return parseJsonOrThrow(response, 'Failed to fetch patch badges');
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
    fearless_used?: string[];
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

  getDraftScoutAdvice: async (payload: {
    blue_team_id: string;
    red_team_id: string;
    managed_team_id: string;
    acting_side: 'BLUE' | 'RED';
    current_turn: number;
    blue_bans: string[];
    red_bans: string[];
    blue_picks: { champion: string; role: string }[];
    red_picks: { champion: string; role: string }[];
    focus_role?: string;
    limit?: number;
    session_id?: string;
    fearless_used?: string[];
  }): Promise<DraftScoutAdviceResponse> => {
    const response = await fetch(`${API_BASE}/draft/scout-advice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to get draft scout advice');
  },

  recordDraftScoutAction: async (payload: {
    session_id: string;
    current_turn: number;
    action: string;
    champion: string;
    role?: string;
  }) => {
    const response = await fetch(`${API_BASE}/draft/scout-session/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseJsonOrThrow(response, 'Failed to record scout action');
  },

  getScoutHistory: async (teamId: string): Promise<{
    team_id: string;
    history: ScoutEvaluation[];
    count: number;
  }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/scout-history`);
    return parseJsonOrThrow(response, 'Failed to fetch scout history');
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

  getMarketWindow: async (): Promise<MarketWindowStatus> => {
    const response = await fetch(`${API_BASE}/market/window`);
    return parseJsonOrThrow(response, 'Failed to fetch market window');
  },

  getFreeAgents: async (opts?: {
    role?: string;
    managedTeamId?: string;
  }): Promise<{ free_agents: ApiPlayer[]; count: number; market_window?: MarketWindowStatus }> => {
    const params = new URLSearchParams();
    if (opts?.role) params.set('role', opts.role);
    if (opts?.managedTeamId) params.set('managed_team_id', opts.managedTeamId);
    const qs = params.toString() ? `?${params}` : '';
    const response = await fetch(`${API_BASE}/market/free-agents${qs}`);
    return parseJsonOrThrow(response, 'Failed to fetch free agents');
  },

  getTeamStaff: async (teamId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/staff`);
    return parseJsonOrThrow(response, 'Failed to fetch staff');
  },

  getTeamPractice: async (teamId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/practice`);
    return parseJsonOrThrow(response, 'Failed to fetch practice status');
  },

  getTeamMorale: async (teamId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/morale`);
    return parseJsonOrThrow(response, 'Failed to fetch morale');
  },

  getTeamOrg: async (teamId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/org`);
    return parseJsonOrThrow(response, 'Failed to fetch org');
  },

  setBoardGoal: async (teamId: string, goal: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/org/board-goal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal }),
    });
    return parseJsonOrThrow(response, 'Failed to set board goal');
  },

  acceptSponsor: async (teamId: string, offerId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/org/sponsors/accept`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ offer_id: offerId }),
    });
    return parseJsonOrThrow(response, 'Failed to accept sponsor');
  },

  dropSponsor: async (teamId: string, sponsorId: string) => {
    const response = await fetch(
      `${API_BASE}/teams/${teamId}/org/sponsors/${sponsorId}/drop`,
      { method: 'POST' }
    );
    return parseJsonOrThrow(response, 'Failed to drop sponsor');
  },

  upgradeFacility: async (teamId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/org/facility/upgrade`, {
      method: 'POST',
    });
    return parseJsonOrThrow(response, 'Failed to upgrade facility');
  },

  getStaffCandidates: async (teamId: string): Promise<{
    candidates: StaffCandidate[];
    budget: number;
    current_counts?: Record<string, number>;
  }> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/staff/candidates`);
    return parseJsonOrThrow(response, 'Failed to fetch staff candidates');
  },

  hireStaff: async (
    teamId: string,
    payload: {
      name: string;
      role: string;
      meta_reading: number;
      communication: number;
      candidate_id?: string;
    }
  ) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/staff/hire`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId, ...payload }),
    });
    return parseJsonOrThrow(response, 'Failed to hire staff');
  },

  fireStaff: async (teamId: string, staffId: string) => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/staff/fire`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId, staff_id: staffId }),
    });
    return parseJsonOrThrow(response, 'Failed to fire staff');
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
    scout_session_id?: string;
    blue_bans?: string[];
    red_bans?: string[];
    series_id?: string;
    fearless_used?: string[];
    series_score?: { home: number; away: number };
    map_index?: number;
    momentum_team_id?: string;
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
