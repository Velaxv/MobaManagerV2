# -*- coding: utf-8 -*-
"""
Academy e lineup: promover reservas/rookies a titulares e rebaixar.

Regras MVP:
  - 1 titular por role (TOP/JG/MID/BOT/SUP)
  - promote(player): vira is_starter da role; titular anterior vira reserva
  - demote(player): sai da lineup; se sobrar gap, melhor CA da role assume
  - Cláusula rookie exposta no snapshot (participação, threshold 25%)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import get_settings
from src.models.contract import Contract
from src.models.player import Player
from src.models.team import Team
from src.shared.enums import ContractStatus, PlayerRole

logger = logging.getLogger(__name__)
settings = get_settings()

ROLE_ORDER = [
    PlayerRole.TOP,
    PlayerRole.JUNGLE,
    PlayerRole.MID,
    PlayerRole.BOT,
    PlayerRole.SUPPORT,
]

ACTIVE_CONTRACT = (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL)


class AcademyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def load_team(self, team_id: str) -> Team:
        result = await self.db.execute(
            select(Team)
            .where(Team.id == uuid.UUID(str(team_id)))
            .options(
                selectinload(Team.players).selectinload(Player.contracts),
            )
        )
        team = result.scalar_one_or_none()
        if not team:
            raise ValueError("Time não encontrado.")
        return team

    async def ensure_lineup(self, team: Team) -> List[Player]:
        """
        Garante exatamente 1 is_starter por role quando possível.
        Se ninguém marcado, promove o de maior CA de cada role.
        """
        changed = False
        for role in ROLE_ORDER:
            role_players = [p for p in team.players if p.role == role]
            if not role_players:
                continue
            marked = [p for p in role_players if p.is_starter]
            if len(marked) == 1:
                continue
            if len(marked) > 1:
                marked.sort(key=lambda p: int(p.current_ability or 0), reverse=True)
                for i, p in enumerate(marked):
                    p.is_starter = i == 0
                changed = True
                continue
            # Nenhum marcado: melhor CA
            role_players.sort(key=lambda p: int(p.current_ability or 0), reverse=True)
            role_players[0].is_starter = True
            changed = True
        if changed:
            await self.db.flush()
        return team.get_starters()

    def _active_contract(self, player: Player) -> Optional[Contract]:
        for c in getattr(player, "contracts", []) or []:
            if c.status in ACTIVE_CONTRACT:
                return c
        return None

    def _squad_status(self, player: Player, starters: List[Player]) -> str:
        if player in starters or any(str(s.id) == str(player.id) for s in starters):
            return "STARTER"
        if player.is_rookie or "Academy" in (player.name or ""):
            return "ACADEMY"
        return "BENCH"

    def _rookie_info(self, player: Player) -> Dict[str, Any]:
        contract = self._active_contract(player)
        threshold = float(getattr(settings, "rookie_clause_threshold", 0.25) or 0.25)
        if not contract:
            return {
                "has_rookie_clause": False,
                "participation_rate": 0.0,
                "games_played": 0,
                "total_league_games": 0,
                "threshold": threshold,
                "extension_triggered": False,
                "on_track": False,
            }
        rate = float(contract.rookie_participation_rate or 0.0)
        return {
            "has_rookie_clause": bool(contract.has_rookie_clause),
            "participation_rate": rate,
            "games_played": int(contract.rookie_games_played or 0),
            "total_league_games": int(contract.rookie_total_league_games or 0),
            "threshold": threshold,
            "extension_triggered": bool(contract.rookie_extension_triggered),
            "on_track": bool(contract.has_rookie_clause and rate >= threshold),
        }

    def _player_row(self, player: Player, starters: List[Player]) -> Dict[str, Any]:
        status = self._squad_status(player, starters)
        rookie = self._rookie_info(player)
        return {
            "player_id": str(player.id),
            "name": player.name,
            "role": player.role.value if player.role else None,
            "current_ability": int(player.current_ability or 0),
            "potential_ability": int(player.potential_ability or 0),
            "age": player.get_age() if hasattr(player, "get_age") else None,
            "is_rookie": bool(player.is_rookie),
            "is_starter": bool(player.is_starter),
            "squad_status": status,
            "can_promote": status in ("ACADEMY", "BENCH"),
            "can_demote": status == "STARTER",
            "rookie_clause": rookie,
        }

    async def get_roster(self, team_id: str) -> Dict[str, Any]:
        team = await self.load_team(team_id)
        await self.ensure_lineup(team)
        starters = team.get_starters()
        starter_ids = {str(s.id) for s in starters}

        starter_rows = []
        for role in ROLE_ORDER:
            p = next((s for s in starters if s.role == role), None)
            if p:
                starter_rows.append(self._player_row(p, starters))
            else:
                starter_rows.append(
                    {
                        "player_id": None,
                        "name": None,
                        "role": role.value,
                        "squad_status": "EMPTY",
                        "can_promote": False,
                        "can_demote": False,
                    }
                )

        bench = [
            self._player_row(p, starters)
            for p in team.players
            if str(p.id) not in starter_ids
            and not p.is_rookie
            and "Academy" not in (p.name or "")
        ]
        academy = [
            self._player_row(p, starters)
            for p in team.players
            if str(p.id) not in starter_ids
            and (p.is_rookie or "Academy" in (p.name or ""))
        ]
        # Também inclui rookies titulares na seção cláusula
        clause_watch = [
            self._player_row(p, starters)
            for p in team.players
            if self._rookie_info(p).get("has_rookie_clause")
        ]

        return {
            "team_id": str(team.id),
            "team_name": team.name,
            "starters": starter_rows,
            "bench": bench,
            "academy": academy,
            "rookie_clauses": clause_watch,
            "counts": {
                "starters": len([s for s in starter_rows if s.get("player_id")]),
                "bench": len(bench),
                "academy": len(academy),
                "total": len(team.players),
            },
        }

    async def promote(self, team_id: str, player_id: str) -> Dict[str, Any]:
        """Sobe reserva/academy para titular da role (rebaixa o titular atual)."""
        team = await self.load_team(team_id)
        await self.ensure_lineup(team)

        player = next((p for p in team.players if str(p.id) == str(player_id)), None)
        if not player:
            raise ValueError("Jogador não pertence a este time.")
        if not player.role:
            raise ValueError("Jogador sem role definida.")

        demoted = None
        for p in team.players:
            if p.role == player.role and p.is_starter and str(p.id) != str(player.id):
                p.is_starter = False
                demoted = p

        player.is_starter = True
        # Promoção de academy: deixa de ser só "rookie de base" na UI se já joga no main?
        # Mantém is_rookie — cláusula ainda vale. Apenas marca titular.

        await self.db.commit()
        await self.db.refresh(player)

        return {
            "message": f"{player.name} promovido a titular ({player.role.value}).",
            "promoted": {
                "player_id": str(player.id),
                "name": player.name,
                "role": player.role.value,
                "is_rookie": player.is_rookie,
            },
            "demoted": (
                {
                    "player_id": str(demoted.id),
                    "name": demoted.name,
                    "role": demoted.role.value if demoted.role else None,
                }
                if demoted
                else None
            ),
            "roster": await self.get_roster(team_id),
        }

    async def demote(self, team_id: str, player_id: str) -> Dict[str, Any]:
        """Rebaixa titular; se possível, promove o melhor da role no banco/academy."""
        team = await self.load_team(team_id)
        await self.ensure_lineup(team)

        player = next((p for p in team.players if str(p.id) == str(player_id)), None)
        if not player:
            raise ValueError("Jogador não pertence a este time.")
        if not player.is_starter:
            raise ValueError("Jogador não é titular.")

        role = player.role
        player.is_starter = False

        replacement = None
        if role:
            candidates = [
                p
                for p in team.players
                if p.role == role and str(p.id) != str(player.id)
            ]
            candidates.sort(key=lambda p: int(p.current_ability or 0), reverse=True)
            if candidates:
                replacement = candidates[0]
                replacement.is_starter = True

        await self.db.commit()

        return {
            "message": f"{player.name} rebaixado da lineup principal.",
            "demoted": {
                "player_id": str(player.id),
                "name": player.name,
                "role": role.value if role else None,
            },
            "promoted": (
                {
                    "player_id": str(replacement.id),
                    "name": replacement.name,
                    "role": replacement.role.value if replacement.role else None,
                }
                if replacement
                else None
            ),
            "roster": await self.get_roster(team_id),
        }

    async def set_lineup(
        self,
        team_id: str,
        starter_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Define lineup pelos ids (ideal: 5, um por role).
        Roles sem id mantêm/auto-preenchem com ensure_lineup.
        """
        team = await self.load_team(team_id)
        by_id = {str(p.id): p for p in team.players}

        chosen: List[Player] = []
        for sid in starter_ids:
            p = by_id.get(str(sid))
            if p:
                chosen.append(p)

        # Valida roles únicas
        seen_roles = set()
        for p in chosen:
            if p.role in seen_roles:
                raise ValueError(f"Role duplicada na lineup: {p.role.value}")
            seen_roles.add(p.role)

        for p in team.players:
            p.is_starter = False
        for p in chosen:
            p.is_starter = True

        await self.db.flush()
        await self.ensure_lineup(team)
        await self.db.commit()

        return {
            "message": "Lineup atualizada.",
            "roster": await self.get_roster(team_id),
        }
