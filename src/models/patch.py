import uuid
from datetime import date
from sqlalchemy import String, Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import Base, TimestampMixin, UUIDMixin

class Patch(Base, UUIDMixin, TimestampMixin):
    """
    Representa uma versão do patch competitivo.
    """
    __tablename__ = "patches"

    version: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    release_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Data em vigor competitiva (release_date + 7 dias)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relacionamentos
    patch_metas: Mapped[list["ChampionPatchMeta"]] = relationship(
        "ChampionPatchMeta", back_populates="patch", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Patch(version={self.version!r}, effective={self.effective_date})>"


class ChampionPatchMeta(Base, UUIDMixin, TimestampMixin):
    """
    Modificadores de Buff/Nerf aplicados por um Patch específico sobre os status da Role do Campeão.
    """
    __tablename__ = "champion_patch_meta"

    patch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patches.id", ondelete="CASCADE"), nullable=False
    )
    champion_role_stats_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("champion_role_stats.id", ondelete="CASCADE"), nullable=False
    )

    # Modificadores multiplicativos (ex: 1.05 = +5% buff, 0.95 = -5% nerf)
    damage_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    utility_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    survivability_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Relacionamentos
    patch: Mapped["Patch"] = relationship("Patch", back_populates="patch_metas")
    role_stats: Mapped["ChampionRoleStats"] = relationship("ChampionRoleStats", back_populates="patch_metas")

    def __repr__(self) -> str:
        return (
            f"<ChampionPatchMeta(patch={self.patch_id}, stats={self.champion_role_stats_id}, "
            f"dmg_mod={self.damage_modifier})>"
        )
