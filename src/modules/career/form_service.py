# -*- coding: utf-8 -*-
"""
Forma recente do jogador (últimas 5 notas de partida).

Redis: career:form:player:{player_id}
  - ratings: [{rating, note, match_id, minute, at}, ...]  (máx 5, mais recente por último)
  - avg: média aritmética
  - trend: UP | FLAT | DOWN
  - games: contagem
  - discontent: 0–100 (banco de reserva / sem minutos)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.redis_client import redis_client
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

MAX_RATINGS = 5


class FormService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _key(self, player_id: str) -> str:
        return f"career:form:player:{player_id}"

    async def get_form(self, player_id: str) -> Dict[str, Any]:
        data = await redis_client.get_generic(self._key(str(player_id)))
        if not isinstance(data, dict):
            return {
                "player_id": str(player_id),
                "ratings": [],
                "avg": None,
                "trend": "FLAT",
                "games": 0,
                "discontent": 0.0,
                "form_label": "—",
            }
        ratings = list(data.get("ratings") or [])[-MAX_RATINGS:]
        avg = self._avg(ratings)
        trend = self._trend(ratings)
        disc = float(data.get("discontent") or 0)
        return {
            "player_id": str(player_id),
            "ratings": ratings,
            "avg": avg,
            "trend": trend,
            "games": len(ratings),
            "discontent": round(disc, 1),
            "form_label": self._label(avg, disc),
            "last_rating": ratings[-1]["rating"] if ratings else None,
        }

    async def get_forms_bulk(self, player_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for pid in player_ids:
            out[str(pid)] = await self.get_form(pid)
        return out

    async def record_rating(
        self,
        player_id: str,
        *,
        rating: float,
        note: str = "",
        match_id: Optional[str] = None,
        played: bool = True,
    ) -> Dict[str, Any]:
        state = await redis_client.get_generic(self._key(str(player_id)))
        if not isinstance(state, dict):
            state = {"ratings": [], "discontent": 0.0}
        ratings = list(state.get("ratings") or [])
        if played:
            ratings.append(
                {
                    "rating": round(float(rating), 1),
                    "note": note or "",
                    "match_id": match_id,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            ratings = ratings[-MAX_RATINGS:]
            # Jogar reduz discontent
            disc = max(0.0, float(state.get("discontent") or 0) - 12.0)
        else:
            disc = clamp(float(state.get("discontent") or 0) + 8.0, 0.0, 100.0)
        state["ratings"] = ratings
        state["discontent"] = disc
        await redis_client.set_generic(self._key(str(player_id)), state)
        return await self.get_form(player_id)

    async def apply_match_ratings(
        self,
        player_ratings: List[Dict[str, Any]],
        *,
        match_id: Optional[str] = None,
        starter_ids: Optional[Sequence[str]] = None,
        roster_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """
        Grava ratings dos que jogaram e sobe discontent dos bancos (roster − starters).
        """
        played_ids = set()
        for r in player_ratings or []:
            pid = str(r.get("player_id") or "")
            if not pid:
                continue
            played_ids.add(pid)
            await self.record_rating(
                pid,
                rating=float(r.get("rating") or 5.0),
                note=str(r.get("note") or ""),
                match_id=match_id,
                played=True,
            )

        starters = set(str(x) for x in (starter_ids or played_ids))
        bench_events: List[str] = []
        for pid in roster_ids or []:
            sp = str(pid)
            if sp in starters or sp in played_ids:
                continue
            form = await self.record_rating(sp, rating=0, played=False)
            if form["discontent"] >= 40:
                bench_events.append(sp)
        return {
            "recorded": len(played_ids),
            "bench_discontent_ids": bench_events,
        }

    async def apply_bench_discontent_morale(
        self,
        team_id: str,
        roster_players: Sequence[Any],
        starter_ids: Sequence[str],
    ) -> List[str]:
        """
        Aplica hit de mental_fatigue / focus leve em bancos com discontent alto.
        Retorna nomes afetados.
        """
        affected: List[str] = []
        starter_set = set(str(x) for x in starter_ids)
        for p in roster_players:
            pid = str(getattr(p, "id", ""))
            if not pid or pid in starter_set:
                continue
            form = await self.get_form(pid)
            disc = float(form.get("discontent") or 0)
            if disc < 35:
                continue
            # Pressão crescente
            hit = 1.5 if disc < 55 else 3.0
            try:
                p.mental_fatigue = clamp(float(p.mental_fatigue or 0) + hit, 0, 100)
                if disc >= 55 and hasattr(p, "focus"):
                    p.focus = max(1, int(p.focus) - 1)
                affected.append(getattr(p, "name", pid))
            except Exception:
                pass
        return affected

    @staticmethod
    def _avg(ratings: List[Dict[str, Any]]) -> Optional[float]:
        if not ratings:
            return None
        vals = [float(r.get("rating") or 0) for r in ratings]
        return round(sum(vals) / len(vals), 2)

    @staticmethod
    def _trend(ratings: List[Dict[str, Any]]) -> str:
        if len(ratings) < 2:
            return "FLAT"
        recent = [float(r.get("rating") or 0) for r in ratings[-3:]]
        if len(recent) < 2:
            return "FLAT"
        delta = recent[-1] - recent[0]
        if delta >= 0.6:
            return "UP"
        if delta <= -0.6:
            return "DOWN"
        return "FLAT"

    @staticmethod
    def _label(avg: Optional[float], discontent: float) -> str:
        if discontent >= 60:
            return "Insatisfeito"
        if avg is None:
            return "Sem amostra"
        if avg >= 8.0:
            return "Em grande forma"
        if avg >= 7.0:
            return "Boa forma"
        if avg >= 6.0:
            return "Estável"
        if avg >= 5.0:
            return "Irregular"
        return "Má fase"
