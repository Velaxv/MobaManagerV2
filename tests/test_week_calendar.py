"""Testes da grade semanal sincronizada com round-robin."""

from src.shared.round_robin import get_round_pairs, match_day_round_index
from src.shared.week_calendar import build_week_calendar


CBLOL_TEAMS = [
    {"id": "1", "name": "Fluxo W7M", "abbreviation": "FX7"},
    {"id": "2", "name": "FURIA Esports", "abbreviation": "FUR"},
    {"id": "3", "name": "Leviatán", "abbreviation": "LEV"},
    {"id": "4", "name": "LOUD", "abbreviation": "LLL"},
    {"id": "5", "name": "LØS", "abbreviation": "LOS"},
    {"id": "6", "name": "paiN Gaming", "abbreviation": "PNG"},
    {"id": "7", "name": "RED Canids Kalunga", "abbreviation": "RED"},
    {"id": "8", "name": "Vivo Keyd Stars", "abbreviation": "VKS"},
]


def test_week_has_seven_days():
    days = build_week_calendar(0, 0, "REGULAR_SEASON", CBLOL_TEAMS, managed_team_id="6")
    assert len(days) == 7
    assert [d["dayOfWeek"] for d in days] == ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]


def test_match_days_are_wed_and_sat_in_regular():
    days = build_week_calendar(0, 0, "REGULAR_SEASON", CBLOL_TEAMS, managed_team_id="6")
    assert days[2]["type"] == "MATCH_DAY"
    assert days[5]["type"] == "MATCH_DAY"
    assert days[6]["type"] == "REST"


def test_manager_opponent_matches_round_robin():
    managed = "6"  # paiN
    week = 0
    days = build_week_calendar(0, week, "REGULAR_SEASON", CBLOL_TEAMS, managed_team_id=managed)

    ordered = sorted(CBLOL_TEAMS, key=lambda t: (t["name"], t["id"]))
    ordered_ids = [t["id"] for t in ordered]
    lookup = {t["id"]: t for t in CBLOL_TEAMS}

    for day_index in (2, 5):
        round_idx = match_day_round_index(week, day_index)
        pairs = get_round_pairs(ordered_ids, round_idx)
        manager_pair = next(
            ((h, a) for h, a in pairs if managed in (h, a)),
            None,
        )
        assert manager_pair is not None

        day = days[day_index]
        assert day["roundIndex"] == round_idx
        assert day["opponentAbbr"] is not None
        assert "vs " in (day["eventName"] or "")

        home, away = manager_pair
        if managed == home:
            assert day["isHome"] is True
            assert day["opponentId"] == away
            assert day["opponentAbbr"] == lookup[away]["abbreviation"]
            assert "(casa)" in day["eventName"]
        else:
            assert day["isHome"] is False
            assert day["opponentId"] == home
            assert day["opponentAbbr"] == lookup[home]["abbreviation"]
            assert "(fora)" in day["eventName"]


def test_wed_and_sat_use_different_rounds():
    days = build_week_calendar(0, 1, "REGULAR_SEASON", CBLOL_TEAMS, managed_team_id="1")
    assert days[2]["roundIndex"] == match_day_round_index(1, 2)
    assert days[5]["roundIndex"] == match_day_round_index(1, 5)
    assert days[2]["roundIndex"] != days[5]["roundIndex"]


def test_without_manager_shows_round_summary():
    days = build_week_calendar(0, 0, "REGULAR_SEASON", CBLOL_TEAMS, managed_team_id=None)
    assert days[2]["eventName"].startswith("Rodada ")
    assert "×" in days[2]["eventName"]
    assert days[2]["opponentAbbr"] is None
    assert len(days[2]["allMatches"]) == 4


def test_is_today_flag():
    days = build_week_calendar(3, 0, "REGULAR_SEASON", CBLOL_TEAMS, managed_team_id="1")
    assert days[3]["isToday"] is True
    assert sum(1 for d in days if d["isToday"]) == 1


def test_offseason_has_no_rr_match_labels():
    days = build_week_calendar(0, 0, "OFFSEASON", CBLOL_TEAMS, managed_team_id="1")
    match_days = [d for d in days if d["type"] == "MATCH_DAY"]
    assert match_days == []
