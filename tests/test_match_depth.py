# -*- coding: utf-8 -*-
"""Testes da profundidade de partida (chemistry, torres, ratings, win reason)."""

from types import SimpleNamespace

from src.modules.simulation import match_depth
from src.shared.enums import PlayerRole


def test_chemistry_duel_bonus_scales():
    low = match_depth.chemistry_duel_bonus(
        PlayerRole.MID, chemistry=20, bot_synergy=50, jg_mid_synergy=20, teamwork=8
    )
    high = match_depth.chemistry_duel_bonus(
        PlayerRole.MID, chemistry=90, bot_synergy=50, jg_mid_synergy=90, teamwork=16
    )
    assert high > low
    # Duo jg-mid puxa mid
    assert high > 0


def test_bot_synergy_affects_bot_not_top_as_much():
    bot = match_depth.chemistry_duel_bonus(
        PlayerRole.BOT, chemistry=50, bot_synergy=100, jg_mid_synergy=50, teamwork=10
    )
    top = match_depth.chemistry_duel_bonus(
        PlayerRole.TOP, chemistry=50, bot_synergy=100, jg_mid_synergy=50, teamwork=10
    )
    assert bot > top


def test_destroy_tower_progression():
    structs = match_depth.default_map_structures()
    assert structs["red"]["mid"] == 3
    structs, label = match_depth.destroy_tower(structs, attacker_side="BLUE", location="MID_LANE")
    assert structs["red"]["mid"] == 2
    assert label is not None
    assert "MID" in label
    # Destroy all mid towers then inhib
    for _ in range(5):
        structs, _ = match_depth.destroy_tower(structs, attacker_side="BLUE", location="MID_LANE")
    assert structs["red"]["mid"] == 0
    assert structs["red"]["inhibs"] < 3


def test_compute_player_ratings_mvp():
    def make_p(name, role, ca=140):
        return SimpleNamespace(
            id=name,
            name=name,
            role=role,
            current_ability=ca,
            burnout_meter=10,
            big_match_aptitude=14,
            consistency=12,
        )

    blue = [
        make_p("BTop", PlayerRole.TOP),
        make_p("BJg", PlayerRole.JUNGLE, 160),
        make_p("BMid", PlayerRole.MID),
        make_p("BBot", PlayerRole.BOT),
        make_p("BSup", PlayerRole.SUPPORT),
    ]
    red = [
        make_p("RTop", PlayerRole.TOP, 100),
        make_p("RJg", PlayerRole.JUNGLE, 100),
        make_p("RMid", PlayerRole.MID, 100),
        make_p("RBot", PlayerRole.BOT, 100),
        make_p("RSup", PlayerRole.SUPPORT, 100),
    ]
    contrib = match_depth.default_role_contrib()
    match_depth.bump_contrib(contrib, "BLUE", PlayerRole.JUNGLE, kills=3, obj=2, pressure=10)
    ratings = match_depth.compute_player_ratings(
        blue_starters=blue,
        red_starters=red,
        blue_draft=[{"champion": "LeeSin", "role": "JUNGLE"}],
        red_draft=[],
        contrib=contrib,
        winner_side="BLUE",
        blue_team_name="Blue",
        red_team_name="Red",
    )
    assert len(ratings) == 10
    assert all(0 <= r["rating"] <= 10 for r in ratings)
    mvps = [r for r in ratings if r.get("mvp")]
    assert len(mvps) >= 1
    assert mvps[0]["side"] == "BLUE"


def test_win_reason_snowball():
    wr = match_depth.win_reason_from_state(
        reason_code="SNOWBALL",
        winner_side="BLUE",
        winner_name="paiN",
        gold_diff=13000,
        blue_dragons=3,
        red_dragons=1,
        blue_barons=1,
        red_barons=0,
        blue_towers=7,
        red_towers=2,
        minute=28,
    )
    assert "paiN" in wr["summary"]
    assert wr["code"] == "SNOWBALL"
    assert any("Ouro" in f for f in wr["factors"])
