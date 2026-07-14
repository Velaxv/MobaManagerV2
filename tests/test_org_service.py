# -*- coding: utf-8 -*-
"""Org S4: board, sponsors, facility."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.modules.career.org_service import (
    OrgService,
    FACILITY_LEVELS,
    BOARD_GOALS,
    _default_org,
)


def test_facility_levels():
    assert 1 in FACILITY_LEVELS and 3 in FACILITY_LEVELS
    assert FACILITY_LEVELS[3]["monthly_cost"] > FACILITY_LEVELS[1]["monthly_cost"]
    assert FACILITY_LEVELS[2]["upgrade_cost"] > 0


def test_board_goals_defined():
    assert "PLAYOFFS" in BOARD_GOALS
    assert "TITLE" in BOARD_GOALS


def test_default_org_shape():
    d = _default_org("abc")
    assert d["facility_level"] == 1
    assert d["board_confidence"] > 0
    assert d["fired"] is False


@pytest.mark.asyncio
async def test_set_board_goal_ambition():
    svc = OrgService(MagicMock())
    state = _default_org("t1")
    state["board_goal"] = "MID_TABLE"
    state["board_confidence"] = 50.0
    svc.get_state = AsyncMock(return_value=state)
    svc.save_state = AsyncMock()
    svc.get_public = AsyncMock(
        return_value={"board_goal": "TITLE", "board_confidence": 54}
    )
    await svc.set_board_goal("t1", "TITLE")
    assert state["board_goal"] == "TITLE"
    assert state["board_confidence"] > 50


@pytest.mark.asyncio
async def test_match_win_raises_confidence():
    svc = OrgService(MagicMock())
    state = _default_org("t1")
    state["board_confidence"] = 50.0
    svc.get_state = AsyncMock(return_value=state)
    svc.save_state = AsyncMock()
    await svc.on_match_result("t1", won=True, is_playoff=False)
    assert state["board_confidence"] > 50


@pytest.mark.asyncio
async def test_playoff_loss_can_fire():
    svc = OrgService(MagicMock())
    state = _default_org("t1")
    state["board_confidence"] = 12.0
    state["fired"] = False
    svc.get_state = AsyncMock(return_value=state)
    svc.save_state = AsyncMock()
    await svc.on_match_result("t1", won=False, is_playoff=True)
    assert state["fired"] is True


def test_facility_bonuses():
    svc = OrgService(MagicMock())
    b1 = svc.facility_bonuses({"facility_level": 1})
    b3 = svc.facility_bonuses({"facility_level": 3})
    assert b3["scrim_chem_bonus"] > b1["scrim_chem_bonus"]
    assert b3["rest_morale_bonus"] > b1["rest_morale_bonus"]
