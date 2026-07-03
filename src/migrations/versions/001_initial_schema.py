"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

Migration inicial que cria TODAS as tabelas do LoL Manager:
  - players        → jogadores com atributos, burnout e fadiga
  - teams          → times com orçamento e staff
  - contracts      → contratos com cláusula rookie
  - leagues        → ligas com splits e configurações
  - league_teams   → standings e participação de times nas ligas
  - matches        → partidas com logs JSON e resultado
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ──────────────────────────────────────────────────────────────────────────────
# Metadados da revisão Alembic
# ──────────────────────────────────────────────────────────────────────────────
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cria todos os ENUMs PostgreSQL e todas as tabelas do sistema.
    Ordem: ENUMs → tabelas sem FK → tabelas com FK → índices.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # 1. ENUM TYPES
    # Criados antes das tabelas pois são referenciados como tipos de coluna.
    # ──────────────────────────────────────────────────────────────────────────

    # Posições dos jogadores no mapa (roles do LoL/MOBA)
    player_role_enum = postgresql.ENUM(
        "TOP",
        "JUNGLE",
        "MID",
        "BOT",
        "SUPPORT",
        name="playerrole",
        create_type=True,
    )
    player_role_enum.create(op.get_bind(), checkfirst=True)

    # Status do contrato do jogador
    contract_status_enum = postgresql.ENUM(
        "ACTIVE",
        "EXPIRED",
        "TERMINATED",
        "PENDING",
        name="contractstatus",
        create_type=True,
    )
    contract_status_enum.create(op.get_bind(), checkfirst=True)

    # Fase atual do split/temporada (usada na tabela de ligas)
    split_phase_enum = postgresql.ENUM(
        "OFFSEASON",
        "PRESEASON",
        "REGULAR_SEASON",
        "PLAYOFFS",
        name="splitphase",
        create_type=True,
    )
    split_phase_enum.create(op.get_bind(), checkfirst=True)

    # Resultado de uma partida do ponto de vista de um time
    match_result_enum = postgresql.ENUM(
        "WIN",
        "LOSS",
        "DRAW",
        "NOT_PLAYED",
        name="matchresult",
        create_type=True,
    )
    match_result_enum.create(op.get_bind(), checkfirst=True)

    # Tipo de partida (fase do torneio)
    match_type_enum = postgresql.ENUM(
        "REGULAR",
        "PLAYOFF_QUARTER",
        "PLAYOFF_SEMI",
        "PLAYOFF_FINAL",
        "SCRIM",
        name="matchtype",
        create_type=True,
    )
    match_type_enum.create(op.get_bind(), checkfirst=True)

    # Nível de burnout do jogador (calculado a partir de burnout_meter)
    burnout_level_enum = postgresql.ENUM(
        "LOW",       # 0–30
        "MODERATE",  # 31–60
        "HIGH",      # 61–80
        "CRITICAL",  # 81–100
        name="burnoutlevel",
        create_type=True,
    )
    burnout_level_enum.create(op.get_bind(), checkfirst=True)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. TABELA: teams
    # Criada antes de players pois players referencia teams via FK.
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "teams",
        # Identificador único UUID (gerado pelo PostgreSQL)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("tag", sa.String(8), nullable=False, comment="Abreviação do time (ex: T1, FNC)"),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("country", sa.String(80), nullable=True),
        # Orçamento anual em USD (deve ser >= 0)
        sa.Column(
            "budget",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default="500000.00",
        ),
        # Receita gerada por patrocínios e premiações
        sa.Column(
            "revenue",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        # Reputação do time (0–100): afeta recrutamento e contratos
        sa.Column(
            "reputation",
            sa.Integer,
            nullable=False,
            server_default="50",
        ),
        # Número de títulos conquistados (histórico)
        sa.Column("titles_won", sa.Integer, nullable=False, server_default="0"),
        # Informações de staff (coach, analista, etc.)
        sa.Column("head_coach", sa.String(120), nullable=True),
        sa.Column("analyst", sa.String(120), nullable=True),
        # Timestamps de auditoria
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Constraints
        sa.CheckConstraint("budget >= 0", name="ck_teams_budget_non_negative"),
        sa.CheckConstraint("reputation BETWEEN 0 AND 100", name="ck_teams_reputation_range"),
        sa.CheckConstraint("titles_won >= 0", name="ck_teams_titles_non_negative"),
        sa.UniqueConstraint("tag", "region", name="uq_teams_tag_region"),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 3. TABELA: players
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "players",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("nickname", sa.String(60), nullable=False, comment="IGN (In-Game Name)"),
        sa.Column("age", sa.Integer, nullable=False),
        sa.Column("nationality", sa.String(80), nullable=True),

        # Referência ao time atual (nullable: jogador pode ser free agent)
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),

        # Posição no jogo
        sa.Column("role", sa.Enum("TOP", "JUNGLE", "MID", "BOT", "SUPPORT", name="playerrole"), nullable=False),

        # ── Habilidade (CA/PA no estilo Football Manager) ──────────────────
        # CA: Current Ability — habilidade atual (1–100)
        sa.Column("ca", sa.Integer, nullable=False, server_default="50"),
        # PA: Potential Ability — teto de crescimento (1–100 ou -1 para "indeterminado")
        sa.Column("pa", sa.Integer, nullable=False, server_default="60"),

        # ── Atributos técnicos (1–20, estilo FM) ──────────────────────────
        sa.Column("mechanics", sa.Integer, nullable=False, server_default="10",
                  comment="Precisão de mecânicas (kiting, skillshots)"),
        sa.Column("game_sense", sa.Integer, nullable=False, server_default="10",
                  comment="Leitura de mapa e tomada de decisão"),
        sa.Column("teamwork", sa.Integer, nullable=False, server_default="10",
                  comment="Capacidade de jogar em equipe e comunicação"),
        sa.Column("adaptability", sa.Integer, nullable=False, server_default="10",
                  comment="Velocidade de adaptação a patches e metas"),
        sa.Column("consistency", sa.Integer, nullable=False, server_default="10",
                  comment="Estabilidade de performance entre partidas"),

        # ── Atributos mentais (1–20) ───────────────────────────────────────
        sa.Column("focus", sa.Integer, nullable=False, server_default="10",
                  comment="Concentração em situações de alta pressão"),
        sa.Column("resilience", sa.Integer, nullable=False, server_default="10",
                  comment="Capacidade de recuperar após erros/derrotas"),
        sa.Column("leadership", sa.Integer, nullable=False, server_default="5",
                  comment="Influência positiva no ambiente da equipe"),
        sa.Column("pressure_handling", sa.Integer, nullable=False, server_default="10",
                  comment="Performance em situações de playoffs/bo5"),

        # ── Atributos físicos (1–20) ───────────────────────────────────────
        sa.Column("reaction_time", sa.Integer, nullable=False, server_default="10",
                  comment="APM e tempo de reação a estímulos visuais"),
        sa.Column("stamina", sa.Integer, nullable=False, server_default="10",
                  comment="Resistência a sessões longas de jogo"),

        # ── Sistema de Burnout e Fadiga (0.0–100.0) ───────────────────────
        # burnout_meter: métrica principal de fadiga acumulada
        sa.Column(
            "burnout_meter",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        # visual_fatigue: fadiga dos olhos/concentração visual (afeta mechanics)
        sa.Column(
            "visual_fatigue",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        # mental_fatigue: esgotamento mental (afeta game_sense e focus)
        sa.Column(
            "mental_fatigue",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0.00",
        ),

        # ── Estatísticas do split atual ────────────────────────────────────
        sa.Column("games_played_this_split", sa.Integer, nullable=False, server_default="0"),
        sa.Column("wins_this_split", sa.Integer, nullable=False, server_default="0"),
        sa.Column("losses_this_split", sa.Integer, nullable=False, server_default="0"),

        # ── Metadata ──────────────────────────────────────────────────────
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # ── Foreign Keys ──────────────────────────────────────────────────
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_players_team_id",
            ondelete="SET NULL",  # Free agent se o time for deletado
        ),

        # ── Constraints de validação ──────────────────────────────────────
        sa.CheckConstraint("age BETWEEN 15 AND 45", name="ck_players_age_range"),
        sa.CheckConstraint("ca BETWEEN 1 AND 100", name="ck_players_ca_range"),
        sa.CheckConstraint("pa BETWEEN -1 AND 100", name="ck_players_pa_range"),
        sa.CheckConstraint("ca <= pa OR pa = -1", name="ck_players_ca_lte_pa"),
        # Validação dos atributos técnicos (1–20)
        sa.CheckConstraint("mechanics BETWEEN 1 AND 20", name="ck_players_mechanics_range"),
        sa.CheckConstraint("game_sense BETWEEN 1 AND 20", name="ck_players_game_sense_range"),
        sa.CheckConstraint("teamwork BETWEEN 1 AND 20", name="ck_players_teamwork_range"),
        sa.CheckConstraint("adaptability BETWEEN 1 AND 20", name="ck_players_adaptability_range"),
        sa.CheckConstraint("consistency BETWEEN 1 AND 20", name="ck_players_consistency_range"),
        # Validação dos atributos mentais (1–20)
        sa.CheckConstraint("focus BETWEEN 1 AND 20", name="ck_players_focus_range"),
        sa.CheckConstraint("resilience BETWEEN 1 AND 20", name="ck_players_resilience_range"),
        sa.CheckConstraint("leadership BETWEEN 1 AND 20", name="ck_players_leadership_range"),
        sa.CheckConstraint("pressure_handling BETWEEN 1 AND 20", name="ck_players_pressure_handling_range"),
        # Validação dos atributos físicos (1–20)
        sa.CheckConstraint("reaction_time BETWEEN 1 AND 20", name="ck_players_reaction_time_range"),
        sa.CheckConstraint("stamina BETWEEN 1 AND 20", name="ck_players_stamina_range"),
        # Validação de burnout e fadiga (0–100)
        sa.CheckConstraint("burnout_meter BETWEEN 0 AND 100", name="ck_players_burnout_range"),
        sa.CheckConstraint("visual_fatigue BETWEEN 0 AND 100", name="ck_players_visual_fatigue_range"),
        sa.CheckConstraint("mental_fatigue BETWEEN 0 AND 100", name="ck_players_mental_fatigue_range"),
        # Estatísticas não podem ser negativas
        sa.CheckConstraint("games_played_this_split >= 0", name="ck_players_games_played_non_negative"),
        sa.CheckConstraint("wins_this_split >= 0", name="ck_players_wins_non_negative"),
        sa.CheckConstraint("losses_this_split >= 0", name="ck_players_losses_non_negative"),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 4. TABELA: contracts
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "contracts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),

        # Duração em anos (máximo 4 anos, conforme regras da liga)
        sa.Column("duration_years", sa.Integer, nullable=False),
        # Data de início e fim do contrato
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),

        # Salário anual acordado em USD
        sa.Column(
            "annual_salary",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        # Cláusula de rescisão (buyout clause)
        sa.Column(
            "buyout_clause",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
            comment="Valor de rescisão antecipada (opcional)",
        ),

        # Cláusula rookie: verdadeiro para jogadores em primeiro contrato profissional
        # Impede algumas negociações e aplica teto salarial especial
        sa.Column(
            "is_rookie",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="True para contratos de estreia (rookie clause ativa)",
        ),
        # Partidas jogadas sob este contrato específico
        sa.Column("games_played", sa.Integer, nullable=False, server_default="0"),

        # Status do contrato
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "EXPIRED", "TERMINATED", "PENDING", name="contractstatus"),
            nullable=False,
            server_default="PENDING",
        ),

        # Extensões de contrato (quantas vezes foi renovado)
        sa.Column("extensions_count", sa.Integer, nullable=False, server_default="0"),

        # Timestamps de auditoria
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # Foreign Keys
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="fk_contracts_player_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_contracts_team_id",
            ondelete="CASCADE",
        ),

        # Constraints de validação
        sa.CheckConstraint(
            "duration_years BETWEEN 1 AND 4",
            name="ck_contracts_duration_range",
        ),
        sa.CheckConstraint(
            "annual_salary > 0",
            name="ck_contracts_salary_positive",
        ),
        sa.CheckConstraint(
            "buyout_clause IS NULL OR buyout_clause >= annual_salary",
            name="ck_contracts_buyout_gte_salary",
        ),
        sa.CheckConstraint(
            "end_date > start_date",
            name="ck_contracts_end_after_start",
        ),
        sa.CheckConstraint(
            "games_played >= 0",
            name="ck_contracts_games_played_non_negative",
        ),
        sa.CheckConstraint(
            "extensions_count >= 0",
            name="ck_contracts_extensions_non_negative",
        ),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 5. TABELA: leagues
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "leagues",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("tier", sa.Integer, nullable=False, server_default="1",
                  comment="1 = Liga principal, 2 = Segunda divisão, etc."),

        # ── Configuração do calendário ────────────────────────────────────
        # Número de semanas na temporada regular (padrão: 9)
        sa.Column("regular_season_weeks", sa.Integer, nullable=False, server_default="9"),
        # Número de times participantes
        sa.Column("teams_count", sa.Integer, nullable=False, server_default="10"),
        # Número de times que avançam para os playoffs
        sa.Column("playoff_teams_count", sa.Integer, nullable=False, server_default="6"),

        # ── Estado atual do calendário ────────────────────────────────────
        sa.Column(
            "current_phase",
            sa.Enum("OFFSEASON", "PRESEASON", "REGULAR_SEASON", "PLAYOFFS", name="splitphase"),
            nullable=False,
            server_default="OFFSEASON",
        ),
        # Semana atual da temporada (0 = pré-início)
        sa.Column("current_week", sa.Integer, nullable=False, server_default="0"),
        # Total de dias simulados desde o início da liga
        sa.Column("current_day", sa.Integer, nullable=False, server_default="0"),
        # Número do split atual (1 = primeiro split do ano)
        sa.Column("current_split", sa.Integer, nullable=False, server_default="1"),
        # Ano do jogo (não o ano real)
        sa.Column("season_year", sa.Integer, nullable=False, server_default="2024"),

        # ── Premiação ─────────────────────────────────────────────────────
        # Prêmio total do split (distribuído entre os finalistas)
        sa.Column(
            "prize_pool",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="100000.00",
        ),
        # Prêmio específico para o campeão
        sa.Column(
            "champion_prize",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="50000.00",
        ),

        # Timestamps de auditoria
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # Constraints de validação
        sa.CheckConstraint("tier BETWEEN 1 AND 5", name="ck_leagues_tier_range"),
        sa.CheckConstraint(
            "regular_season_weeks BETWEEN 1 AND 26",
            name="ck_leagues_regular_season_weeks_range",
        ),
        sa.CheckConstraint("teams_count >= 2", name="ck_leagues_teams_count_min"),
        sa.CheckConstraint(
            "playoff_teams_count >= 2 AND playoff_teams_count <= teams_count",
            name="ck_leagues_playoff_teams_valid",
        ),
        sa.CheckConstraint("prize_pool >= 0", name="ck_leagues_prize_pool_non_negative"),
        sa.CheckConstraint(
            "champion_prize <= prize_pool",
            name="ck_leagues_champion_prize_lte_pool",
        ),
        sa.UniqueConstraint("name", "region", "season_year", name="uq_leagues_name_region_year"),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 6. TABELA: league_teams (standings / participação)
    # Tabela de associação com dados de standings para o split atual.
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "league_teams",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),

        # ── Standings do split atual ───────────────────────────────────────
        sa.Column("wins", sa.Integer, nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer, nullable=False, server_default="0"),
        # Saldo de mapas (wins - losses de mapas individuais)
        sa.Column("map_diff", sa.Integer, nullable=False, server_default="0"),
        # Pontuação total no split (pode ter peso diferente por partida)
        sa.Column(
            "points",
            sa.Numeric(precision=8, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        # Posição atual na tabela (calculada dinamicamente, mas armazenada para cache)
        sa.Column("standing_position", sa.Integer, nullable=True),

        # ── Dados de playoffs ─────────────────────────────────────────────
        sa.Column("qualified_for_playoffs", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("playoff_round_reached", sa.Integer, nullable=True,
                  comment="0=Não classificado, 1=Quartas, 2=Semi, 3=Final, 4=Campeão"),

        # Timestamps de auditoria
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # Foreign Keys
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name="fk_league_teams_league_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_league_teams_team_id",
            ondelete="CASCADE",
        ),

        # Constraints de validação
        sa.CheckConstraint("wins >= 0", name="ck_league_teams_wins_non_negative"),
        sa.CheckConstraint("losses >= 0", name="ck_league_teams_losses_non_negative"),
        sa.CheckConstraint("points >= 0", name="ck_league_teams_points_non_negative"),
        # Um time não pode aparecer duas vezes na mesma liga no mesmo ano
        sa.UniqueConstraint("league_id", "team_id", name="uq_league_teams_league_team"),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 7. TABELA: matches
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "matches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("league_id", postgresql.UUID(as_uuid=True), nullable=False),

        # Times participantes
        sa.Column("team_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_b_id", postgresql.UUID(as_uuid=True), nullable=False),

        # Tipo e fase da partida
        sa.Column(
            "match_type",
            sa.Enum(
                "REGULAR", "PLAYOFF_QUARTER", "PLAYOFF_SEMI", "PLAYOFF_FINAL", "SCRIM",
                name="matchtype",
            ),
            nullable=False,
            server_default="REGULAR",
        ),

        # Semana do split em que a partida ocorre
        sa.Column("week_number", sa.Integer, nullable=False, server_default="1"),
        # Dia absoluto do calendário em que a partida ocorre
        sa.Column("scheduled_day", sa.Integer, nullable=False),

        # ── Resultado ─────────────────────────────────────────────────────
        # Winner: UUID do time vencedor (null se ainda não jogado)
        sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=True),

        # Placar de mapas (ex: 2-1 em um Bo3)
        sa.Column("team_a_maps_won", sa.Integer, nullable=False, server_default="0"),
        sa.Column("team_b_maps_won", sa.Integer, nullable=False, server_default="0"),

        # Resultado da perspectiva de cada time (calculado após a partida)
        sa.Column(
            "team_a_result",
            sa.Enum("WIN", "LOSS", "DRAW", "NOT_PLAYED", name="matchresult"),
            nullable=False,
            server_default="NOT_PLAYED",
        ),
        sa.Column(
            "team_b_result",
            sa.Enum("WIN", "LOSS", "DRAW", "NOT_PLAYED", name="matchresult"),
            nullable=False,
            server_default="NOT_PLAYED",
        ),

        # ── Logs e estatísticas detalhadas ────────────────────────────────
        # JSON com o log completo da simulação (kills, objectives, timeline, etc.)
        sa.Column(
            "match_log",
            postgresql.JSONB,
            nullable=True,
            comment="Log completo da simulação em formato JSONB",
        ),
        # Estatísticas de performance dos jogadores (indexado por player_id)
        sa.Column(
            "player_stats",
            postgresql.JSONB,
            nullable=True,
            comment="Performance individual: KDA, damage, CS, etc.",
        ),
        # Dados de burnout antes e depois da partida (para rastreabilidade)
        sa.Column(
            "burnout_snapshot",
            postgresql.JSONB,
            nullable=True,
            comment="Snapshot de burnout/fadiga antes e após a partida",
        ),

        # Duração da partida em minutos
        sa.Column("duration_minutes", sa.Integer, nullable=True),

        # Se a partida foi simulada ou inserida manualmente
        sa.Column("is_simulated", sa.Boolean, nullable=False, server_default="true"),

        # Timestamps de auditoria
        sa.Column(
            "played_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Momento exato em que a partida foi simulada",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        # Foreign Keys
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name="fk_matches_league_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_a_id"],
            ["teams.id"],
            name="fk_matches_team_a_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_b_id"],
            ["teams.id"],
            name="fk_matches_team_b_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["winner_id"],
            ["teams.id"],
            name="fk_matches_winner_id",
            ondelete="SET NULL",
        ),

        # Constraints de validação
        sa.CheckConstraint(
            "team_a_id <> team_b_id",
            name="ck_matches_different_teams",
        ),
        sa.CheckConstraint(
            "week_number >= 1",
            name="ck_matches_week_positive",
        ),
        sa.CheckConstraint(
            "team_a_maps_won >= 0",
            name="ck_matches_team_a_maps_non_negative",
        ),
        sa.CheckConstraint(
            "team_b_maps_won >= 0",
            name="ck_matches_team_b_maps_non_negative",
        ),
        sa.CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0",
            name="ck_matches_duration_positive",
        ),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 8. ÍNDICES DE PERFORMANCE
    # Criados após as tabelas para otimizar consultas frequentes.
    # ──────────────────────────────────────────────────────────────────────────

    # Players: busca por time e por role (query frequente no match engine)
    op.create_index("ix_players_team_id", "players", ["team_id"])
    op.create_index("ix_players_role", "players", ["role"])
    op.create_index("ix_players_ca", "players", ["ca"])

    # Contracts: busca por jogador e por status
    op.create_index("ix_contracts_player_id", "contracts", ["player_id"])
    op.create_index("ix_contracts_team_id", "contracts", ["team_id"])
    op.create_index("ix_contracts_status", "contracts", ["status"])

    # Leagues: busca por região e fase atual
    op.create_index("ix_leagues_region", "leagues", ["region"])
    op.create_index("ix_leagues_current_phase", "leagues", ["current_phase"])

    # League_teams: busca por liga (para standings) e por time
    op.create_index("ix_league_teams_league_id", "league_teams", ["league_id"])
    op.create_index("ix_league_teams_team_id", "league_teams", ["team_id"])

    # Matches: busca por liga e semana (query de agendamento)
    op.create_index("ix_matches_league_id", "matches", ["league_id"])
    op.create_index("ix_matches_week_number", "matches", ["week_number"])
    op.create_index("ix_matches_scheduled_day", "matches", ["scheduled_day"])
    # Índice composto para buscar partidas não jogadas de uma liga
    op.create_index(
        "ix_matches_league_result",
        "matches",
        ["league_id", "team_a_result"],
    )
    # Índice GIN no JSONB de match_log para consultas dentro do JSON
    op.create_index(
        "ix_matches_match_log_gin",
        "matches",
        ["match_log"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """
    Reverte todas as mudanças criadas em upgrade().
    Ordem: tabelas com FK primeiro, depois tabelas base, depois ENUMs.
    """

    # Remove índices primeiro
    op.drop_index("ix_matches_match_log_gin", table_name="matches")
    op.drop_index("ix_matches_league_result", table_name="matches")
    op.drop_index("ix_matches_scheduled_day", table_name="matches")
    op.drop_index("ix_matches_week_number", table_name="matches")
    op.drop_index("ix_matches_league_id", table_name="matches")
    op.drop_index("ix_league_teams_team_id", table_name="league_teams")
    op.drop_index("ix_league_teams_league_id", table_name="league_teams")
    op.drop_index("ix_leagues_current_phase", table_name="leagues")
    op.drop_index("ix_leagues_region", table_name="leagues")
    op.drop_index("ix_contracts_status", table_name="contracts")
    op.drop_index("ix_contracts_team_id", table_name="contracts")
    op.drop_index("ix_contracts_player_id", table_name="contracts")
    op.drop_index("ix_players_ca", table_name="players")
    op.drop_index("ix_players_role", table_name="players")
    op.drop_index("ix_players_team_id", table_name="players")

    # Remove tabelas em ordem reversa (dependências FK)
    op.drop_table("matches")
    op.drop_table("league_teams")
    op.drop_table("leagues")
    op.drop_table("contracts")
    op.drop_table("players")
    op.drop_table("teams")

    # Remove os ENUM types criados
    # Necessário explicitamente no PostgreSQL
    op.execute("DROP TYPE IF EXISTS matchresult")
    op.execute("DROP TYPE IF EXISTS matchtype")
    op.execute("DROP TYPE IF EXISTS splitphase")
    op.execute("DROP TYPE IF EXISTS contractstatus")
    op.execute("DROP TYPE IF EXISTS burnoutlevel")
    op.execute("DROP TYPE IF EXISTS playerrole")
