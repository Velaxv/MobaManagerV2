"""
Modelo do Jogador profissional de LoL.

Cobre todos os atributos necessários para a simulação:
  - Habilidade base (CA/PA)
  - Atributos técnicos e mentais
  - Atributos ocultos (não exibidos ao usuário)
  - Medidores de fadiga e burnout
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.shared.enums import PlayerRole, Region

if TYPE_CHECKING:
    from src.models.contract import Contract
    from src.models.team import Team


class Player(Base, UUIDMixin, TimestampMixin):
    """
    Modelo do Jogador profissional de LoL.

    Atributos:
        Habilidade Base: CA (Current Ability) e PA (Potential Ability)
        Técnicos: mechanics, champion_pool
        Mentais: focus, resilience, coachability, teamwork
        Ocultos: consistency, big_match_aptitude (não visíveis ao jogador)
        Fadiga: burnout_meter, visual_fatigue, mental_fatigue
    """

    __tablename__ = "players"
    __table_args__ = (
        # Restrições de integridade dos atributos numéricos
        CheckConstraint("current_ability BETWEEN 0 AND 200", name="ck_player_ca_range"),
        CheckConstraint("potential_ability BETWEEN 0 AND 200", name="ck_player_pa_range"),
        CheckConstraint("potential_ability >= current_ability", name="ck_player_pa_gte_ca"),
        CheckConstraint("mechanics BETWEEN 1 AND 20", name="ck_player_mechanics_range"),
        CheckConstraint("focus BETWEEN 1 AND 20", name="ck_player_focus_range"),
        CheckConstraint("resilience BETWEEN 1 AND 20", name="ck_player_resilience_range"),
        CheckConstraint("coachability BETWEEN 1 AND 20", name="ck_player_coachability_range"),
        CheckConstraint("teamwork BETWEEN 1 AND 20", name="ck_player_teamwork_range"),
        CheckConstraint("consistency BETWEEN 1 AND 20", name="ck_player_consistency_range"),
        CheckConstraint("big_match_aptitude BETWEEN 1 AND 20", name="ck_player_bma_range"),
        CheckConstraint("burnout_meter BETWEEN 0 AND 100", name="ck_player_burnout_range"),
        CheckConstraint("visual_fatigue BETWEEN 0 AND 100", name="ck_player_visual_fatigue_range"),
        CheckConstraint("mental_fatigue BETWEEN 0 AND 100", name="ck_player_mental_fatigue_range"),
    )

    # --- Informações Básicas ---
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Nome/apelido do jogador."
    )
    date_of_birth: Mapped[date] = mapped_column(
        Date, nullable=False, doc="Data de nascimento — usada para validação de idade na liga."
    )
    nationality: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Nacionalidade do jogador (ISO ou nome do país)."
    )
    role: Mapped[PlayerRole] = mapped_column(
        SAEnum(PlayerRole), nullable=False, doc="Posição principal do jogador no time."
    )
    region: Mapped[Optional[Region]] = mapped_column(
        SAEnum(Region), nullable=True, doc="Região de origem/residência do jogador."
    )
    is_rookie: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="True se o jogador ainda está em seu primeiro contrato profissional.",
    )

    # --- Habilidade Base ---
    # CA: representa a habilidade atual real do jogador (0-200)
    current_ability: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        doc="Current Ability: habilidade atual real do jogador (0-200).",
    )
    # PA: teto de desenvolvimento futuro do jogador (0-200); -1 = PA desconhecido/aleatório
    potential_ability: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=150,
        doc="Potential Ability: teto de desenvolvimento futuro (0-200).",
    )

    # --- Atributos Técnicos ---
    # Mecânica: precisão de mecânicas de jogo (CS, skillshots, kiting) — escala 1-20
    mechanics: Mapped[float] = mapped_column(
        Float, nullable=False, default=10.0, doc="Mecânica de jogo: CS, skillshots, kiting (1-20)."
    )
    # Pool de campeões: lista de {champion: str, tier: MAIN/SECONDARY}
    champion_pool: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Pool de campeões: lista de dicionários {champion, tier}.",
    )

    # --- Atributos Mentais ---
    # Foco: capacidade de manter concentração durante a partida
    focus: Mapped[float] = mapped_column(
        Float, nullable=False, default=10.0, doc="Foco e concentração durante a partida (1-20)."
    )
    # Resiliência: capacidade de se recuperar de situações adversas
    resilience: Mapped[float] = mapped_column(
        Float, nullable=False, default=10.0, doc="Resiliência: recuperação em situações adversas (1-20)."
    )
    # Coachabilidade: receptividade a instruções do treinador
    coachability: Mapped[float] = mapped_column(
        Float, nullable=False, default=10.0, doc="Coachabilidade: receptividade ao treinador (1-20)."
    )
    # Trabalho em equipe: cooperação e comunicação com o time
    teamwork: Mapped[float] = mapped_column(
        Float, nullable=False, default=10.0, doc="Trabalho em equipe e comunicação (1-20)."
    )

    # --- Atributos Ocultos (não visíveis ao jogador no jogo) ---
    # Consistência: controla a variância de performance (20 = muito consistente, 1 = muito volátil)
    consistency: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=10.0,
        doc="[OCULTO] Consistência: controla variância de performance (1-20).",
    )
    # Aptidão para grandes partidas: bônus em playoffs e torneios importantes
    big_match_aptitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=10.0,
        doc="[OCULTO] Aptidão para grandes jogos: bônus em playoffs/torneios (1-20).",
    )

    # --- Medidores de Fadiga/Burnout ---
    # Medidor geral de burnout (0=descansado, 100=esgotado totalmente)
    burnout_meter: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, doc="Burnout geral do jogador (0=descansado, 100=esgotado)."
    )
    # Fadiga visual: acúmulo de horas de tela — afeta atributo de mecânica
    visual_fatigue: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, doc="Fadiga visual: horas de tela — afeta mecânica (0-100)."
    )
    # Fadiga mental: pressão e estresse acumulados — afeta atributos mentais
    mental_fatigue: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, doc="Fadiga mental: estresse acumulado — afeta atributos mentais (0-100)."
    )

    # --- Estatísticas de Temporada ---
    games_played_this_split: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Número de partidas jogadas no split atual (reiniciado a cada temporada).",
    )

    # --- Relacionamentos ---
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID do time atual do jogador (nullable = agente livre).",
    )
    team: Mapped[Optional["Team"]] = relationship(
        "Team", back_populates="players", doc="Time atual do jogador."
    )
    contracts: Mapped[List["Contract"]] = relationship(
        "Contract",
        back_populates="player",
        cascade="all, delete-orphan",
        doc="Histórico completo de contratos do jogador.",
    )

    # -------------------------------------------------------------------------
    # Métodos de domínio
    # -------------------------------------------------------------------------

    def get_age(self) -> int:
        """
        Calcula a idade atual do jogador em anos completos.

        Returns:
            Idade do jogador em anos.
        """
        from datetime import date as dt_date

        today = dt_date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def get_burnout_level(self) -> str:
        """
        Retorna o nível de burnout baseado no medidor atual.

        Returns:
            BurnoutLevel correspondente ao valor de burnout_meter.
        """
        from src.shared.enums import BurnoutLevel

        if self.burnout_meter <= 25:
            return BurnoutLevel.FRESH
        elif self.burnout_meter <= 50:
            return BurnoutLevel.TIRED
        elif self.burnout_meter <= 75:
            return BurnoutLevel.FATIGUED
        elif self.burnout_meter <= 90:
            return BurnoutLevel.CRITICAL
        return BurnoutLevel.BURNED_OUT

    def get_champion_pool_tier(self, champion_name: str) -> str:
        """
        Verifica o tier do campeão no pool do jogador.

        Args:
            champion_name: Nome do campeão a verificar (case-insensitive).

        Returns:
            ChampionPoolTier: MAIN, SECONDARY ou OFF_POOL.
        """
        from src.shared.enums import ChampionPoolTier

        pool = self.champion_pool if isinstance(self.champion_pool, list) else []
        for entry in pool:
            if entry.get("champion", "").lower() == champion_name.lower():
                return entry.get("tier", ChampionPoolTier.SECONDARY)
        return ChampionPoolTier.OFF_POOL

    def is_eligible_for_league(self, min_age: int) -> bool:
        """
        Verifica se o jogador atende à idade mínima da liga.

        Args:
            min_age: Idade mínima exigida pela liga (ex: 18 para LEC, 16 para ERL).

        Returns:
            True se o jogador atende ao requisito de idade.
        """
        return self.get_age() >= min_age

    def apply_burnout_recovery(self, rest_days: int) -> None:
        """
        Reduz o burnout do jogador com base em dias de descanso.
        Recuperação: 5 pontos por dia de descanso, limitado a 0.

        Args:
            rest_days: Número de dias de descanso.
        """
        from src.shared.math_utils import clamp

        recovery = rest_days * 5.0
        self.burnout_meter = clamp(self.burnout_meter - recovery, 0.0, 100.0)

    def __repr__(self) -> str:
        return f"<Player(name={self.name!r}, role={self.role}, ca={self.current_ability})>"
