# -*- coding: utf-8 -*-
"""
Comissão técnica: listar, contratar e demitir staff.

Impacto jogável (sem migration de schema):
  - meta_reading médio → scouting power + draft scout quality
  - communication → coach comms effectiveness (já usado em partes)
  - PERFORMANCE_COACH → bônus implícito via meta_reading alto no burnout recovery (leve)

Custos:
  - signing_fee na contratação (orçamento)
  - monthly_cost calculado (exibido; payroll de staff opcional no summary)
"""

from __future__ import annotations

import logging
import random
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.staff import Staff
from src.models.team import Team
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

STAFF_ROLES = (
    "HEAD_COACH",
    "STRATEGIC_COACH",
    "ASSISTANT_COACH",
    "PERFORMANCE_COACH",
)

# Máximo por cargo no time
ROLE_CAPS = {
    "HEAD_COACH": 1,
    "STRATEGIC_COACH": 1,
    "ASSISTANT_COACH": 2,
    "PERFORMANCE_COACH": 1,
}

ROLE_LABELS = {
    "HEAD_COACH": "Head Coach",
    "STRATEGIC_COACH": "Strategic Coach",
    "ASSISTANT_COACH": "Assistant Coach",
    "PERFORMANCE_COACH": "Performance Coach",
}

ROLE_HINTS = {
    "HEAD_COACH": "Comunicação em partida e disciplina do elenco",
    "STRATEGIC_COACH": "Leitura de meta, draft scout e counters",
    "ASSISTANT_COACH": "Suporte tático e scouting de elenco",
    "PERFORMANCE_COACH": "Recuperação de burnout e forma física",
}

_FIRST = [
    "Rafael", "Bruno", "Lucas", "Diego", "André", "Felipe", "Thiago", "Gustavo",
    "Marcelo", "Pedro", "Henrique", "Caio", "Rodrigo", "Vitor", "Eduardo",
]
_LAST = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Ferreira",
    "Almeida", "Ribeiro", "Carvalho", "Gomes", "Martins", "Rocha", "Barbosa",
]


def estimate_monthly_cost(meta_reading: float, communication: float, role: str) -> float:
    base = 800 + (meta_reading + communication) * 90
    mult = {
        "HEAD_COACH": 1.35,
        "STRATEGIC_COACH": 1.20,
        "ASSISTANT_COACH": 0.85,
        "PERFORMANCE_COACH": 1.0,
    }.get(role, 1.0)
    return float(Decimal(str(base * mult)).quantize(Decimal("1")))


def estimate_signing_fee(meta_reading: float, communication: float, role: str) -> float:
    monthly = estimate_monthly_cost(meta_reading, communication, role)
    return float(Decimal(str(monthly * 2.5)).quantize(Decimal("100")))


def serialize_staff(s: Staff) -> Dict[str, Any]:
    meta = float(s.meta_reading or 10)
    comm = float(s.communication or 10)
    role = s.role or "ASSISTANT_COACH"
    return {
        "id": str(s.id),
        "name": s.name,
        "role": role,
        "role_label": ROLE_LABELS.get(role, role),
        "role_hint": ROLE_HINTS.get(role, ""),
        "meta_reading": meta,
        "communication": comm,
        "monthly_cost": estimate_monthly_cost(meta, comm, role),
        "signing_fee": estimate_signing_fee(meta, comm, role),
        "team_id": str(s.team_id) if s.team_id else None,
    }


class StaffService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_team_staff(self, team_id: str) -> Dict[str, Any]:
        team = await self.db.get(Team, uuid.UUID(team_id))
        if not team:
            raise ValueError("Time não encontrado.")
        q = await self.db.execute(select(Staff).where(Staff.team_id == team.id))
        staffs = [serialize_staff(s) for s in q.scalars().all()]
        staffs.sort(key=lambda x: (x["role"], -x["meta_reading"]))
        power = self._power_from_list(staffs)
        monthly = sum(s["monthly_cost"] for s in staffs)
        return {
            "team_id": str(team.id),
            "team_name": team.name,
            "staff": staffs,
            "count": len(staffs),
            "monthly_staff_cost": round(monthly, 0),
            "power": power,
            "role_caps": ROLE_CAPS,
            "roles": list(STAFF_ROLES),
        }

    def _power_from_list(self, staffs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not staffs:
            return {
                "avg_meta_reading": 8.0,
                "avg_communication": 8.0,
                "scout_mult": 0.75,
                "draft_confidence": 0.4,
                "burnout_recovery_bonus": 0.0,
            }
        avg_m = sum(s["meta_reading"] for s in staffs) / len(staffs)
        avg_c = sum(s["communication"] for s in staffs) / len(staffs)
        has_perf = any(s["role"] == "PERFORMANCE_COACH" for s in staffs)
        has_strat = any(s["role"] == "STRATEGIC_COACH" for s in staffs)
        scout_mult = clamp(0.55 + (avg_m / 20.0), 0.7, 1.55)
        if has_strat:
            scout_mult = min(1.6, scout_mult * 1.08)
        draft_conf = clamp(0.35 + avg_m / 20.0 * 0.55, 0.35, 0.95)
        burn_bonus = 0.12 if has_perf else 0.0
        burn_bonus += max(0, (avg_c - 12) * 0.01)
        return {
            "avg_meta_reading": round(avg_m, 1),
            "avg_communication": round(avg_c, 1),
            "scout_mult": round(scout_mult, 2),
            "draft_confidence": round(draft_conf, 2),
            "burnout_recovery_bonus": round(burn_bonus, 3),
            "has_strategic_coach": has_strat,
            "has_performance_coach": has_perf,
        }

    async def list_candidates(self, team_id: str, limit: int = 12) -> Dict[str, Any]:
        """Gera pool de free agents de staff (determinístico por seed do time + re-roll)."""
        team = await self.db.get(Team, uuid.UUID(team_id))
        if not team:
            raise ValueError("Time não encontrado.")

        # Contagem atual por role
        q = await self.db.execute(select(Staff).where(Staff.team_id == team.id))
        current = list(q.scalars().all())
        counts: Dict[str, int] = {r: 0 for r in STAFF_ROLES}
        for s in current:
            counts[s.role] = counts.get(s.role, 0) + 1

        rng = random.Random(f"staff-pool-{team.id}-{len(current)}")
        candidates: List[Dict[str, Any]] = []
        for i in range(max(8, limit)):
            role = STAFF_ROLES[i % len(STAFF_ROLES)]
            # Bias: se falta head/strat, gera mais desses
            open_roles = [r for r in STAFF_ROLES if counts.get(r, 0) < ROLE_CAPS.get(r, 1)]
            if open_roles and rng.random() < 0.55:
                role = rng.choice(open_roles)
            meta = float(rng.randint(8, 19))
            comm = float(rng.randint(8, 19))
            # elite rare
            if rng.random() < 0.12:
                meta = float(rng.randint(16, 20))
                comm = float(rng.randint(14, 20))
            name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
            cid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{team.id}:{role}:{i}:{name}"))
            candidates.append(
                {
                    "candidate_id": cid,
                    "name": name,
                    "role": role,
                    "role_label": ROLE_LABELS.get(role, role),
                    "role_hint": ROLE_HINTS.get(role, ""),
                    "meta_reading": meta,
                    "communication": comm,
                    "monthly_cost": estimate_monthly_cost(meta, comm, role),
                    "signing_fee": estimate_signing_fee(meta, comm, role),
                    "slot_available": counts.get(role, 0) < ROLE_CAPS.get(role, 1),
                }
            )

        candidates.sort(key=lambda c: (-c["meta_reading"], c["role"]))
        return {
            "team_id": str(team.id),
            "candidates": candidates[:limit],
            "current_counts": counts,
            "role_caps": ROLE_CAPS,
            "budget": float(team.budget),
        }

    async def hire(
        self,
        team_id: str,
        *,
        name: str,
        role: str,
        meta_reading: float,
        communication: float,
        candidate_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        role = (role or "").upper().strip()
        if role not in STAFF_ROLES:
            raise ValueError(f"Cargo inválido. Use: {', '.join(STAFF_ROLES)}")

        team = await self.db.get(Team, uuid.UUID(team_id))
        if not team:
            raise ValueError("Time não encontrado.")

        q = await self.db.execute(select(Staff).where(Staff.team_id == team.id))
        current = list(q.scalars().all())
        same_role = sum(1 for s in current if s.role == role)
        cap = ROLE_CAPS.get(role, 1)
        if same_role >= cap:
            raise ValueError(
                f"Limite de {ROLE_LABELS.get(role, role)} atingido ({cap}). "
                "Demita alguém antes de contratar."
            )

        meta = clamp(float(meta_reading), 1.0, 20.0)
        comm = clamp(float(communication), 1.0, 20.0)
        fee = Decimal(str(estimate_signing_fee(meta, comm, role)))
        monthly = estimate_monthly_cost(meta, comm, role)

        try:
            team.deduct_budget(fee, operation="contratação de staff")
        except Exception as err:
            raise ValueError(str(err)) from err

        staff = Staff(
            id=uuid.uuid4(),
            team_id=team.id,
            name=(name or "Coach").strip()[:100],
            role=role,
            meta_reading=meta,
            communication=comm,
        )
        self.db.add(staff)
        await self.db.flush()

        logger.info(
            f"[Staff] {team.abbreviation} contratou {staff.name} ({role}) fee={fee}"
        )
        return {
            "message": f"{staff.name} contratado como {ROLE_LABELS.get(role, role)}.",
            "staff": serialize_staff(staff),
            "signing_fee": float(fee),
            "monthly_cost": monthly,
            "team_budget": float(team.budget),
            "candidate_id": candidate_id,
        }

    async def fire(self, team_id: str, staff_id: str) -> Dict[str, Any]:
        team = await self.db.get(Team, uuid.UUID(team_id))
        staff = await self.db.get(Staff, uuid.UUID(staff_id))
        if not team or not staff:
            raise ValueError("Time ou staff não encontrado.")
        if str(staff.team_id) != str(team.id):
            raise ValueError("Staff não pertence a este time.")

        # Não permitir demitir o único HEAD se for o último staff? OK demitir todos.
        name = staff.name
        role = staff.role
        await self.db.delete(staff)
        await self.db.flush()

        logger.info(f"[Staff] {team.abbreviation} demitiu {name} ({role})")
        return {
            "message": f"{name} liberado da comissão.",
            "staff_id": staff_id,
            "name": name,
            "role": role,
            "fired": True,
        }
