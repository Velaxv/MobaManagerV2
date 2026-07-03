import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Float, ForeignKey, CheckConstraint, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.patch import ChampionPatchMeta

class Champion(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Campeão de League of Legends enriquecido com atributos táticos e enums.
    """
    __tablename__ = "champions"
    __table_args__ = (
        CheckConstraint("early_game_power BETWEEN 1 AND 100", name="ck_champ_early_game_power"),
        CheckConstraint("late_game_scaling BETWEEN 1 AND 100", name="ck_champ_late_game_scaling"),
        CheckConstraint("mechanical_difficulty BETWEEN 1 AND 100", name="ck_champ_mech_difficulty"),
        CheckConstraint("utility BETWEEN 1 AND 100", name="ck_champ_utility_100"),
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_disabled_for_rework: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Tipagens e enums táticos
    primary_role: Mapped[str] = mapped_column(String(20), nullable=False) # TOP, JUNGLE, MID, ADC, SUPPORT
    secondary_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    class_type: Mapped[str] = mapped_column(String(30), nullable=False) # BRUISER, ASSASSIN, etc.
    damage_type: Mapped[str] = mapped_column(String(15), nullable=False) # AD, AP, etc.

    # Atributos táticos base (Notas de 1 a 100)
    early_game_power: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    late_game_scaling: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    mechanical_difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    utility: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # Relacionamentos de synergies e counters (IDs ou nomes)
    synergies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    counters: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # Relacionamentos antigos mantidos
    role_stats: Mapped[List["ChampionRoleStats"]] = relationship(
        "ChampionRoleStats", back_populates="champion", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def attributes(self) -> dict:
        """Retorna os atributos empacotados como dicionário estruturado."""
        return {
            "earlyGamePower": self.early_game_power,
            "lateGameScaling": self.late_game_scaling,
            "mechanicalDifficulty": self.mechanical_difficulty,
            "utility": self.utility
        }

    def __repr__(self) -> str:
        return f"<Champion(name={self.name!r}, disabled={self.is_disabled_for_rework})>"


class ChampionRoleStats(Base, UUIDMixin, TimestampMixin):
    """
    Especificação de atributos base do Campeão em uma determinada Role (Flex Picks).
    """
    __tablename__ = "champion_role_stats"
    __table_args__ = (
        CheckConstraint(
            "role IN ('TOP', 'JUNGLE', 'MID', 'BOT', 'SUPPORT')", 
            name="ck_champion_role_stats_role"
        ),
        CheckConstraint("base_damage BETWEEN 0.0 AND 10.0", name="ck_base_damage_range"),
        CheckConstraint("base_utility BETWEEN 0.0 AND 10.0", name="ck_base_utility_range"),
        CheckConstraint("base_survivability BETWEEN 0.0 AND 10.0", name="ck_base_survivability_range"),
    )

    champion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("champions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)

    # Status base (multiplicadores para simulação, escala de 0.0 a 10.0)
    base_damage: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    base_utility: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    base_survivability: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)

    # Relacionamentos
    champion: Mapped["Champion"] = relationship("Champion", back_populates="role_stats")
    patch_metas: Mapped[List["ChampionPatchMeta"]] = relationship(
        "ChampionPatchMeta", back_populates="role_stats", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChampionRoleStats(champion={self.champion_id}, role={self.role}, dmg={self.base_damage})>"
