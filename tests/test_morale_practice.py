# -*- coding: utf-8 -*-
"""Moral, chemistry, scrims e VOD (Sprint S3)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.modules.career.morale_service import MoraleService, DEFAULT_STATE
from src.modules.career.practice_service import PracticeService
from src.shared.week_calendar import build_week_calendar


@pytest.mark.asyncio
async def test_morale_win_loss_streak():
    svc = MoraleService(MagicMock())
    svc.get_state = AsyncMock(return_value=dict(DEFAULT_STATE, team_id="t1"))
    saved = {}

    async def _save(tid, state):
        saved.update(state)

    svc.save_state = _save  # type: ignore

    st = await svc.on_match_result("t1", won=True, opponent_name="FUR")
    assert st["win_streak"] == 1
    assert st["team_morale"] > DEFAULT_STATE["team_morale"]

    st = await svc.on_match_result("t1", won=False, opponent_name="LLL")
    assert st["loss_streak"] == 1
    assert st["win_streak"] == 0


@pytest.mark.asyncio
async def test_rest_raises_morale():
    svc = MoraleService(MagicMock())
    base = dict(DEFAULT_STATE, team_id="t1", team_morale=40.0)
    svc.get_state = AsyncMock(return_value=base)
    svc.save_state = AsyncMock()
    st = await svc.on_rest_day("t1")
    assert st["team_morale"] > 40.0


def test_public_view_labels():
    svc = MoraleService(MagicMock())
    view = svc.public_view({**DEFAULT_STATE, "team_morale": 80, "chemistry": 75})
    assert view["morale_label"] == "Alto"
    assert view["chemistry_label"] == "Sincronizado"


def test_regular_week_has_scrim_and_media():
    teams = [{"id": str(i), "name": f"T{i}", "abbreviation": f"T{i}"} for i in range(1, 9)]
    days = build_week_calendar(0, 0, "REGULAR_SEASON", teams, managed_team_id="1")
    types = [d["type"] for d in days]
    assert "SCRIM" in types
    assert "MEDIA" in types
    assert types[2] == "MATCH_DAY"
    assert types[5] == "MATCH_DAY"


@pytest.mark.asyncio
async def test_scrim_produces_report():
    my = MagicMock()
    my.id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    my.name = "Mine"
    my.abbreviation = "MIN"
    my.get_average_ca = MagicMock(return_value=150.0)

    opp = MagicMock()
    opp.id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    opp.name = "Other"
    opp.abbreviation = "OTH"
    opp.get_average_ca = MagicMock(return_value=140.0)

    db = MagicMock()
    svc = PracticeService(db)
    svc.morale.get_state = AsyncMock(
        return_value=dict(DEFAULT_STATE, team_id=str(my.id))
    )
    svc.morale.apply_delta = AsyncMock(
        return_value=dict(DEFAULT_STATE, team_id=str(my.id))
    )
    svc.morale.get_public = AsyncMock(return_value={"team_morale": 60})

    with patch(
        "src.modules.career.practice_service.redis_client"
    ) as redis:
        redis.set_generic = AsyncMock()
        redis.get_generic = AsyncMock(return_value=None)
        report = await svc.run_scrim(my, [my, opp])

    assert report["type"] == "SCRIM"
    assert report["result"] in ("WIN", "LOSS")
    assert report["opponent_abbr"] == "OTH"
    assert "notes" in report
