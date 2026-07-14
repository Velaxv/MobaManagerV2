# -*- coding: utf-8 -*-
"""
Organização (S4): sponsors, board confidence e facility.

Estado Redis: career:org:team:{id}
  - board_confidence 0–100
  - board_goal: PLAYOFFS | TOP4 | TITLE | MID_TABLE
  - sponsors: lista ativa
  - facility_level: 1–3
  - brand: 0–100 (simples)
  - fired: bool (game-over soft)
  - last_events: []

Facility bônus:
  1 base
  2 scrim room → +chemistry em scrim (via practice hook)
  3 analyst+recovery → VOD melhor + rest morale extra

Sponsors:
  - monthly_payout no tick financeiro
  - goals avaliados no fim de split / mensal por standings
"""

from __future__ import annotations

import logging
import random
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.redis_client import redis_client
from src.models.league import League, LeagueTeam
from src.models.team import Team
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

BOARD_GOALS = ("MID_TABLE", "PLAYOFFS", "TOP4", "TITLE")
GOAL_LABELS = {
    "MID_TABLE": "Evitar zona inferior (top 6 ok)",
    "PLAYOFFS": "Classificar aos playoffs (top 6)",
    "TOP4": "Terminar no top 4 da regular",
    "TITLE": "Campeão do split",
}

FACILITY_LEVELS = {
    1: {
        "name": "Gaming house básica",
        "monthly_cost": 5000,
        "upgrade_cost": 0,
        "scrim_chem_bonus": 0.0,
        "vod_conf_bonus": 0.0,
        "rest_morale_bonus": 0.0,
        "scout_mult_bonus": 0.0,
    },
    2: {
        "name": "Scrim Room",
        "monthly_cost": 12000,
        "upgrade_cost": 180000,
        "scrim_chem_bonus": 1.5,
        "vod_conf_bonus": 0.05,
        "rest_morale_bonus": 0.5,
        "scout_mult_bonus": 0.02,
    },
    3: {
        "name": "HQ Pro (analyst + recovery)",
        "monthly_cost": 22000,
        "upgrade_cost": 400000,
        "scrim_chem_bonus": 2.5,
        "vod_conf_bonus": 0.12,
        "rest_morale_bonus": 2.0,
        "scout_mult_bonus": 0.05,
    },
}

SPONSOR_TEMPLATES = [
    {"name": "HyperX Kit", "tier": "C", "base": 8000, "goal": "MID_TABLE"},
    {"name": "Local Telecom", "tier": "C", "base": 10000, "goal": "PLAYOFFS"},
    {"name": "Energy Drink BR", "tier": "B", "base": 18000, "goal": "PLAYOFFS"},
    {"name": "Bank Partner", "tier": "B", "base": 25000, "goal": "TOP4"},
    {"name": "Global Soft", "tier": "A", "base": 40000, "goal": "TOP4"},
    {"name": "Title Sponsor", "tier": "S", "base": 65000, "goal": "TITLE"},
]


def _default_org(team_id: str) -> Dict[str, Any]:
    return {
        "team_id": str(team_id),
        "board_confidence": 62.0,
        "board_goal": "PLAYOFFS",
        "facility_level": 1,
        "brand": 45.0,
        "fired": False,
        "sponsors": [],
        "last_events": [],
        "months_under_goal": 0,
    }


class OrgService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _key(self, team_id: str) -> str:
        return f"career:org:team:{team_id}"

    async def get_state(self, team_id: str) -> Dict[str, Any]:
        data = await redis_client.get_generic(self._key(str(team_id)))
        if not isinstance(data, dict):
            state = _default_org(team_id)
            # starter sponsors
            state["sponsors"] = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Starter Merch Co",
                    "tier": "C",
                    "monthly_payout": 12000,
                    "goal": "PLAYOFFS",
                    "active": True,
                    "months_left": 6,
                }
            ]
            await self.save_state(team_id, state)
            return state
        out = _default_org(team_id)
        out.update(data)
        return out

    async def save_state(self, team_id: str, state: Dict[str, Any]) -> None:
        state = dict(state)
        state["team_id"] = str(team_id)
        ev = state.get("last_events") or []
        if len(ev) > 15:
            state["last_events"] = ev[-15:]
        await redis_client.set_generic(self._key(str(team_id)), state)

    def _push(self, state: Dict[str, Any], text: str, kind: str = "info") -> None:
        ev = list(state.get("last_events") or [])
        ev.append({"text": text, "kind": kind})
        state["last_events"] = ev[-15:]

    def facility_info(self, level: int) -> Dict[str, Any]:
        lv = max(1, min(3, int(level or 1)))
        info = dict(FACILITY_LEVELS[lv])
        info["level"] = lv
        next_lv = lv + 1 if lv < 3 else None
        info["next_level"] = next_lv
        info["next_upgrade_cost"] = (
            FACILITY_LEVELS[next_lv]["upgrade_cost"] if next_lv else None
        )
        info["next_name"] = FACILITY_LEVELS[next_lv]["name"] if next_lv else None
        return info

    async def ensure_initialized(self, team_id: str) -> Dict[str, Any]:
        return await self.get_state(team_id)

    async def get_public(self, team_id: str) -> Dict[str, Any]:
        team = await self.db.get(Team, uuid.UUID(str(team_id)))
        state = await self.get_state(team_id)
        conf = float(state.get("board_confidence") or 0)
        if conf >= 75:
            conf_label = "Sólida"
        elif conf >= 50:
            conf_label = "Estável"
        elif conf >= 30:
            conf_label = "Tensa"
        else:
            conf_label = "Crítica"

        fac = self.facility_info(int(state.get("facility_level") or 1))
        sponsors = [s for s in (state.get("sponsors") or []) if s.get("active")]
        sponsor_income = sum(float(s.get("monthly_payout") or 0) for s in sponsors)
        goal = state.get("board_goal") or "PLAYOFFS"

        return {
            "team_id": str(team_id),
            "team_name": team.name if team else None,
            "board_confidence": round(conf, 1),
            "board_confidence_label": conf_label,
            "board_goal": goal,
            "board_goal_label": GOAL_LABELS.get(goal, goal),
            "goals_available": [
                {"id": g, "label": GOAL_LABELS[g]} for g in BOARD_GOALS
            ],
            "facility": fac,
            "brand": round(float(state.get("brand") or 0), 1),
            "sponsors": sponsors,
            "sponsor_monthly_income": sponsor_income,
            "facility_monthly_cost": fac["monthly_cost"],
            "org_monthly_net_extra": sponsor_income - fac["monthly_cost"],
            "fired": bool(state.get("fired")),
            "months_under_goal": int(state.get("months_under_goal") or 0),
            "last_events": list(state.get("last_events") or [])[-8:],
            "sponsor_offers": self._generate_offers(state),
        }

    def _generate_offers(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        brand = float(state.get("brand") or 45)
        active_names = {s.get("name") for s in (state.get("sponsors") or []) if s.get("active")}
        rng = random.Random(f"offers-{state.get('team_id')}-{int(brand)}")
        offers = []
        for tpl in SPONSOR_TEMPLATES:
            if tpl["name"] in active_names:
                continue
            # brand filter
            if tpl["tier"] == "S" and brand < 70:
                continue
            if tpl["tier"] == "A" and brand < 55:
                continue
            mult = 0.85 + brand / 200.0
            payout = int(tpl["base"] * mult / 500) * 500
            offers.append(
                {
                    "offer_id": f"{tpl['name']}-{tpl['goal']}",
                    "name": tpl["name"],
                    "tier": tpl["tier"],
                    "monthly_payout": payout,
                    "goal": tpl["goal"],
                    "goal_label": GOAL_LABELS.get(tpl["goal"], tpl["goal"]),
                    "months": 4 if tpl["tier"] in ("C", "B") else 6,
                }
            )
        rng.shuffle(offers)
        return offers[:4]

    async def set_board_goal(self, team_id: str, goal: str) -> Dict[str, Any]:
        goal = (goal or "PLAYOFFS").upper()
        if goal not in BOARD_GOALS:
            raise ValueError(f"Meta inválida. Use: {', '.join(BOARD_GOALS)}")
        state = await self.get_state(team_id)
        if state.get("fired"):
            raise ValueError("Você foi demitido — inicie nova carreira.")
        old = state.get("board_goal")
        state["board_goal"] = goal
        # meta mais ambiciosa: board confia mais; mais fácil: leve queda
        order = list(BOARD_GOALS)
        if order.index(goal) > order.index(old or "PLAYOFFS"):
            state["board_confidence"] = clamp(
                float(state["board_confidence"]) + 4, 0, 100
            )
            self._push(state, f"Board aceitou meta ambiciosa: {GOAL_LABELS[goal]}", "good")
        elif order.index(goal) < order.index(old or "PLAYOFFS"):
            state["board_confidence"] = clamp(
                float(state["board_confidence"]) - 3, 0, 100
            )
            self._push(state, f"Board frustrou-se com meta reduzida: {GOAL_LABELS[goal]}", "bad")
        else:
            self._push(state, f"Meta mantida: {GOAL_LABELS[goal]}", "info")
        await self.save_state(team_id, state)
        return await self.get_public(team_id)

    async def accept_sponsor(self, team_id: str, offer_id: str) -> Dict[str, Any]:
        state = await self.get_state(team_id)
        if state.get("fired"):
            raise ValueError("Demitido — sem poder de assinatura.")
        offers = self._generate_offers(state)
        offer = next((o for o in offers if o["offer_id"] == offer_id), None)
        if not offer:
            # tenta match por nome
            offer = next((o for o in offers if o["name"] in (offer_id or "")), None)
        if not offer:
            raise ValueError("Oferta de sponsor não disponível.")

        active = [s for s in (state.get("sponsors") or []) if s.get("active")]
        if len(active) >= 4:
            raise ValueError("Máximo de 4 sponsors ativos. Encerre um contrato.")

        sponsor = {
            "id": str(uuid.uuid4()),
            "name": offer["name"],
            "tier": offer["tier"],
            "monthly_payout": offer["monthly_payout"],
            "goal": offer["goal"],
            "active": True,
            "months_left": offer["months"],
        }
        sponsors = list(state.get("sponsors") or [])
        sponsors.append(sponsor)
        state["sponsors"] = sponsors
        state["brand"] = clamp(float(state.get("brand") or 45) + 3, 0, 100)
        self._push(
            state,
            f"Sponsor {sponsor['name']}: +€{sponsor['monthly_payout']}/mês "
            f"(meta {GOAL_LABELS.get(sponsor['goal'], sponsor['goal'])})",
            "good",
        )
        await self.save_state(team_id, state)
        return await self.get_public(team_id)

    async def drop_sponsor(self, team_id: str, sponsor_id: str) -> Dict[str, Any]:
        state = await self.get_state(team_id)
        sponsors = list(state.get("sponsors") or [])
        found = False
        for s in sponsors:
            if str(s.get("id")) == str(sponsor_id) and s.get("active"):
                s["active"] = False
                found = True
                self._push(state, f"Contrato com {s.get('name')} encerrado.", "mixed")
                state["board_confidence"] = clamp(
                    float(state["board_confidence"]) - 2, 0, 100
                )
        if not found:
            raise ValueError("Sponsor não encontrado.")
        state["sponsors"] = sponsors
        await self.save_state(team_id, state)
        return await self.get_public(team_id)

    async def upgrade_facility(self, team_id: str) -> Dict[str, Any]:
        team = await self.db.get(Team, uuid.UUID(str(team_id)))
        if not team:
            raise ValueError("Time não encontrado.")
        state = await self.get_state(team_id)
        if state.get("fired"):
            raise ValueError("Demitido.")
        lv = int(state.get("facility_level") or 1)
        if lv >= 3:
            raise ValueError("Facility já no nível máximo.")
        cost = Decimal(str(FACILITY_LEVELS[lv + 1]["upgrade_cost"]))
        try:
            team.deduct_budget(cost, operation="upgrade de facility")
        except Exception as e:
            raise ValueError(str(e)) from e
        state["facility_level"] = lv + 1
        state["brand"] = clamp(float(state.get("brand") or 45) + 5, 0, 100)
        name = FACILITY_LEVELS[lv + 1]["name"]
        self._push(
            state,
            f"Upgrade de sede → Nv.{lv + 1} {name} (−€{int(cost):,})",
            "good",
        )
        await self.save_state(team_id, state)
        await self.db.flush()
        pub = await self.get_public(team_id)
        pub["team_budget"] = float(team.budget)
        return pub

    async def monthly_finance_delta(self, team_id: str) -> Dict[str, Any]:
        """
        Retorna {sponsor_income, facility_cost, net} e aplica months_left nos sponsors.
        Não altera budget — FinanceService aplica.
        """
        state = await self.get_state(team_id)
        fac = self.facility_info(int(state.get("facility_level") or 1))
        sponsors = list(state.get("sponsors") or [])
        income = 0.0
        for s in sponsors:
            if not s.get("active"):
                continue
            income += float(s.get("monthly_payout") or 0)
            left = int(s.get("months_left") or 0) - 1
            s["months_left"] = left
            if left <= 0:
                s["active"] = False
                self._push(state, f"Sponsor {s.get('name')} expirou.", "mixed")
        state["sponsors"] = sponsors
        cost = float(fac["monthly_cost"])
        await self.save_state(team_id, state)
        return {
            "sponsor_income": income,
            "facility_cost": cost,
            "net": income - cost,
            "facility_level": fac["level"],
        }

    async def on_match_result(
        self,
        team_id: str,
        *,
        won: bool,
        is_playoff: bool = False,
    ) -> Dict[str, Any]:
        state = await self.get_state(team_id)
        if state.get("fired"):
            return state
        delta = 3.5 if won else -4.0
        if is_playoff:
            delta *= 1.4
        state["board_confidence"] = clamp(
            float(state["board_confidence"]) + delta, 0, 100
        )
        state["brand"] = clamp(
            float(state.get("brand") or 45) + (2.0 if won else -1.0), 0, 100
        )
        self._push(
            state,
            ("Board satisfeita com a vitória" if won else "Board preocupada com a derrota")
            + (" (playoff)" if is_playoff else ""),
            "good" if won else "bad",
        )
        await self._check_firing(state, team_id)
        await self.save_state(team_id, state)
        return state

    async def evaluate_standings_pressure(
        self, team_id: str, league_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Chamado no tick mensal: pressão por posição vs meta."""
        state = await self.get_state(team_id)
        if state.get("fired"):
            return state

        rank = await self._team_rank(team_id, league_id)
        goal = state.get("board_goal") or "PLAYOFFS"
        ok = False
        if rank is None:
            await self.save_state(team_id, state)
            return state

        if goal == "MID_TABLE":
            ok = rank <= 6
        elif goal == "PLAYOFFS":
            ok = rank <= 6
        elif goal == "TOP4":
            ok = rank <= 4
        elif goal == "TITLE":
            ok = rank == 1

        if ok:
            state["months_under_goal"] = 0
            state["board_confidence"] = clamp(
                float(state["board_confidence"]) + 2.5, 0, 100
            )
            self._push(
                state,
                f"Meta no caminho: #{rank} (objetivo {GOAL_LABELS.get(goal, goal)})",
                "good",
            )
        else:
            state["months_under_goal"] = int(state.get("months_under_goal") or 0) + 1
            pen = 4.0 + state["months_under_goal"] * 1.5
            state["board_confidence"] = clamp(
                float(state["board_confidence"]) - pen, 0, 100
            )
            self._push(
                state,
                f"Fora da meta: #{rank} · pressão board −{pen:.0f}",
                "bad",
            )
            # sponsors com goal falhando: aviso
            for s in state.get("sponsors") or []:
                if s.get("active") and s.get("goal") == goal and not ok:
                    self._push(
                        state,
                        f"{s.get('name')} ameaça revisar o contrato",
                        "bad",
                    )

        await self._check_firing(state, team_id)
        await self.save_state(team_id, state)
        return state

    async def _team_rank(
        self, team_id: str, league_id: Optional[str] = None
    ) -> Optional[int]:
        if league_id:
            q = await self.db.execute(
                select(LeagueTeam).where(LeagueTeam.league_id == uuid.UUID(str(league_id)))
            )
        else:
            q = await self.db.execute(select(LeagueTeam))
        rows = list(q.scalars().all())
        if not rows:
            return None
        # filter same league as team
        my = [r for r in rows if str(r.team_id) == str(team_id)]
        if not my:
            return None
        lid = my[0].league_id
        peers = [r for r in rows if r.league_id == lid]
        peers.sort(key=lambda lt: (lt.points, lt.wins, -lt.losses), reverse=True)
        for i, r in enumerate(peers, start=1):
            if str(r.team_id) == str(team_id):
                return i
        return None

    async def _check_firing(self, state: Dict[str, Any], team_id: str) -> None:
        conf = float(state.get("board_confidence") or 0)
        if conf <= 15 and not state.get("fired"):
            state["fired"] = True
            self._push(
                state,
                "DEMISSÃO: a diretoria encerrou o projeto com você.",
                "bad",
            )
            logger.warning(f"[Org] Manager demitido do time {team_id}")

    async def on_champion(self, team_id: str) -> None:
        state = await self.get_state(team_id)
        state["board_confidence"] = clamp(float(state["board_confidence"]) + 25, 0, 100)
        state["brand"] = clamp(float(state.get("brand") or 45) + 15, 0, 100)
        self._push(state, "Título! Board e sponsors em êxtase.", "good")
        await self.save_state(team_id, state)

    def facility_bonuses(self, state: Dict[str, Any]) -> Dict[str, float]:
        fac = self.facility_info(int(state.get("facility_level") or 1))
        return {
            "scrim_chem_bonus": float(fac["scrim_chem_bonus"]),
            "vod_conf_bonus": float(fac["vod_conf_bonus"]),
            "rest_morale_bonus": float(fac["rest_morale_bonus"]),
            "scout_mult_bonus": float(fac["scout_mult_bonus"]),
        }
