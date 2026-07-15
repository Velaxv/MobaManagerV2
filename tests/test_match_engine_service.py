import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.modules.simulation.match_engine_service import (
    MatchEngineService,
    LiveMatchState,
    _map_meta,
    _normalize_event_log,
)
from src.shared.enums import PlayerRole
from src.core.redis_client import redis_client


def test_live_match_state_has_depth_fields():
    """Estado live expõe chemistry, estruturas e ratings."""
    state = LiveMatchState(
        match_id=str(uuid.uuid4()),
        league_id=str(uuid.uuid4()),
        split_week=1,
        is_playoff=False,
        blue_team_id=str(uuid.uuid4()),
        red_team_id=str(uuid.uuid4()),
        blue_team_name="A",
        red_team_name="B",
    )
    assert state.blue_chemistry == 55.0
    assert state.map_structures == {} or state.map_structures is not None
    assert state.player_ratings is None
    assert state.win_reason is None


def test_map_meta_on_event_logs():
    """Eventos da live carregam metadados de minimapa (Summoner's Rift)."""
    kill = _normalize_event_log({
        "event_type": "SOLO_KILL",
        "description": "[TOP] solo kill",
        "map": _map_meta("TOP_LANE", role="TOP", side="BLUE", intensity=0.9),
    })
    assert kill["map"]["location"] == "TOP_LANE"
    assert kill["map"]["role"] == "TOP"
    assert kill["map"]["side"] == "BLUE"
    assert kill["severity"] == "high"

    # Fallback automático quando map não é enviado
    dragon = _normalize_event_log({
        "event_type": "DRAGON_SECURED",
        "description": "Dragon",
    })
    assert dragon["map"]["location"] == "DRAGON"

    turret = _normalize_event_log({
        "event_type": "TURRET_DESTROYED",
        "description": "Torre Mid",
        "map": _map_meta("MID_LANE", side="BLUE", intensity=0.8),
    })
    assert turret["map"]["location"] == "MID_LANE"
    assert turret["map"]["side"] == "BLUE"
    assert turret["severity"] == "medium"

class MockStaff:
    def __init__(self, name, role, comm):
        self.name = name
        self.role = role
        self.communication = comm

class MockPlayer:
    def __init__(self, name, role, coachability, focus):
        self.id = uuid.uuid4()
        self.name = name
        self.role = role
        self.coachability = coachability
        self.focus = focus

class MockTeam:
    def __init__(self, name, staffs, players):
        self.id = uuid.uuid4()
        self.name = name
        self.staffs = staffs
        self.players = players
        
    def get_starters(self):
        return self.players

class MockChampion:
    def __init__(self, name, primary_role, class_type, damage_type):
        self.name = name
        self.primary_role = primary_role
        self.secondary_role = None
        self.class_type = class_type
        self.damage_type = damage_type
        self.early_game_power = 60
        self.late_game_scaling = 70
        self.mechanical_difficulty = 50
        self.utility = 50
        self.consistency = 12.0
        
    def get_champion_pool_tier(self, name):
        return "MAIN"

@pytest.mark.asyncio
async def test_live_match_initialization():
    await redis_client.connect()
    service = MatchEngineService()
    
    match_id = str(uuid.uuid4())
    league_id = str(uuid.uuid4())
    
    blue_team = MockTeam("paiN Gaming", [], [])
    red_team = MockTeam("LOUD", [], [])
    
    blue_draft = [{"champion": "Azir", "role": "MID"}]
    red_draft = [{"champion": "Viktor", "role": "MID"}]
    
    # Inicializa
    state = await service.start_live_simulation(
        match_id=match_id,
        league_id=league_id,
        split_week=1,
        is_playoff=False,
        blue_team=blue_team,
        red_team=red_team,
        blue_draft=blue_draft,
        red_draft=red_draft
    )
    
    assert state.match_id == match_id
    assert state.phase == "SETUP"
    assert state.is_complete is False
    
    # Valida no Redis
    stored = await service.get_live_state(match_id)
    assert stored is not None
    assert stored["match_id"] == match_id
    
    await redis_client.disconnect()

@pytest.mark.asyncio
async def test_live_coach_comm_success():
    await redis_client.connect()
    service = MatchEngineService()
    # Chance tática é clampada a 0.92 — força RNG determinístico (sempre sucesso, sem confusão)
    class _DetRng:
        def random(self):
            return 0.0

        def uniform(self, a, b):
            return float(a)

    service.rng = _DetRng()

    match_id = str(uuid.uuid4())
    key = f"live_match:{match_id}"
    blue_id = str(uuid.uuid4())

    # Salva um estado inicial no Redis
    state = LiveMatchState(
        match_id=match_id,
        league_id=str(uuid.uuid4()),
        split_week=1,
        is_playoff=False,
        blue_team_id=blue_id,
        red_team_id=str(uuid.uuid4()),
        blue_team_name="paiN Gaming",
        red_team_name="LOUD",
        phase="EARLY_GAME",
        blue_gold=15000,
    )
    await redis_client.set_generic(key, state.model_dump())

    # Mock do banco de dados e consulta do time
    mock_coach = MockStaff("Sarkis", "HEAD_COACH", 20.0)  # alta comunicação
    mock_mid = MockPlayer("dyru", PlayerRole.MID, 20.0, 20.0)  # alta coachability/foco
    mock_team = MockTeam("paiN Gaming", [mock_coach], [mock_mid])

    # Mock do get do Session
    db_mock = AsyncMock()
    db_mock.get.return_value = mock_team

    # Staff power: evita await em AsyncMock do DB (warning)
    async def _fake_power(_team_id):
        return {"coach_comm_success_bonus": 0.0}

    import src.modules.simulation.match_engine_service as mes
    import src.modules.career.staff_service as staff_mod

    orig_session = mes.AsyncSessionLocal
    orig_get_power = staff_mod.StaffService.get_team_power

    session_mock = MagicMock()
    session_mock.return_value.__aenter__.return_value = db_mock
    mes.AsyncSessionLocal = session_mock
    staff_mod.StaffService.get_team_power = _fake_power

    try:
        res = await service.apply_coach_comm(match_id, "BLUE")
        assert res["success"] is True
        assert "Sarkis" in res["log"]
        assert "Sucesso" in res["log"]

        updated = await service.get_live_state(match_id)
        assert updated["blue_coach_comms_used"] == 1
        assert updated["blue_gold"] == 15150  # +150 no sucesso tático
        assert len(updated["event_logs"]) == 1
    finally:
        mes.AsyncSessionLocal = orig_session
        staff_mod.StaffService.get_team_power = orig_get_power
        await redis_client.disconnect()
