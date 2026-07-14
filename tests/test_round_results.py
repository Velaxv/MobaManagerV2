"""Testes da montagem de resultados da rodada no calendário."""

from src.modules.calendar.calendar_service import CalendarService


def test_merge_round_results_combines_auto_and_pending():
    all_matches = [
        {
            "blue_team_id": "a",
            "blue_team_name": "Alpha",
            "blue_team_abbr": "ALP",
            "red_team_id": "b",
            "red_team_name": "Beta",
            "red_team_abbr": "BET",
        },
        {
            "blue_team_id": "c",
            "blue_team_name": "Gamma",
            "blue_team_abbr": "GAM",
            "red_team_id": "d",
            "red_team_name": "Delta",
            "red_team_abbr": "DEL",
        },
    ]
    auto = [
        {
            **all_matches[0],
            "match_id": "m1",
            "winner_team_id": "a",
            "winner_name": "Alpha",
            "duration": 32.5,
        }
    ]
    interactive = [all_matches[1]]

    rows = CalendarService._merge_round_results(all_matches, auto, interactive)
    assert len(rows) == 2
    done = next(r for r in rows if r["blue_team_id"] == "a")
    pending = next(r for r in rows if r["blue_team_id"] == "c")
    assert done["status"] == "complete"
    assert done["winner_name"] == "Alpha"
    assert done["match_id"] == "m1"
    assert pending["status"] == "pending"
    assert pending["winner_name"] is None
