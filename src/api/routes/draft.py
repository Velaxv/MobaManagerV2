"""Draft AI turno a turno (oponente no frontend)."""

import logging
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import DraftAIDecisionRequest
from src.core.database import get_db
from src.models import Team
from src.modules.draft.snake_draft import DraftTeam

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["draft"])


@router.post("/draft/ai-decision", status_code=status.HTTP_200_OK)
async def draft_ai_decision(req: DraftAIDecisionRequest, db: AsyncSession = Depends(get_db)):
    """
    Usa DraftAI do backend para o turno do oponente (ou qualquer lado).
    Reconstrói o DraftState a partir do estado do frontend.
    """
    from src.modules.draft.snake_draft import DraftState, DRAFT_ORDER as BACKEND_DRAFT_ORDER
    from src.modules.draft.draft_ai import DraftAI

    side = (req.acting_side or "").upper()
    if side not in ("BLUE", "RED"):
        raise HTTPException(status_code=400, detail="acting_side deve ser BLUE ou RED.")

    blue = await db.get(Team, uuid.UUID(req.blue_team_id))
    red = await db.get(Team, uuid.UUID(req.red_team_id))
    if not blue or not red:
        raise HTTPException(status_code=404, detail="Time blue/red não encontrado.")

    def _norm_picks(picks: List[Dict[str, str]]) -> List[dict]:
        out = []
        for p in picks or []:
            champ = p.get("champion") or p.get("name")
            if not champ:
                continue
            role = p.get("role") or p.get("role_hint") or "MID"
            out.append({"champion": champ, "role_hint": role})
        return out

    turn = max(0, min(int(req.current_turn or 0), 19))
    state = DraftState(
        match_id="interactive",
        blue_bans=list(req.blue_bans or []),
        red_bans=list(req.red_bans or []),
        blue_picks=_norm_picks(req.blue_picks),
        red_picks=_norm_picks(req.red_picks),
        current_turn=turn,
        is_complete=turn >= 20,
    )

    if state.is_complete:
        raise HTTPException(status_code=400, detail="Draft já completo.")

    expected = BACKEND_DRAFT_ORDER[turn]
    expected_side = expected[1]
    expected_action = expected[2]
    acting = DraftTeam.BLUE if side == "BLUE" else DraftTeam.RED
    if expected_side != acting:
        raise HTTPException(
            status_code=400,
            detail=f"Turno {turn} é de {expected_side.value}, não de {side}.",
        )

    team_obj = blue if acting == DraftTeam.BLUE else red
    opp_obj = red if acting == DraftTeam.BLUE else blue

    try:
        champion, role = DraftAI().make_decision(
            draft_state=state,
            team_side=acting,
            team_obj=team_obj,
            opponent_team_obj=opp_obj,
        )
    except Exception as e:
        logger.error(f"DraftAI falhou: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DraftAI error: {e}")

    return {
        "champion": champion,
        "role": role.value if role else None,
        "action": expected_action.value if hasattr(expected_action, "value") else str(expected_action),
        "team": side,
        "current_turn": turn,
        "source": "backend_draft_ai",
    }
