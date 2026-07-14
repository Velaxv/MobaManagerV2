"""Testes do save/load de carreira (JSON + helpers)."""

import json
from pathlib import Path

import pytest

from src.modules.career import save_service
from src.modules.career.save_service import (
    SAVE_VERSION,
    SEED_TAG,
    _slot_path,
    list_save_files,
)


def test_slot_path_rejects_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "saves_dir", lambda: tmp_path)
    with pytest.raises(ValueError):
        _slot_path("../evil")
    with pytest.raises(ValueError):
        _slot_path("has space")
    p = _slot_path("slot1")
    assert p.name == "slot1.json"


def test_list_save_files_reads_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "saves_dir", lambda: tmp_path)
    payload = {
        "save_version": SAVE_VERSION,
        "seed_tag": SEED_TAG,
        "meta": {
            "manager_name": "Coach",
            "team_id": "abc",
            "team_name": "paiN Gaming",
            "team_abbr": "PNG",
            "saved_at": "2026-07-14T12:00:00Z",
            "phase": "REGULAR_SEASON",
            "week": 2,
            "day": 10,
        },
    }
    (tmp_path / "slot1.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    items = list_save_files()
    assert any(i["slot"] == "slot1" and i["manager_name"] == "Coach" for i in items)
    assert any(i.get("error") for i in items if i["slot"] == "broken")


def test_delete_save_static(tmp_path, monkeypatch):
    monkeypatch.setattr(save_service, "saves_dir", lambda: tmp_path)
    path = tmp_path / "slot1.json"
    path.write_text("{}", encoding="utf-8")
    assert save_service.CareerSaveService.delete_save_static("slot1") is True
    assert not path.exists()
    assert save_service.CareerSaveService.delete_save_static("slot1") is False
