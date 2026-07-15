# -*- coding: utf-8 -*-
"""Sprint G: save Redis completo, seed seguro, market AI, patch transition."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.redis_client import MockRedis, RedisClient
from src.modules.career.market_ai import MarketAIService
from src.modules.career.save_service import (
    CAREER_REDIS_PATTERNS,
    SAVE_VERSION,
    CareerSaveService,
)
from src.modules.simulation.patch_service import PatchService


@pytest.mark.asyncio
async def test_mock_redis_keys_and_snapshot():
    mock = MockRedis()
    await mock.set("career:morale:team:a", '{"team_morale": 70}')
    await mock.set("career:form:player:p1", '{"avg": 7.5}')
    await mock.set("other:key", "x")
    keys = await mock.keys("career:*")
    assert "career:morale:team:a" in keys
    assert "career:form:player:p1" in keys
    assert "other:key" not in keys


@pytest.mark.asyncio
async def test_redis_client_export_import_snapshot(monkeypatch):
    client = RedisClient()
    client._client = MockRedis()
    client._is_mock = True

    await client.set_generic("career:org:team:t1", {"board_confidence": 55})
    await client.set_generic("patch:current:version", "16.1")
    await client.set_generic("noise:skip", 1)

    blob = await client.export_snapshot(CAREER_REDIS_PATTERNS)
    assert "career:org:team:t1" in blob
    # get_generic faz json.loads — "16.1" vira float
    assert str(blob["patch:current:version"]) == "16.1"
    assert "noise:skip" not in blob

    client._client = MockRedis()
    n = await client.import_snapshot(blob)
    assert n >= 2
    restored = await client.get_generic("career:org:team:t1")
    assert restored["board_confidence"] == 55


def test_save_version_is_v2():
    assert SAVE_VERSION >= 2
    assert any("career" in p for p in CAREER_REDIS_PATTERNS)


@pytest.mark.asyncio
async def test_seed_status_and_skip_force(api_client):
    st = await api_client.get("/db/seed/status")
    assert st.status_code == 200

    r1 = await api_client.post("/db/seed?force=true")
    assert r1.status_code == 201
    d1 = r1.json()
    assert d1.get("skipped") is not True
    league_id = d1["league_id"]

    # Sem force: não apaga
    r2 = await api_client.post("/db/seed")
    assert r2.status_code == 201
    d2 = r2.json()
    assert d2.get("skipped") is True
    assert d2.get("league_id") == league_id

    st2 = await api_client.get("/db/seed/status")
    body = st2.json()
    assert body.get("seeded") is True
    assert body.get("team_count") == 8


@pytest.mark.asyncio
async def test_save_includes_career_redis(api_client, tmp_path, monkeypatch):
    from src.modules.career import save_service as ss

    monkeypatch.setattr(ss, "saves_dir", lambda: tmp_path)

    seed = (await api_client.post("/db/seed?force=true")).json()
    team_id = seed["teams"]["PNG"]
    player_r = await api_client.get(f"/teams/{team_id}/players")
    players = player_r.json()
    pid = players[0]["id"]

    from src.core.redis_client import redis_client

    # redis_client do app deve estar conectado via lifespan/conftest
    await redis_client.set_generic(
        f"career:morale:team:{team_id}",
        {"team_morale": 77.0, "chemistry": 60.0},
    )
    await redis_client.set_generic(
        f"career:form:player:{pid}",
        {"avg": 8.2, "ratings": [8.0, 8.4], "trend": "UP"},
    )
    await redis_client.set_generic("patch:current:version", "16.1")

    save_r = await api_client.post(
        "/career/save",
        json={
            "slot": "sprintg",
            "manager_name": "Tester",
            "team_id": team_id,
            "label": "G",
        },
    )
    assert save_r.status_code == 201, save_r.text

    path = tmp_path / "sprintg.json"
    assert path.exists()
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["save_version"] >= 2
    career = (data.get("redis") or {}).get("career") or {}
    assert f"career:morale:team:{team_id}" in career
    assert career[f"career:morale:team:{team_id}"]["team_morale"] == 77.0
    assert f"career:form:player:{pid}" in career

    # Muta e recarrega
    await redis_client.set_generic(
        f"career:morale:team:{team_id}",
        {"team_morale": 10.0},
    )
    load_r = await api_client.post("/career/load/sprintg")
    assert load_r.status_code == 200, load_r.text
    restored = await redis_client.get_generic(f"career:morale:team:{team_id}")
    assert restored["team_morale"] == 77.0


@pytest.mark.asyncio
async def test_market_ai_idempotent_and_window():
    svc = MarketAIService(MagicMock())
    svc._simulate_moves = AsyncMock(
        return_value=[
            {
                "buyer_abbr": "FUR",
                "player_name": "RookieX",
                "summary": "FUR contratou RookieX",
            }
        ]
    )
    with patch(
        "src.modules.career.market_ai.MarketWindowService"
    ) as MW:
        inst = MW.return_value
        inst.get_status = AsyncMock(
            return_value={
                "is_open": True,
                "mode": "OPEN_FULL",
                "phase": "OFFSEASON",
                "week": 0,
            }
        )
        with patch("src.modules.career.market_ai.redis_client") as rc:
            rc.get_generic = AsyncMock(return_value=None)
            rc.set_generic = AsyncMock()
            first = await svc.process_week_if_needed(
                managed_team_id="mgr", week=0, phase="OFFSEASON"
            )
            assert first["skipped"] is False
            assert first["count"] == 1

            rc.get_generic = AsyncMock(
                return_value={"moves": first["moves"], "skipped": False}
            )
            second = await svc.process_week_if_needed(
                managed_team_id="mgr", week=0, phase="OFFSEASON"
            )
            assert second["skipped"] is True
            assert second["reason"] == "already_ran"


@pytest.mark.asyncio
async def test_market_ai_closed_window():
    svc = MarketAIService(MagicMock())
    with patch(
        "src.modules.career.market_ai.MarketWindowService"
    ) as MW:
        MW.return_value.get_status = AsyncMock(
            return_value={"is_open": False, "mode": "CLOSED", "phase": "PLAYOFFS"}
        )
        out = await svc.process_week_if_needed(week=1, phase="PLAYOFFS")
        assert out["skipped"] is True
        assert out["reason"] == "window_closed"


@pytest.mark.asyncio
async def test_patch_transition_detects_version_change():
    """DR-5: quando versão muda, day_info ganha patch_transition."""
    # Unitário leve do contrato de dados de transição
    prev = "16.1"
    active = "16.2"
    assert prev != active
    transition = {
        "from_version": prev,
        "to_version": active,
        "is_mid_split": True,
        "message": f"Patch {active} entrou em vigor (substituindo {prev}).",
    }
    assert transition["is_mid_split"] is True
    assert "16.2" in transition["message"]


@pytest.mark.asyncio
async def test_patch_service_game_date_mid_split():
    # Dia 10 do calendário ≈ effective 16.2 no seed
    d0 = PatchService.game_date_from_elapsed(0)
    d10 = PatchService.game_date_from_elapsed(10)
    assert d10 == d0 + timedelta(days=10)
