# -*- coding: utf-8 -*-
"""
Offseason mínimo: renovar/liberar contratos e reiniciar split.

Fluxo:
  1. Entrar em OFFSEASON (após playoffs ou forçado)
  2. Manager renova ou libera atletas com contrato curto
  3. start_new_split → reseta standings, limpa playoffs, tica contratos, REGULAR_SEASON
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.redis_client import redis_client
from src.models.contract import SEASON_DURATION_DAYS, Contract
from src.models.league import League, LeagueTeam
from src.models.player import Player
from src.models.team import Team
from src.shared.enums import ContractStatus, SplitPhase

logger = logging.getLogger(__name__)


class OffseasonService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_league(self) -> League:
        result = await self.db.execute(select(League).limit(1))
        league = result.scalar_one_or_none()
        if not league:
            raise ValueError("Nenhuma liga encontrada. Rode o seed.")
        return league

    async def force_offseason(self, league: Optional[League] = None) -> Dict[str, Any]:
        """Força SM + DB para OFFSEASON (playtest ou pós-campeão)."""
        from src.modules.calendar.calendar_service import CalendarService

        league = league or await self.get_league()
        calendar_service = CalendarService(self.db)
        sm = await calendar_service._get_or_create_sm(league)
        await sm.force_transition_to("OFFSEASON")

        league.current_phase = SplitPhase.OFFSEASON
        league.current_week = 0
        await self.db.flush()

        logger.info(f"[Offseason] Fase forçada para OFFSEASON (liga {league.name})")
        return {
            "phase": "OFFSEASON",
            "league_id": str(league.id),
            "week": 0,
            "message": "Offseason iniciada.",
        }

    async def list_team_contracts(self, team_id: str) -> List[Dict[str, Any]]:
        """Elenco do time com status de contrato para UI de renovação."""
        tid = uuid.UUID(team_id)
        team = await self.db.get(Team, tid)
        if not team:
            raise ValueError("Time não encontrado.")

        players_q = await self.db.execute(select(Player).where(Player.team_id == tid))
        players = list(players_q.scalars().all())

        rows: List[Dict[str, Any]] = []
        for p in players:
            cq = await self.db.execute(
                select(Contract).where(
                    Contract.player_id == p.id,
                    Contract.status.in_(
                        [ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL]
                    ),
                )
            )
            contract = cq.scalar_one_or_none()
            remaining = contract.remaining_seasons if contract else 0
            rows.append(
                {
                    "player_id": str(p.id),
                    "player_name": p.name,
                    "role": p.role.value if p.role else None,
                    "current_ability": p.current_ability,
                    "is_rookie": bool(p.is_rookie),
                    "contract_id": str(contract.id) if contract else None,
                    "status": contract.status.value if contract else "FREE",
                    "monthly_salary": float(contract.monthly_salary) if contract else 0.0,
                    "remaining_seasons": remaining,
                    "seasons_duration": contract.seasons_duration if contract else 0,
                    "needs_renewal": remaining <= 1 or contract is None,
                    "end_date": contract.end_date.isoformat() if contract and contract.end_date else None,
                }
            )

        rows.sort(key=lambda r: (0 if r["needs_renewal"] else 1, r["player_name"] or ""))
        return rows

    async def renew_contract(
        self,
        team_id: str,
        player_id: str,
        seasons: int = 1,
        monthly_salary: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Renova ou cria contrato ativo.
        seasons: 1–4 temporadas adicionais a partir de hoje.
        """
        seasons = max(1, min(4, int(seasons)))
        tid = uuid.UUID(team_id)
        pid = uuid.UUID(player_id)

        player = await self.db.get(Player, pid)
        if not player or str(player.team_id) != str(tid):
            raise ValueError("Jogador não pertence a este time.")

        cq = await self.db.execute(
            select(Contract).where(Contract.player_id == pid).order_by(Contract.created_at.desc())
        )
        contracts = list(cq.scalars().all())
        active = next(
            (
                c
                for c in contracts
                if c.status in (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL)
            ),
            None,
        )

        salary = (
            Decimal(str(monthly_salary))
            if monthly_salary is not None
            else (active.monthly_salary if active else Decimal("5000"))
        )
        if salary < 0:
            raise ValueError("Salário não pode ser negativo.")

        # Encerra contratos anteriores do jogador
        for c in contracts:
            if c.status in (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL):
                c.status = ContractStatus.EXPIRED

        new_contract = Contract(
            id=uuid.uuid4(),
            player_id=pid,
            team_id=tid,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=SEASON_DURATION_DAYS * seasons),
            seasons_duration=seasons,
            monthly_salary=salary,
            status=ContractStatus.ACTIVE,
            has_rookie_clause=bool(player.is_rookie),
            rookie_games_played=0,
            rookie_total_league_games=0,
            rookie_extension_triggered=False,
        )
        self.db.add(new_contract)
        player.team_id = tid
        await self.db.flush()

        logger.info(
            f"[Offseason] Renovado {player.name} por {seasons} split(s) @ €{salary}/mês"
        )
        return {
            "player_id": str(pid),
            "player_name": player.name,
            "contract_id": str(new_contract.id),
            "seasons": seasons,
            "monthly_salary": float(salary),
            "end_date": new_contract.end_date.isoformat(),
        }

    async def release_player(self, team_id: str, player_id: str) -> Dict[str, Any]:
        """Libera jogador: encerra contrato e remove do time (vira free agent)."""
        tid = uuid.UUID(team_id)
        pid = uuid.UUID(player_id)
        player = await self.db.get(Player, pid)
        if not player or str(player.team_id) != str(tid):
            raise ValueError("Jogador não pertence a este time.")

        # Roster mínimo: 6 jogadores (validate_roster_size)
        count_q = await self.db.execute(select(Player).where(Player.team_id == tid))
        roster_count = len(list(count_q.scalars().all()))
        if roster_count <= 6:
            raise ValueError(
                "Não é possível liberar: roster ficaria abaixo do mínimo (6 atletas)."
            )

        cq = await self.db.execute(select(Contract).where(Contract.player_id == pid))
        for c in cq.scalars().all():
            if c.status in (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL):
                c.terminate()

        player.team_id = None
        await self.db.flush()

        logger.info(f"[Offseason] Liberado {player.name} de {team_id}")
        return {
            "player_id": str(pid),
            "player_name": player.name,
            "released": True,
        }

    async def start_new_split(self) -> Dict[str, Any]:
        """
        Fecha offseason e inicia novo split (REGULAR_SEASON):
          - zera standings e flags de playoff
          - limpa bracket Redis
          - tica contratos (1 temporada)
          - recupera parcialmente fadiga
          - zera games_played do split
        """
        from src.modules.calendar.calendar_service import CalendarService

        league = await self.get_league()

        # 1. Standings
        lt_q = await self.db.execute(
            select(LeagueTeam).where(LeagueTeam.league_id == league.id)
        )
        for lt in lt_q.scalars().all():
            lt.wins = 0
            lt.losses = 0
            lt.points = 0
            lt.is_in_playoffs = False
            lt.playoff_seed = None
            lt.final_placement = None
            lt.prize_earned = Decimal("0")

        # 2. Players: stats de split + recuperação leve
        players_q = await self.db.execute(select(Player))
        for p in players_q.scalars().all():
            p.games_played_this_split = 0
            p.burnout_meter = max(0.0, float(p.burnout_meter or 0) * 0.35)
            p.visual_fatigue = max(0.0, float(p.visual_fatigue or 0) * 0.25)
            p.mental_fatigue = max(0.0, float(p.mental_fatigue or 0) * 0.25)

        # 3. Contratos: consome 1 temporada
        expired_count = 0
        cq = await self.db.execute(
            select(Contract).where(
                Contract.status.in_(
                    [ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED]
                )
            )
        )
        for c in cq.scalars().all():
            remaining = c.seasons_duration
            if remaining <= 1:
                c.mark_expired()
                expired_count += 1
                # Free agent se era o time atual do player
                player = await self.db.get(Player, c.player_id)
                if player and player.team_id == c.team_id:
                    # Só libera se não houver outro contrato ativo (acabamos de expirar)
                    player.team_id = None
            else:
                c.seasons_duration = remaining - 1
                c.end_date = date.today() + timedelta(
                    days=SEASON_DURATION_DAYS * c.seasons_duration
                )
                c.rookie_games_played = 0
                c.rookie_extension_triggered = False
                if c.status == ContractStatus.ROOKIE_EXTENDED:
                    c.status = ContractStatus.ACTIVE

        # 4. Redis playoffs + calendário novo
        await redis_client.delete_playoff_state(str(league.id))
        await redis_client.delete_calendar_state(str(league.id))

        league.current_phase = SplitPhase.REGULAR_SEASON
        league.current_week = 0
        league.current_day = 0

        calendar_service = CalendarService(self.db)
        # Limpa cache SM e recria em regular season
        calendar_service._state_machines.pop(str(league.id), None)
        sm = await calendar_service._get_or_create_sm(league)
        # initialize() may restore empty redis as REGULAR_SEASON already (see SM)
        # force to be sure
        if sm.context and sm.context.current_state_name != "REGULAR_SEASON":
            await sm.force_transition_to("REGULAR_SEASON")
        elif sm.context:
            sm.context.current_week = 0
            sm.context.current_day_of_week = 0
            sm.context.total_days_elapsed = 0
            sm.context.is_match_day = False
            await sm._persist_state()

        await self.db.flush()

        logger.info(
            f"[Offseason] Novo split iniciado. Contratos expirados: {expired_count}"
        )
        return {
            "phase": "REGULAR_SEASON",
            "league_id": str(league.id),
            "contracts_expired": expired_count,
            "message": "Novo split iniciado. Standings zerados.",
        }

    async def get_status(self, managed_team_id: Optional[str] = None) -> Dict[str, Any]:
        league = await self.get_league()
        phase = league.current_phase.value if league.current_phase else "OFFSEASON"
        payload: Dict[str, Any] = {
            "phase": phase,
            "is_offseason": phase == "OFFSEASON",
            "league_id": str(league.id),
            "week": league.current_week,
            "day": league.current_day,
        }
        if managed_team_id and phase == "OFFSEASON":
            try:
                contracts = await self.list_team_contracts(managed_team_id)
                payload["contracts"] = contracts
                payload["needs_attention"] = sum(1 for c in contracts if c["needs_renewal"])
            except ValueError:
                payload["contracts"] = []
                payload["needs_attention"] = 0
        return payload
