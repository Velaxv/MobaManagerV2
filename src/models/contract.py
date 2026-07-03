"""
Modelo de Contrato entre Jogador e Time.

Regras de negócio:
  - Duração máxima de 4 temporadas (≈ 2 anos, sendo 2 splits/ano de ~6 meses cada)
  - Cláusula de Desenvolvimento de Rookie: extensão automática de 1 temporada
    se o rookie jogar > 25% das partidas da liga principal
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.shared.enums import ContractStatus
from src.shared.exceptions import ContractDurationViolation

if TYPE_CHECKING:
    from src.models.player import Player
    from src.models.team import Team


# Duração máxima: 4 temporadas = 2 anos (2 splits por ano)
MAX_CONTRACT_SEASONS: int = 4

# Duração aproximada de cada split em dias (6 meses ≈ 180 dias)
SEASON_DURATION_DAYS: int = 180


class Contract(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Contrato entre Jogador e Time.

    Regras:
        - Duração máxima de 4 temporadas (≈ 2 anos)
        - Cláusula de Desenvolvimento de Rookie: extensão automática de 1 temporada
          se o rookie jogar > 25% das partidas da liga principal no período
        - Salário mensal nunca pode ser negativo
    """

    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("monthly_salary >= 0", name="ck_contract_salary_positive"),
        CheckConstraint("seasons_duration BETWEEN 1 AND 4", name="ck_contract_max_seasons"),
        CheckConstraint("rookie_games_played >= 0", name="ck_contract_rookie_games_positive"),
        CheckConstraint("rookie_total_league_games >= 0", name="ck_contract_total_league_games_positive"),
    )

    # --- Partes Contratantes ---
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID do jogador contratado.",
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID do time contratante.",
    )

    # --- Termos do Contrato ---
    start_date: Mapped[date] = mapped_column(
        Date, nullable=False, doc="Data de início do contrato."
    )
    end_date: Mapped[date] = mapped_column(
        Date, nullable=False, doc="Data de término do contrato (pode ser estendida pela cláusula rookie)."
    )
    # Duração em temporadas/splits: 1 a 4 (máximo 4 splits ≈ 2 anos)
    seasons_duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        doc="Duração do contrato em temporadas/splits (1-4).",
    )
    monthly_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Salário mensal bruto do jogador em euros.",
    )
    status: Mapped[ContractStatus] = mapped_column(
        SAEnum(ContractStatus),
        nullable=False,
        default=ContractStatus.ACTIVE,
        doc="Status atual do contrato.",
    )

    # --- Cláusula de Desenvolvimento de Rookie ---
    # Flag que habilita a cláusula de extensão automática para rookies
    has_rookie_clause: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Indica se o contrato possui a cláusula de desenvolvimento de rookie.",
    )
    # Número de partidas da liga principal que o rookie jogou no período
    rookie_games_played: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Partidas da liga principal jogadas pelo rookie no período do contrato.",
    )
    # Total de partidas da liga na temporada (definido pelo serviço da liga ao iniciar o split)
    rookie_total_league_games: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Total de partidas da liga na temporada (referência para calcular participação).",
    )
    # Flag que indica se a extensão automática já foi disparada (evita dupla extensão)
    rookie_extension_triggered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="True se a extensão automática de rookie já foi ativada neste contrato.",
    )

    # --- Relacionamentos ---
    player: Mapped["Player"] = relationship(
        "Player", back_populates="contracts", doc="Jogador ao qual este contrato pertence."
    )

    # -------------------------------------------------------------------------
    # Propriedades calculadas
    # -------------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """
        Verifica se o contrato está ativo hoje.

        Returns:
            True se status=ACTIVE e a data atual está dentro do período do contrato.
        """
        return (
            self.status == ContractStatus.ACTIVE
            and self.start_date <= date.today() <= self.end_date
        )

    @property
    def rookie_participation_rate(self) -> float:
        """
        Taxa de participação do rookie nas partidas da liga principal.

        Returns:
            Proporção de jogos jogados em relação ao total (0.0 a 1.0).
            Retorna 0.0 se rookie_total_league_games for 0.
        """
        if self.rookie_total_league_games == 0:
            return 0.0
        return self.rookie_games_played / self.rookie_total_league_games

    @property
    def remaining_seasons(self) -> int:
        """
        Calcula o número aproximado de temporadas restantes no contrato.

        Returns:
            Número inteiro de temporadas restantes (arredondado para cima).
        """
        remaining_days = (self.end_date - date.today()).days
        if remaining_days <= 0:
            return 0
        return max(1, round(remaining_days / SEASON_DURATION_DAYS))

    # -------------------------------------------------------------------------
    # Métodos de domínio
    # -------------------------------------------------------------------------

    def check_and_trigger_rookie_extension(
        self, threshold: float = 0.25
    ) -> bool:
        """
        Verifica e dispara a extensão automática de contrato para rookies.

        A extensão é ativada se:
        1. O contrato possui a cláusula rookie (has_rookie_clause=True)
        2. A extensão ainda não foi disparada (rookie_extension_triggered=False)
        3. A taxa de participação do rookie supera o threshold (padrão: 25%)

        Ao ser ativada, o contrato é estendido por SEASON_DURATION_DAYS dias
        e seasons_duration é incrementado em 1.

        Args:
            threshold: Taxa mínima de participação para disparar a extensão (padrão: 0.25).

        Returns:
            True se a extensão foi ativada nesta chamada, False caso contrário.
        """
        # Pré-condições
        if not self.has_rookie_clause:
            return False
        if self.rookie_extension_triggered:
            return False  # Extensão já foi aplicada anteriormente

        # Verifica threshold de participação
        if self.rookie_participation_rate >= threshold:
            # Estende o contrato por mais uma temporada (≈ 6 meses)
            self.end_date += timedelta(days=SEASON_DURATION_DAYS)
            self.seasons_duration += 1
            self.rookie_extension_triggered = True
            self.status = ContractStatus.ROOKIE_EXTENDED
            return True

        return False

    def terminate(self) -> None:
        """
        Encerra o contrato antecipadamente.
        Define o status como TERMINATED e a data de término como hoje.
        """
        self.status = ContractStatus.TERMINATED
        self.end_date = date.today()

    def mark_expired(self) -> None:
        """
        Marca o contrato como expirado (usado pelo scheduler no fim de cada split).
        """
        self.status = ContractStatus.EXPIRED

    # -------------------------------------------------------------------------
    # Métodos de classe (validação)
    # -------------------------------------------------------------------------

    @classmethod
    def validate_duration(cls, seasons: int) -> None:
        """
        Valida que a duração do contrato não excede o máximo permitido.

        Args:
            seasons: Número de temporadas do contrato.

        Raises:
            ContractDurationViolation: Se seasons > MAX_CONTRACT_SEASONS.
        """
        if seasons > MAX_CONTRACT_SEASONS:
            raise ContractDurationViolation(
                f"Duração de {seasons} temporadas excede o máximo de {MAX_CONTRACT_SEASONS} "
                f"temporadas (≈ {MAX_CONTRACT_SEASONS // 2} anos).",
                code="CONTRACT_TOO_LONG",
            )
        if seasons < 1:
            raise ContractDurationViolation(
                "A duração mínima do contrato é de 1 temporada.",
                code="CONTRACT_TOO_SHORT",
            )

    def __repr__(self) -> str:
        return (
            f"<Contract(player_id={self.player_id}, team_id={self.team_id}, "
            f"seasons={self.seasons_duration}, status={self.status})>"
        )
