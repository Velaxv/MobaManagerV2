"""Testes unitários leves do offseason (sem DB)."""

from datetime import date, timedelta

from src.models.contract import SEASON_DURATION_DAYS


def test_season_duration_constant():
    assert SEASON_DURATION_DAYS == 180


def test_renew_end_date_math():
    seasons = 2
    end = date.today() + timedelta(days=SEASON_DURATION_DAYS * seasons)
    remaining_days = (end - date.today()).days
    approx = max(1, round(remaining_days / SEASON_DURATION_DAYS))
    assert approx == seasons


def test_tick_contract_seasons_logic():
    """Espelha a regra: seasons_duration <= 1 expira; senão decrementa."""
    cases = [
        (1, True, 0),
        (2, False, 1),
        (4, False, 3),
    ]
    for remaining, should_expire, after in cases:
        if remaining <= 1:
            assert should_expire
        else:
            assert remaining - 1 == after
