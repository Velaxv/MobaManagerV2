"""Mercado e transferências."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import SignPlayerRequest
from src.api.serializers import serialize_player
from src.core.database import get_db
from src.models import Player, Contract
from src.shared.enums import ContractStatus

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["market"])


@router.get("/market/players", status_code=status.HTTP_200_OK)
async def get_market_players(
    exclude_team_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Mercado: jogadores de outros times + agentes livres.
    exclude_team_id remove o elenco do manager da listagem.
    """
    query = select(Player).options(selectinload(Player.contracts))
    if exclude_team_id:
        query = query.where(
            (Player.team_id != uuid.UUID(exclude_team_id)) | (Player.team_id.is_(None))
        )
    result = await db.execute(query)
    players = result.scalars().all()
    return [serialize_player(p) for p in players]


@router.get("/transfers/valuation/{player_id}", status_code=status.HTTP_200_OK)
async def transfer_valuation(player_id: str, db: AsyncSession = Depends(get_db)):
    """Valor de mercado e exigências (taxa, salário, duração)."""
    from src.modules.career.transfer_service import TransferService

    try:
        return await TransferService(db).get_valuation(player_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/transfers/negotiate", status_code=status.HTTP_200_OK)
async def negotiate_transfer(req: SignPlayerRequest, db: AsyncSession = Depends(get_db)):
    """
    Avalia oferta: accepted | counter | rejected (+ contra-proposta).
    Não altera o banco — use /transfers/sign para concluir.
    """
    from src.modules.career.transfer_service import TransferService

    try:
        return await TransferService(db).negotiate(
            buyer_team_id=req.team_id,
            player_id=req.player_id,
            transfer_fee=req.transfer_fee,
            monthly_salary=req.monthly_salary,
            seasons=req.seasons,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfers/sign", status_code=status.HTTP_200_OK)
async def sign_player(req: SignPlayerRequest, db: AsyncSession = Depends(get_db)):
    """
    Conclui transferência após negociação aceita:
    debita taxa, credita vendedor, cria contrato ACTIVE.
    """
    from src.modules.career.transfer_service import TransferService

    try:
        result = await TransferService(db).complete_transfer(
            buyer_team_id=req.team_id,
            player_id=req.player_id,
            transfer_fee=req.transfer_fee,
            monthly_salary=req.monthly_salary,
            seasons=req.seasons,
            skip_negotiation=False,
        )
        player = await db.get(Player, uuid.UUID(req.player_id))
        if player:
            await db.refresh(player)
            cq = await db.execute(
                select(Contract).where(
                    Contract.player_id == player.id,
                    Contract.status == ContractStatus.ACTIVE,
                )
            )
            contract = cq.scalar_one_or_none()
            result["player"] = serialize_player(player, contract)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transfer sign error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
