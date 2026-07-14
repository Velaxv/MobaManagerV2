# -*- coding: utf-8 -*-
"""
Pool de free agents no mercado (offseason / janela parcial).

- Lista jogadores sem time (team_id is None)
- Garante pool mínimo na entrada da offseason com gerados do "circuito"
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.serializers import serialize_player
from src.models.player import Player
from src.models.team import Team
from src.shared.enums import PlayerRole, Region

logger = logging.getLogger(__name__)

_FA_NAMES = [
    ("Nertz", PlayerRole.TOP),
    ("Kojima", PlayerRole.TOP),
    ("Absolut", PlayerRole.JUNGLE),
    ("Yampi", PlayerRole.JUNGLE),
    ("dyNquedo", PlayerRole.MID),
    ("Lava", PlayerRole.MID),
    ("DudsTheBoy", PlayerRole.BOT),
    ("Trigo", PlayerRole.BOT),
    ("RedBert", PlayerRole.SUPPORT),  # may exist — name suffix handles collision
    ("Damage", PlayerRole.SUPPORT),
    ("Hidan", PlayerRole.TOP),
    ("Minerva", PlayerRole.JUNGLE),
    ("toyk", PlayerRole.MID),
    ("Netuno", PlayerRole.BOT),
    ("Wos", PlayerRole.SUPPORT),
    ("Tyrin", PlayerRole.TOP),
    ("Aegis", PlayerRole.JUNGLE),
    ("Goku", PlayerRole.MID),
    ("Route", PlayerRole.BOT),
    ("Ceos", PlayerRole.SUPPORT),
]


class FreeAgencyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def count_free_agents(self) -> int:
        q = await self.db.execute(
            select(func.count()).select_from(Player).where(Player.team_id.is_(None))
        )
        return int(q.scalar() or 0)

    async def list_free_agents(
        self,
        *,
        role: Optional[str] = None,
        scouting_team_id: Optional[str] = None,
        limit: int = 80,
    ) -> Dict[str, Any]:
        from src.modules.career.scouting_service import ScoutingService

        q = (
            select(Player)
            .where(Player.team_id.is_(None))
            .options(selectinload(Player.contracts))
            .order_by(Player.current_ability.desc())
            .limit(limit)
        )
        if role:
            try:
                pr = PlayerRole(role.upper())
                q = q.where(Player.role == pr)
            except ValueError:
                pass

        result = await self.db.execute(q)
        players = list(result.scalars().all())

        knowledge: dict = {}
        if scouting_team_id:
            knowledge = await ScoutingService(self.db).get_knowledge(scouting_team_id)

        rows = [
            {
                **serialize_player(
                    p,
                    scouting_knowledge=knowledge.get(str(p.id)),
                    is_own_roster=False,
                    apply_scouting_mask=True,
                ),
                "isFreeAgent": True,
                "teamId": None,
            }
            for p in players
        ]
        return {
            "count": len(rows),
            "free_agents": rows,
            "role_filter": role,
        }

    async def ensure_pool(self, min_count: int = 8) -> Dict[str, Any]:
        """
        Se houver poucos free agents, gera jogadores do circuito (FA sintéticos).
        """
        current = await self.count_free_agents()
        created = 0
        if current >= min_count:
            return {"created": 0, "total": current, "message": "Pool de FA suficiente."}

        existing_names = set()
        nq = await self.db.execute(select(Player.name))
        existing_names = {n for (n,) in nq.all()}

        need = min_count - current
        rng = random.Random(f"fa-pool-{current}-{date.today().isoformat()}")
        used = set()

        for _ in range(need * 3):
            if created >= need:
                break
            base_name, role = rng.choice(_FA_NAMES)
            suffix = rng.randint(1, 99)
            name = base_name if base_name not in existing_names and base_name not in used else f"{base_name}{suffix}"
            if name in existing_names or name in used:
                continue
            used.add(name)
            ca = rng.randint(105, 155)
            pa = min(200, ca + rng.randint(5, 35))
            age = rng.randint(17, 28)
            dob = date.today() - timedelta(days=age * 365 + rng.randint(0, 300))
            player = Player(
                id=uuid.uuid4(),
                name=name,
                role=role,
                date_of_birth=dob,
                nationality="BR",
                region=Region.CBLOL,
                team_id=None,
                is_rookie=age <= 19,
                is_starter=False,
                current_ability=ca,
                potential_ability=pa,
                mechanics=float(rng.randint(8, 16)),
                focus=float(rng.randint(8, 16)),
                resilience=float(rng.randint(8, 15)),
                coachability=float(rng.randint(9, 17)),
                teamwork=float(rng.randint(8, 16)),
                consistency=float(rng.randint(7, 16)),
                big_match_aptitude=float(rng.randint(7, 16)),
                burnout_meter=0.0,
                visual_fatigue=0.0,
                mental_fatigue=0.0,
                champion_pool=[],
            )
            # Pool mínima por role
            from src.modules.draft.draft_ai import CHAMPIONS_BY_ROLE

            champs = list(CHAMPIONS_BY_ROLE.get(role, ["Aatrox"]))[:4]
            pool = []
            if champs:
                pool.append({"champion": champs[0], "tier": "MAIN"})
                for c in champs[1:3]:
                    pool.append({"champion": c, "tier": "SECONDARY"})
            player.champion_pool = pool
            self.db.add(player)
            created += 1
            existing_names.add(name)

        await self.db.flush()
        total = await self.count_free_agents()
        logger.info(f"[FreeAgency] Pool garantido: +{created} (total {total})")
        return {
            "created": created,
            "total": total,
            "message": f"Pool de free agents atualizado (+{created}).",
        }
