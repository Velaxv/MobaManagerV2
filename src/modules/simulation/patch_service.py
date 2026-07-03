import logging
from datetime import date
from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.core.redis_client import redis_client
from src.models.patch import Patch, ChampionPatchMeta
from src.models.champion import ChampionRoleStats, Champion

logger = logging.getLogger("lol_manager_patch_service")

class PatchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_patch(self, current_date: date) -> Optional[Patch]:
        """
        Retorna o patch competitivo ativo para a data informada.
        Regra: effective_date <= current_date.
        """
        stmt = (
            select(Patch)
            .where(Patch.effective_date <= current_date)
            .order_by(Patch.effective_date.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_patch_cache(self, current_date: date) -> Optional[str]:
        """
        Verifica o patch ativo para a data, calcula os status consolidados dos campeões 
        e atualiza o cache em memória virtual no Redis Simulado.
        Retorna a versão do patch ativada ou None.
        """
        active_patch = await self.get_active_patch(current_date)
        if not active_patch:
            logger.warning(f"Nenhum patch competitivo em vigor para a data {current_date}.")
            # Se não houver patch, limpa o cache para usar valores base padrão
            await redis_client.delete("patch:current:meta")
            await redis_client.delete("patch:current:version")
            return None

        # Verifica se já está cacheado para este patch
        cached_version = await redis_client.get_generic("patch:current:version")
        if cached_version == active_patch.version:
            logger.debug(f"Cache do patch {active_patch.version} já atualizado no Redis Virtual.")
            return active_patch.version

        logger.info(f"Carregando modificadores do patch {active_patch.version} em memória virtual...")

        # 1. Carrega todos os ChampionRoleStats (atributos base)
        stats_stmt = select(ChampionRoleStats).join(Champion)
        stats_result = await self.db.execute(stats_stmt)
        all_stats = stats_result.scalars().all()

        # 2. Carrega modificadores específicos do patch atual
        meta_stmt = select(ChampionPatchMeta).where(ChampionPatchMeta.patch_id == active_patch.id)
        meta_result = await self.db.execute(meta_stmt)
        patch_metas = meta_result.scalars().all()

        # Mapeia modificadores para busca rápida
        meta_map: Dict[str, ChampionPatchMeta] = {
            str(m.champion_role_stats_id): m for m in patch_metas
        }

        # 3. Consolida os atributos (base * modifier)
        compiled_meta: Dict[str, Dict[str, float]] = {}
        for stat in all_stats:
            # Chave composta: "NomeDoCampeão:ROLE"
            key = f"{stat.champion.name.lower()}:{stat.role.upper()}"
            
            modifier = meta_map.get(str(stat.id))
            dmg_mod = modifier.damage_modifier if modifier else 1.0
            utl_mod = modifier.utility_modifier if modifier else 1.0
            srv_mod = modifier.survivability_modifier if modifier else 1.0

            # Aplica modificadores limitando a escala entre 0.0 e 10.0
            compiled_meta[key] = {
                "damage": max(0.0, min(10.0, stat.base_damage * dmg_mod)),
                "utility": max(0.0, min(10.0, stat.base_utility * utl_mod)),
                "survivability": max(0.0, min(10.0, stat.base_survivability * srv_mod))
            }

        # 4. Salva no cache virtual
        await redis_client.set_generic("patch:current:meta", compiled_meta)
        await redis_client.set_generic("patch:current:version", active_patch.version)
        logger.info(f"Cache do patch {active_patch.version} carregado com sucesso (Zero Dependency Mode).")
        return active_patch.version

    @staticmethod
    async def get_cached_champion_stats(champion_name: str, role: str) -> Dict[str, float]:
        """
        Busca os atributos (dano, utilidade, sobrevivência) do campeão no cache virtual.
        Retorna valores padrão 5.0 caso o campeão ou cache não existam.
        """
        meta = await redis_client.get_generic("patch:current:meta")
        key = f"{champion_name.lower()}:{role.upper()}"
        
        if meta and key in meta:
            return meta[key]
            
        # Fallback padrão caso não haja cache
        return {"damage": 5.0, "utility": 5.0, "survivability": 5.0}
