# -*- coding: utf-8 -*-
"""
Finanças reais do clube: folha, receita mensal, tick e insolvência.

Regras MVP:
  - Todo mês de calendário (28 dias de SM) aplica:
      budget += monthly_revenue
      budget -= folha de contratos ACTIVE/ROOKIE_EXTENDED
  - Se a folha não cabe: paga o possível, zera caixa, marca insolvente
    e tenta liberar os mais baratos (CA baixo) até a folha caber na receita.
  - Transferências e prêmios de playoff já alteram budget em outros serviços.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.contract import Contract
from src.models.player import Player
from src.models.team import Team
from src.shared.enums import ContractStatus

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED)
MONTH_DAYS = 28  # alinhado a ~4 semanas de calendário


class FinanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _load_team(self, team_id: uuid.UUID) -> Team:
        result = await self.db.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.players).selectinload(Player.contracts))
        )
        team = result.scalar_one_or_none()
        if not team:
            raise ValueError("Time não encontrado.")
        return team

    async def _active_contracts_for_team(self, team_id: uuid.UUID) -> List[Contract]:
        q = await self.db.execute(
            select(Contract)
            .where(
                Contract.team_id == team_id,
                Contract.status.in_(list(ACTIVE_STATUSES)),
            )
            .options(selectinload(Contract.player))
        )
        return list(q.scalars().all())

    async def compute_payroll(self, team_id: uuid.UUID) -> Decimal:
        contracts = await self._active_contracts_for_team(team_id)
        total = Decimal("0")
        for c in contracts:
            total += Decimal(str(c.monthly_salary or 0))
        return total

    async def get_snapshot(self, team_id: str) -> Dict[str, Any]:
        tid = uuid.UUID(team_id)
        team = await self._load_team(tid)
        contracts = await self._active_contracts_for_team(tid)
        payroll = sum((Decimal(str(c.monthly_salary or 0)) for c in contracts), Decimal("0"))
        revenue = Decimal(str(team.monthly_revenue or 0))
        budget = Decimal(str(team.budget or 0))
        sponsor_income = Decimal("0")
        facility_cost = Decimal("0")
        try:
            from src.modules.career.org_service import OrgService

            org_pub = await OrgService(self.db).get_public(str(tid))
            sponsor_income = Decimal(str(org_pub.get("sponsor_monthly_income") or 0))
            facility_cost = Decimal(str(org_pub.get("facility_monthly_cost") or 0))
        except Exception:
            pass
        net = revenue + sponsor_income - payroll - facility_cost
        runway_months = None
        if net < 0 and budget > 0:
            runway_months = float(budget / abs(net))
        elif net >= 0:
            runway_months = None  # sustentável

        wage_list = []
        for c in sorted(contracts, key=lambda x: float(x.monthly_salary or 0), reverse=True):
            p = c.player
            wage_list.append(
                {
                    "player_id": str(c.player_id),
                    "player_name": p.name if p else "?",
                    "role": p.role.value if p and p.role else None,
                    "monthly_salary": float(c.monthly_salary or 0),
                    "status": c.status.value if c.status else None,
                    "remaining_seasons": c.remaining_seasons if hasattr(c, "remaining_seasons") else None,
                }
            )

        health = "healthy"
        if budget < payroll:
            health = "critical"
        elif net < 0 and (runway_months is not None and runway_months < 2):
            health = "warning"
        elif net < 0:
            health = "tight"

        return {
            "team_id": str(team.id),
            "team_name": team.name,
            "team_abbr": team.abbreviation,
            "budget": float(budget),
            "monthly_revenue": float(revenue),
            "sponsor_income": float(sponsor_income),
            "facility_cost": float(facility_cost),
            "monthly_payroll": float(payroll),
            "monthly_net": float(net),
            "runway_months": runway_months,
            "health": health,
            "wages": wage_list,
            "player_count": len(wage_list),
        }

    async def process_monthly_tick_for_team(self, team: Team) -> Dict[str, Any]:
        """
        Aplica um ciclo mensal a um time. Retorna log do evento.
        """
        tid = team.id if isinstance(team.id, uuid.UUID) else uuid.UUID(str(team.id))
        # refresh with contracts
        team = await self._load_team(tid)
        contracts = await self._active_contracts_for_team(tid)
        payroll = sum((Decimal(str(c.monthly_salary or 0)) for c in contracts), Decimal("0"))
        revenue = Decimal(str(team.monthly_revenue or 0))
        before = Decimal(str(team.budget or 0))

        # Org S4: sponsors + facility (Redis)
        sponsor_income = Decimal("0")
        facility_cost = Decimal("0")
        try:
            from src.modules.career.org_service import OrgService

            org = OrgService(self.db)
            await org.ensure_initialized(str(tid))
            delta = await org.monthly_finance_delta(str(tid))
            sponsor_income = Decimal(str(delta.get("sponsor_income") or 0))
            facility_cost = Decimal(str(delta.get("facility_cost") or 0))
            await org.evaluate_standings_pressure(str(tid))
        except Exception as oe:
            logger.warning(f"[Finance] org delta: {oe}")

        # 1) Receita base + sponsors
        after_revenue = before + revenue + sponsor_income

        # 2) Facility + Folha
        after_revenue = after_revenue - facility_cost
        if after_revenue < 0:
            after_revenue = Decimal("0")

        released: List[str] = []
        insolvent = False
        paid = Decimal("0")

        if after_revenue >= payroll:
            after = after_revenue - payroll
            paid = payroll
        else:
            # Paga o que pode, zera caixa
            paid = after_revenue
            after = Decimal("0")
            insolvent = True
            remaining_contracts = sorted(
                contracts,
                key=lambda c: (
                    float(c.monthly_salary or 0),
                    float(c.player.current_ability if c.player else 0),
                ),
            )
            current_payroll = payroll
            roster_count = len([p for p in team.players if p.team_id == tid])
            for c in remaining_contracts:
                if current_payroll <= revenue + sponsor_income:
                    break
                if roster_count <= 6:
                    break
                c.status = ContractStatus.TERMINATED
                if c.player:
                    c.player.team_id = None
                    released.append(c.player.name)
                current_payroll -= Decimal(str(c.monthly_salary or 0))
                roster_count -= 1

        team.budget = after
        await self.db.flush()

        event = {
            "team_id": str(tid),
            "team_name": team.name,
            "type": "MONTHLY_TICK",
            "budget_before": float(before),
            "revenue": float(revenue),
            "sponsor_income": float(sponsor_income),
            "facility_cost": float(facility_cost),
            "payroll": float(payroll),
            "paid": float(paid),
            "budget_after": float(after),
            "insolvent": insolvent,
            "released": released,
        }
        logger.info(
            f"[Finance] {team.abbreviation}: {before:.0f} +{revenue:.0f}"
            f"+sponsor{sponsor_income:.0f} -fac{facility_cost:.0f} -{paid:.0f} "
            f"= {after:.0f}" + (" INSOLVENT" if insolvent else "")
        )
        return event

    async def process_monthly_tick_all_league_teams(
        self, teams: List[Team]
    ) -> List[Dict[str, Any]]:
        events = []
        for team in teams:
            try:
                events.append(await self.process_monthly_tick_for_team(team))
            except Exception as exc:
                logger.error(f"[Finance] Falha no tick de {team.name}: {exc}", exc_info=True)
        return events

    @staticmethod
    def is_month_boundary(total_days: int) -> bool:
        """True a cada MONTH_DAYS de calendário (dia 28, 56, …)."""
        d = int(total_days or 0)
        return d > 0 and d % MONTH_DAYS == 0
