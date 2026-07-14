"""Rotas de times, elenco, finanças e treino."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import TrainingPlanRequest
from src.api.serializers import serialize_player
from src.core.database import get_db
from src.models import Player, Team

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["teams"])


@router.get("/teams", status_code=status.HTTP_200_OK)
async def get_teams(db: AsyncSession = Depends(get_db)):
    """Busca todas as equipes cadastradas."""
    query = await db.execute(select(Team))
    teams = query.scalars().all()
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "abbreviation": t.abbreviation,
            "budget": float(t.budget),
            "monthlyRevenue": float(t.monthly_revenue),
            "region": t.region.value if t.region else None,
        }
        for t in teams
    ]


@router.get("/teams/{team_id}/players", status_code=status.HTTP_200_OK)
async def get_team_players(team_id: str, db: AsyncSession = Depends(get_db)):
    """Busca os jogadores de uma equipe específica (com contrato e pool)."""
    query = await db.execute(
        select(Player)
        .options(selectinload(Player.contracts))
        .where(Player.team_id == uuid.UUID(team_id))
    )
    players = query.scalars().all()
    return [serialize_player(p) for p in players]


@router.get("/teams/{team_id}/finance", status_code=status.HTTP_200_OK)
async def get_team_finance(team_id: str, db: AsyncSession = Depends(get_db)):
    """
    Snapshot financeiro do clube: caixa, receita, folha, net mensal e lista de salários.
    """
    from src.modules.career.finance_service import FinanceService

    try:
        return await FinanceService(db).get_snapshot(team_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/teams/{team_id}/finance/month-tick", status_code=status.HTTP_200_OK)
async def force_finance_month_tick(team_id: str, db: AsyncSession = Depends(get_db)):
    """Dev: força um tick mensal (receita − folha) neste time."""
    from src.modules.career.finance_service import FinanceService

    team = await db.get(Team, uuid.UUID(team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Time não encontrado.")
    try:
        event = await FinanceService(db).process_monthly_tick_for_team(team)
        return {"message": "Tick financeiro aplicado.", "event": event}
    except Exception as e:
        logger.error(f"Finance tick: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teams/{team_id}/training", status_code=status.HTTP_200_OK)
async def get_team_training(team_id: str, db: AsyncSession = Depends(get_db)):
    """
    Plano de treino (foco/intensidade) + última sessão de desenvolvimento.
    """
    from src.modules.career.training_service import TrainingService

    try:
        return await TrainingService(db).get_status(team_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/teams/{team_id}/training", status_code=status.HTTP_200_OK)
async def set_team_training(
    team_id: str,
    req: TrainingPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Define foco e intensidade de treino do clube."""
    from src.modules.career.training_service import TrainingService

    try:
        plan = await TrainingService(db).set_plan(
            team_id,
            focus=req.focus,
            intensity=req.intensity,
        )
        return {"message": "Plano de treino atualizado.", **plan}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Training plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teams/{team_id}/training/session", status_code=status.HTTP_200_OK)
async def force_training_session(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Dev/playtest: força uma sessão de treino TRAINING no elenco."""
    from src.modules.career.training_service import TrainingService
    from src.shared.enums import CalendarDayType

    svc = TrainingService(db)
    try:
        team = await svc.load_team_with_players(team_id)
        session = await svc.process_team_day(
            team,
            CalendarDayType.TRAINING.value,
            source="manual",
        )
        await db.commit()
        return {"message": "Sessão de treino aplicada.", "session": session}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Training session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
