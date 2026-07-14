# -*- coding: utf-8 -*-
"""Janela de transferências e free agency (Sprint S1)."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.modules.career.market_window import MarketWindowService, WINDOW_BY_PHASE
from src.shared.enums import SplitPhase


@pytest.mark.asyncio
async def test_window_offseason_full():
    league = SimpleNamespace(
        id="lg",
        current_phase=SplitPhase.OFFSEASON,
        current_week=0,
    )
    svc = MarketWindowService(MagicMock())
    svc.get_league = AsyncMock(return_value=league)
    st = await svc.get_status()
    assert st["mode"] == "OPEN_FULL"
    assert st["can_buy_from_clubs"] is True
    assert st["can_sign_free_agents"] is True


@pytest.mark.asyncio
async def test_window_regular_fa_only():
    league = SimpleNamespace(
        id="lg",
        current_phase=SplitPhase.REGULAR_SEASON,
        current_week=3,
    )
    svc = MarketWindowService(MagicMock())
    svc.get_league = AsyncMock(return_value=league)
    st = await svc.get_status()
    assert st["mode"] == "OPEN_FA_ONLY"
    assert st["can_buy_from_clubs"] is False
    assert st["can_sign_free_agents"] is True


@pytest.mark.asyncio
async def test_window_playoffs_closed():
    league = SimpleNamespace(
        id="lg",
        current_phase=SplitPhase.PLAYOFFS,
        current_week=10,
    )
    svc = MarketWindowService(MagicMock())
    svc.get_league = AsyncMock(return_value=league)
    st = await svc.get_status()
    assert st["mode"] == "CLOSED"
    with pytest.raises(ValueError, match="fechada"):
        await svc.assert_can_transfer(is_free_agent=True)


@pytest.mark.asyncio
async def test_assert_club_transfer_blocked_in_regular():
    league = SimpleNamespace(
        id="lg",
        current_phase=SplitPhase.REGULAR_SEASON,
        current_week=2,
    )
    svc = MarketWindowService(MagicMock())
    svc.get_league = AsyncMock(return_value=league)
    with pytest.raises(ValueError, match="offseason"):
        await svc.assert_can_transfer(is_free_agent=False, seller_team_id="x")
    # FA ok
    st = await svc.assert_can_transfer(is_free_agent=True)
    assert st["mode"] == "OPEN_FA_ONLY"


def test_all_phases_mapped():
    for phase in (
        SplitPhase.OFFSEASON,
        SplitPhase.PRESEASON,
        SplitPhase.REGULAR_SEASON,
        SplitPhase.PLAYOFFS,
    ):
        assert phase.value in WINDOW_BY_PHASE
