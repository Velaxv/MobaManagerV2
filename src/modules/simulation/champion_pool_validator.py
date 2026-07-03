"""
Validador de Champion Pool.

Responsável por calcular o multiplicador de Mecânica de um jogador
com base na sua proficiência no campeão escolhido no draft.

Regras de Negócio:
    - Campeão MAIN:      +10% de Mecânica (jogador domina o campeão)
    - Campeão SECONDARY: -20% de Mecânica (conhece mas não é o principal)
    - Fora da Pool:      -45% de Mecânica (debuff severo — jogador desconfortável)
"""

import logging
from dataclasses import dataclass

from src.shared.enums import ChampionPoolTier
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ChampionPoolResult:
    """Resultado da validação do champion pool."""
    champion_name: str
    player_name: str
    tier: ChampionPoolTier
    mechanics_multiplier: float
    is_off_pool: bool
    description: str


class ChampionPoolValidator:
    """
    Valida se um campeão está no pool de um jogador e retorna
    o multiplicador de mecânica correspondente.

    Multiplicadores (configuráveis via Settings):
        MAIN:      1.10 (bônus por excelência no campeão)
        SECONDARY: 0.80 (leve penalidade por pouca prática recente)
        OFF_POOL:  0.55 (penalidade severa — jogador fora da zona de conforto)
    """

    def validate(self, player, champion_name: str) -> ChampionPoolResult:
        """
        Valida o campeão escolhido contra o pool do jogador.

        Args:
            player: Instância do modelo Player com atributo champion_pool.
            champion_name: Nome do campeão escolhido no draft.

        Returns:
            ChampionPoolResult com o multiplicador de mecânica aplicável.
        """
        tier = self._get_champion_tier(player, champion_name)
        multiplier = self._get_multiplier(tier)
        is_off_pool = tier == ChampionPoolTier.OFF_POOL

        description = self._build_description(player.name, champion_name, tier, multiplier)

        if is_off_pool:
            logger.warning(
                f"[ChampionPool] {player.name} escolheu {champion_name!r} FORA do seu pool! "
                f"Debuff severo aplicado: {multiplier:.0%} de Mecânica."
            )
        else:
            logger.info(
                f"[ChampionPool] {player.name} → {champion_name!r} ({tier.value}): "
                f"multiplicador {multiplier:.0%}"
            )

        return ChampionPoolResult(
            champion_name=champion_name,
            player_name=player.name,
            tier=tier,
            mechanics_multiplier=multiplier,
            is_off_pool=is_off_pool,
            description=description,
        )

    def _get_champion_tier(self, player, champion_name: str) -> ChampionPoolTier:
        """
        Busca o tier do campeão na lista champion_pool do jogador.
        A champion_pool é uma lista de dicts: [{champion: str, tier: str}, ...]
        """
        pool: list = player.champion_pool if isinstance(player.champion_pool, list) else []

        for entry in pool:
            if isinstance(entry, dict):
                pool_champion = entry.get("champion", "")
                if pool_champion.lower() == champion_name.lower():
                    tier_str = entry.get("tier", "SECONDARY")
                    try:
                        return ChampionPoolTier(tier_str)
                    except ValueError:
                        logger.warning(
                            f"Tier inválido {tier_str!r} no pool de {player.name}. "
                            "Usando SECONDARY como padrão."
                        )
                        return ChampionPoolTier.SECONDARY

        # Campeão não encontrado no pool
        return ChampionPoolTier.OFF_POOL

    def _get_multiplier(self, tier: ChampionPoolTier) -> float:
        """Retorna o multiplicador de mecânica para cada tier."""
        multiplier_map = {
            ChampionPoolTier.MAIN: settings.champion_pool_main_bonus,       # 1.10
            ChampionPoolTier.SECONDARY: settings.champion_pool_secondary_debuff,  # 0.80
            ChampionPoolTier.OFF_POOL: settings.champion_pool_off_pool_debuff,    # 0.55
        }
        return multiplier_map[tier]

    def _build_description(
        self,
        player_name: str,
        champion_name: str,
        tier: ChampionPoolTier,
        multiplier: float
    ) -> str:
        """Gera descrição textual legível do resultado."""
        tier_descriptions = {
            ChampionPoolTier.MAIN: f"Campeão principal de {player_name} — bônus de mecânica aplicado.",
            ChampionPoolTier.SECONDARY: f"{champion_name} é secundário no pool de {player_name} — leve penalidade.",
            ChampionPoolTier.OFF_POOL: (
                f"⚠️  {player_name} escolheu {champion_name!r} FORA do seu pool! "
                f"Penalidade severa de {(1 - multiplier):.0%} em Mecânica."
            ),
        }
        return tier_descriptions[tier]


# Instância singleton do validador
champion_pool_validator = ChampionPoolValidator()
