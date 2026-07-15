# -*- coding: utf-8 -*-
"""Sprint H: counter-pick, narração, sponsors com meta."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.draft.counter_matchup import (
    analyze_lane_counters,
    duel_multiplier_from_edge,
    lane_counter_edge,
)
from src.modules.simulation.narration import enrich_log, narrate
from src.modules.career.org_service import OrgService, GOAL_LABELS


def test_lane_counter_jax_vs_aatrox():
    # Jax countera Aatrox no COUNTER_MAP
    assert lane_counter_edge("Jax", "Aatrox") == 1.0
    assert lane_counter_edge("Aatrox", "Jax") == -1.0
    assert lane_counter_edge("Azir", "RandomChamp") == 0.0


def test_duel_mult_from_edge():
    assert duel_multiplier_from_edge(1.0) > 1.0
    assert duel_multiplier_from_edge(-1.0) < 1.0
    assert duel_multiplier_from_edge(0.0) == 1.0


def test_analyze_lane_counters_report():
    blue = [
        {"role_hint": "TOP", "champion": "Jax"},
        {"role_hint": "JUNGLE", "champion": "Lee Sin"},
        {"role_hint": "MID", "champion": "Azir"},
        {"role_hint": "BOT", "champion": "Jinx"},
        {"role_hint": "SUPPORT", "champion": "Thresh"},
    ]
    red = [
        {"role_hint": "TOP", "champion": "Aatrox"},
        {"role_hint": "JUNGLE", "champion": "Sejuani"},
        {"role_hint": "MID", "champion": "Sylas"},
        {"role_hint": "BOT", "champion": "Kai'Sa"},
        {"role_hint": "SUPPORT", "champion": "Nautilus"},
    ]
    report = analyze_lane_counters(blue, red)
    assert "lanes" in report
    assert len(report["lanes"]) == 5
    assert "blue_duel_mults" in report
    assert report["blue_duel_mults"]["TOP"] > 1.0  # Jax > Aatrox
    assert report["summary"]


def test_narrate_variants_are_nonempty():
    for et in (
        "SOLO_KILL",
        "TURRET_DESTROYED",
        "DRAGON_SECURED",
        "BARON_SECURED",
        "COUNTER_SPIKE",
        "VICTORY",
    ):
        line = narrate(et, minute=12, actor="Robo", victim="Guigo", side="BLUE", role="TOP")
        assert isinstance(line, str) and len(line) > 10


def test_enrich_log_fills_short_description():
    log = enrich_log(
        {
            "event_type": "DRAGON_SECURED",
            "timestamp": "18:00",
            "description": "ok",
            "team_name": "paiN",
        }
    )
    # description curta ("ok") → regenera
    assert "paiN" in log["description"] or "Dragão" in log["description"] or len(log["description"]) > 5


def test_org_goal_satisfied():
    assert OrgService._goal_satisfied("PLAYOFFS", 6) is True
    assert OrgService._goal_satisfied("PLAYOFFS", 7) is False
    assert OrgService._goal_satisfied("TOP4", 4) is True
    assert OrgService._goal_satisfied("TITLE", 1) is True
    assert OrgService._goal_satisfied("TITLE", 2) is False


@pytest.mark.asyncio
async def test_sponsor_payout_adjusts_on_rank():
    svc = OrgService(MagicMock())
    state = {
        "team_id": "t1",
        "board_confidence": 60,
        "brand": 50,
        "sponsors": [
            {
                "id": "s1",
                "name": "Bank Partner",
                "active": True,
                "goal": "TOP4",
                "base_payout": 20000,
                "monthly_payout": 20000,
                "min_wins": 2,
                "wins_credited": 5,
                "months_left": 3,
            }
        ],
        "last_events": [],
    }
    # rank 3 = TOP4 ok + wins ok → bônus
    await svc._apply_sponsor_goal_payouts(state, rank=3)
    assert state["sponsors"][0]["monthly_payout"] >= 20000
    assert state["sponsors"][0]["on_track"] is True

    # rank 8 = falha → corte
    await svc._apply_sponsor_goal_payouts(state, rank=8)
    assert state["sponsors"][0]["monthly_payout"] < 20000
    assert state["sponsors"][0]["on_track"] is False


def test_goal_labels_exist():
    for g in ("MID_TABLE", "PLAYOFFS", "TOP4", "TITLE"):
        assert g in GOAL_LABELS
