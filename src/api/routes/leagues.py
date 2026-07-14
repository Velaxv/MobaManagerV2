"""Ligas, standings, playoffs e resultados da rodada."""

import logging
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.serializers import match_summary_row
from src.core.database import get_db
from src.core.redis_client import redis_client
from src.models import Team, League, LeagueTeam, Match
from src.modules.calendar.calendar_service import CalendarService
from src.shared.enums import SplitPhase

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["leagues"])


@router.get("/leagues", status_code=status.HTTP_200_OK)
async def get_leagues(db: AsyncSession = Depends(get_db)):
    """Lista ligas ativas (seed atual = 1 CBLOL)."""
    query = await db.execute(select(League))
    leagues = query.scalars().all()
    return [
        {
            "id": str(lg.id),
            "name": lg.name,
            "abbreviation": lg.abbreviation,
            "region": lg.region.value if lg.region else None,
            "current_phase": lg.current_phase.value if lg.current_phase else None,
            "current_week": lg.current_week,
            "current_day": lg.current_day,
        }
        for lg in leagues
    ]


@router.get("/leagues/{league_id}/standings", status_code=status.HTTP_200_OK)
async def get_league_standings(league_id: str, db: AsyncSession = Depends(get_db)):
    """Busca a tabela de classificação (standings) de uma liga."""
    query = await db.execute(
        select(LeagueTeam).where(LeagueTeam.league_id == uuid.UUID(league_id))
    )
    teams = query.scalars().all()

    standings = []
    for lt in teams:
        team_query = await db.execute(select(Team).where(Team.id == lt.team_id))
        t = team_query.scalar_one()
        standings.append({
            "team_id": str(lt.team_id),
            "team_name": t.name,
            "wins": lt.wins,
            "losses": lt.losses,
            "points": lt.points,
            "win_rate": f"{lt.win_rate * 100:.1f}%",
            "is_in_playoffs": bool(lt.is_in_playoffs),
            "playoff_seed": lt.playoff_seed,
            "final_placement": lt.final_placement,
            "prize_earned": float(lt.prize_earned or 0),
        })

    if any(s.get("final_placement") for s in standings):
        standings.sort(
            key=lambda x: (
                x["final_placement"] is None,
                x["final_placement"] if x["final_placement"] is not None else 99,
                -x["points"],
                -x["wins"],
            )
        )
    else:
        standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)
    return standings


@router.get("/leagues/{league_id}/playoffs", status_code=status.HTTP_200_OK)
async def get_league_playoffs(league_id: str, db: AsyncSession = Depends(get_db)):
    """
    Bracket de playoffs (top 6). Gera sob demanda se a fase já for PLAYOFFS.
    """
    from src.modules.calendar.playoff_service import PlayoffService

    league = await db.get(League, uuid.UUID(league_id))
    if not league:
        raise HTTPException(status_code=404, detail="Liga não encontrada.")

    ps = PlayoffService(db)
    bracket = await ps.get_bracket(league_id)

    if not bracket and league.current_phase == SplitPhase.PLAYOFFS:
        try:
            bracket = await ps.ensure_bracket(league)
            await db.commit()
        except Exception as e:
            logger.error(f"Falha ao gerar bracket: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    if not bracket:
        return {
            "status": "not_started",
            "message": "Playoffs ainda não iniciados. Avance a temporada regular até o fim.",
            "bracket": None,
        }

    return {"status": bracket.get("status", "active"), "bracket": bracket}


@router.post("/leagues/{league_id}/playoffs/start", status_code=status.HTTP_201_CREATED)
async def force_start_playoffs(league_id: str, db: AsyncSession = Depends(get_db)):
    """
    Dev/playtest: força PLAYOFFS + bracket top 6 sem avançar semanas.
    """
    from src.modules.calendar.playoff_service import PlayoffService

    league = await db.get(League, uuid.UUID(league_id))
    if not league:
        raise HTTPException(status_code=404, detail="Liga não encontrada.")

    calendar_service = CalendarService(db)
    sm = await calendar_service._get_or_create_sm(league)
    await sm.force_transition_to("PLAYOFFS")

    league.current_phase = SplitPhase.PLAYOFFS
    league.current_week = 0

    await redis_client.delete_playoff_state(str(league.id))
    ps = PlayoffService(db)
    bracket = await ps.initialize_from_standings(league)
    await db.commit()

    return {
        "message": "Playoffs iniciados (forçado).",
        "league_id": str(league.id),
        "bracket": bracket,
    }


@router.get("/leagues/{league_id}/matches", status_code=status.HTTP_200_OK)
async def list_league_matches(
    league_id: str,
    week: Optional[int] = None,
    is_playoff: Optional[bool] = None,
    latest_round: bool = True,
    limit: int = 40,
    db: AsyncSession = Depends(get_db),
):
    """
    Lista partidas da liga (resultados da rodada).

    - latest_round=true (default): só a semana mais recente que tem jogos.
    - week=: filtra semana específica (ignora latest_round).
    """
    league = await db.get(League, uuid.UUID(league_id))
    if not league:
        raise HTTPException(status_code=404, detail="Liga não encontrada.")

    limit = max(1, min(int(limit or 40), 100))
    base = select(Match).where(Match.league_id == uuid.UUID(league_id))

    if is_playoff is not None:
        base = base.where(Match.is_playoff == is_playoff)

    if week is not None:
        base = base.where(Match.split_week == int(week))
    elif latest_round:
        sub = select(Match.split_week).where(Match.league_id == uuid.UUID(league_id))
        if is_playoff is not None:
            sub = sub.where(Match.is_playoff == is_playoff)
        sub = sub.order_by(Match.split_week.desc(), Match.scheduled_at.desc()).limit(1)
        latest = (await db.execute(sub)).scalar_one_or_none()
        if latest is not None:
            base = base.where(Match.split_week == latest)

    query = await db.execute(
        base.order_by(Match.scheduled_at.desc()).limit(limit)
    )
    matches = list(query.scalars().all())

    team_ids = set()
    for m in matches:
        team_ids.add(m.blue_team_id)
        team_ids.add(m.red_team_id)
    teams_map: Dict[uuid.UUID, Team] = {}
    if team_ids:
        tq = await db.execute(select(Team).where(Team.id.in_(list(team_ids))))
        for t in tq.scalars().all():
            teams_map[t.id] = t

    rows = []
    for m in matches:
        blue = teams_map.get(m.blue_team_id)
        red = teams_map.get(m.red_team_id)
        if not blue or not red:
            continue
        rows.append(match_summary_row(m, blue, red))

    rows.reverse()

    return {
        "league_id": league_id,
        "count": len(rows),
        "week": rows[0]["split_week"] if rows else week,
        "matches": rows,
    }
