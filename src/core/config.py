"""
Configurações centralizadas da aplicação LoL Manager.
Carregadas a partir do arquivo .env via Pydantic Settings (v2).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Banco de dados ────────────────────────────────────────────────────────
    # URL assíncrona usada pelo SQLAlchemy/FastAPI (driver asyncpg)
    database_url: str

    # URL síncrona usada pelo Alembic para gerar e aplicar migrações
    sync_database_url: str

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── Configurações da aplicação ────────────────────────────────────────────
    secret_key: str = "dev-secret-key"
    debug: bool = False
    environment: str = "development"  # development | staging | production

    # ── Regras do jogo: elegibilidade e contratos ─────────────────────────────
    # Idade mínima para competir nas ERLs (ligas regionais)
    min_age_erl: int = 16
    # Idade mínima para competir na LEC (liga principal europeia)
    min_age_lec: int = 18
    # Número máximo de temporadas que um contrato pode cobrir
    max_contract_seasons: int = 4
    # Número mínimo de jogadores registrados por time (5 titulares + subs)
    min_roster_size: int = 11
    # Cláusula de rookies: % mínima de partidas da liga para acionar proteções
    rookie_clause_threshold: float = 0.25

    # ── Mecânicas de burnout ───────────────────────────────────────────────────
    # Penalidade de burnout aplicada em MATCH_DAY (titulares)
    burnout_daily_penalty: int = 5
    # Limite crítico de burnout — acima disso o jogador entra em colapso
    burnout_critical_threshold: int = 80
    # Pontos de burnout recuperados por período de descanso (base REST)
    burnout_recovery_per_rest: int = 12
    # Recuperação visual/mental em REST (base)
    visual_recovery_per_rest: int = 10
    mental_recovery_per_rest: int = 8
    # Limite de burnout que aplica debuff visível nas mecânicas
    visual_fatigue_mechanics_debuff_threshold: int = 70
    # Alerta de hub (burnout ou visual acima deste valor)
    fatigue_alert_threshold: int = 70

    # ── Motor de partidas: bônus/debuffs de champion pool ────────────────────
    # Multiplicador de performance ao jogar campeão do pool principal
    champion_pool_main_bonus: float = 1.10
    # Multiplicador ao jogar campeão do pool secundário
    champion_pool_secondary_debuff: float = 0.80
    # Multiplicador ao jogar fora do pool (comfort pick forçado por draft)
    champion_pool_off_pool_debuff: float = 0.55

    # ── Motor de partidas: comunicação do coach ───────────────────────────────
    # Número máximo de comunicações por round antes de causar confusão
    coach_comms_max_before_confusion: int = 3
    # Probabilidade base de confusão ao ultrapassar o limite de comunicações
    coach_comms_confusion_base_chance: float = 0.15


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna a instância singleton das configurações.
    O cache garante que o arquivo .env seja lido apenas uma vez.
    """
    return Settings()
