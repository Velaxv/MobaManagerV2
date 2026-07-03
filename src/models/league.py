"""
Modelos de Liga e Standings do LoL Manager.

Inclui:
  - League: configuração da competição (fase, formato, premiação)
  - LeagueTeam: tabela de junção com standings de cada time na liga
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.shared.enums import LeagueType, Region, SplitPhase

if TYPE_CHECKING:
    from src.models.match import Match
    from src.models.team import Team


class League(Base, UUIDMixin, TimestampMixin):
    """
    Liga/competição de LoL.

    Armazena a configuração completa da competição:
    formato, fase atual, regras de promoção/rebaixamento e premiação.
    """

    __tablename__ = "leagues"

    # --- Identificação ---
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Nome completo da liga (ex: 'LEC Spring 2025')."
    )
    abbreviation: Mapped[str] = mapped_column(
        String(10), nullable=False, doc="Sigla da liga (ex: 'LEC', 'CBLOL')."
    )
    league_type: Mapped[LeagueType] = mapped_column(
        SAEnum(LeagueType), nullable=False, doc="Tipo da liga: LEC, ERL ou ACADEMY."
    )
    region: Mapped[Region] = mapped_column(
        SAEnum(Region), nullable=False, doc="Região competitiva da liga."
    )

    # --- Estado atual da temporada ---
    current_phase: Mapped[SplitPhase] = mapped_column(
        SAEnum(SplitPhase),
        nullable=False,
        default=SplitPhase.OFFSEASON,
        doc="Fase atual da temporada (OFFSEASON, PRESEASON, REGULAR_SEASON, PLAYOFFS, WORLDS).",
    )
    current_week: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, doc="Semana atual dentro da fase corrente (começa em 0)."
    )
    current_day: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, doc="Dia atual dentro da semana corrente (começa em 0)."
    )

    # --- Formato da competição ---
    # Número de semanas na fase regular (padrão LEC: 9 semanas)
    regular_season_weeks: Mapped[int] = mapped_column(
        Integer, default=9, nullable=False, doc="Duração da fase regular em semanas."
    )
    # Partidas por semana na fase regular (padrão: 2 jogos por time/semana)
    matches_per_week: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False, doc="Número de partidas por time por semana na fase regular."
    )
    # Número de times classificados para playoffs
    playoff_teams: Mapped[int] = mapped_column(
        Integer, default=6, nullable=False, doc="Número de times classificados para os playoffs."
    )

    # --- Promoção e Rebaixamento ---
    # Times rebaixados para a ERL/ACADEMY ao fim da temporada
    relegation_slots: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False, doc="Vagas de rebaixamento ao fim da temporada."
    )
    # Times promovidos da ERL/ACADEMY para a LEC ao fim da temporada
    promotion_slots: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False, doc="Vagas de promoção ao fim da temporada."
    )

    # --- Premiação ---
    # Distribuição de premiação: {"1": 100000, "2": 50000, "3-4": 25000, ...}
    prize_pool: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Distribuição de premiação por posição final (JSON).",
    )
    total_prize_pool: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
        doc="Premio total da liga em euros.",
    )

    # --- Relacionamentos ---
    league_teams: Mapped[List["LeagueTeam"]] = relationship(
        "LeagueTeam",
        back_populates="league",
        cascade="all, delete-orphan",
        doc="Standings de cada time participante.",
    )
    matches: Mapped[List["Match"]] = relationship(
        "Match",
        back_populates="league",
        cascade="all, delete-orphan",
        doc="Partidas realizadas nesta liga.",
    )

    # -------------------------------------------------------------------------
    # Propriedades calculadas
    # -------------------------------------------------------------------------

    @property
    def total_regular_season_matches(self) -> int:
        """
        Total de partidas na fase regular por time.

        Returns:
            regular_season_weeks * matches_per_week
        """
        return self.regular_season_weeks * self.matches_per_week

    @property
    def is_in_regular_season(self) -> bool:
        """Retorna True se a liga está na fase regular."""
        return self.current_phase == SplitPhase.REGULAR_SEASON

    @property
    def is_in_playoffs(self) -> bool:
        """Retorna True se a liga está na fase de playoffs."""
        return self.current_phase == SplitPhase.PLAYOFFS

    # -------------------------------------------------------------------------
    # Métodos de domínio
    # -------------------------------------------------------------------------

    def advance_week(self) -> None:
        """
        Avança a liga para a próxima semana de jogo.
        Reseta o dia atual para 0.
        """
        self.current_week += 1
        self.current_day = 0

    def advance_day(self) -> None:
        """Avança a liga para o próximo dia de competição."""
        self.current_day += 1

    def get_standings(self) -> List["LeagueTeam"]:
        """
        Retorna os standings da liga ordenados por pontos (desc) e wins (desc).

        Returns:
            Lista de LeagueTeam ordenada por classificação.
        """
        return sorted(
            self.league_teams,
            key=lambda lt: (lt.points, lt.wins),
            reverse=True,
        )

    def get_prize_for_placement(self, placement: int) -> Decimal:
        """
        Retorna o prêmio para uma determinada posição final.

        Args:
            placement: Posição final do time (1 = campeão).

        Returns:
            Valor do prêmio em euros, ou Decimal("0") se não houver prêmio para a posição.
        """
        prize = self.prize_pool.get(str(placement), 0)
        return Decimal(str(prize))

    def __repr__(self) -> str:
        return (
            f"<League(name={self.name!r}, type={self.league_type}, phase={self.current_phase})>"
        )


class LeagueTeam(Base, UUIDMixin, TimestampMixin):
    """
    Tabela de junção entre Liga e Time.

    Armazena os standings e dados de playoff de cada time participante.
    """

    __tablename__ = "league_teams"

    # --- Chaves Estrangeiras ---
    league_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID da liga.",
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID do time participante.",
    )

    # --- Standings da Fase Regular ---
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Vitórias na fase regular.")
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Derrotas na fase regular.")
    points: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, doc="Pontos acumulados (sistema de pontuação da liga)."
    )

    # --- Dados de Playoff ---
    is_in_playoffs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="True se o time se classificou para os playoffs."
    )
    playoff_seed: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Seed do time nos playoffs (1 = melhor classificado)."
    )
    final_placement: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Posição final do time na temporada."
    )
    prize_earned: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
        doc="Prêmio recebido ao fim da temporada em euros.",
    )

    # --- Relacionamentos ---
    league: Mapped["League"] = relationship("League", back_populates="league_teams")
    team: Mapped["Team"] = relationship("Team", back_populates="league_teams")

    # -------------------------------------------------------------------------
    # Propriedades calculadas
    # -------------------------------------------------------------------------

    @property
    def win_rate(self) -> float:
        """
        Taxa de vitórias do time na liga.

        Returns:
            Proporção de vitórias (0.0 a 1.0). Retorna 0.0 se sem jogos.
        """
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

    @property
    def games_played(self) -> int:
        """Total de partidas jogadas (vitórias + derrotas)."""
        return self.wins + self.losses

    # -------------------------------------------------------------------------
    # Métodos de domínio
    # -------------------------------------------------------------------------

    def record_win(self, points_per_win: int = 1) -> None:
        """
        Registra uma vitória para o time na liga.

        Args:
            points_per_win: Pontos concedidos por vitória (padrão: 1).
        """
        self.wins += 1
        self.points += points_per_win

    def record_loss(self) -> None:
        """Registra uma derrota para o time na liga."""
        self.losses += 1

    def qualify_for_playoffs(self, seed: int) -> None:
        """
        Classifica o time para os playoffs com o seed especificado.

        Args:
            seed: Seed do time nos playoffs (1 = melhor seed).
        """
        self.is_in_playoffs = True
        self.playoff_seed = seed

    def __repr__(self) -> str:
        return (
            f"<LeagueTeam(team_id={self.team_id}, league_id={self.league_id}, "
            f"W={self.wins}/L={self.losses}, pts={self.points})>"
        )
