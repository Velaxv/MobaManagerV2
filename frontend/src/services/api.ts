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

export const api = {
  getTeams: async (): Promise<Team[]> => {
    const response = await fetch(`${API_BASE}/teams`);
    if (!response.ok) throw new Error('Failed to fetch teams');
    return response.json();
  },

  getTeamPlayers: async (teamId: string): Promise<any[]> => {
    const response = await fetch(`${API_BASE}/teams/${teamId}/players`);
    if (!response.ok) throw new Error('Failed to fetch players');
    const data = await response.json();
    return data;
  },

  getChampions: async (): Promise<Champion[]> => {
    const response = await fetch(`${API_BASE}/champions`);
    if (!response.ok) throw new Error('Failed to fetch champions');
    const data = await response.json();
    return data;
  },

  startLiveMatch: async (payload: {
    blue_team_id: string;
    red_team_id: string;
    is_playoff: boolean;
    split_week: number;
    blue_draft: { champion: string; role: string }[];
    red_draft: { champion: string; role: string }[];
  }) => {
    const response = await fetch(`${API_BASE}/matches/live/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to start live match');
    return response.json();
  },

  getLiveMatchState: async (matchId: string) => {
    const response = await fetch(`${API_BASE}/matches/live/${matchId}/state`);
    if (!response.ok) throw new Error('Failed to fetch match state');
    return response.json();
  },

  sendCoachComm: async (matchId: string, teamSide: 'BLUE' | 'RED') => {
    const response = await fetch(`${API_BASE}/matches/live/${matchId}/coach-comm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_side: teamSide })
    });
    if (!response.ok) throw new Error('Failed to send coach comms');
    return response.json();
  },

  getCalendar: async () => {
    const response = await fetch(`${API_BASE}/calendar`);
    if (!response.ok) throw new Error('Failed to fetch calendar');
    return response.json();
  },

  advanceCalendar: async () => {
    const response = await fetch(`${API_BASE}/calendar/advance`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to advance calendar');
    return response.json();
  }
};
