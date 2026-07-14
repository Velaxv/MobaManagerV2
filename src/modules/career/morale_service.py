# -*- coding: utf-8 -*-
"""
Moral e chemistry do elenco (estilo FM + locker room de LoL).

Estado em Redis: career:morale:team:{id}
  - team_morale: 0–100 (humor geral)
  - chemistry: 0–100 (coesão tática / shotcalling)
  - bot_synergy, jg_mid_synergy: 0–100 (duos)
  - streak: vitórias/derrotas recentes
  - last_events: log curto

Efeitos:
  - Scrim/VOD/treino/rest/partida mexem nos números
  - chemistry alta → leve bônus de teamwork percebido
  - morale baixa → burnout mental sobe mais em dias pesados (opcional hook)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.redis_client import redis_client
from src.models.team import Team
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

DEFAULT_STATE = {
    "team_morale": 62.0,
    "chemistry": 55.0,
    "bot_synergy": 50.0,
    "jg_mid_synergy": 50.0,
    "win_streak": 0,
    "loss_streak": 0,
    "last_events": [],
}


class MoraleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _key(self, team_id: str) -> str:
        return f"career:morale:team:{team_id}"

    async def get_state(self, team_id: str) -> Dict[str, Any]:
        data = await redis_client.get_generic(self._key(str(team_id)))
        if not isinstance(data, dict):
            state = dict(DEFAULT_STATE)
            state["team_id"] = str(team_id)
            return state
        out = dict(DEFAULT_STATE)
        out.update(data)
        out["team_id"] = str(team_id)
        return out

    async def save_state(self, team_id: str, state: Dict[str, Any]) -> None:
        state = dict(state)
        state["team_id"] = str(team_id)
        # trim events
        ev = state.get("last_events") or []
        if len(ev) > 12:
            state["last_events"] = ev[-12:]
        await redis_client.set_generic(self._key(str(team_id)), state)

    def _push_event(self, state: Dict[str, Any], text: str, kind: str = "info") -> None:
        ev = list(state.get("last_events") or [])
        ev.append({"text": text, "kind": kind})
        state["last_events"] = ev[-12:]

    async def apply_delta(
        self,
        team_id: str,
        *,
        morale: float = 0.0,
        chemistry: float = 0.0,
        bot_synergy: float = 0.0,
        jg_mid_synergy: float = 0.0,
        event: Optional[str] = None,
        kind: str = "info",
    ) -> Dict[str, Any]:
        state = await self.get_state(team_id)
        state["team_morale"] = clamp(float(state.get("team_morale") or 62) + morale, 0.0, 100.0)
        state["chemistry"] = clamp(float(state.get("chemistry") or 55) + chemistry, 0.0, 100.0)
        state["bot_synergy"] = clamp(float(state.get("bot_synergy") or 50) + bot_synergy, 0.0, 100.0)
        state["jg_mid_synergy"] = clamp(
            float(state.get("jg_mid_synergy") or 50) + jg_mid_synergy, 0.0, 100.0
        )
        if event:
            self._push_event(state, event, kind)
        await self.save_state(team_id, state)
        return state

    async def on_match_result(
        self,
        team_id: str,
        *,
        won: bool,
        is_playoff: bool = False,
        opponent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = await self.get_state(team_id)
        opp = opponent_name or "oponente"
        if won:
            m = 6.0 if is_playoff else 4.0
            c = 3.0 if is_playoff else 2.0
            state["win_streak"] = int(state.get("win_streak") or 0) + 1
            state["loss_streak"] = 0
            # streak bonus
            m += min(4.0, state["win_streak"] * 0.8)
            msg = f"Vitória vs {opp} elevou o moral (+{m:.0f})"
            kind = "good"
        else:
            m = -7.0 if is_playoff else -5.0
            c = -2.5 if is_playoff else -1.5
            state["loss_streak"] = int(state.get("loss_streak") or 0) + 1
            state["win_streak"] = 0
            m -= min(4.0, state["loss_streak"] * 0.7)
            msg = f"Derrota vs {opp} abalou o elenco ({m:.0f})"
            kind = "bad"

        state["team_morale"] = clamp(float(state["team_morale"]) + m, 0.0, 100.0)
        state["chemistry"] = clamp(float(state["chemistry"]) + c, 0.0, 100.0)
        # vitórias solidificam bot e jg-mid levemente
        if won:
            state["bot_synergy"] = clamp(float(state["bot_synergy"]) + 1.5, 0.0, 100.0)
            state["jg_mid_synergy"] = clamp(float(state["jg_mid_synergy"]) + 1.5, 0.0, 100.0)
        self._push_event(state, msg, kind)
        await self.save_state(team_id, state)
        return state

    async def on_rest_day(self, team_id: str) -> Dict[str, Any]:
        return await self.apply_delta(
            team_id,
            morale=2.5,
            chemistry=1.0,
            event="Dia de descanso: elenco recuperou o humor",
            kind="good",
        )

    async def on_hard_training(self, team_id: str) -> Dict[str, Any]:
        return await self.apply_delta(
            team_id,
            morale=-1.5,
            chemistry=2.0,
            event="Treino intenso: cansa, mas melhora a coesão",
            kind="mixed",
        )

    def public_view(self, state: Dict[str, Any], team_name: Optional[str] = None) -> Dict[str, Any]:
        morale = float(state.get("team_morale") or 0)
        chem = float(state.get("chemistry") or 0)
        if morale >= 75:
            morale_label = "Alto"
        elif morale >= 50:
            morale_label = "Estável"
        elif morale >= 30:
            morale_label = "Baixo"
        else:
            morale_label = "Crítico"

        if chem >= 70:
            chem_label = "Sincronizado"
        elif chem >= 50:
            chem_label = "Ok"
        elif chem >= 35:
            chem_label = "Frouxo"
        else:
            chem_label = "Desconectado"

        return {
            "team_id": state.get("team_id"),
            "team_name": team_name,
            "team_morale": round(morale, 1),
            "chemistry": round(chem, 1),
            "bot_synergy": round(float(state.get("bot_synergy") or 0), 1),
            "jg_mid_synergy": round(float(state.get("jg_mid_synergy") or 0), 1),
            "morale_label": morale_label,
            "chemistry_label": chem_label,
            "win_streak": int(state.get("win_streak") or 0),
            "loss_streak": int(state.get("loss_streak") or 0),
            "last_events": list(state.get("last_events") or [])[-6:],
            # bônus derivados para UI / motor
            "match_focus_bonus": round(clamp((morale - 50) / 100.0 * 0.08, -0.06, 0.08), 3),
            "draft_teamwork_hint": round(clamp((chem - 50) / 100.0 * 0.1, -0.05, 0.1), 3),
        }

    async def get_public(self, team_id: str) -> Dict[str, Any]:
        team = await self.db.get(Team, __import__("uuid").UUID(str(team_id)))
        state = await self.get_state(team_id)
        return self.public_view(state, team.name if team else None)
