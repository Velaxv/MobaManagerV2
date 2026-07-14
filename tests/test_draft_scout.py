# -*- coding: utf-8 -*-
"""Testes do Draft Scout Advisor (recomendações ban/pick)."""

import random
from types import SimpleNamespace
from typing import List, Optional

from src.modules.draft.draft_scout import DraftScoutAdvisor
from src.modules.draft.snake_draft import DraftState
from src.shared.enums import DraftTeam, PlayerRole


class FakePlayer:
    def __init__(
        self,
        name: str,
        role: PlayerRole,
        pool: Optional[List[dict]] = None,
        ca: int = 150,
    ):
        self.name = name
        self.role = role
        self.champion_pool = pool or []
        self.current_ability = ca
        self.is_starter = True

    def get_champion_pool_tier(self, champion_name: str) -> str:
        for entry in self.champion_pool:
            if entry.get("champion", "").lower() == champion_name.lower():
                return entry.get("tier", "SECONDARY")
        return "OFF_POOL"


class FakeTeam:
    def __init__(self, name: str, players: List[FakePlayer], staffs=None):
        self.name = name
        self.players = players
        self.staffs = staffs or []

    def get_starters(self):
        return list(self.players)[:5]


def _staff(meta: float = 15.0, name: str = "Analyst BR"):
    return SimpleNamespace(
        name=name,
        role="STRATEGIC_COACH",
        meta_reading=meta,
        communication=12.0,
    )


def _team_pair():
    blue = FakeTeam(
        "BLUE",
        [
            FakePlayer(
                "TopA",
                PlayerRole.TOP,
                [{"champion": "Aatrox", "tier": "MAIN"}, {"champion": "Jax", "tier": "SECONDARY"}],
            ),
            FakePlayer(
                "JgA",
                PlayerRole.JUNGLE,
                [{"champion": "Lee Sin", "tier": "MAIN"}, {"champion": "Sejuani", "tier": "SECONDARY"}],
            ),
            FakePlayer(
                "MidA",
                PlayerRole.MID,
                [{"champion": "Azir", "tier": "MAIN"}, {"champion": "Orianna", "tier": "SECONDARY"}],
            ),
            FakePlayer(
                "BotA",
                PlayerRole.BOT,
                [{"champion": "Jinx", "tier": "MAIN"}, {"champion": "Ezreal", "tier": "SECONDARY"}],
            ),
            FakePlayer(
                "SupA",
                PlayerRole.SUPPORT,
                [{"champion": "Thresh", "tier": "MAIN"}, {"champion": "Nautilus", "tier": "SECONDARY"}],
            ),
        ],
        staffs=[_staff(16.0, "Scout Kaze")],
    )
    red = FakeTeam(
        "RED",
        [
            FakePlayer(
                "TopB",
                PlayerRole.TOP,
                [{"champion": "Gnar", "tier": "MAIN"}, {"champion": "Ornn", "tier": "SECONDARY"}],
            ),
            FakePlayer(
                "JgB",
                PlayerRole.JUNGLE,
                [{"champion": "Graves", "tier": "MAIN"}],
            ),
            FakePlayer(
                "MidB",
                PlayerRole.MID,
                [{"champion": "Sylas", "tier": "MAIN"}, {"champion": "Azir", "tier": "SECONDARY"}],
            ),
            FakePlayer(
                "BotB",
                PlayerRole.BOT,
                [{"champion": "Kai'Sa", "tier": "MAIN"}],
            ),
            FakePlayer(
                "SupB",
                PlayerRole.SUPPORT,
                [{"champion": "Rakan", "tier": "MAIN"}],
            ),
        ],
    )
    return blue, red


def test_scout_ban_prioritizes_opponent_main():
    blue, red = _team_pair()
    state = DraftState(
        match_id="t",
        blue_bans=[],
        red_bans=[],
        blue_picks=[],
        red_picks=[],
        current_turn=0,  # BLUE BAN
        is_complete=False,
    )
    advisor = DraftScoutAdvisor(
        patch_bias={"azir": 0.12, "gnar": 0.08},
        patch_version="16.1",
        rng=random.Random(42),
    )
    result = advisor.advise(
        draft_state=state,
        team_side=DraftTeam.BLUE,
        my_team=blue,
        opponent_team=red,
        staffs=blue.staffs,
        limit=5,
    )
    assert result["action"] == "BAN"
    assert result["scout"]["name"] == "Scout Kaze"
    assert len(result["recommendations"]) >= 1
    champs = [r["champion"] for r in result["recommendations"]]
    # Mains do RED (Gnar, Graves, Sylas, Kai'Sa, Rakan) ou Azir secondary devem aparecer
    red_threats = {"Gnar", "Graves", "Sylas", "Kai'Sa", "Rakan", "Azir", "Ornn"}
    assert any(c in red_threats for c in champs)
    top = result["recommendations"][0]
    assert "reasons" in top and len(top["reasons"]) >= 1
    assert top["global_meta"]["games_played_world"] > 0
    assert "score" in top


def test_scout_pick_prefers_player_main_and_patch():
    blue, red = _team_pair()
    # Turno 6 = BLUE PICK (após 6 bans)
    state = DraftState(
        match_id="t",
        blue_bans=["Gnar", "Graves", "Sylas", "Kai'Sa", "Rakan"],
        red_bans=["Aatrox", "Lee Sin", "Jinx", "Thresh", "Sejuani"],
        blue_picks=[],
        red_picks=[],
        current_turn=6,
        is_complete=False,
    )
    advisor = DraftScoutAdvisor(
        patch_bias={"azir": 0.15, "orianna": -0.05},
        patch_version="16.2",
        rng=random.Random(7),
    )
    result = advisor.advise(
        draft_state=state,
        team_side=DraftTeam.BLUE,
        my_team=blue,
        opponent_team=red,
        staffs=blue.staffs,
        focus_role="MID",
        limit=5,
    )
    assert result["action"] == "PICK"
    assert len(result["recommendations"]) >= 1
    # Azir é MAIN do mid + buff → deve estar bem ranqueado
    names = [r["champion"] for r in result["recommendations"][:3]]
    assert "Azir" in names or any(
        r.get("pool_tier") == "MAIN" for r in result["recommendations"][:3]
    )
    azir = next((r for r in result["recommendations"] if r["champion"] == "Azir"), None)
    if azir:
        assert azir["pool_tier"] == "MAIN"
        assert azir["factors"]["mastery"] > 20


def test_scout_wrong_side_returns_empty_or_message():
    blue, red = _team_pair()
    state = DraftState(
        match_id="t",
        blue_bans=[],
        red_bans=[],
        blue_picks=[],
        red_picks=[],
        current_turn=0,  # BLUE turn
        is_complete=False,
    )
    advisor = DraftScoutAdvisor(rng=random.Random(1))
    result = advisor.advise(
        draft_state=state,
        team_side=DraftTeam.RED,  # errado
        my_team=red,
        opponent_team=blue,
        limit=3,
    )
    assert result.get("error") or result["recommendations"] == []


def test_global_presence_deterministic():
    a = DraftScoutAdvisor(patch_version="16.1", rng=random.Random(0))
    m1 = a._global_presence("Azir")
    m2 = a._global_presence("Azir")
    assert m1 == m2
    assert m1["tier"] in ("S", "A", "B", "C", "D")
