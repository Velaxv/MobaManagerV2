"""Testes do bracket de playoffs top-6."""

import pytest

from src.modules.calendar.playoff_service import (
    ROUND_FINAL,
    ROUND_QUARTER,
    ROUND_SEMI,
    apply_series_result,
    build_top6_bracket,
    series_for_round,
    series_ready,
    week_to_playoff_round,
)


def _seeds():
    return [
        {
            "seed": i,
            "team_id": f"t{i}",
            "team_name": f"Team {i}",
            "team_abbr": f"T{i}",
        }
        for i in range(1, 7)
    ]


def test_build_top6_structure():
    b = build_top6_bracket(_seeds())
    assert b["status"] == "active"
    assert len(b["series"]) == 5
    assert len(b["seeds"]) == 6
    qf = [s for s in b["series"] if s["round"] == ROUND_QUARTER]
    assert len(qf) == 2
    assert qf[0]["home"]["seed"] == 3 and qf[0]["away"]["seed"] == 6
    assert qf[1]["home"]["seed"] == 4 and qf[1]["away"]["seed"] == 5
    sf1 = next(s for s in b["series"] if s["id"] == "sf1")
    assert sf1["home"]["seed"] == 1
    assert sf1["away"]["team_id"] is None
    assert sf1["status"] == "pending"


def test_needs_six_seeds():
    with pytest.raises(ValueError):
        build_top6_bracket(_seeds()[:4])


def test_week_to_round():
    assert week_to_playoff_round(0) == ROUND_QUARTER
    assert week_to_playoff_round(1) == ROUND_SEMI
    assert week_to_playoff_round(2) == ROUND_FINAL
    assert week_to_playoff_round(5) == ROUND_FINAL


def test_apply_qf_feeds_semi():
    b = build_top6_bracket(_seeds())
    apply_series_result(b, "qf1", "t3")  # 3 beats 6
    sf2 = next(s for s in b["series"] if s["id"] == "sf2")
    assert sf2["away"]["team_id"] == "t3"
    assert sf2["status"] == "ready"  # seed 2 already home
    assert any(e["team_id"] == "t6" for e in b["eliminated"])


def test_full_bracket_to_champion():
    b = build_top6_bracket(_seeds())
    # QF: 3 and 4 advance
    apply_series_result(b, "qf1", "t3")
    apply_series_result(b, "qf2", "t4")
    assert b["current_round"] == ROUND_SEMI

    # SF: 1 and 2 advance
    apply_series_result(b, "sf1", "t1")
    apply_series_result(b, "sf2", "t2")
    assert b["current_round"] == ROUND_FINAL
    final = next(s for s in b["series"] if s["id"] == "final")
    assert series_ready(final)
    assert final["home"]["team_id"] == "t1"
    assert final["away"]["team_id"] == "t2"

    apply_series_result(b, "final", "t1")
    assert b["status"] == "complete"
    assert b["champion_team_id"] == "t1"
    assert b["champion_name"] == "Team 1"


def test_series_for_round_only_ready():
    b = build_top6_bracket(_seeds())
    ready = series_for_round(b, ROUND_QUARTER)
    assert len(ready) == 2
    assert series_for_round(b, ROUND_SEMI) == []
    apply_series_result(b, "qf1", "t3")
    apply_series_result(b, "qf2", "t5")
    ready_sf = series_for_round(b, ROUND_SEMI)
    assert len(ready_sf) == 2
