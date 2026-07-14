# -*- coding: utf-8 -*-
"""
Scouting e revelação de atributos ocultos.

Atributos mascarados até scoutar:
  - consistency (consistência)
  - big_match_aptitude (aptidão em jogos grandes)
  - potential_ability (PA — mostrado como faixa até revelar)

Regras MVP:
  - Conhecimento por time em Redis: scouting:team:{id}:knowledge
  - Atribuição ativa: scouting:team:{id}:assignment (1 alvo por vez)
  - Progresso diário no advance: staff meta_reading acelera
  - Elenco próprio ganha progresso passivo leve (você os vê treinar)
  - Thresholds: 35% = faixa larga, 70% = faixa estreita, 100% = valor real
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.redis_client import redis_client
from src.models.player import Player
from src.models.staff import Staff
from src.models.team import Team
from src.shared.enums import CalendarDayType
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

HIDDEN_ATTRS = ("consistency", "big_match_aptitude", "potential_ability")
SCOUT_FOCUSES = ("ALL", "CONSISTENCY", "BMA", "PA")

# Progresso por dia base (antes de mult staff/dia)
BASE_PROGRESS = {
    CalendarDayType.TRAINING.value: 12.0,
    CalendarDayType.SCRIM.value: 14.0,
    CalendarDayType.MATCH_DAY.value: 10.0,
    CalendarDayType.REST.value: 4.0,
    CalendarDayType.MEDIA.value: 3.0,
    CalendarDayType.TRAVEL.value: 2.0,
}
PASSIVE_OWN_ROSTER = 3.5  # por dia, sem assignment

THRESHOLDS = {
    "band_wide": 35.0,
    "band_tight": 70.0,
    "full": 100.0,
}


def normalize_scout_focus(focus: Optional[str]) -> str:
    f = (focus or "ALL").upper().strip()
    return f if f in SCOUT_FOCUSES else "ALL"


def _band_for(value: float, progress: float, attr: str) -> Optional[Dict[str, Any]]:
    """
    Retorna faixa estimada ou valor revelado conforme progresso.
    value: valor real (1-20 attrs ou 0-200 PA)
    """
    is_pa = attr == "potential_ability"
    lo_bound, hi_bound = (0, 200) if is_pa else (1, 20)

    if progress >= THRESHOLDS["full"]:
        return {
            "known": True,
            "value": int(round(value)) if is_pa else round(float(value), 1),
            "min": None,
            "max": None,
            "label": "known",
        }

    if progress < THRESHOLDS["band_wide"]:
        return {
            "known": False,
            "value": None,
            "min": None,
            "max": None,
            "label": "unknown",
        }

    # Largura da banda diminui com progresso
    if progress >= THRESHOLDS["band_tight"]:
        half = 8 if is_pa else 1.5
        label = "tight"
    else:
        half = 20 if is_pa else 3.5
        label = "wide"

    # Offset determinístico a partir do valor (não random a cada request)
    seed = int(value * 17 + progress) % 7
    offset = (seed - 3) * (0.15 if not is_pa else 1.0)
    center = value + offset
    lo = max(lo_bound, math.floor(center - half))
    hi = min(hi_bound, math.ceil(center + half))
    if lo > hi:
        lo, hi = hi, lo
    # Garante que o valor real esteja na faixa (fairness)
    if value < lo:
        lo = max(lo_bound, int(math.floor(value)))
    if value > hi:
        hi = min(hi_bound, int(math.ceil(value)))

    return {
        "known": False,
        "value": None,
        "min": int(lo) if is_pa else round(float(lo), 1),
        "max": int(hi) if is_pa else round(float(hi), 1),
        "label": label,
    }


class ScoutingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _knowledge_key(self, team_id: str) -> str:
        return f"scouting:team:{team_id}:knowledge"

    def _assignment_key(self, team_id: str) -> str:
        return f"scouting:team:{team_id}:assignment"

    async def get_knowledge(self, team_id: str) -> Dict[str, Dict[str, Any]]:
        data = await redis_client.get_generic(self._knowledge_key(str(team_id)))
        return data if isinstance(data, dict) else {}

    async def save_knowledge(self, team_id: str, knowledge: Dict[str, Any]) -> None:
        await redis_client.set_generic(self._knowledge_key(str(team_id)), knowledge)

    async def get_assignment(self, team_id: str) -> Optional[Dict[str, Any]]:
        data = await redis_client.get_generic(self._assignment_key(str(team_id)))
        return data if isinstance(data, dict) else None

    async def clear_assignment(self, team_id: str) -> Dict[str, Any]:
        await redis_client.delete(self._assignment_key(str(team_id)))
        return {"team_id": str(team_id), "assignment": None, "cleared": True}

    async def staff_scouting_power(self, team_id: str) -> Dict[str, Any]:
        """meta_reading médio da comissão (1–20) → mult ~0.7–1.5."""
        q = await self.db.execute(
            select(Staff).where(Staff.team_id == uuid.UUID(str(team_id)))
        )
        staffs = list(q.scalars().all())
        if not staffs:
            return {
                "staff_count": 0,
                "avg_meta_reading": 10.0,
                "power_mult": 0.85,
                "staff": [],
            }
        avg = sum(float(s.meta_reading or 10) for s in staffs) / len(staffs)
        mult = clamp(0.55 + (avg / 20.0), 0.7, 1.55)
        return {
            "staff_count": len(staffs),
            "avg_meta_reading": round(avg, 1),
            "power_mult": round(mult, 2),
            "staff": [
                {
                    "name": s.name,
                    "role": s.role,
                    "meta_reading": float(s.meta_reading or 10),
                    "communication": float(s.communication or 10),
                }
                for s in staffs
            ],
        }

    async def assign(
        self,
        team_id: str,
        player_id: str,
        focus: str = "ALL",
    ) -> Dict[str, Any]:
        team = await self.db.get(Team, uuid.UUID(str(team_id)))
        if not team:
            raise ValueError("Time não encontrado.")
        player = await self.db.get(Player, uuid.UUID(str(player_id)))
        if not player:
            raise ValueError("Jogador não encontrado.")

        focus_v = normalize_scout_focus(focus)
        knowledge = await self.get_knowledge(team_id)
        entry = knowledge.get(str(player_id)) or self._empty_entry()

        assignment = {
            "team_id": str(team_id),
            "player_id": str(player_id),
            "player_name": player.name,
            "player_role": player.role.value if player.role else None,
            "player_team_id": str(player.team_id) if player.team_id else None,
            "focus": focus_v,
            "days_invested": int(entry.get("days_invested") or 0),
            "progress": float(entry.get("progress") or 0),
        }
        await redis_client.set_generic(self._assignment_key(str(team_id)), assignment)
        return {
            "message": f"Scouting iniciado: {player.name}",
            "assignment": assignment,
            "knowledge": self._public_entry(entry, player),
        }

    async def get_status(self, team_id: str) -> Dict[str, Any]:
        team = await self.db.get(Team, uuid.UUID(str(team_id)))
        if not team:
            raise ValueError("Time não encontrado.")
        power = await self.staff_scouting_power(team_id)
        assignment = await self.get_assignment(team_id)
        knowledge = await self.get_knowledge(team_id)

        # Enriquece assignment com progresso atual
        if assignment and assignment.get("player_id"):
            pid = str(assignment["player_id"])
            entry = knowledge.get(pid) or self._empty_entry()
            assignment = {
                **assignment,
                "progress": float(entry.get("progress") or 0),
                "days_invested": int(entry.get("days_invested") or 0),
                "fully_scouted": float(entry.get("progress") or 0) >= 100,
            }

        # Lista resumida de conhecidos
        known_list = []
        for pid, entry in knowledge.items():
            if not isinstance(entry, dict):
                continue
            prog = float(entry.get("progress") or 0)
            if prog <= 0:
                continue
            known_list.append(
                {
                    "player_id": pid,
                    "progress": prog,
                    "fully_scouted": prog >= 100,
                    "days_invested": int(entry.get("days_invested") or 0),
                }
            )
        known_list.sort(key=lambda x: -x["progress"])

        return {
            "team_id": str(team_id),
            "team_name": team.name,
            "assignment": assignment,
            "staff_power": power,
            "knowledge_count": len(known_list),
            "knowledge_summary": known_list[:40],
            "thresholds": THRESHOLDS,
            "focuses": list(SCOUT_FOCUSES),
        }

    async def process_day_for_team(
        self,
        team: Team,
        day_type: str,
    ) -> Dict[str, Any]:
        """Avanço diário: assignment ativo + passivo no elenco próprio."""
        team_id = str(team.id)
        knowledge = await self.get_knowledge(team_id)
        power = await self.staff_scouting_power(team_id)
        mult = float(power.get("power_mult") or 1.0)
        day_base = BASE_PROGRESS.get(day_type, 5.0)

        events: List[Dict[str, Any]] = []
        assignment = await self.get_assignment(team_id)

        # 1) Assignment ativo
        if assignment and assignment.get("player_id"):
            pid = str(assignment["player_id"])
            player = await self.db.get(Player, uuid.UUID(pid))
            if player:
                focus = normalize_scout_focus(assignment.get("focus"))
                focus_mult = 1.35 if focus != "ALL" else 1.0
                gain = day_base * mult * focus_mult
                entry = knowledge.get(pid) or self._empty_entry()
                before = float(entry.get("progress") or 0)
                after = clamp(before + gain, 0.0, 100.0)
                entry["progress"] = after
                entry["days_invested"] = int(entry.get("days_invested") or 0) + 1
                entry["focus"] = focus
                # Marca attrs focados com progresso extra lógico (mesmo progress global)
                if focus == "CONSISTENCY":
                    entry["attr_boost"] = {"consistency": min(100.0, after + 10)}
                elif focus == "BMA":
                    entry["attr_boost"] = {"big_match_aptitude": min(100.0, after + 10)}
                elif focus == "PA":
                    entry["attr_boost"] = {"potential_ability": min(100.0, after + 10)}
                else:
                    entry["attr_boost"] = {}
                knowledge[pid] = entry
                events.append(
                    {
                        "type": "SCOUT_PROGRESS",
                        "player_id": pid,
                        "player_name": player.name,
                        "progress_before": before,
                        "progress_after": after,
                        "gain": round(gain, 1),
                        "focus": focus,
                        "fully_scouted": after >= 100,
                    }
                )
                # Atualiza assignment cache
                assignment["progress"] = after
                assignment["days_invested"] = entry["days_invested"]
                if after >= 100:
                    await redis_client.delete(self._assignment_key(team_id))
                    events.append(
                        {
                            "type": "SCOUT_COMPLETE",
                            "player_id": pid,
                            "player_name": player.name,
                        }
                    )
                else:
                    await redis_client.set_generic(
                        self._assignment_key(team_id), assignment
                    )

        # 2) Passivo no elenco próprio (sem assignment)
        assigned_id = str(assignment["player_id"]) if assignment and assignment.get("player_id") else None
        for player in getattr(team, "players", []) or []:
            pid = str(player.id)
            if pid == assigned_id:
                continue
            entry = knowledge.get(pid) or self._empty_entry()
            before = float(entry.get("progress") or 0)
            if before >= 100:
                continue
            gain = PASSIVE_OWN_ROSTER * mult * (1.1 if day_type in (
                CalendarDayType.TRAINING.value,
                CalendarDayType.SCRIM.value,
            ) else 0.8)
            after = clamp(before + gain, 0.0, 100.0)
            if after > before:
                entry["progress"] = after
                entry["days_invested"] = int(entry.get("days_invested") or 0) + 1
                knowledge[pid] = entry

        await self.save_knowledge(team_id, knowledge)
        return {
            "team_id": team_id,
            "team_name": team.name,
            "day_type": day_type,
            "events": events,
            "assignment": await self.get_assignment(team_id),
        }

    async def process_league_day(
        self,
        teams: List[Team],
        day_type: str,
        *,
        managed_team_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for team in teams:
            # Só processa scouting detalhado do manager; IA não precisa de UI
            if managed_team_id and str(team.id) != str(managed_team_id):
                continue
            if not managed_team_id:
                # Sem manager: processa todos (dev) mas leve
                pass
            try:
                results.append(await self.process_day_for_team(team, day_type))
            except Exception as exc:
                logger.error(
                    f"[ScoutingService] Erro no time {getattr(team, 'name', '?')}: {exc}",
                    exc_info=True,
                )
        return results

    def player_knowledge_view(
        self,
        player: Player,
        knowledge_entry: Optional[Dict[str, Any]],
        *,
        is_own_roster: bool = False,
    ) -> Dict[str, Any]:
        """
        Visão de atributos ocultos para serialização.
        is_own_roster: elenco próprio começa com bônus leve de progresso mínimo.
        """
        entry = knowledge_entry or self._empty_entry()
        progress = float(entry.get("progress") or 0)
        if is_own_roster and progress < 40:
            # Elenco próprio: faixa larga de cara (você já os viu treinar/jogar)
            progress = max(progress, 40.0)

        boosts = entry.get("attr_boost") or {}
        true_values = {
            "consistency": float(player.consistency or 10),
            "big_match_aptitude": float(player.big_match_aptitude or 10),
            "potential_ability": float(player.potential_ability or player.current_ability or 100),
        }

        scouting: Dict[str, Any] = {
            "progress": round(progress, 1),
            "fully_scouted": progress >= 100,
            "days_invested": int(entry.get("days_invested") or 0),
        }

        for attr in HIDDEN_ATTRS:
            attr_progress = float(boosts.get(attr, progress))
            # Para PA, se progress global alto mas focus PA, boost ajuda
            if attr not in boosts:
                attr_progress = progress
            band = _band_for(true_values[attr], attr_progress, attr)
            scouting[attr] = band

        return scouting

    def mask_player_payload(
        self,
        base: Dict[str, Any],
        player: Player,
        knowledge_entry: Optional[Dict[str, Any]],
        *,
        is_own_roster: bool = False,
    ) -> Dict[str, Any]:
        """Aplica máscara de scouting no dict serializado."""
        view = self.player_knowledge_view(
            player, knowledge_entry, is_own_roster=is_own_roster
        )
        out = dict(base)

        # Consistency
        c = view["consistency"]
        if c.get("known"):
            out["consistency"] = c["value"]
            out["consistencyKnown"] = True
            out["consistencyMin"] = None
            out["consistencyMax"] = None
        else:
            out["consistency"] = None
            out["consistencyKnown"] = False
            out["consistencyMin"] = c.get("min")
            out["consistencyMax"] = c.get("max")

        # BMA
        b = view["big_match_aptitude"]
        if b.get("known"):
            out["bigMatchAptitude"] = b["value"]
            out["bigMatchAptitudeKnown"] = True
            out["bigMatchAptitudeMin"] = None
            out["bigMatchAptitudeMax"] = None
        else:
            out["bigMatchAptitude"] = None
            out["bigMatchAptitudeKnown"] = False
            out["bigMatchAptitudeMin"] = b.get("min")
            out["bigMatchAptitudeMax"] = b.get("max")

        # PA (potencial)
        p = view["potential_ability"]
        if p.get("known"):
            out["potentialAbility"] = p["value"]
            out["potentialAbilityKnown"] = True
            out["potentialAbilityMin"] = None
            out["potentialAbilityMax"] = None
        else:
            # Mantém CA real; PA vira null ou faixa
            out["potentialAbility"] = None
            out["potentialAbilityKnown"] = False
            out["potentialAbilityMin"] = p.get("min")
            out["potentialAbilityMax"] = p.get("max")
            # Se totalmente unknown, não minta com PA = CA do seed
            if p.get("label") == "unknown":
                out["potentialAbilityMin"] = None
                out["potentialAbilityMax"] = None

        out["scoutingProgress"] = view["progress"]
        out["scoutingFullyScouted"] = view["fully_scouted"]
        out["scoutingDaysInvested"] = view["days_invested"]
        return out

    @staticmethod
    def _empty_entry() -> Dict[str, Any]:
        return {
            "progress": 0.0,
            "days_invested": 0,
            "focus": "ALL",
            "attr_boost": {},
        }

    def _public_entry(self, entry: Dict[str, Any], player: Player) -> Dict[str, Any]:
        return self.player_knowledge_view(player, entry, is_own_roster=False)
