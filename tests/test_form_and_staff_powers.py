# -*- coding: utf-8 -*-
"""Sprint F: forma, staff powers, board semanal."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.modules.career.form_service import FormService
from src.modules.career.staff_service import StaffService
from src.modules.career.org_service import OrgService


@pytest.mark.asyncio
async def test_form_record_and_avg():
    store = {}

    async def get_generic(key):
        return store.get(key)

    async def set_generic(key, val):
        store[key] = val

    with patch("src.modules.career.form_service.redis_client") as rc:
        rc.get_generic = AsyncMock(side_effect=get_generic)
        rc.set_generic = AsyncMock(side_effect=set_generic)
        fs = FormService(db=None)  # type: ignore
        pid = str(uuid.uuid4())
        await fs.record_rating(pid, rating=7.5, note="ok", match_id="m1", played=True)
        await fs.record_rating(pid, rating=8.0, note="great", match_id="m2", played=True)
        form = await fs.get_form(pid)
        assert form["games"] == 2
        assert form["avg"] == 7.75
        assert form["trend"] in ("UP", "FLAT", "DOWN")
        assert form["discontent"] == 0.0


@pytest.mark.asyncio
async def test_bench_discontent_increases():
    store = {}

    async def get_generic(key):
        return store.get(key)

    async def set_generic(key, val):
        store[key] = val

    with patch("src.modules.career.form_service.redis_client") as rc:
        rc.get_generic = AsyncMock(side_effect=get_generic)
        rc.set_generic = AsyncMock(side_effect=set_generic)
        fs = FormService(db=None)  # type: ignore
        bench = str(uuid.uuid4())
        await fs.record_rating(bench, rating=0, played=False)
        form = await fs.get_form(bench)
        assert form["discontent"] >= 8.0
        assert form["games"] == 0


def test_staff_power_head_coach_comms():
    svc = StaffService(db=None)  # type: ignore
    staffs = [
        {
            "role": "HEAD_COACH",
            "meta_reading": 16,
            "communication": 18,
            "monthly_cost": 1000,
        },
        {
            "role": "STRATEGIC_COACH",
            "meta_reading": 17,
            "communication": 14,
            "monthly_cost": 900,
        },
        {
            "role": "PERFORMANCE_COACH",
            "meta_reading": 15,
            "communication": 12,
            "monthly_cost": 800,
        },
    ]
    power = svc._power_from_list(staffs)
    assert power["has_head_coach"] is True
    assert power["has_strategic_coach"] is True
    assert power["has_performance_coach"] is True
    assert power["coach_comms_max"] >= 3
    assert power["scout_mult"] >= 1.0
    assert power["burnout_recovery_bonus"] > 0
    assert len(power["powers"]) >= 2


def test_staff_power_empty_defaults():
    power = StaffService(db=None)._power_from_list([])  # type: ignore
    assert power["coach_comms_max"] == 2
    assert power["has_head_coach"] is False


def test_goal_satisfied():
    assert OrgService._goal_satisfied("PLAYOFFS", 6) is True
    assert OrgService._goal_satisfied("PLAYOFFS", 7) is False
    assert OrgService._goal_satisfied("TOP4", 4) is True
    assert OrgService._goal_satisfied("TITLE", 1) is True
    assert OrgService._goal_satisfied("TITLE", 2) is False


@pytest.mark.asyncio
async def test_weekly_board_review_idempotent():
    store = {}
    tid = str(uuid.uuid4())

    async def get_generic(key):
        return store.get(key)

    async def set_generic(key, val):
        store[key] = dict(val)

    db = AsyncMock()
    org = OrgService(db)
    with patch("src.modules.career.org_service.redis_client") as rc:
        rc.get_generic = AsyncMock(side_effect=get_generic)
        rc.set_generic = AsyncMock(side_effect=set_generic)
        with patch.object(org, "_team_rank", AsyncMock(return_value=3)):
            with patch.object(org, "get_public", AsyncMock(return_value={"board_confidence": 64})):
                with patch.object(org, "_check_firing", AsyncMock()):
                    r1 = await org.weekly_board_review(tid, week=2)
                    r2 = await org.weekly_board_review(tid, week=2)
                    assert r1.get("skipped") is False
                    assert r2.get("skipped") is True
                    assert r2.get("reason") == "already_reviewed"
