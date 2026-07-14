"""Testes de táticas pré-partida."""

from src.modules.simulation.tactics import (
    apply_style_to_phase_result,
    clamp_coach_comms,
    normalize_style,
    style_phase_multiplier,
)
from src.modules.simulation.strategies.base import PhaseResult, TeamMatchState


def test_normalize_style():
    assert normalize_style("early") == "EARLY"
    assert normalize_style("nope") == "BALANCED"
    assert normalize_style(None) == "BALANCED"


def test_clamp_coach_comms():
    assert clamp_coach_comms(-1) == 0
    assert clamp_coach_comms(9) == 6
    assert clamp_coach_comms(3) == 3
    assert clamp_coach_comms(None) == 2


def test_style_multipliers():
    assert style_phase_multiplier("EARLY", "EARLY_GAME") > 1.0
    assert style_phase_multiplier("EARLY", "LATE_GAME") < 1.0
    assert style_phase_multiplier("LATE", "LATE_GAME") > 1.0
    assert style_phase_multiplier("BALANCED", "MID_GAME") == 1.0


def test_apply_style_to_phase_result():
    pr = PhaseResult(
        phase_name="EARLY_GAME",
        blue_state=TeamMatchState(team_id="b", team_name="B", phase_score=100, gold_earned=1000),
        red_state=TeamMatchState(team_id="r", team_name="R", phase_score=100, gold_earned=1000),
        gold_difference=0,
        score_difference=0,
    )
    apply_style_to_phase_result(pr, "EARLY", "LATE")
    assert pr.blue_state.gold_earned > 1000
    assert pr.red_state.gold_earned < 1000
    assert pr.gold_difference > 0
