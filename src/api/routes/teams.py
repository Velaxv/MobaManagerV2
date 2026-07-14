"""Rotas de times, elenco, finanças e treino."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import (
    TrainingPlanRequest,
    ScoutAssignRequest,
    AcademyPlayerRequest,
    LineupRequest,
)
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
    """Busca os jogadores de uma equipe específica (com contrato e pool + scouting)."""
    from src.modules.career.scouting_service import ScoutingService
    from src.modules.career.academy_service import AcademyService

    # Garante is_starter coerente (1 por role) em times antigos / pós-seed
    try:
        team = await AcademyService(db).load_team(team_id)
        await AcademyService(db).ensure_lineup(team)
        await db.commit()
    except ValueError:
        pass

    query = await db.execute(
        select(Player)
        .options(selectinload(Player.contracts))
        .where(Player.team_id == uuid.UUID(team_id))
    )
    players = query.scalars().all()
    knowledge = await ScoutingService(db).get_knowledge(team_id)
    return [
        serialize_player(
            p,
            scouting_knowledge=knowledge.get(str(p.id)),
            is_own_roster=True,
            apply_scouting_mask=True,
        )
        for p in players
    ]


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


@router.get("/teams/{team_id}/scouting", status_code=status.HTTP_200_OK)
async def get_team_scouting(team_id: str, db: AsyncSession = Depends(get_db)):
    """Status de scouting: assignment, staff power, conhecimento acumulado."""
    from src.modules.career.scouting_service import ScoutingService

    try:
        return await ScoutingService(db).get_status(team_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/teams/{team_id}/scouting/assign", status_code=status.HTTP_200_OK)
async def assign_scout(
    team_id: str,
    req: ScoutAssignRequest,
    db: AsyncSession = Depends(get_db),
):
    """Atribui o scouting a um jogador (1 alvo por vez)."""
    from src.modules.career.scouting_service import ScoutingService

    try:
        return await ScoutingService(db).assign(
            team_id,
            player_id=req.player_id,
            focus=req.focus,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Scout assign: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teams/{team_id}/scouting/clear", status_code=status.HTTP_200_OK)
async def clear_scout_assignment(team_id: str, db: AsyncSession = Depends(get_db)):
    """Cancela a atribuição de scouting ativa."""
    from src.modules.career.scouting_service import ScoutingService

    try:
        # Valida time
        await ScoutingService(db).get_status(team_id)
        return await ScoutingService(db).clear_assignment(team_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teams/{team_id}/academy", status_code=status.HTTP_200_OK)
async def get_team_academy(team_id: str, db: AsyncSession = Depends(get_db)):
    """
    Roster estruturado: titulares, reservas, academy + cláusulas rookie.
    Garante lineup (1 starter por role) se necessário.
    """
    from src.modules.career.academy_service import AcademyService

    try:
        return await AcademyService(db).get_roster(team_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/teams/{team_id}/academy/promote", status_code=status.HTTP_200_OK)
async def promote_player(
    team_id: str,
    req: AcademyPlayerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Promove reserva/academy a titular da role (rebaixa o titular atual)."""
    from src.modules.career.academy_service import AcademyService

    try:
        return await AcademyService(db).promote(team_id, req.player_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Promote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teams/{team_id}/academy/demote", status_code=status.HTTP_200_OK)
async def demote_player(
    team_id: str,
    req: AcademyPlayerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rebaixa titular; melhor CA da role assume se houver."""
    from src.modules.career.academy_service import AcademyService

    try:
        return await AcademyService(db).demote(team_id, req.player_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Demote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teams/{team_id}/lineup", status_code=status.HTTP_200_OK)
async def set_team_lineup(
    team_id: str,
    req: LineupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Define lineup principal pelos player ids (ideal: 5, roles distintas)."""
    from src.modules.career.academy_service import AcademyService

    try:
        return await AcademyService(db).set_lineup(team_id, req.starter_ids or [])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lineup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
