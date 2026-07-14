"""
Modelo do Time de esports.

Regras de negócio:
  - Mínimo de 11 jogadores (5 titulares + 6 reservas/base)
  - Orçamento e receita em euros/dólares (Decimal para precisão financeira)
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.shared.enums import Region
from src.shared.exceptions import RosterSizeViolation

if TYPE_CHECKING:
    from src.models.league import LeagueTeam
    from src.models.player import Player
    from src.models.staff import Staff


class Team(Base, UUIDMixin, TimestampMixin):
    """
    Modelo do Time de esports.

    Regras:
        - Mínimo de 11 jogadores (5 titulares + 6 reservas/base)
        - Budget nunca pode ser negativo
        - Cada time pertence a uma região específica
    """

    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint("budget >= 0", name="ck_team_budget_positive"),
        CheckConstraint("monthly_revenue >= 0", name="ck_team_revenue_positive"),
    )

    # --- Informações Básicas ---
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, doc="Nome completo do time (único no sistema)."
    )
    abbreviation: Mapped[str] = mapped_column(
        String(10), nullable=False, doc="Sigla/abreviação do time (ex: 'G2', 'FNC')."
    )
    region: Mapped[Region] = mapped_column(
        SAEnum(Region), nullable=False, doc="Região competitiva do time."
    )

    # --- Financeiro ---
    # Orçamento atual do time (em euros) — nunca pode ser negativo
    budget: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("1000000"),
        doc="Orçamento disponível do time em euros.",
    )
    # Receita mensal esperada (patrocinadores, viewership, merchandising)
    monthly_revenue: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("50000"),
        doc="Receita mensal esperada (patrocinadores, etc.) em euros.",
    )

    # --- Relacionamentos ---
    players: Mapped[List["Player"]] = relationship(
        "Player",
        back_populates="team",
        lazy="selectin",
        doc="Lista de jogadores vinculados ao time.",
    )
    league_teams: Mapped[List["LeagueTeam"]] = relationship(
        "LeagueTeam",
        back_populates="team",
        doc="Participações do time em ligas (standings).",
    )
    staffs: Mapped[List["Staff"]] = relationship(
        "Staff",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Lista de membros da comissão técnica do time.",
    )

    # -------------------------------------------------------------------------
    # Propriedades calculadas
    # -------------------------------------------------------------------------

    @property
    def roster_count(self) -> int:
        """Número total de jogadores atualmente no time."""
        return len(self.players)

    @property
    def monthly_salary_total(self) -> Decimal:
        """Soma de todos os salários mensais dos contratos ativos."""
        from src.shared.enums import ContractStatus

        total = Decimal("0")
        for player in self.players:
            for contract in player.contracts:
                if contract.status == ContractStatus.ACTIVE:
                    total += contract.monthly_salary
        return total

    @property
    def has_academy_team(self) -> bool:
        """Verifica se a organização possui uma equipe de base (academy/rookie)."""
        return any(p.is_rookie for p in self.players)

    # -------------------------------------------------------------------------
    # Métodos de validação e domínio
    # -------------------------------------------------------------------------

    def validate_roster_size(self) -> None:
        """
        Valida que o time possui o número mínimo de jogadores exigido.
        Se tiver academy: mínimo 11. Se não tiver: mínimo 6.

        Raises:
            RosterSizeViolation: Se o time tiver menos que o mínimo exigido.
        """
        min_size = 11 if self.has_academy_team else 6
        if self.roster_count < min_size:
            raise RosterSizeViolation(
                f"Time {self.name!r} possui {self.roster_count} jogadores. "
                f"Mínimo exigido: {min_size} (somando principal e base/academy).",
                code="ROSTER_TOO_SMALL",
            )

    def get_starters(self) -> List["Player"]:
        """
        Retorna os 5 titulares ordenados por role (TOP, JG, MID, BOT, SUP).

        Prefere jogadores com is_starter=True; se faltar role, usa o de maior CA.
        """
        from src.shared.enums import PlayerRole

        role_order = [
            PlayerRole.TOP,
            PlayerRole.JUNGLE,
            PlayerRole.MID,
            PlayerRole.BOT,
            PlayerRole.SUPPORT,
        ]
        starters = []
        for role in role_order:
            marked = [
                p
                for p in self.players
                if p.role == role and getattr(p, "is_starter", False) and p not in starters
            ]
            if marked:
                # Em caso de múltiplos marcados, maior CA
                marked.sort(key=lambda p: int(p.current_ability or 0), reverse=True)
                starters.append(marked[0])
                continue
            # Fallback: melhor CA da role
            candidates = [p for p in self.players if p.role == role and p not in starters]
            if candidates:
                candidates.sort(key=lambda p: int(p.current_ability or 0), reverse=True)
                starters.append(candidates[0])
        return starters[:5]

    def get_bench(self) -> List["Player"]:
        """Reservas de primeiro time (não titulares, não academy/rookie puro)."""
        starter_ids = {id(p) for p in self.get_starters()}
        bench = []
        for p in self.players:
            if id(p) in starter_ids:
                continue
            if p.is_rookie:
                continue
            bench.append(p)
        bench.sort(key=lambda p: (p.role.value if p.role else "", -int(p.current_ability or 0)))
        return bench

    def get_academy(self) -> List["Player"]:
        """Academy / rookies que não são titulares."""
        starter_ids = {id(p) for p in self.get_starters()}
        academy = [
            p
            for p in self.players
            if id(p) not in starter_ids and (p.is_rookie or "Academy" in (p.name or ""))
        ]
        academy.sort(key=lambda p: (p.role.value if p.role else "", -int(p.current_ability or 0)))
        return academy

    def get_average_ca(self) -> float:
        """
        Calcula o CA médio dos titulares do time.

        Returns:
            Média de Current Ability dos 5 titulares, ou 0.0 se não houver titulares.
        """
        starters = self.get_starters()
        if not starters:
            return 0.0
        return sum(p.current_ability for p in starters) / len(starters)

    def get_average_teamwork(self) -> float:
        """
        Calcula a média de teamwork dos titulares do time.

        Returns:
            Média de teamwork dos titulares, ou 0.0 se não houver titulares.
        """
        starters = self.get_starters()
        if not starters:
            return 0.0
        return sum(p.teamwork for p in starters) / len(starters)

    def deduct_budget(self, amount: Decimal, operation: str = "operação") -> None:
        """
        Desconta um valor do orçamento do time.

        Args:
            amount: Valor a ser descontado.
            operation: Descrição da operação (para mensagem de erro).

        Raises:
            InsufficientBudget: Se o time não tiver orçamento suficiente.
        """
        from src.shared.exceptions import InsufficientBudget

        if self.budget < amount:
            raise InsufficientBudget(
                required_amount=float(amount),
                available_amount=float(self.budget),
                operation=operation,
            )
        self.budget -= amount

    def __repr__(self) -> str:
        return f"<Team(name={self.name!r}, region={self.region}, players={self.roster_count})>"
