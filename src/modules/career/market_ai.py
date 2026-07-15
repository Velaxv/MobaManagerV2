# -*- coding: utf-8 -*-
"""
IA de mercado dos rivais (Sprint G / MK-1).

Na janela aberta, times não-controlados fazem 1–2 movimentos por semana:
  - Assinam free agents se houver
  - Na offseason (OPEN_FULL), compram reservas/academy baratos de outras orgs

Idempotente por fase+semana (Redis).
"""

from __future__ import annotations

import hashlib
import logging
import random
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.redis_client import redis_client
from src.models.player import Player
from src.models.team import Team
from src.modules.career.market_window import MarketWindowService
from src.modules.career.transfer_service import TransferService, compute_valuation
from src.shared.enums import ContractStatus, PlayerRole

logger = logging.getLogger(__name__)

ACTIVE = (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL)
ROLES = [PlayerRole.TOP, PlayerRole.JUNGLE, PlayerRole.MID, PlayerRole.BOT, PlayerRole.SUPPORT]


class MarketAIService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _week_key(self, phase: str, week: int) -> str:
        return f"market:ai:done:{phase}:{int(week)}"

    def _rng(self, phase: str, week: int) -> random.Random:
        seed = int(hashlib.md5(f"{phase}:{week}:market_ai".encode()).hexdigest()[:8], 16)
        return random.Random(seed)

    async def process_week_if_needed(
        self,
        *,
        managed_team_id: Optional[str] = None,
        week: Optional[int] = None,
        phase: Optional[str] = None,
        max_moves: int = 2,
    ) -> Dict[str, Any]:
        window = await MarketWindowService(self.db).get_status()
        if not window.get("is_open"):
            return {"skipped": True, "reason": "window_closed", "moves": []}

        ph = phase or window.get("phase") or "OFFSEASON"
        w = int(week if week is not None else (window.get("week") or 0))
        key = self._week_key(ph, w)
        already = await redis_client.get_generic(key)
        if already:
            return {
                "skipped": True,
                "reason": "already_ran",
                "moves": already.get("moves") if isinstance(already, dict) else [],
            }

        moves = await self._simulate_moves(
            managed_team_id=managed_team_id,
            window_mode=window.get("mode") or "CLOSED",
            phase=ph,
            week=w,
            max_moves=max_moves,
        )
        payload = {
            "skipped": False,
            "phase": ph,
            "week": w,
            "mode": window.get("mode"),
            "moves": moves,
            "count": len(moves),
        }
        await redis_client.set_generic(key, payload)
        if moves:
            logger.info(
                "[MarketAI] %s moves na semana %s (%s): %s",
                len(moves),
                w,
                ph,
                "; ".join(m.get("summary", "") for m in moves),
            )
        return payload

    async def _simulate_moves(
        self,
        *,
        managed_team_id: Optional[str],
        window_mode: str,
        phase: str,
        week: int,
        max_moves: int,
    ) -> List[Dict[str, Any]]:
        rng = self._rng(phase, week)
        teams = list((await self.db.execute(select(Team))).scalars().all())
        if not teams:
            return []

        managed = str(managed_team_id) if managed_team_id else None
        rivals = [t for t in teams if str(t.id) != managed]
        rng.shuffle(rivals)

        # Free agents
        fa_q = await self.db.execute(
            select(Player)
            .where(Player.team_id.is_(None))
            .options(selectinload(Player.contracts))
        )
        free_agents = list(fa_q.scalars().all())

        # Candidatos a venda: reservas/academy (não starter) de times rivais
        sale_pool: List[Player] = []
        if window_mode == "OPEN_FULL":
            sale_q = await self.db.execute(
                select(Player)
                .where(Player.team_id.is_not(None))
                .options(selectinload(Player.contracts))
            )
            for p in sale_q.scalars().all():
                if managed and str(p.team_id) == managed:
                    continue
                if bool(getattr(p, "is_starter", False)):
                    continue
                ca = int(p.current_ability or 0)
                if ca < 90 or ca > 130:
                    continue
                sale_pool.append(p)

        moves: List[Dict[str, Any]] = []
        used_players: set = set()
        transfer = TransferService(self.db)

        for buyer in rivals:
            if len(moves) >= max_moves:
                break
            budget = float(buyer.budget or 0)
            if budget < 80_000:
                continue

            # Role mais fraca do elenco do comprador
            weak_role = await self._weakest_role(str(buyer.id))
            candidate: Optional[Player] = None
            is_fa = True

            # Prefer FA do role fraco
            role_fas = [
                p
                for p in free_agents
                if str(p.id) not in used_players
                and (p.role == weak_role or True)
            ]
            role_fas.sort(
                key=lambda p: (
                    0 if p.role == weak_role else 1,
                    -int(p.current_ability or 0),
                )
            )
            if role_fas:
                # Escolhe entre top 3
                pick_from = role_fas[: min(3, len(role_fas))]
                candidate = rng.choice(pick_from)
                is_fa = True
            elif window_mode == "OPEN_FULL" and sale_pool:
                pool = [
                    p
                    for p in sale_pool
                    if str(p.id) not in used_players
                    and str(p.team_id) != str(buyer.id)
                ]
                pool.sort(
                    key=lambda p: (
                        0 if p.role == weak_role else 1,
                        int(p.current_ability or 0),
                    )
                )
                if pool:
                    candidate = rng.choice(pool[: min(4, len(pool))])
                    is_fa = False

            if not candidate:
                continue

            contract = None
            for c in candidate.contracts or []:
                if c.status in ACTIVE:
                    contract = c
                    break
            val = compute_valuation(candidate, contract)
            fee = float(val["min_fee"]) * (1.0 if is_fa else 0.95)
            # Rivais pagam o mínimo + folga pequena
            fee = min(fee * 1.02, budget * 0.35)
            sal = float(val["min_salary"]) * 1.05
            seasons = int(val["preferred_seasons"] or 2)

            if fee > budget:
                continue

            try:
                result = await transfer.complete_transfer(
                    str(buyer.id),
                    str(candidate.id),
                    transfer_fee=fee,
                    monthly_salary=sal,
                    seasons=seasons,
                    skip_negotiation=True,
                )
            except Exception as exc:
                logger.debug(
                    "[MarketAI] falha %s → %s: %s",
                    candidate.name,
                    buyer.abbreviation,
                    exc,
                )
                continue

            used_players.add(str(candidate.id))
            if is_fa and candidate in free_agents:
                free_agents.remove(candidate)
            if candidate in sale_pool:
                sale_pool.remove(candidate)

            summary = (
                f"{buyer.abbreviation} contratou {candidate.name} "
                f"({candidate.role.value if hasattr(candidate.role, 'value') else candidate.role}) "
                f"{'FA' if is_fa else 'transfer'} €{int(fee):,}"
            )
            moves.append(
                {
                    "buyer_team_id": str(buyer.id),
                    "buyer_abbr": buyer.abbreviation,
                    "player_id": str(candidate.id),
                    "player_name": candidate.name,
                    "role": (
                        candidate.role.value
                        if hasattr(candidate.role, "value")
                        else str(candidate.role)
                    ),
                    "is_free_agent": is_fa,
                    "transfer_fee": float(result.get("transfer_fee") or fee),
                    "monthly_salary": float(result.get("monthly_salary") or sal),
                    "summary": summary,
                }
            )

        await self.db.flush()
        return moves

    async def _weakest_role(self, team_id: str) -> PlayerRole:
        q = await self.db.execute(
            select(Player).where(Player.team_id == uuid.UUID(team_id))
        )
        players = list(q.scalars().all())
        best: Dict[PlayerRole, int] = {r: 0 for r in ROLES}
        for p in players:
            role = p.role if isinstance(p.role, PlayerRole) else PlayerRole(str(p.role))
            ca = int(p.current_ability or 0)
            if ca > best.get(role, 0):
                best[role] = ca
        # Role com menor CA de "melhor jogador"
        return min(ROLES, key=lambda r: best.get(r, 0))
