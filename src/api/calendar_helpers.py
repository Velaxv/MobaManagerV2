"""Helpers de calendário semanal (round-robin + state machine)."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Team, League
from src.models.league import LeagueTeam
from src.modules.calendar.calendar_service import CalendarService
from src.shared.enums import CalendarDayType


async def teams_for_week_calendar(db: AsyncSession, league_id) -> list:
    """Times da liga no formato usado por build_week_calendar (ordem livre)."""
    result = await db.execute(
        select(Team)
        .join(LeagueTeam, LeagueTeam.team_id == Team.id)
        .where(LeagueTeam.league_id == league_id)
    )
    return [
        {"id": str(t.id), "name": t.name, "abbreviation": t.abbreviation}
        for t in result.scalars().all()
    ]


async def build_week_calendar_for_league(
    db: AsyncSession,
    league: League,
    managed_team_id: Optional[str] = None,
) -> dict:
    """
    Estado do calendário + grade semanal com adversário real do round-robin.
    Prefere a State Machine (Redis) quando disponível para week/day_of_week.
    """
    from src.shared.week_calendar import build_week_calendar

    phase = league.current_phase.value if league.current_phase else "OFFSEASON"
    day_of_week = max(0, (int(league.current_day or 1) - 1) % 7)
    current_week = int(league.current_week or 0)
    current_day = int(league.current_day or 0)

    # Usa a SM da liga já carregada (evita re-query UUID string vs UUID column)
    calendar_service = CalendarService(db)
    sm = await calendar_service._get_or_create_sm(league)
    if sm.is_initialized and sm.context is not None:
        ctx = sm.context
        day_of_week = int(ctx.current_day_of_week or 0)
        current_week = int(ctx.current_week or 0)
        current_day = int(ctx.total_days_elapsed or current_day)
        if ctx.current_state_name:
            phase = ctx.current_state_name

    team_rows = await teams_for_week_calendar(db, league.id)
    week_calendar = build_week_calendar(
        current_day_of_week=day_of_week,
        current_week=current_week,
        phase=phase,
        teams=team_rows,
        managed_team_id=managed_team_id,
    )

    # Próximo confronto do manager na semana atual (match day futuro ou hoje)
    next_match = None
    today = day_of_week % 7
    for day in week_calendar:
        if day.get("type") != CalendarDayType.MATCH_DAY.value:
            continue
        if day.get("dayIndex", 0) < today:
            continue
        if managed_team_id and day.get("opponentAbbr"):
            next_match = day
            break
        if not managed_team_id and day.get("eventName"):
            next_match = day
            break

    return {
        "current_day": current_day,
        "current_week": current_week,
        "current_phase": phase,
        "day_of_week": day_of_week,
        "league_id": str(league.id),
        "league_name": league.name,
        "week_calendar": week_calendar,
        "next_match": {
            "dayIndex": next_match["dayIndex"],
            "dayOfWeek": next_match["dayOfWeek"],
            "eventName": next_match.get("eventName"),
            "opponentAbbr": next_match.get("opponentAbbr"),
            "opponentName": next_match.get("opponentName"),
            "isHome": next_match.get("isHome"),
            "roundIndex": next_match.get("roundIndex"),
        }
        if next_match
        else None,
    }
