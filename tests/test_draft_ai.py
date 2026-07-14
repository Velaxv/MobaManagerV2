"""
Testes unitários para o Sistema de Draft e IA de Counter-Picking.
"""

import pytest
from typing import List
from src.shared.enums import DraftTeam, DraftAction, PlayerRole, ChampionPoolTier
from src.modules.draft.snake_draft import SnakeDraft, DraftState
from src.modules.draft.draft_ai import DraftAI, calculate_draft_penalties

class MockPlayer:
    def __init__(self, name: str, role: PlayerRole, champion_pool: List[dict]):
        self.name = name
        self.role = role
        self.champion_pool = champion_pool

    def get_champion_pool_tier(self, champion_name: str) -> str:
        for entry in self.champion_pool:
            if entry.get("champion", "").lower() == champion_name.lower():
                return entry.get("tier", "SECONDARY")
        return "OFF_POOL"

class MockTeam:
    def __init__(self, id_str: str, name: str, players: List[MockPlayer]):
        self.id = id_str
        self.name = name
        self.players = players

    def get_starters(self) -> List[MockPlayer]:
        # Retorna todos que são instanciados como titulares
        return self.players[:5]

@pytest.fixture
def mock_teams():
    # Cria pools de campeões mockados
    blue_pool = [
        {"champion": "Azir", "tier": ChampionPoolTier.MAIN.value},
        {"champion": "Aatrox", "tier": ChampionPoolTier.MAIN.value},
        {"champion": "Jinx", "tier": ChampionPoolTier.MAIN.value},
        {"champion": "Lee Sin", "tier": ChampionPoolTier.SECONDARY.value},
        {"champion": "Thresh", "tier": ChampionPoolTier.SECONDARY.value},
    ]
    red_pool = [
        {"champion": "Viktor", "tier": ChampionPoolTier.MAIN.value}, # Viktor countera Azir
        {"champion": "Jax", "tier": ChampionPoolTier.MAIN.value},    # Jax countera Aatrox
        {"champion": "Ezreal", "tier": ChampionPoolTier.MAIN.value}, # Ezreal countera Jinx
        {"champion": "Graves", "tier": ChampionPoolTier.SECONDARY.value},
        {"champion": "Morgana", "tier": ChampionPoolTier.SECONDARY.value},
    ]

    blue_players = [
        MockPlayer("B_Top", PlayerRole.TOP, blue_pool),
        MockPlayer("B_Jg", PlayerRole.JUNGLE, blue_pool),
        MockPlayer("B_Mid", PlayerRole.MID, blue_pool),
        MockPlayer("B_Bot", PlayerRole.BOT, blue_pool),
        MockPlayer("B_Sup", PlayerRole.SUPPORT, blue_pool),
    ]

    red_players = [
        MockPlayer("R_Top", PlayerRole.TOP, red_pool),
        MockPlayer("R_Jg", PlayerRole.JUNGLE, red_pool),
        MockPlayer("R_Mid", PlayerRole.MID, red_pool),
        MockPlayer("R_Bot", PlayerRole.BOT, red_pool),
        MockPlayer("R_Sup", PlayerRole.SUPPORT, red_pool),
    ]

    return (
        MockTeam("blue-id", "Blue Team", blue_players),
        MockTeam("red-id", "Red Team", red_players),
    )

def test_draft_ai_from_partial_state(mock_teams):
    """Simula reconstrução do estado FE e uma decisão de ban RED no turno 1."""
    blue, red = mock_teams
    state = DraftState(
        match_id="interactive",
        blue_bans=["Azir"],
        red_bans=[],
        blue_picks=[],
        red_picks=[],
        current_turn=1,
    )
    champ, role = DraftAI().make_decision(
        draft_state=state,
        team_side=DraftTeam.RED,
        team_obj=red,
        opponent_team_obj=blue,
    )
    assert isinstance(champ, str) and len(champ) > 0
    assert role is None  # ban


def test_snake_draft_sequence():
    draft = SnakeDraft(match_id="test-match")
    state = draft.initialize()
    assert state.current_turn == 0
    assert not state.is_complete

    # Testa banimento no turno 1
    expected = draft.get_expected_action()
    assert expected["team"] == "BLUE"
    assert expected["action"] == "BAN"

    draft.process_action(DraftTeam.BLUE, DraftAction.BAN, "Yone")
    assert "yone" in state.all_banned
    assert state.current_turn == 1

def test_draft_ai_simulation(mock_teams):
    blue_team, red_team = mock_teams
    draft = SnakeDraft(match_id="test-match-ai")
    draft.initialize()
    draft_ai = DraftAI()

    # Executa o draft de 20 turnos completo com a IA decidindo para ambos os lados
    while not draft.get_current_state().is_complete:
        expected = draft.get_expected_action()
        current_side = DraftTeam(expected["team"])
        
        active_team = blue_team if current_side == DraftTeam.BLUE else red_team
        opponent_team = red_team if current_side == DraftTeam.BLUE else blue_team

        # IA toma decisão
        chosen_champ, role = draft_ai.make_decision(
            draft_state=draft.get_current_state(),
            team_side=current_side,
            team_obj=active_team,
            opponent_team_obj=opponent_team
        )

        # Registra ação no draft
        draft.process_action(
            team=current_side,
            action=DraftAction(expected["action"]),
            champion=chosen_champ,
            role_hint=role.value if role else None
        )

    state = draft.get_current_state()
    assert state.is_complete
    assert len(state.blue_bans) == 5
    assert len(state.red_bans) == 5
    assert len(state.blue_picks) == 5
    assert len(state.red_picks) == 5

    # Testa o cálculo de penalidade do draft
    blue_penalty, red_penalty = calculate_draft_penalties(
        blue_picks=state.blue_picks,
        red_picks=state.red_picks,
        blue_team=blue_team,
        red_team=red_team
    )
    
    # Penalidades devem ser valores decimais <= 0.40
    assert 0.0 <= blue_penalty <= 0.40
    assert 0.0 <= red_penalty <= 0.40
    # O Red deve ter menos penalidade por ter counter-picks fortes na pool (Viktor contra Azir, Jax contra Aatrox, Ezreal contra Jinx)
    print(f"Test Draft Penalties - Blue: {blue_penalty:.2f}, Red: {red_penalty:.2f}")
