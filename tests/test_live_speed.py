"""Testes de velocidade da partida ao vivo."""

import pytest
import uuid
from src.modules.simulation.match_engine_service import (
    MatchEngineService,
    LIVE_SPEED_PRESETS,
)
from src.core.redis_client import redis_client


class MockTeam:
    def __init__(self, name):
        self.id = uuid.uuid4()
        self.name = name
        self.staffs = []
        self.players = []

    def get_starters(self):
        return []


@pytest.mark.asyncio
async def test_start_with_speed_presets():
    await redis_client.connect()
    service = MatchEngineService()
    match_id = str(uuid.uuid4())

    state = await service.start_live_simulation(
        match_id=match_id,
        league_id=str(uuid.uuid4()),
        split_week=1,
        is_playoff=False,
        blue_team=MockTeam("Blue"),
        red_team=MockTeam("Red"),
        blue_draft=[{"champion": "Azir", "role": "MID"}],
        red_draft=[{"champion": "Viktor", "role": "MID"}],
        speed="4x",
    )
    assert state.tick_ms == LIVE_SPEED_PRESETS["4x"]
    assert state.speed_label == "4x"

    stored = await service.get_live_state(match_id)
    assert stored["tick_ms"] == 500
    assert stored["speed_label"] == "4x"


@pytest.mark.asyncio
async def test_set_live_speed_mid_match():
    await redis_client.connect()
    service = MatchEngineService()
    match_id = str(uuid.uuid4())

    await service.start_live_simulation(
        match_id=match_id,
        league_id=str(uuid.uuid4()),
        split_week=1,
        is_playoff=False,
        blue_team=MockTeam("Blue"),
        red_team=MockTeam("Red"),
        blue_draft=[{"champion": "Azir", "role": "MID"}],
        red_draft=[{"champion": "Viktor", "role": "MID"}],
        speed="1x",
    )

    res = await service.set_live_speed(match_id, "instant")
    assert res["success"] is True
    assert res["tick_ms"] == 0

    stored = await service.get_live_state(match_id)
    assert stored["tick_ms"] == 0
    assert stored["speed_label"] == "instant"


@pytest.mark.asyncio
async def test_invalid_speed():
    await redis_client.connect()
    service = MatchEngineService()
    match_id = str(uuid.uuid4())
    await service.start_live_simulation(
        match_id=match_id,
        league_id=str(uuid.uuid4()),
        split_week=1,
        is_playoff=False,
        blue_team=MockTeam("Blue"),
        red_team=MockTeam("Red"),
        blue_draft=[{"champion": "Azir", "role": "MID"}],
        red_draft=[{"champion": "Viktor", "role": "MID"}],
    )
    res = await service.set_live_speed(match_id, "99x")
    assert "error" in res
