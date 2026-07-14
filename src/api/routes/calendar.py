"""Rotas de calendário / rotina diária."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.calendar_helpers import build_week_calendar_for_league
from src.core.database import get_db
from src.models import League
from src.modules.calendar.calendar_service import CalendarService

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["calendar"])


@router.get("/calendar", status_code=status.HTTP_200_OK)
async def get_calendar_state(
    managed_team_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o estado atual do calendário (liga ativa) + grade semanal.

    Query param opcional:
      managed_team_id — personaliza match days com adversário real do round-robin.
    """
    from src.shared.week_calendar import build_week_calendar

    league_query = await db.execute(select(League).limit(1))
    league = league_query.scalar_one_or_none()
    if not league:
        return {
            "current_day": 1,
            "current_week": 0,
            "current_phase": "OFFSEASON",
            "day_of_week": 0,
            "league_id": None,
            "week_calendar": build_week_calendar(0, 0, "OFFSEASON"),
            "next_match": None,
        }

    return await build_week_calendar_for_league(
        db, league, managed_team_id=managed_team_id
    )


@router.post("/calendar/advance", status_code=status.HTTP_200_OK)
async def advance_calendar(
    managed_team_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Avança um dia no calendário do jogo.
    Processa a State Machine do calendário e roda o BurnoutService
    para aplicar penalidades de fadiga e burnout aos jogadores.

    Query param opcional:
      managed_team_id — partidas desse time ficam para o jogador (não auto-simula).
    """
    calendar_service = CalendarService(db)
    results = await calendar_service.advance_all_leagues(managed_team_id=managed_team_id)
    return {
        "message": "Calendário avançado em 1 dia.",
        "results": results,
    }
