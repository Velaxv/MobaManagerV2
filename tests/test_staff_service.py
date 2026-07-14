# -*- coding: utf-8 -*-
from src.modules.career.staff_service import (
    estimate_monthly_cost,
    estimate_signing_fee,
    ROLE_CAPS,
    StaffService,
)


def test_staff_costs_scale_with_attrs():
    low = estimate_monthly_cost(8, 8, "ASSISTANT_COACH")
    high = estimate_monthly_cost(18, 18, "HEAD_COACH")
    assert high > low
    assert estimate_signing_fee(15, 15, "STRATEGIC_COACH") > 0


def test_role_caps_defined():
    assert ROLE_CAPS["HEAD_COACH"] == 1
    assert ROLE_CAPS["ASSISTANT_COACH"] >= 1


def test_power_empty_staff():
    p = StaffService(None)._power_from_list([])  # type: ignore
    assert p["scout_mult"] < 1.0


def test_power_with_strategic():
    staffs = [
        {
            "role": "STRATEGIC_COACH",
            "meta_reading": 18,
            "communication": 14,
            "monthly_cost": 2000,
        },
        {
            "role": "PERFORMANCE_COACH",
            "meta_reading": 14,
            "communication": 12,
            "monthly_cost": 1500,
        },
    ]
    p = StaffService(None)._power_from_list(staffs)  # type: ignore
    assert p["has_strategic_coach"] is True
    assert p["has_performance_coach"] is True
    assert p["scout_mult"] >= 1.0
    assert p["burnout_recovery_bonus"] > 0
