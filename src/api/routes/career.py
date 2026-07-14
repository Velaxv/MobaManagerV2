"""Save / load de carreira."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import CareerSaveRequest
from src.core.database import get_db

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["career"])


@router.get("/career/saves", status_code=status.HTTP_200_OK)
async def list_career_saves():
    """Lista saves JSON em disco (pasta saves/)."""
    from src.modules.career.save_service import list_save_files

    return {"saves": list_save_files()}


@router.post("/career/save", status_code=status.HTTP_201_CREATED)
async def save_career(req: CareerSaveRequest, db: AsyncSession = Depends(get_db)):
    """Salva progresso da carreira no slot indicado."""
    from src.modules.career.save_service import CareerSaveService

    svc = CareerSaveService(db)
    try:
        result = await svc.save_career(
            slot=req.slot.strip() or "slot1",
            manager_name=req.manager_name.strip(),
            team_id=req.team_id,
            label=req.label,
        )
        return {"message": "Carreira salva.", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao salvar carreira: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/career/load/{slot}", status_code=status.HTTP_200_OK)
async def load_career(slot: str, db: AsyncSession = Depends(get_db)):
    """
    Carrega save no DB + Redis e devolve manager/time para o frontend rehidratar.
    """
    from src.modules.career.save_service import CareerSaveService

    svc = CareerSaveService(db)
    try:
        result = await svc.load_career(slot)
        return {"message": "Carreira carregada.", **result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao carregar carreira: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/career/saves/{slot}", status_code=status.HTTP_200_OK)
async def delete_career_save(slot: str):
    from src.modules.career.save_service import CareerSaveService

    ok = CareerSaveService.delete_save_static(slot)
    if not ok:
        raise HTTPException(status_code=404, detail="Save não encontrado.")
    return {"message": f"Save '{slot}' removido."}
