"""Testes de valuation e negociação de transferências."""

from types import SimpleNamespace

from src.modules.career.transfer_service import compute_valuation, evaluate_offer
from src.shared.enums import ContractStatus, PlayerRole


def _player(ca=150, pa=170, age_years=22, team_id="t1"):
    from datetime import date

    dob = date(date.today().year - age_years, 1, 1)
    return SimpleNamespace(
        current_ability=ca,
        potential_ability=pa,
        team_id=team_id,
        date_of_birth=dob,
        get_age=lambda: age_years,
        role=PlayerRole.MID,
        is_rookie=False,
        name="Test",
        contracts=[],
    )


def _contract(salary=8000, seasons=2):
    return SimpleNamespace(
        monthly_salary=salary,
        seasons_duration=seasons,
        remaining_seasons=seasons,
        status=ContractStatus.ACTIVE,
    )


def test_valuation_higher_for_star():
    low = compute_valuation(_player(ca=120, pa=130), _contract())
    high = compute_valuation(_player(ca=170, pa=185), _contract())
    assert high["asking_fee"] > low["asking_fee"]
    assert high["desired_salary"] >= low["desired_salary"]


def test_free_agent_cheaper_fee():
    bound = compute_valuation(_player(team_id="x"), _contract())
    fa = compute_valuation(_player(team_id=None), None)
    assert fa["is_free_agent"] is True
    assert fa["asking_fee"] < bound["asking_fee"]


def test_evaluate_accept_good_offer():
    val = compute_valuation(_player(), _contract())
    res = evaluate_offer(
        val,
        transfer_fee=val["asking_fee"],
        monthly_salary=val["desired_salary"],
        seasons=val["preferred_seasons"],
    )
    assert res["status"] == "accepted"


def test_evaluate_reject_lowball():
    val = compute_valuation(_player(), _contract())
    res = evaluate_offer(
        val,
        transfer_fee=val["min_fee"] * 0.3,
        monthly_salary=val["min_salary"] * 0.3,
        seasons=1,
    )
    assert res["status"] == "rejected"


def test_evaluate_counter_mid_offer():
    val = compute_valuation(_player(), _contract())
    mid_fee = (val["min_fee"] + val["asking_fee"]) / 2
    mid_sal = (val["min_salary"] + val["desired_salary"]) / 2
    res = evaluate_offer(val, transfer_fee=mid_fee, monthly_salary=mid_sal, seasons=1)
    assert res["status"] in ("counter", "accepted")
    if res["status"] == "counter":
        assert res["counter"]["transfer_fee"] >= mid_fee
