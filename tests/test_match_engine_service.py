import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.modules.simulation.match_engine_service import MatchEngineService, LiveMatchState
from src.shared.enums import PlayerRole
from src.core.redis_client import redis_client

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
    
    match_id = str(uuid.uuid4())
    key = f"live_match:{match_id}"
    
    # Salva um estado inicial no Redis
    state = LiveMatchState(
        match_id=match_id,
        league_id=str(uuid.uuid4()),
        split_week=1,
        is_playoff=False,
        blue_team_id=str(uuid.uuid4()),
        red_team_id=str(uuid.uuid4()),
        blue_team_name="paiN Gaming",
        red_team_name="LOUD",
        phase="EARLY_GAME"
    )
    await redis_client.set_generic(key, state.dict())
    
    # Mock do banco de dados e consulta do time
    mock_coach = MockStaff("Sarkis", "HEAD_COACH", 20.0) # alta comunicação
    mock_mid = MockPlayer("dyru", PlayerRole.MID, 20.0, 20.0) # alta coachability/foco
    mock_team = MockTeam("paiN Gaming", [mock_coach], [mock_mid])
    
    # Mock do get do Session
    db_mock = AsyncMock()
    db_mock.get.return_value = mock_team
    
    # Interceptamos a sessão com um mock
    import src.modules.simulation.match_engine_service as mes
    orig_session = mes.AsyncSessionLocal
    
    session_mock = MagicMock()
    session_mock.return_value.__aenter__.return_value = db_mock
    mes.AsyncSessionLocal = session_mock
    
    try:
        # Executa coach comm
        res = await service.apply_coach_comm(match_id, "BLUE")
        assert res["success"] is True
        assert "Sarkis" in res["log"]
        
        # Valida alteração de saldo/logs no Redis
        updated = await service.get_live_state(match_id)
        assert updated["blue_coach_comms_used"] == 1
        assert updated["blue_gold"] > 15000 # ganhou bônus
        assert len(updated["event_logs"]) == 1
    finally:
        mes.AsyncSessionLocal = orig_session
        await redis_client.disconnect()
