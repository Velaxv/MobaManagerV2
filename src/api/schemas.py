"""DTOs Pydantic compartilhados pela API."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class CreateMatchRequest(BaseModel):
    blue_team_id: str
    red_team_id: str
    league_id: str
    week: int
    is_playoff: bool = False
    blue_coach_comms: int = 0
    red_coach_comms: int = 0


class SignPlayerRequest(BaseModel):
    team_id: str
    player_id: str
    transfer_fee: float = 250000.0
    monthly_salary: float = 5000.0
    seasons: int = 2


class DraftAIDecisionRequest(BaseModel):
    blue_team_id: str
    red_team_id: str
    acting_side: str  # BLUE | RED
    current_turn: int = 0
    blue_bans: List[str] = []
    red_bans: List[str] = []
    blue_picks: List[Dict[str, str]] = []  # {champion, role}
    red_picks: List[Dict[str, str]] = []


class DraftScoutAdviceRequest(BaseModel):
    """Recomendações do scout da comissão no draft interativo."""

    blue_team_id: str
    red_team_id: str
    managed_team_id: str  # time do manager (quem recebe o conselho)
    acting_side: str  # BLUE | RED — lado do manager no draft
    current_turn: int = 0
    blue_bans: List[str] = []
    red_bans: List[str] = []
    blue_picks: List[Dict[str, str]] = []
    red_picks: List[Dict[str, str]] = []
    focus_role: Optional[str] = None  # role selecionada no FE
    limit: int = 5
    session_id: Optional[str] = None  # histórico de dicas na sessão de draft


class DraftScoutActionRequest(BaseModel):
    """Registra ban/pick do manager para avaliar se seguiu o scout."""

    session_id: str
    current_turn: int
    action: str  # BAN | PICK
    champion: str
    role: Optional[str] = None


class DraftScoutEvaluateRequest(BaseModel):
    """Avalia a sessão do scout vs draft final (e opcionalmente vencedor)."""

    session_id: str
    managed_side: Optional[str] = None
    blue_bans: List[str] = []
    red_bans: List[str] = []
    blue_picks: List[Dict[str, str]] = []
    red_picks: List[Dict[str, str]] = []
    winner_side: Optional[str] = None  # BLUE | RED


class RenewContractRequest(BaseModel):
    team_id: str
    player_id: str
    seasons: int = 1
    monthly_salary: Optional[float] = None


class ReleasePlayerRequest(BaseModel):
    team_id: str
    player_id: str


class CareerSaveRequest(BaseModel):
    slot: str = "slot1"
    manager_name: str
    team_id: str
    label: Optional[str] = None


class StartLiveMatchRequest(BaseModel):
    blue_team_id: str
    red_team_id: str
    is_playoff: bool = False
    split_week: int = 1
    blue_draft: List[Dict[str, str]]
    red_draft: List[Dict[str, str]]
    # Velocidade: 1x (2s/min) | 2x | 4x | instant
    speed: str = "2x"
    # Táticas do manager (aplicadas no lado correspondente)
    managed_team_id: Optional[str] = None
    game_style: str = "BALANCED"  # EARLY | MID | LATE | BALANCED
    coach_comms: int = 3
    starter_ids: Optional[List[str]] = None
    # Sessão do draft scout para avaliar acertos pós-partida
    scout_session_id: Optional[str] = None
    # Bans do draft interativo (para avaliação do scout)
    blue_bans: Optional[List[str]] = None
    red_bans: Optional[List[str]] = None


class CoachCommRequest(BaseModel):
    team_side: str  # "BLUE" ou "RED"


class LiveSpeedRequest(BaseModel):
    speed: str  # 1x | 2x | 4x | instant


class TrainingPlanRequest(BaseModel):
    focus: str = "BALANCED"  # BALANCED | MECHANICS | MENTAL | TEAMPLAY | ROLE
    intensity: str = "NORMAL"  # LIGHT | NORMAL | HARD


class ScoutAssignRequest(BaseModel):
    player_id: str
    focus: str = "ALL"  # ALL | CONSISTENCY | BMA | PA


class AcademyPlayerRequest(BaseModel):
    player_id: str


class LineupRequest(BaseModel):
    starter_ids: List[str] = []
