# -*- coding: utf-8 -*-
"""
Negociação de transferências (P2-2).

Fluxo:
  1. valuation() — taxa e salário de referência
  2. evaluate_offer() — accept | counter | reject
  3. complete_transfer() — debita comprador, credita vendedor, cria contrato
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.contract import SEASON_DURATION_DAYS, Contract
from src.models.player import Player
from src.models.team import Team
from src.shared.enums import ContractStatus

logger = logging.getLogger(__name__)

ACTIVE = (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL)


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def compute_valuation(
    player: Player,
    active_contract: Optional[Contract],
) -> Dict[str, Any]:
    """
    Valor de mercado e exigências mínimas.

    Taxa base ~ CA*3500 + (PA-CA)*800, ajustada por idade e contrato.
    Free agent: taxa bem menor (bônus de assinatura).
    """
    ca = int(player.current_ability or 100)
    pa = int(player.potential_ability or ca)
    age = int(player.get_age() if hasattr(player, "get_age") else 20)

    base = Decimal(ca * 3500 + max(0, pa - ca) * 800)

    # Idade: jovem valoriza, veterano barateia
    if age <= 20:
        base *= Decimal("1.15")
    elif age <= 24:
        base *= Decimal("1.05")
    elif age >= 30:
        base *= Decimal("0.75")
    elif age >= 27:
        base *= Decimal("0.90")

    free_agent = player.team_id is None or active_contract is None
    remaining = 0
    current_salary = Decimal("3000")
    if active_contract:
        remaining = int(getattr(active_contract, "remaining_seasons", None) or active_contract.seasons_duration or 1)
        current_salary = _d(active_contract.monthly_salary)
        # Contrato longo = clube pede mais
        if remaining >= 3:
            base *= Decimal("1.25")
        elif remaining == 2:
            base *= Decimal("1.10")
        elif remaining <= 1:
            base *= Decimal("0.85")

    if free_agent:
        # Taxa = bônus de assinatura
        asking_fee = max(Decimal("25000"), base * Decimal("0.20"))
        min_fee = asking_fee * Decimal("0.70")
    else:
        asking_fee = max(Decimal("100000"), base)
        min_fee = asking_fee * Decimal("0.80")

    # Salário desejado: ~80–120% do atual, com piso por CA
    floor_sal = Decimal(max(2000, ca * 40))
    desired_salary = max(floor_sal, current_salary * Decimal("1.10") if not free_agent else floor_sal)
    min_salary = max(floor_sal * Decimal("0.85"), current_salary if not free_agent else floor_sal * Decimal("0.80"))

    # Duração preferida
    preferred_seasons = 2 if age >= 28 else 3
    min_seasons = 1

    return {
        "asking_fee": float(asking_fee.quantize(Decimal("1"))),
        "min_fee": float(min_fee.quantize(Decimal("1"))),
        "desired_salary": float(desired_salary.quantize(Decimal("1"))),
        "min_salary": float(min_salary.quantize(Decimal("1"))),
        "preferred_seasons": preferred_seasons,
        "min_seasons": min_seasons,
        "current_salary": float(current_salary),
        "remaining_seasons": remaining,
        "is_free_agent": free_agent,
        "age": age,
        "ca": ca,
    }


def evaluate_offer(
    valuation: Dict[str, Any],
    transfer_fee: float,
    monthly_salary: float,
    seasons: int,
) -> Dict[str, Any]:
    """Decide aceitar, contra-propor ou recusar."""
    seasons = max(1, min(4, int(seasons)))
    fee = float(transfer_fee)
    sal = float(monthly_salary)

    ask_f = float(valuation["asking_fee"])
    min_f = float(valuation["min_fee"])
    des_s = float(valuation["desired_salary"])
    min_s = float(valuation["min_salary"])
    pref_seasons = int(valuation["preferred_seasons"])
    min_seasons = int(valuation["min_seasons"])

    fee_ok = fee >= ask_f * 0.95
    fee_mid = fee >= min_f
    sal_ok = sal >= des_s * 0.95
    sal_mid = sal >= min_s
    seasons_ok = seasons >= pref_seasons
    seasons_mid = seasons >= min_seasons

    score = 0
    score += 2 if fee_ok else (1 if fee_mid else 0)
    score += 2 if sal_ok else (1 if sal_mid else 0)
    score += 1 if seasons_ok else (1 if seasons_mid else 0)

    if fee < min_f or sal < min_s or seasons < min_seasons:
        return {
            "status": "rejected",
            "message": "Oferta recusada — abaixo do mínimo do clube/jogador.",
            "valuation": valuation,
            "counter": None,
        }

    if score >= 4 and fee_ok and sal_ok:
        return {
            "status": "accepted",
            "message": "Oferta aceita! Confirme para concluir a contratação.",
            "valuation": valuation,
            "counter": None,
            "accepted_terms": {
                "transfer_fee": fee,
                "monthly_salary": sal,
                "seasons": seasons,
            },
        }

    # Contra-oferta: sobe o que estiver fraco
    counter_fee = max(fee, ask_f * 0.98, min_f)
    counter_sal = max(sal, des_s * 0.98, min_s)
    counter_seasons = max(seasons, pref_seasons)

    # arredonda
    counter_fee = float(Decimal(counter_fee).quantize(Decimal("1000")))
    counter_sal = float(Decimal(counter_sal).quantize(Decimal("100")))

    return {
        "status": "counter",
        "message": "O clube/jogador pediu melhores termos.",
        "valuation": valuation,
        "counter": {
            "transfer_fee": counter_fee,
            "monthly_salary": counter_sal,
            "seasons": int(counter_seasons),
        },
    }


class TransferService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _load_player(self, player_id: uuid.UUID) -> Player:
        q = await self.db.execute(
            select(Player)
            .where(Player.id == player_id)
            .options(selectinload(Player.contracts))
        )
        player = q.scalar_one_or_none()
        if not player:
            raise ValueError("Jogador não encontrado.")
        return player

    def _active_contract(self, player: Player) -> Optional[Contract]:
        for c in player.contracts or []:
            if c.status in ACTIVE:
                return c
        return None

    async def get_valuation(self, player_id: str) -> Dict[str, Any]:
        player = await self._load_player(uuid.UUID(player_id))
        contract = self._active_contract(player)
        val = compute_valuation(player, contract)
        seller = None
        if player.team_id:
            team = await self.db.get(Team, player.team_id)
            if team:
                seller = {
                    "team_id": str(team.id),
                    "team_name": team.name,
                    "team_abbr": team.abbreviation,
                }
        return {
            "player_id": str(player.id),
            "player_name": player.name,
            "seller": seller,
            **val,
        }

    async def negotiate(
        self,
        buyer_team_id: str,
        player_id: str,
        transfer_fee: float,
        monthly_salary: float,
        seasons: int,
    ) -> Dict[str, Any]:
        from src.modules.career.market_window import MarketWindowService

        buyer = await self.db.get(Team, uuid.UUID(buyer_team_id))
        player = await self._load_player(uuid.UUID(player_id))
        if not buyer:
            raise ValueError("Time comprador não encontrado.")
        if player.team_id and str(player.team_id) == buyer_team_id:
            raise ValueError("Jogador já pertence a este time.")

        age = player.get_age()
        from src.core.config import get_settings

        settings = get_settings()
        if age < settings.min_age_erl:
            raise ValueError(
                f"Jogador com {age} anos é inelegível (mínimo {settings.min_age_erl})."
            )

        contract = self._active_contract(player)
        is_fa = player.team_id is None or contract is None
        # Janela de mercado (offseason full / split só FA / playoffs fechado)
        try:
            window = await MarketWindowService(self.db).assert_can_transfer(
                is_free_agent=is_fa,
                seller_team_id=str(player.team_id) if player.team_id else None,
            )
        except ValueError as win_err:
            return {
                "status": "rejected",
                "message": str(win_err),
                "valuation": compute_valuation(player, contract),
                "counter": None,
                "window": await MarketWindowService(self.db).get_status(),
                "player_id": str(player.id),
                "player_name": player.name,
                "can_afford": False,
                "buyer_budget": float(buyer.budget),
            }

        valuation = compute_valuation(player, contract)
        result = evaluate_offer(valuation, transfer_fee, monthly_salary, seasons)
        result["window"] = window

        # Checa se comprador tem grana para a taxa proposta (ou contra)
        check_fee = transfer_fee
        if result["status"] == "counter" and result.get("counter"):
            check_fee = result["counter"]["transfer_fee"]
        if result["status"] == "accepted":
            check_fee = transfer_fee

        can_afford = float(buyer.budget) >= float(check_fee)
        result["buyer_budget"] = float(buyer.budget)
        result["can_afford"] = can_afford
        if result["status"] == "accepted" and not can_afford:
            result["status"] = "rejected"
            result["message"] = "Orçamento insuficiente para esta taxa."
            result["accepted_terms"] = None

        result["player_id"] = str(player.id)
        result["player_name"] = player.name
        return result

    async def complete_transfer(
        self,
        buyer_team_id: str,
        player_id: str,
        transfer_fee: float,
        monthly_salary: float,
        seasons: int,
        *,
        skip_negotiation: bool = False,
    ) -> Dict[str, Any]:
        """
        Executa a transferência. Se skip_negotiation=False, revalida a oferta.
        """
        if not skip_negotiation:
            neg = await self.negotiate(
                buyer_team_id, player_id, transfer_fee, monthly_salary, seasons
            )
            if neg["status"] != "accepted":
                raise ValueError(neg.get("message") or "Oferta não aceita.")

        from src.modules.career.market_window import MarketWindowService

        buyer = await self.db.get(Team, uuid.UUID(buyer_team_id))
        player = await self._load_player(uuid.UUID(player_id))
        if not buyer or not player:
            raise ValueError("Time ou jogador não encontrado.")

        contract_chk = self._active_contract(player)
        is_fa = player.team_id is None or contract_chk is None
        await MarketWindowService(self.db).assert_can_transfer(is_free_agent=is_fa)

        fee = _d(transfer_fee)
        seasons = max(1, min(4, int(seasons)))
        salary = _d(monthly_salary)

        seller: Optional[Team] = None
        if player.team_id:
            seller = await self.db.get(Team, player.team_id)

        try:
            buyer.deduct_budget(fee, operation="transferência")
        except Exception as err:
            raise ValueError(str(err)) from err

        if seller and fee > 0:
            seller.budget = _d(seller.budget) + fee

        # Encerra contratos ativos
        for c in player.contracts or []:
            if c.status in ACTIVE:
                c.terminate()

        # Também busca no DB por segurança
        cq = await self.db.execute(
            select(Contract).where(
                Contract.player_id == player.id,
                Contract.status.in_(list(ACTIVE)),
            )
        )
        for old in cq.scalars().all():
            old.terminate()

        today = date.today()
        new_contract = Contract(
            id=uuid.uuid4(),
            player_id=player.id,
            team_id=buyer.id,
            start_date=today,
            end_date=today + timedelta(days=SEASON_DURATION_DAYS * seasons),
            seasons_duration=seasons,
            monthly_salary=salary,
            status=ContractStatus.ACTIVE,
            has_rookie_clause=bool(player.is_rookie),
            rookie_games_played=0,
            rookie_total_league_games=0,
            rookie_extension_triggered=False,
        )
        player.team_id = buyer.id
        self.db.add(new_contract)
        await self.db.flush()

        logger.info(
            f"[Transfer] {player.name} → {buyer.abbreviation} "
            f"fee={fee} sal={salary} {seasons}s"
            + (f" (de {seller.abbreviation})" if seller else " (FA)")
        )

        return {
            "message": f"{player.name} contratado por {buyer.name}.",
            "team_budget": float(buyer.budget),
            "transfer_fee": float(fee),
            "monthly_salary": float(salary),
            "seasons": seasons,
            "seller_team_id": str(seller.id) if seller else None,
            "player_id": str(player.id),
            "player_name": player.name,
            "contract_id": str(new_contract.id),
        }
