# -*- coding: utf-8 -*-
"""
Janela de transferências por fase da temporada (estilo FM + offseason LoL).

Regras:
  OFFSEASON  → OPEN_FULL (compras entre times + free agents)
  PRESEASON  → OPEN_FA_ONLY (só free agents / liberados)
  REGULAR    → OPEN_FA_ONLY (mercado mid-split limitado a FA)
  PLAYOFFS   → CLOSED
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.league import League
from src.shared.enums import SplitPhase

# phase -> window mode
WINDOW_BY_PHASE = {
    SplitPhase.OFFSEASON.value: "OPEN_FULL",
    SplitPhase.PRESEASON.value: "OPEN_FA_ONLY",
    SplitPhase.REGULAR_SEASON.value: "OPEN_FA_ONLY",
    SplitPhase.PLAYOFFS.value: "CLOSED",
}

WINDOW_LABELS = {
    "OPEN_FULL": "Janela aberta (mercado completo)",
    "OPEN_FA_ONLY": "Janela parcial (apenas free agents)",
    "CLOSED": "Janela fechada",
}


class MarketWindowService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_league(self) -> Optional[League]:
        result = await self.db.execute(select(League).limit(1))
        return result.scalar_one_or_none()

    async def get_status(self) -> Dict[str, Any]:
        league = await self.get_league()
        phase = (
            league.current_phase.value
            if league and league.current_phase
            else SplitPhase.OFFSEASON.value
        )
        mode = WINDOW_BY_PHASE.get(phase, "CLOSED")
        return {
            "phase": phase,
            "mode": mode,
            "label": WINDOW_LABELS.get(mode, mode),
            "can_buy_from_clubs": mode == "OPEN_FULL",
            "can_sign_free_agents": mode in ("OPEN_FULL", "OPEN_FA_ONLY"),
            "is_open": mode != "CLOSED",
            "league_id": str(league.id) if league else None,
            "week": league.current_week if league else 0,
            "rules": {
                "OPEN_FULL": "Offseason: transferências entre orgs + free agents.",
                "OPEN_FA_ONLY": "Temporada/pré-season: só agentes livres (sem buyout).",
                "CLOSED": "Playoffs: mercado fechado.",
            },
        }

    async def assert_can_transfer(
        self,
        *,
        is_free_agent: bool,
        seller_team_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Levanta ValueError se a operação não for permitida na janela atual.
        """
        status = await self.get_status()
        mode = status["mode"]
        if mode == "CLOSED":
            raise ValueError(
                "Janela de transferências fechada (playoffs). "
                "Aguarde a offseason para movimentar o elenco."
            )
        if is_free_agent:
            if not status["can_sign_free_agents"]:
                raise ValueError("Assinatura de free agents não permitida nesta fase.")
            return status
        # Transferência entre clubes
        if not status["can_buy_from_clubs"]:
            raise ValueError(
                "Transferências entre times só na offseason. "
                "Durante o split, contrate free agents ou aguarde a janela completa."
            )
        return status
