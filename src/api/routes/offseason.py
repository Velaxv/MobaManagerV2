"""Offseason: renovar / liberar / novo split."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import RenewContractRequest, ReleasePlayerRequest
from src.core.database import get_db

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["offseason"])


@router.get("/offseason/status", status_code=status.HTTP_200_OK)
async def offseason_status(
    managed_team_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Status da offseason + contratos do time gerenciado."""
    from src.modules.career.offseason_service import OffseasonService

    try:
        return await OffseasonService(db).get_status(managed_team_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/offseason/start", status_code=status.HTTP_201_CREATED)
async def force_start_offseason(db: AsyncSession = Depends(get_db)):
    """Dev/playtest: força fase OFFSEASON."""
    from src.modules.career.offseason_service import OffseasonService

    try:
        return await OffseasonService(db).force_offseason()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/offseason/contracts", status_code=status.HTTP_200_OK)
async def offseason_contracts(team_id: str, db: AsyncSession = Depends(get_db)):
    """Lista contratos do time para renovação."""
    from src.modules.career.offseason_service import OffseasonService

    try:
        rows = await OffseasonService(db).list_team_contracts(team_id)
        return {"team_id": team_id, "contracts": rows}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/offseason/renew", status_code=status.HTTP_200_OK)
async def offseason_renew(req: RenewContractRequest, db: AsyncSession = Depends(get_db)):
    from src.modules.career.offseason_service import OffseasonService

    try:
        result = await OffseasonService(db).renew_contract(
            team_id=req.team_id,
            player_id=req.player_id,
            seasons=req.seasons,
            monthly_salary=req.monthly_salary,
        )
        return {"message": "Contrato renovado.", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/offseason/release", status_code=status.HTTP_200_OK)
async def offseason_release(req: ReleasePlayerRequest, db: AsyncSession = Depends(get_db)):
    from src.modules.career.offseason_service import OffseasonService

    try:
        result = await OffseasonService(db).release_player(
            team_id=req.team_id,
            player_id=req.player_id,
        )
        return {"message": "Jogador liberado.", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/offseason/new-split", status_code=status.HTTP_200_OK)
async def offseason_new_split(db: AsyncSession = Depends(get_db)):
    """Fecha offseason, zera tabela e inicia REGULAR_SEASON."""
    from src.modules.career.offseason_service import OffseasonService

    try:
        return await OffseasonService(db).start_new_split()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao iniciar novo split: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
