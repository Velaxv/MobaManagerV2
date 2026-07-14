"""Patches competitivos — notas e meta ativa."""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.modules.simulation.patch_service import PatchService

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["patches"])


def _resolve_date(days_elapsed: Optional[int]) -> date:
    if days_elapsed is None:
        return date.today()
    return date.today() + timedelta(days=max(0, int(days_elapsed)))


@router.get("/patches", status_code=status.HTTP_200_OK)
async def list_patches(
    days_elapsed: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista patches + status (active/upcoming/expired) na data do calendário do jogo."""
    svc = PatchService(db)
    try:
        return await svc.get_status(_resolve_date(days_elapsed))
    except Exception as e:
        logger.error(f"list patches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patches/current", status_code=status.HTTP_200_OK)
async def current_patch(
    days_elapsed: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Patch ativo, changelist e badges para draft."""
    svc = PatchService(db)
    try:
        status_payload = await svc.get_status(_resolve_date(days_elapsed))
        return {
            "calendar_date": status_payload["calendar_date"],
            "active": status_payload["active"],
            "upcoming": status_payload["upcoming"],
            "badges": status_payload["badges"],
            "bias": status_payload["bias"],
        }
    except Exception as e:
        logger.error(f"current patch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patches/badges", status_code=status.HTTP_200_OK)
async def patch_badges(db: AsyncSession = Depends(get_db)):
    """
    Mapa champion->BUFF|NERF do patch ativo (cache Redis).
    Usado pelo draft FE para badges e ordenação.
    """
    from src.core.redis_client import redis_client

    version = await redis_client.get_generic("patch:current:version")
    if not version:
        # Tenta aquecer cache com data de hoje
        await PatchService(db).update_patch_cache(date.today())
        version = await redis_client.get_generic("patch:current:version")

    badges = await PatchService.get_cached_badges()
    changes = await redis_client.get_generic("patch:current:changes") or []
    return {
        "version": version,
        "badges": badges,
        "changes": changes,
    }


@router.post("/patches/refresh", status_code=status.HTTP_200_OK)
async def refresh_patch_cache(
    days_elapsed: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Dev: força recálculo do cache de patch."""
    d = _resolve_date(days_elapsed)
    svc = PatchService(db)
    # Invalidar versão para forçar rebuild
    from src.core.redis_client import redis_client

    await redis_client.delete("patch:current:version")
    version = await svc.update_patch_cache(d)
    status_payload = await svc.get_status(d)
    return {"message": "Cache de patch atualizado.", "version": version, **status_payload}
