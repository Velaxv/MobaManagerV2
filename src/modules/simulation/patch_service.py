import logging
from datetime import date, timedelta
from typing import Dict, Optional, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.core.redis_client import redis_client
from src.models.patch import Patch, ChampionPatchMeta
from src.models.champion import ChampionRoleStats, Champion

logger = logging.getLogger("lol_manager_patch_service")


def _classify_change(
    dmg: float, utl: float, srv: float
) -> tuple[str, float, List[str]]:
    """
    Classifica buff/nerf/mixed e score de tendência (-1..+1).
    """
    tags: List[str] = []
    score = 0.0
    for label, val in (("DMG", dmg), ("UTL", utl), ("SRV", srv)):
        if val > 1.001:
            tags.append(f"BUFF_{label}")
            score += (val - 1.0)
        elif val < 0.999:
            tags.append(f"NERF_{label}")
            score -= (1.0 - val)
    if score > 0.01:
        kind = "BUFF"
    elif score < -0.01:
        kind = "NERF"
    else:
        kind = "NEUTRAL"
    return kind, score, tags


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

    async def get_upcoming_patch(self, current_date: date) -> Optional[Patch]:
        stmt = (
            select(Patch)
            .where(Patch.effective_date > current_date)
            .order_by(Patch.effective_date.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_patches(self) -> List[Patch]:
        result = await self.db.execute(select(Patch).order_by(Patch.effective_date.asc()))
        return list(result.scalars().all())

    async def _changes_for_patch(self, patch: Patch) -> List[Dict[str, Any]]:
        """Lista legível de buffs/nerfs do patch."""
        stmt = (
            select(ChampionPatchMeta)
            .where(ChampionPatchMeta.patch_id == patch.id)
            .options(selectinload(ChampionPatchMeta.role_stats).selectinload(ChampionRoleStats.champion))
        )
        result = await self.db.execute(stmt)
        metas = list(result.scalars().all())
        changes: List[Dict[str, Any]] = []
        for m in metas:
            rs = m.role_stats
            if not rs or not rs.champion:
                continue
            dmg = float(m.damage_modifier or 1.0)
            utl = float(m.utility_modifier or 1.0)
            srv = float(m.survivability_modifier or 1.0)
            kind, score, tags = _classify_change(dmg, utl, srv)
            if kind == "NEUTRAL":
                continue
            changes.append(
                {
                    "champion": rs.champion.name,
                    "role": rs.role if isinstance(rs.role, str) else getattr(rs.role, "value", str(rs.role)),
                    "kind": kind,
                    "score": round(score, 3),
                    "tags": tags,
                    "damage_modifier": dmg,
                    "utility_modifier": utl,
                    "survivability_modifier": srv,
                    "summary": self._summary_line(rs.champion.name, kind, dmg, utl, srv),
                }
            )
        changes.sort(key=lambda c: (-abs(c["score"]), c["champion"]))
        return changes

    @staticmethod
    def _summary_line(name: str, kind: str, dmg: float, utl: float, srv: float) -> str:
        parts = []
        if abs(dmg - 1.0) > 0.001:
            parts.append(f"dano {((dmg - 1.0) * 100):+.0f}%")
        if abs(utl - 1.0) > 0.001:
            parts.append(f"util {((utl - 1.0) * 100):+.0f}%")
        if abs(srv - 1.0) > 0.001:
            parts.append(f"surv {((srv - 1.0) * 100):+.0f}%")
        detail = ", ".join(parts) if parts else "ajuste"
        return f"{name}: {kind} ({detail})"

    async def get_status(self, current_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Snapshot para o frontend: patch ativo, próximos, changelist, bias de draft.
        """
        today = current_date or date.today()
        active = await self.get_active_patch(today)
        upcoming = await self.get_upcoming_patch(today)
        all_patches = await self.list_patches()

        # Garante cache se houver ativo
        if active:
            await self.update_patch_cache(today)

        active_changes = await self._changes_for_patch(active) if active else []
        upcoming_changes = await self._changes_for_patch(upcoming) if upcoming else []

        # Bias map: champion name lower -> score (para draft AI / FE badges)
        bias: Dict[str, float] = {}
        badges: Dict[str, str] = {}  # "azir" -> BUFF|NERF
        for ch in active_changes:
            key = ch["champion"].lower()
            bias[key] = bias.get(key, 0.0) + float(ch["score"])
            # Prefer BUFF if any buff, else NERF if net negative
            if bias[key] > 0.01:
                badges[key] = "BUFF"
            elif bias[key] < -0.01:
                badges[key] = "NERF"

        await redis_client.set_generic("patch:current:bias", bias)
        await redis_client.set_generic("patch:current:badges", badges)
        await redis_client.set_generic("patch:current:changes", active_changes)

        patches_list = []
        for p in all_patches:
            status = "upcoming"
            if active and p.id == active.id:
                status = "active"
            elif p.effective_date <= today:
                status = "expired"
            patches_list.append(
                {
                    "id": str(p.id),
                    "version": p.version,
                    "release_date": p.release_date.isoformat(),
                    "effective_date": p.effective_date.isoformat(),
                    "status": status,
                    "days_until_effective": (p.effective_date - today).days,
                }
            )

        return {
            "calendar_date": today.isoformat(),
            "active": (
                {
                    "version": active.version,
                    "release_date": active.release_date.isoformat(),
                    "effective_date": active.effective_date.isoformat(),
                    "changes": active_changes,
                    "buff_count": sum(1 for c in active_changes if c["kind"] == "BUFF"),
                    "nerf_count": sum(1 for c in active_changes if c["kind"] == "NERF"),
                }
                if active
                else None
            ),
            "upcoming": (
                {
                    "version": upcoming.version,
                    "release_date": upcoming.release_date.isoformat(),
                    "effective_date": upcoming.effective_date.isoformat(),
                    "days_until": (upcoming.effective_date - today).days,
                    "changes": upcoming_changes,
                }
                if upcoming
                else None
            ),
            "patches": patches_list,
            "badges": badges,
            "bias": bias,
        }

    async def update_patch_cache(self, current_date: date) -> Optional[str]:
        """
        Verifica o patch ativo para a data, calcula os status consolidados dos campeões 
        e atualiza o cache em memória virtual no Redis Simulado.
        Retorna a versão do patch ativada ou None.
        """
        active_patch = await self.get_active_patch(current_date)
        if not active_patch:
            logger.warning(f"Nenhum patch competitivo em vigor para a data {current_date}.")
            await redis_client.delete("patch:current:meta")
            await redis_client.delete("patch:current:version")
            await redis_client.delete("patch:current:bias")
            await redis_client.delete("patch:current:badges")
            await redis_client.delete("patch:current:changes")
            return None

        cached_version = await redis_client.get_generic("patch:current:version")
        if cached_version == active_patch.version:
            logger.debug(f"Cache do patch {active_patch.version} já atualizado no Redis Virtual.")
            return active_patch.version

        logger.info(f"Carregando modificadores do patch {active_patch.version} em memória virtual...")

        stats_stmt = (
            select(ChampionRoleStats)
            .options(selectinload(ChampionRoleStats.champion))
            .join(Champion)
        )
        stats_result = await self.db.execute(stats_stmt)
        all_stats = stats_result.scalars().all()

        meta_stmt = (
            select(ChampionPatchMeta)
            .where(ChampionPatchMeta.patch_id == active_patch.id)
            .options(
                selectinload(ChampionPatchMeta.role_stats).selectinload(
                    ChampionRoleStats.champion
                )
            )
        )
        meta_result = await self.db.execute(meta_stmt)
        patch_metas = meta_result.scalars().all()

        meta_map: Dict[str, ChampionPatchMeta] = {
            str(m.champion_role_stats_id): m for m in patch_metas
        }

        compiled_meta: Dict[str, Dict[str, float]] = {}
        for stat in all_stats:
            champ = getattr(stat, "champion", None)
            if not champ:
                continue
            key = f"{champ.name.lower()}:{str(stat.role).upper()}"
            
            modifier = meta_map.get(str(stat.id))
            dmg_mod = modifier.damage_modifier if modifier else 1.0
            utl_mod = modifier.utility_modifier if modifier else 1.0
            srv_mod = modifier.survivability_modifier if modifier else 1.0

            compiled_meta[key] = {
                "damage": max(0.0, min(10.0, stat.base_damage * dmg_mod)),
                "utility": max(0.0, min(10.0, stat.base_utility * utl_mod)),
                "survivability": max(0.0, min(10.0, stat.base_survivability * srv_mod))
            }

        changes = await self._changes_for_patch(active_patch)
        bias: Dict[str, float] = {}
        badges: Dict[str, str] = {}
        for ch in changes:
            key = ch["champion"].lower()
            bias[key] = bias.get(key, 0.0) + float(ch["score"])
            if bias[key] > 0.01:
                badges[key] = "BUFF"
            elif bias[key] < -0.01:
                badges[key] = "NERF"

        await redis_client.set_generic("patch:current:meta", compiled_meta)
        await redis_client.set_generic("patch:current:version", active_patch.version)
        await redis_client.set_generic("patch:current:bias", bias)
        await redis_client.set_generic("patch:current:badges", badges)
        await redis_client.set_generic("patch:current:changes", changes)
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
            
        return {"damage": 5.0, "utility": 5.0, "survivability": 5.0}

    @staticmethod
    async def get_cached_badges() -> Dict[str, str]:
        data = await redis_client.get_generic("patch:current:badges")
        return data if isinstance(data, dict) else {}

    @staticmethod
    async def get_cached_bias() -> Dict[str, float]:
        data = await redis_client.get_generic("patch:current:bias")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def game_date_from_elapsed(total_days: int) -> date:
        """Data de calendário do jogo (seed usa date.today() como dia 0)."""
        return date.today() + timedelta(days=max(0, int(total_days or 0)))
