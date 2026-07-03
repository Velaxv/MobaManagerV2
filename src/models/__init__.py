"""
Pacote de modelos SQLAlchemy do LoL Manager.

Exporta todos os modelos e a Base para uso no Alembic e nos serviços.
"""

from src.models.base import Base
from src.models.contract import Contract
from src.models.league import League, LeagueTeam
from src.models.match import Match
from src.models.player import Player
from src.models.team import Team
from src.models.champion import Champion, ChampionRoleStats
from src.models.patch import Patch, ChampionPatchMeta
from src.models.staff import Staff

__all__ = [
    "Base",
    "Player",
    "Team",
    "Contract",
    "League",
    "LeagueTeam",
    "Match",
    "Champion",
    "ChampionRoleStats",
    "Patch",
    "ChampionPatchMeta",
    "Staff",
]
