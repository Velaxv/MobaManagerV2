"""Testes do sistema de treino / desenvolvimento CA→PA."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.modules.career.training_service import (
    TrainingService,
    normalize_focus,
    normalize_intensity,
    FOCUS_ATTRS,
)
from src.shared.enums import CalendarDayType, PlayerRole


def test_normalize_focus_and_intensity():
    assert normalize_focus("mechanics") == "MECHANICS"
    assert normalize_focus("nope") == "BALANCED"
    assert normalize_focus(None) == "BALANCED"
    assert normalize_intensity("hard") == "HARD"
    assert normalize_intensity("x") == "NORMAL"


def test_age_factor_curve():
    assert TrainingService._age_factor(17) > TrainingService._age_factor(25)
    assert TrainingService._age_factor(25) > TrainingService._age_factor(31)
    assert TrainingService._age_factor(32) == 0.3


def _make_player(
    *,
    ca=120,
    pa=160,
    age_years=20,
    coachability=16.0,
    burnout=10.0,
    is_rookie=True,
    role=PlayerRole.MID,
    name="TestMid",
):
    dob = date(date.today().year - age_years, 6, 15)
    return SimpleNamespace(
        id="p1",
        name=name,
        role=role,
        current_ability=ca,
        potential_ability=pa,
        date_of_birth=dob,
        coachability=coachability,
        burnout_meter=burnout,
        visual_fatigue=0.0,
        mental_fatigue=0.0,
        is_rookie=is_rookie,
        mechanics=12.0,
        focus=12.0,
        resilience=12.0,
        teamwork=12.0,
        get_age=lambda self=None, y=age_years: y,
    )


def test_develop_player_can_gain_ca(monkeypatch):
    svc = TrainingService(db=AsyncMock())
    player = _make_player(ca=100, pa=150, age_years=19, coachability=18, burnout=5)

    # Força ganho de CA
    monkeypatch.setattr("src.modules.career.training_service.random.random", lambda: 0.0)

    result = svc._develop_player(
        player,
        day_mult=1.0,
        focus="BALANCED",
        intensity="NORMAL",
        extra_burnout=0.0,
        day_type="TRAINING",
    )
    assert result is not None
    assert result["ca_delta"] == 1
    assert player.current_ability == 101
    assert result["ca_after"] == 101


def test_develop_player_never_exceeds_pa(monkeypatch):
    svc = TrainingService(db=AsyncMock())
    player = _make_player(ca=150, pa=150, age_years=19, coachability=20, burnout=0)

    monkeypatch.setattr("src.modules.career.training_service.random.random", lambda: 0.0)

    result = svc._develop_player(
        player,
        day_mult=2.0,
        focus="MECHANICS",
        intensity="HARD",
        extra_burnout=0.0,
        day_type="TRAINING",
    )
    # Sem room de CA, mas attrs podem subir
    assert player.current_ability == 150
    if result:
        assert result["ca_delta"] == 0


def test_hard_intensity_adds_burnout(monkeypatch):
    svc = TrainingService(db=AsyncMock())
    player = _make_player(ca=100, pa=180, burnout=20.0)

    # Sempre "ganha" algo (attr ou ca)
    monkeypatch.setattr("src.modules.career.training_service.random.random", lambda: 0.0)

    before = player.burnout_meter
    svc._develop_player(
        player,
        day_mult=1.0,
        focus="MECHANICS",
        intensity="HARD",
        extra_burnout=2.5,
        day_type="TRAINING",
    )
    assert player.burnout_meter >= before + 2.5 - 0.01


def test_high_burnout_blocks_most_gains(monkeypatch):
    svc = TrainingService(db=AsyncMock())
    player = _make_player(ca=100, pa=180, burnout=90.0, coachability=10)

    # random 0.5 — com burn_factor baixo a chance de CA fica pequena
    calls = {"n": 0}

    def rnd():
        calls["n"] += 1
        return 0.5

    monkeypatch.setattr("src.modules.career.training_service.random.random", rnd)

    ca_before = player.current_ability
    svc._develop_player(
        player,
        day_mult=1.0,
        focus="BALANCED",
        intensity="NORMAL",
        extra_burnout=0.0,
        day_type="TRAINING",
    )
    # Com chance reduzida e random 0.5, CA tipicamente não sobe
    assert player.current_ability == ca_before


def test_focus_attrs_mapping():
    assert "mechanics" in FOCUS_ATTRS["MECHANICS"]
    assert "teamwork" in FOCUS_ATTRS["TEAMPLAY"]
    assert "coachability" in FOCUS_ATTRS["MENTAL"]


@pytest.mark.asyncio
async def test_process_team_day_skips_rest():
    svc = TrainingService(db=AsyncMock())
    team = SimpleNamespace(id="t1", name="Test", players=[], get_starters=lambda: [])

    with patch.object(svc, "get_plan", new=AsyncMock(return_value={"focus": "BALANCED", "intensity": "NORMAL"})):
        with patch("src.modules.career.training_service.redis_client.set_generic", new=AsyncMock()):
            session = await svc.process_team_day(team, CalendarDayType.REST.value)
    assert session["skipped"] is True
    assert session["ca_gains"] == 0


@pytest.mark.asyncio
async def test_process_league_day_only_training_scrim():
    svc = TrainingService(db=AsyncMock())
    team = SimpleNamespace(id="t1", name="Test", players=[])

    sessions = await svc.process_league_day([team], CalendarDayType.MATCH_DAY.value)
    assert len(sessions) == 1
    assert sessions[0]["skipped"] is True
