"""Testes do sistema de scouting / atributos ocultos."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.modules.career.scouting_service import (
    ScoutingService,
    normalize_scout_focus,
    _band_for,
    THRESHOLDS,
)
from src.shared.enums import PlayerRole, CalendarDayType


def test_normalize_scout_focus():
    assert normalize_scout_focus("bma") == "BMA"
    assert normalize_scout_focus(None) == "ALL"
    assert normalize_scout_focus("x") == "ALL"


def test_band_unknown_below_threshold():
    band = _band_for(14.0, 10.0, "consistency")
    assert band["label"] == "unknown"
    assert band["known"] is False
    assert band["value"] is None


def test_band_wide_and_tight():
    wide = _band_for(14.0, THRESHOLDS["band_wide"], "consistency")
    assert wide["label"] == "wide"
    assert wide["min"] is not None
    assert wide["max"] is not None
    assert wide["min"] <= 14 <= wide["max"]

    tight = _band_for(14.0, THRESHOLDS["band_tight"], "consistency")
    assert tight["label"] == "tight"
    assert tight["max"] - tight["min"] <= wide["max"] - wide["min"]


def test_band_full_reveals_value():
    band = _band_for(16.5, 100.0, "consistency")
    assert band["known"] is True
    assert band["value"] == 16.5


def test_band_pa_full():
    band = _band_for(155, 100.0, "potential_ability")
    assert band["known"] is True
    assert band["value"] == 155


def _player(ca=120, pa=160, consistency=14.0, bma=11.0):
    return SimpleNamespace(
        id="pid-1",
        name="ScoutMe",
        role=PlayerRole.MID,
        current_ability=ca,
        potential_ability=pa,
        consistency=consistency,
        big_match_aptitude=bma,
        team_id=None,
        get_age=lambda: 21,
    )


def test_mask_hides_until_scouted():
    svc = ScoutingService(db=AsyncMock())
    player = _player()
    base = {
        "id": "pid-1",
        "name": "ScoutMe",
        "currentAbility": 120,
        "potentialAbility": 160,
        "consistency": 14.0,
        "bigMatchAptitude": 11.0,
    }
    masked = svc.mask_player_payload(base, player, None, is_own_roster=False)
    assert masked["consistency"] is None
    assert masked["consistencyKnown"] is False
    assert masked["bigMatchAptitude"] is None
    assert masked["potentialAbility"] is None
    assert masked["potentialAbilityKnown"] is False
    assert masked["scoutingProgress"] == 0.0


def test_mask_own_roster_has_band():
    svc = ScoutingService(db=AsyncMock())
    player = _player()
    base = {
        "id": "pid-1",
        "potentialAbility": 160,
        "consistency": 14.0,
        "bigMatchAptitude": 11.0,
    }
    masked = svc.mask_player_payload(base, player, None, is_own_roster=True)
    # Baseline 40% → faixa larga
    assert masked["consistencyKnown"] is False
    assert masked["consistencyMin"] is not None
    assert masked["consistencyMax"] is not None
    assert masked["scoutingProgress"] >= 40


def test_mask_full_knowledge():
    svc = ScoutingService(db=AsyncMock())
    player = _player(consistency=17.0, bma=9.0, pa=170)
    entry = {"progress": 100.0, "days_invested": 10, "attr_boost": {}}
    base = {
        "potentialAbility": 170,
        "consistency": 17.0,
        "bigMatchAptitude": 9.0,
    }
    masked = svc.mask_player_payload(base, player, entry, is_own_roster=False)
    assert masked["consistencyKnown"] is True
    assert masked["consistency"] == 17.0
    assert masked["bigMatchAptitude"] == 9.0
    assert masked["potentialAbility"] == 170
    assert masked["scoutingFullyScouted"] is True


@pytest.mark.asyncio
async def test_process_day_progresses_assignment():
    svc = ScoutingService(db=AsyncMock())
    player = _player()
    team = SimpleNamespace(id="team-1", name="T", players=[])

    assignment = {
        "player_id": "00000000-0000-0000-0000-000000000001",
        "focus": "ALL",
        "progress": 0,
        "days_invested": 0,
    }
    # Use real UUID string
    pid = "00000000-0000-0000-0000-000000000001"
    player.id = pid
    assignment["player_id"] = pid

    knowledge = {}

    saved: dict = {}

    async def get_k(_):
        return dict(knowledge)

    async def save_k(_, k):
        knowledge.clear()
        knowledge.update(k)
        saved.clear()
        saved.update(k)

    assignment_holder = {"a": dict(assignment)}

    async def get_a(_):
        return assignment_holder["a"]

    async def set_generic(key, val):
        if "assignment" in str(key):
            assignment_holder["a"] = dict(val)

    async def delete(_key):
        assignment_holder["a"] = None

    with patch.object(svc, "get_knowledge", side_effect=get_k):
        with patch.object(svc, "save_knowledge", side_effect=save_k):
            with patch.object(svc, "get_assignment", side_effect=get_a):
                with patch.object(
                    svc,
                    "staff_scouting_power",
                    new=AsyncMock(
                        return_value={"power_mult": 1.2, "staff_count": 1, "avg_meta_reading": 15}
                    ),
                ):
                    with patch(
                        "src.modules.career.scouting_service.redis_client.set_generic",
                        new=AsyncMock(side_effect=set_generic),
                    ):
                        with patch(
                            "src.modules.career.scouting_service.redis_client.delete",
                            new=AsyncMock(side_effect=delete),
                        ):
                            svc.db.get = AsyncMock(return_value=player)
                            result = await svc.process_day_for_team(
                                team, CalendarDayType.TRAINING.value
                            )

    assert result["events"]
    assert any(e["type"] == "SCOUT_PROGRESS" for e in result["events"])
    assert knowledge[pid]["progress"] > 0
    assert saved[pid]["progress"] > 0
