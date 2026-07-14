# -*- coding: utf-8 -*-
"""
Treino e desenvolvimento de elenco (CA → PA).

Regras MVP:
  - Foco de treino por time: BALANCED | MECHANICS | MENTAL | TEAMPLAY | ROLE
  - Intensidade: LIGHT | NORMAL | HARD (HARD acelera ganho e cansa mais)
  - Dias TRAINING/SCRIM: roster inteiro tem chance de evoluir
  - MATCH_DAY / match XP: só titulares (uso real)
  - CA sobe no máximo +1 por sessão; nunca ultrapassa PA
  - Rookies e jovens crescem mais; burnout alto freia; coachability ajuda
  - Plano de treino em Redis: training:team:{id}
"""

from __future__ import annotations

import logging
import random
import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.redis_client import redis_client
from src.models.player import Player
from src.models.team import Team
from src.shared.enums import CalendarDayType
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

FOCUSES = ("BALANCED", "MECHANICS", "MENTAL", "TEAMPLAY", "ROLE")
INTENSITIES = ("LIGHT", "NORMAL", "HARD")

# Atributos mentais/técnicos afetados por cada foco (escala 1–20)
FOCUS_ATTRS: Dict[str, List[str]] = {
    "BALANCED": ["mechanics", "focus", "teamwork"],
    "MECHANICS": ["mechanics"],
    "MENTAL": ["focus", "resilience", "coachability"],
    "TEAMPLAY": ["teamwork", "focus"],
    "ROLE": ["mechanics", "focus"],  # domínio de role = mecânica + foco
}

DAY_MULT = {
    CalendarDayType.TRAINING.value: 1.0,
    CalendarDayType.SCRIM.value: 1.25,
    CalendarDayType.MATCH_DAY.value: 0.6,
    "MATCH_XP": 0.75,  # pós-live / auto-sim titular
}

INTENSITY_CFG = {
    "LIGHT": {"gain": 0.75, "extra_burnout": 0.0},
    "NORMAL": {"gain": 1.0, "extra_burnout": 0.0},
    "HARD": {"gain": 1.35, "extra_burnout": 2.5},
}

FOCUS_CA_WEIGHT = {
    "BALANCED": 1.0,
    "MECHANICS": 0.9,
    "MENTAL": 0.85,
    "TEAMPLAY": 0.85,
    "ROLE": 1.1,
}


def normalize_focus(focus: Optional[str]) -> str:
    f = (focus or "BALANCED").upper().strip()
    return f if f in FOCUSES else "BALANCED"


def normalize_intensity(intensity: Optional[str]) -> str:
    i = (intensity or "NORMAL").upper().strip()
    return i if i in INTENSITIES else "NORMAL"


class TrainingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _plan_key(self, team_id: str) -> str:
        return f"training:team:{team_id}"

    def _log_key(self, team_id: str) -> str:
        return f"training:team:{team_id}:last"

    async def get_plan(self, team_id: str) -> Dict[str, Any]:
        data = await redis_client.get_generic(self._plan_key(str(team_id)))
        if not isinstance(data, dict):
            return {
                "team_id": str(team_id),
                "focus": "BALANCED",
                "intensity": "NORMAL",
                "source": "default",
            }
        return {
            "team_id": str(team_id),
            "focus": normalize_focus(data.get("focus")),
            "intensity": normalize_intensity(data.get("intensity")),
            "source": "saved",
        }

    async def set_plan(
        self,
        team_id: str,
        focus: str = "BALANCED",
        intensity: str = "NORMAL",
    ) -> Dict[str, Any]:
        tid = str(team_id)
        team = await self.db.get(Team, uuid.UUID(tid))
        if not team:
            raise ValueError("Time não encontrado.")
        plan = {
            "team_id": tid,
            "focus": normalize_focus(focus),
            "intensity": normalize_intensity(intensity),
        }
        await redis_client.set_generic(self._plan_key(tid), plan)
        return {**plan, "source": "saved", "team_name": team.name}

    async def get_last_session(self, team_id: str) -> Optional[Dict[str, Any]]:
        data = await redis_client.get_generic(self._log_key(str(team_id)))
        return data if isinstance(data, dict) else None

    async def get_status(self, team_id: str) -> Dict[str, Any]:
        plan = await self.get_plan(team_id)
        last = await self.get_last_session(team_id)
        team = await self.db.get(Team, uuid.UUID(str(team_id)))
        if not team:
            raise ValueError("Time não encontrado.")
        return {
            **plan,
            "team_name": team.name,
            "last_session": last,
            "focuses": list(FOCUSES),
            "intensities": list(INTENSITIES),
        }

    async def process_team_day(
        self,
        team: Team,
        day_type: str,
        *,
        is_match_day: bool = False,
        only_starters: bool = False,
        focus: Optional[str] = None,
        intensity: Optional[str] = None,
        source: str = "calendar",
    ) -> Dict[str, Any]:
        """
        Aplica desenvolvimento a um time no fim do dia / pós-partida.
        Mutates players in session; caller commits.
        """
        plan = await self.get_plan(str(team.id))
        focus_v = normalize_focus(focus or plan.get("focus"))
        intensity_v = normalize_intensity(intensity or plan.get("intensity"))
        cfg = INTENSITY_CFG[intensity_v]

        day_key = day_type
        if source == "match_xp":
            day_key = "MATCH_XP"
        elif is_match_day and day_type not in (
            CalendarDayType.TRAINING.value,
            CalendarDayType.SCRIM.value,
        ):
            day_key = CalendarDayType.MATCH_DAY.value

        day_mult = DAY_MULT.get(day_key)
        if day_mult is None:
            # REST / MEDIA / TRAVEL: sem treino
            return {
                "team_id": str(team.id),
                "team_name": team.name,
                "day_type": day_type,
                "skipped": True,
                "reason": "day_type_no_training",
                "gains": [],
                "ca_gains": 0,
                "attr_gains": 0,
            }

        players: Sequence[Player] = list(getattr(team, "players", []) or [])
        if only_starters or day_key in (
            CalendarDayType.MATCH_DAY.value,
            "MATCH_XP",
        ):
            starters = team.get_starters() if hasattr(team, "get_starters") else players[:5]
            players = starters

        gains: List[Dict[str, Any]] = []
        ca_count = 0
        attr_count = 0

        for player in players:
            result = self._develop_player(
                player,
                day_mult=day_mult * cfg["gain"],
                focus=focus_v,
                intensity=intensity_v,
                extra_burnout=cfg["extra_burnout"],
                day_type=day_key,
            )
            if result:
                gains.append(result)
                if result.get("ca_delta"):
                    ca_count += 1
                if result.get("attr_deltas"):
                    attr_count += 1

        session = {
            "team_id": str(team.id),
            "team_name": team.name,
            "day_type": day_type,
            "source": source,
            "focus": focus_v,
            "intensity": intensity_v,
            "players_trained": len(players),
            "ca_gains": ca_count,
            "attr_gains": attr_count,
            "gains": gains,
            "skipped": False,
        }
        if intensity_v == "HARD" and source == "calendar":
            try:
                from src.modules.career.morale_service import MoraleService

                await MoraleService(self.db).on_hard_training(str(team.id))
            except Exception:
                pass
        await redis_client.set_generic(self._log_key(str(team.id)), session)
        return session

    async def process_league_day(
        self,
        teams: List[Team],
        day_type: str,
        *,
        is_match_day: bool = False,
        managed_team_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Processa treino de todos os times no advance day.

        Só TRAINING/SCRIM geram desenvolvimento aqui.
        MATCH_DAY não treina no calendário — XP vem de auto-sim / live.
        """
        _ = is_match_day, managed_team_id  # reservados p/ filtros futuros
        if day_type not in (
            CalendarDayType.TRAINING.value,
            CalendarDayType.SCRIM.value,
        ):
            return [
                {
                    "team_id": str(t.id),
                    "team_name": t.name,
                    "day_type": day_type,
                    "skipped": True,
                    "reason": "day_type_no_training",
                    "gains": [],
                    "ca_gains": 0,
                    "attr_gains": 0,
                }
                for t in teams
            ]

        sessions: List[Dict[str, Any]] = []
        for team in teams:
            try:
                session = await self.process_team_day(
                    team,
                    day_type,
                    is_match_day=False,
                    only_starters=False,
                    source="calendar",
                )
                sessions.append(session)
            except Exception as exc:
                logger.error(
                    f"[TrainingService] Erro no time {getattr(team, 'name', '?')}: {exc}",
                    exc_info=True,
                )
        return sessions

    async def apply_match_xp_for_starters(self, team: Team) -> Dict[str, Any]:
        """XP de partida oficial (live ou auto-sim) nos titulares."""
        return await self.process_team_day(
            team,
            day_type=CalendarDayType.MATCH_DAY.value,
            is_match_day=True,
            only_starters=True,
            source="match_xp",
        )

    def _develop_player(
        self,
        player: Player,
        *,
        day_mult: float,
        focus: str,
        intensity: str,
        extra_burnout: float,
        day_type: str,
    ) -> Optional[Dict[str, Any]]:
        ca = int(player.current_ability or 0)
        pa = int(player.potential_ability or ca)
        if pa < ca:
            pa = ca
            player.potential_ability = pa

        age = player.get_age() if hasattr(player, "get_age") else 22
        age_factor = self._age_factor(age)
        coach = float(player.coachability or 10.0)
        coach_factor = 0.55 + (coach / 20.0)  # ~0.6–1.55
        burnout = float(player.burnout_meter or 0.0)
        if burnout >= 85:
            burn_factor = 0.25
        elif burnout >= 70:
            burn_factor = 0.45
        elif burnout >= 50:
            burn_factor = 0.7
        else:
            burn_factor = 1.0

        room = max(0, pa - ca)
        if room <= 0:
            # No teto: ainda pode polir atributos levemente
            progress = 0.0
        else:
            # Mais room = mais fácil; perto do teto freia
            progress = min(1.0, room / max(20.0, pa * 0.15))

        rookie_factor = 1.25 if player.is_rookie else 1.0
        focus_w = FOCUS_CA_WEIGHT.get(focus, 1.0)

        ca_chance = (
            0.20
            * day_mult
            * max(progress, 0.05 if room > 0 else 0.0)
            * age_factor
            * coach_factor
            * burn_factor
            * rookie_factor
            * focus_w
        )
        ca_chance = clamp(ca_chance, 0.0, 0.82)

        ca_delta = 0
        if room > 0 and random.random() < ca_chance:
            ca_delta = 1
            player.current_ability = ca + 1

        attr_deltas: Dict[str, float] = {}
        attrs = FOCUS_ATTRS.get(focus, FOCUS_ATTRS["BALANCED"])
        attr_chance = clamp(0.18 * day_mult * coach_factor * burn_factor * age_factor, 0.02, 0.55)
        for attr in attrs:
            if not hasattr(player, attr):
                continue
            if random.random() >= attr_chance:
                continue
            old = float(getattr(player, attr) or 10.0)
            if old >= 20.0:
                continue
            step = 0.1 if intensity != "HARD" else 0.15
            # ROLE focus: leve bônus se attr for mechanics
            if focus == "ROLE" and attr == "mechanics":
                step += 0.05
            new = clamp(old + step, 1.0, 20.0)
            if new > old + 1e-9:
                setattr(player, attr, new)
                attr_deltas[attr] = round(new - old, 2)

        if extra_burnout > 0:
            player.burnout_meter = clamp(float(player.burnout_meter or 0) + extra_burnout, 0.0, 100.0)
            player.visual_fatigue = clamp(
                float(player.visual_fatigue or 0) + extra_burnout * 0.6, 0.0, 100.0
            )

        if ca_delta == 0 and not attr_deltas:
            return None

        return {
            "player_id": str(player.id),
            "player_name": player.name,
            "role": player.role.value if player.role else None,
            "ca_before": ca,
            "ca_after": int(player.current_ability),
            "ca_delta": ca_delta,
            "pa": pa,
            "attr_deltas": attr_deltas,
            "day_type": day_type,
            "focus": focus,
        }

    @staticmethod
    def _age_factor(age: int) -> float:
        if age <= 18:
            return 1.4
        if age <= 20:
            return 1.25
        if age <= 23:
            return 1.1
        if age <= 26:
            return 1.0
        if age <= 28:
            return 0.75
        if age <= 30:
            return 0.5
        return 0.3

    async def load_team_with_players(self, team_id: str) -> Team:
        result = await self.db.execute(
            select(Team)
            .where(Team.id == uuid.UUID(str(team_id)))
            .options(selectinload(Team.players))
        )
        team = result.scalar_one_or_none()
        if not team:
            raise ValueError("Time não encontrado.")
        return team
