import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.team import Team

class Staff(Base, UUIDMixin, TimestampMixin):
    """
    Representa um membro da comissão técnica (Staff) de um time.
    """
    __tablename__ = "staffs"
    __table_args__ = (
        CheckConstraint(
            "role IN ('HEAD_COACH', 'STRATEGIC_COACH', 'ASSISTANT_COACH', 'PERFORMANCE_COACH')", 
            name="ck_staff_role"
        ),
        CheckConstraint("communication BETWEEN 1.0 AND 20.0", name="ck_staff_communication_range"),
        CheckConstraint("meta_reading BETWEEN 1.0 AND 20.0", name="ck_staff_meta_reading_range"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)

    # Atributos de comissão técnica (escala 1.0 a 20.0)
    communication: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    meta_reading: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)

    # Relacionamentos
    team: Mapped["Team"] = relationship("Team", back_populates="staffs")

    def __repr__(self) -> str:
        return f"<Staff(name={self.name!r}, role={self.role}, comm={self.communication})>"
