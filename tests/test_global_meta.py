# -*- coding: utf-8 -*-
from src.shared.global_meta_data import get_champion_meta, META_PATCH_VERSION


def test_seed_meta_azir():
    m = get_champion_meta("Azir")
    assert m is not None
    assert m["win_rate"] > 45
    assert m["pick_rate"] > 1
    assert m["games_played"] > 100_000
    assert m["pro_presence"] >= 0.5


def test_seed_meta_kaisa_variants():
    a = get_champion_meta("Kai'Sa")
    b = get_champion_meta("kaisa")
    assert a is not None and b is not None
    assert a["win_rate"] == b["win_rate"]


def test_unknown_champion_returns_none():
    assert get_champion_meta("DefinitelyNotAChamp") is None


def test_meta_patch_version_set():
    assert META_PATCH_VERSION
