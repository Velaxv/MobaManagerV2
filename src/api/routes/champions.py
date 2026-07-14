"""Lista de campeões."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models import Champion

router = APIRouter(tags=["champions"])


@router.get("/champions", status_code=status.HTTP_200_OK)
async def get_champions(db: AsyncSession = Depends(get_db)):
    """Busca a lista de todos os 173 campeões cadastrados."""
    query = await db.execute(select(Champion))
    champs = query.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "primary_role": c.primary_role,
            "secondary_role": c.secondary_role,
            "class_type": c.class_type,
            "damage_type": c.damage_type,
            "early_game_power": c.early_game_power,
            "late_game_scaling": c.late_game_scaling,
            "mechanical_difficulty": c.mechanical_difficulty,
            "utility": c.utility,
        }
        for c in champs
    ]
