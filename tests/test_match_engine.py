"""
Testes unitários para o Match Engine e estratégias de simulação (Early, Mid, Late).
"""

import pytest
import numpy as np
from typing import List
from src.shared.enums import PlayerRole, ChampionPoolTier
from src.modules.simulation.match_engine import MatchEngine, MatchInput, MatchSimulationResult

class MockPlayer:
    def __init__(
        self,
        name: str,
        role: PlayerRole,
        current_ability: int,
        mechanics: float,
        champion_pool: List[dict],
        focus: float = 10.0,
        resilience: float = 10.0,
        coachability: float = 10.0,
        teamwork: float = 10.0,
        consistency: float = 10.0,
        big_match_aptitude: float = 10.0,
        burnout_meter: float = 0.0,
        visual_fatigue: float = 0.0,
    ):
        self.id = name + "-uuid"
        self.name = name
        self.role = role
        self.current_ability = current_ability
        self.mechanics = mechanics
        self.champion_pool = champion_pool
        self.focus = focus
        self.resilience = resilience
        self.coachability = coachability
        self.teamwork = teamwork
        self.consistency = consistency
        self.big_match_aptitude = big_match_aptitude
        self.burnout_meter = burnout_meter
        self.visual_fatigue = visual_fatigue
        self.games_played_this_split = 0

    def get_champion_pool_tier(self, champion_name: str) -> str:
        for entry in self.champion_pool:
            if entry.get("champion", "").lower() == champion_name.lower():
                return entry.get("tier", "SECONDARY")
        return "OFF_POOL"

class MockStaff:
    def __init__(self, role: str, communication: float = 10.0, meta_reading: float = 10.0):
        self.name = "Mock Coach"
        self.role = role
        self.communication = communication
        self.meta_reading = meta_reading

class MockTeam:
    def __init__(self, id_str: str, name: str, players: List[MockPlayer], staffs: List = None):
        self.id = id_str
        self.name = name
        self.players = players
        self.staffs = staffs if staffs is not None else [MockStaff("HEAD_COACH")]

    def get_starters(self) -> List[MockPlayer]:
        return self.players[:5]

@pytest.fixture
def mock_teams():
    pool_ok = [
        {"champion": "Azir", "tier": ChampionPoolTier.MAIN.value},
        {"champion": "Aatrox", "tier": ChampionPoolTier.MAIN.value},
        {"champion": "Jinx", "tier": ChampionPoolTier.MAIN.value},
        {"champion": "Lee Sin", "tier": ChampionPoolTier.MAIN.value},
        {"champion": "Thresh", "tier": ChampionPoolTier.MAIN.value},
    ]

    # Time forte
    blue_players = [
        MockPlayer("B_Top", PlayerRole.TOP, 160, 16.0, pool_ok, resilience=15.0, consistency=15.0),
        MockPlayer("B_Jg", PlayerRole.JUNGLE, 155, 15.0, pool_ok, resilience=15.0, consistency=15.0),
        MockPlayer("B_Mid", PlayerRole.MID, 165, 17.0, pool_ok, resilience=15.0, consistency=15.0),
        MockPlayer("B_Bot", PlayerRole.BOT, 160, 16.0, pool_ok, resilience=15.0, consistency=15.0),
        MockPlayer("B_Sup", PlayerRole.SUPPORT, 150, 14.0, pool_ok, resilience=15.0, consistency=15.0),
    ]

    # Time fraco ou cansado
    red_players = [
        MockPlayer("R_Top", PlayerRole.TOP, 100, 10.0, pool_ok, burnout_meter=85.0), # muito burnout
        MockPlayer("R_Jg", PlayerRole.JUNGLE, 110, 11.0, pool_ok, visual_fatigue=90.0), # muita fadiga visual
        MockPlayer("R_Mid", PlayerRole.MID, 105, 10.0, pool_ok),
        MockPlayer("R_Bot", PlayerRole.BOT, 110, 11.0, pool_ok),
        MockPlayer("R_Sup", PlayerRole.SUPPORT, 100, 10.0, pool_ok),
    ]

    return (
        MockTeam("blue-team-id", "Super Team G2", blue_players),
        MockTeam("red-team-id", "Tired Team FNC", red_players),
    )

def test_match_engine_full_simulation(mock_teams):
    blue_team, red_team = mock_teams
    engine = MatchEngine()

    blue_draft = [
        {"champion": "Aatrox", "role_hint": "TOP"},
        {"champion": "Lee Sin", "role_hint": "JUNGLE"},
        {"champion": "Azir", "role_hint": "MID"},
        {"champion": "Jinx", "role_hint": "BOT"},
        {"champion": "Thresh", "role_hint": "SUPPORT"},
    ]

    red_draft = [
        {"champion": "Aatrox", "role_hint": "TOP"},
        {"champion": "Lee Sin", "role_hint": "JUNGLE"},
        {"champion": "Azir", "role_hint": "MID"},
        {"champion": "Jinx", "role_hint": "BOT"},
        {"champion": "Thresh", "role_hint": "SUPPORT"},
    ]

    match_input = MatchInput(
        blue_team=blue_team,
        red_team=red_team,
        blue_draft=blue_draft,
        red_draft=red_draft,
        is_playoff=True,
        random_seed=42, # seed para teste reproduzível
        blue_coach_comms=2,
        red_coach_comms=0,
        blue_draft_penalty=0.0,
        red_draft_penalty=0.10
    )

    result: MatchSimulationResult = engine.simulate(match_input)

    assert result.match_id is not None
    assert result.winner_side in ["BLUE", "RED"]
    assert result.match_duration_minutes > 20.0
    assert 0.0 <= result.blue_win_probability <= 1.0
    
    # O time Super Team G2 (Blue) deve ser amplamente favorito e vencer devido a atributos, sem burnout e coach comms
    assert result.winner_side == "BLUE"
    assert result.blue_win_probability > 0.70
    assert len(result.full_narrative) > 0
    # Verifica se a vitória do Super Team G2 está declarada em algum dos últimos logs da narrativa
    narrative_end = " ".join(result.full_narrative[-3:])
    assert "Super Team G2 (Blue Side) venceu a partida!" in narrative_end
