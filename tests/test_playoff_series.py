# -*- coding: utf-8 -*-
"""Séries multi-map BO3/BO5, fearless e momentum."""

import pytest

from src.modules.calendar.playoff_series import (
    ensure_series_multi_map,
    record_map_result,
    series_is_complete_by_score,
    side_for_next_map,
    wins_needed,
)
from src.modules.calendar.playoff_service import (
    apply_series_result,
    build_top6_bracket,
    series_to_match_payload,
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


def test_wins_needed():
    assert wins_needed(1) == 1
    assert wins_needed(3) == 2
    assert wins_needed(5) == 3


def test_bo3_needs_two_maps():
    b = build_top6_bracket(_seeds())
    s = next(x for x in b["series"] if x["id"] == "qf1")
    ensure_series_multi_map(s)
    assert s["best_of"] == 3

    r1 = record_map_result(
        s,
        winner_team_id="t3",
        blue_team_id="t3",
        red_team_id="t6",
        blue_draft=[{"champion": "Aatrox", "role": "TOP"}],
        red_draft=[{"champion": "Jax", "role": "TOP"}],
    )
    assert r1["series_complete"] is False
    assert r1["score"] == {"home": 1, "away": 0}
    assert "Aatrox" in s["fearless_used"]
    assert s["status"] == "in_progress"

    # Map 2: momentum t3 = blue
    blue, red = side_for_next_map(s)
    assert blue == "t3"
    r2 = record_map_result(
        s,
        winner_team_id="t3",
        blue_team_id=blue,
        red_team_id=red,
        blue_draft=[{"champion": "Ornn", "role": "TOP"}],
        red_draft=[{"champion": "Gnar", "role": "TOP"}],
    )
    assert r2["series_complete"] is True
    assert s["status"] == "awaiting_close"
    assert series_is_complete_by_score(s)

    apply_series_result(b, "qf1", "t3")
    assert s["status"] == "complete"
    sf2 = next(x for x in b["series"] if x["id"] == "sf2")
    assert sf2["away"]["team_id"] == "t3"


def test_fearless_accumulates():
    b = build_top6_bracket(_seeds())
    s = next(x for x in b["series"] if x["id"] == "qf2")
    record_map_result(
        s,
        winner_team_id="t4",
        blue_team_id="t4",
        red_team_id="t5",
        blue_draft=[{"champion": "Azir"}, {"champion": "Orianna"}],
        red_draft=[{"champion": "Sylas"}],
    )
    assert set(s["fearless_used"]) >= {"Azir", "Orianna", "Sylas"}
    payload = series_to_match_payload(s)
    assert "Azir" in payload["fearless_used"]
    assert payload["map_index"] == 2
    assert "1-0" in payload["series_label"] or payload["series_score_display"] == "1-0"


def test_final_is_bo5():
    b = build_top6_bracket(_seeds())
    final = next(x for x in b["series"] if x["id"] == "final")
    assert final["best_of"] == 5
    assert wins_needed(final["best_of"]) == 3
