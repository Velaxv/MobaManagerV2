"""Testes de classificação e status de patch."""

from src.modules.simulation.patch_service import _classify_change, PatchService
from datetime import date, timedelta


def test_classify_buff():
    kind, score, tags = _classify_change(1.10, 1.0, 1.0)
    assert kind == "BUFF"
    assert score > 0
    assert "BUFF_DMG" in tags


def test_classify_nerf():
    kind, score, tags = _classify_change(1.0, 1.0, 0.90)
    assert kind == "NERF"
    assert score < 0
    assert "NERF_SRV" in tags


def test_classify_mixed_net_buff():
    kind, score, _ = _classify_change(1.12, 0.98, 1.0)
    assert kind == "BUFF"
    assert score > 0


def test_game_date_from_elapsed():
    d0 = PatchService.game_date_from_elapsed(0)
    d5 = PatchService.game_date_from_elapsed(5)
    assert d5 == d0 + timedelta(days=5)
    assert isinstance(d0, date)


def test_weighted_choice_prefers_buff():
    from src.modules.draft.draft_ai import DraftAI

    ai = DraftAI(patch_bias={"azir": 0.2, "ryze": -0.1})
    picks = [ai._weighted_choice(["Ryze", "Azir"]) for _ in range(80)]
    # Azir buffado deve aparecer mais que Ryze
    assert picks.count("Azir") > picks.count("Ryze")
