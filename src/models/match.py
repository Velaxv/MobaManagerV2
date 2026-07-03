"""
Modelo de Partida simulada do LoL Manager.

Armazena o resultado completo da simulação incluindo:
  - Contexto da partida (liga, semana, fase)
  - Times e resultado
  - Logs detalhados de cada fase da simulação (draft, early, mid, late)
  - Probabilidade calculada pelo motor (para auditoria e replay)
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.shared.enums import MatchResult, SplitPhase

if TYPE_CHECKING:
    from src.models.league import League
    from src.models.team import Team


class Match(Base, UUIDMixin, TimestampMixin):
    """
    Modelo de Partida simulada.

    Armazena o resultado completo da simulação, incluindo:
      - Logs JSON de cada fase (draft, early game, mid game, late game)
      - Probabilidade calculada (para replay e análise pós-jogo)
      - Referências para os times e a liga
    """

    __tablename__ = "matches"

    # --- Contexto da Partida ---
    league_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID da liga em que a partida ocorreu.",
    )
    split_week: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Semana do split em que a partida foi disputada."
    )
    split_phase: Mapped[SplitPhase] = mapped_column(
        SAEnum(SplitPhase), nullable=False, doc="Fase da temporada (regular season, playoffs, etc.)."
    )
    is_playoff: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="True se a partida é uma partida de playoff.",
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Data e hora agendadas para a partida (UTC).",
    )

    # --- Times ---
    blue_team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id"),
        nullable=False,
        doc="ID do time no Blue Side.",
    )
    red_team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id"),
        nullable=False,
        doc="ID do time no Red Side.",
    )
    winner_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id"),
        nullable=True,
        doc="ID do time vencedor. Null se a partida ainda não foi simulada.",
    )

    # --- Resultado ---
    blue_result: Mapped[Optional[MatchResult]] = mapped_column(
        SAEnum(MatchResult),
        nullable=True,
        doc="Resultado do Blue Side (WIN, LOSS, FORFEIT). Null se não simulada.",
    )
    red_result: Mapped[Optional[MatchResult]] = mapped_column(
        SAEnum(MatchResult),
        nullable=True,
        doc="Resultado do Red Side (WIN, LOSS, FORFEIT). Null se não simulada.",
    )
    match_duration_minutes: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Duração total da partida em minutos (gerada pela simulação).",
    )

    # --- Dados de Auditoria do Motor ---
    # Probabilidade do Blue Side vencer, calculada antes da simulação
    blue_win_probability: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Probabilidade pré-jogo de vitória do Blue Side (0.05 a 0.95).",
    )

    # --- Logs Detalhados por Fase (JSON) ---
    # Log do draft: bans/picks de cada time, ordens, tier dos campeões
    draft_log: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Log completo do draft: bans, picks, ordens e tiers dos campeões.",
    )
    # Log da early game (0-15min): gold diff, kills, objectives por lane
    early_game_log: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Log da early game (0-15min): gold diff, kills, first blood, primeiros drakes.",
    )
    # Log da mid game (15-25min): dragon stacks, herald, teamfights
    mid_game_log: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Log da mid game (15-25min): objetivos, dragon soul, baron, teamfights.",
    )
    # Log da late game (25+min): teamfights decisivas, nexus
    late_game_log: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Log da late game (25+min): teamfights decisivas, push de base, nexo.",
    )

    # --- Relacionamentos ---
    league: Mapped["League"] = relationship(
        "League", back_populates="matches", doc="Liga em que a partida ocorreu."
    )
    blue_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[blue_team_id],
        doc="Time do Blue Side.",
    )
    red_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[red_team_id],
        doc="Time do Red Side.",
    )

    # -------------------------------------------------------------------------
    # Propriedades calculadas
    # -------------------------------------------------------------------------

    @property
    def is_simulated(self) -> bool:
        """Retorna True se a partida já foi simulada (possui resultado)."""
        return self.winner_team_id is not None

    @property
    def red_win_probability(self) -> Optional[float]:
        """
        Probabilidade de vitória do Red Side.

        Returns:
            1.0 - blue_win_probability, ou None se não calculada.
        """
        if self.blue_win_probability is None:
            return None
        return round(1.0 - self.blue_win_probability, 4)

    # -------------------------------------------------------------------------
    # Métodos de domínio
    # -------------------------------------------------------------------------

    def record_result(
        self,
        winner_id: uuid.UUID,
        duration_minutes: float,
        blue_win_prob: float,
    ) -> None:
        """
        Registra o resultado da simulação na partida.

        Args:
            winner_id: UUID do time vencedor (deve ser blue_team_id ou red_team_id).
            duration_minutes: Duração total da partida em minutos.
            blue_win_prob: Probabilidade calculada de vitória do Blue Side.

        Raises:
            ValueError: Se winner_id não corresponder a nenhum time da partida.
        """
        if winner_id not in (self.blue_team_id, self.red_team_id):
            raise ValueError(
                f"winner_id {winner_id} não corresponde ao Blue ({self.blue_team_id}) "
                f"nem ao Red ({self.red_team_id})."
            )

        self.winner_team_id = winner_id
        self.match_duration_minutes = duration_minutes
        self.blue_win_probability = blue_win_prob

        if winner_id == self.blue_team_id:
            self.blue_result = MatchResult.WIN
            self.red_result = MatchResult.LOSS
        else:
            self.blue_result = MatchResult.LOSS
            self.red_result = MatchResult.WIN

    def record_forfeit(self, forfeiting_team_id: uuid.UUID) -> None:
        """
        Registra um W.O. (forfeit) para a partida.

        Args:
            forfeiting_team_id: UUID do time que está dando W.O.

        Raises:
            ValueError: Se forfeiting_team_id não corresponder a nenhum time.
        """
        if forfeiting_team_id not in (self.blue_team_id, self.red_team_id):
            raise ValueError(
                f"forfeiting_team_id {forfeiting_team_id} não pertence a esta partida."
            )

        if forfeiting_team_id == self.blue_team_id:
            self.blue_result = MatchResult.FORFEIT
            self.red_result = MatchResult.WIN
            self.winner_team_id = self.red_team_id
        else:
            self.red_result = MatchResult.FORFEIT
            self.blue_result = MatchResult.WIN
            self.winner_team_id = self.blue_team_id

        self.match_duration_minutes = 0.0

    def __repr__(self) -> str:
        return (
            f"<Match(blue={self.blue_team_id}, red={self.red_team_id}, "
            f"winner={self.winner_team_id})>"
        )
