"""Draft AI turno a turno + scout advisor (manager)."""

import logging
import uuid
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    DraftAIDecisionRequest,
    DraftScoutAdviceRequest,
    DraftScoutActionRequest,
    DraftScoutEvaluateRequest,
)
from src.core.database import get_db
from src.models import Champion, Team
from src.modules.draft.snake_draft import DraftTeam

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["draft"])


def _norm_picks(picks: List[Dict[str, str]]) -> List[dict]:
    out = []
    for p in picks or []:
        champ = p.get("champion") or p.get("name")
        if not champ:
            continue
        role = p.get("role") or p.get("role_hint") or "MID"
        out.append({"champion": champ, "role_hint": role})
    return out


def _build_draft_state(req, turn: int):
    from src.modules.draft.snake_draft import DraftState

    return DraftState(
        match_id="interactive",
        blue_bans=list(req.blue_bans or []),
        red_bans=list(req.red_bans or []),
        blue_picks=_norm_picks(req.blue_picks),
        red_picks=_norm_picks(req.red_picks),
        current_turn=turn,
        is_complete=turn >= 20,
    )


async def _load_patch_context(db: AsyncSession) -> Tuple[Dict[str, float], Optional[str]]:
    from datetime import date

    from src.modules.simulation.patch_service import PatchService

    patch_bias = await PatchService.get_cached_bias()
    patch_version: Optional[str] = None
    try:
        status_data = await PatchService(db).get_status(date.today())
        if not patch_bias:
            patch_bias = status_data.get("bias") or await PatchService.get_cached_bias() or {}
        active = status_data.get("active") or {}
        patch_version = active.get("version")
    except Exception:
        if not patch_bias:
            try:
                await PatchService(db).update_patch_cache(date.today())
                patch_bias = await PatchService.get_cached_bias() or {}
            except Exception:
                patch_bias = {}
    return patch_bias or {}, patch_version


@router.post("/draft/ai-decision", status_code=status.HTTP_200_OK)
async def draft_ai_decision(req: DraftAIDecisionRequest, db: AsyncSession = Depends(get_db)):
    """
    Usa DraftAI do backend para o turno do oponente (ou qualquer lado).
    Reconstrói o DraftState a partir do estado do frontend.
    """
    from src.modules.draft.snake_draft import DRAFT_ORDER as BACKEND_DRAFT_ORDER
    from src.modules.draft.draft_ai import DraftAI

    side = (req.acting_side or "").upper()
    if side not in ("BLUE", "RED"):
        raise HTTPException(status_code=400, detail="acting_side deve ser BLUE ou RED.")

    blue = await db.get(Team, uuid.UUID(req.blue_team_id))
    red = await db.get(Team, uuid.UUID(req.red_team_id))
    if not blue or not red:
        raise HTTPException(status_code=404, detail="Time blue/red não encontrado.")

    turn = max(0, min(int(req.current_turn or 0), 19))
    state = _build_draft_state(req, turn)

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

    patch_bias, _ = await _load_patch_context(db)

    try:
        champion, role = DraftAI(patch_bias=patch_bias or {}).make_decision(
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
        "patch_bias_applied": bool(patch_bias),
    }


@router.post("/draft/scout-advice", status_code=status.HTTP_200_OK)
async def draft_scout_advice(req: DraftScoutAdviceRequest, db: AsyncSession = Depends(get_db)):
    """
    Conselho do scout da comissão no turno do manager.

    Combina maestria, patch, role, meta seed (WR/PR), counters, staff e
    scouting de estrelas do oponente (conhecimento do hub).
    """
    from src.modules.career.scouting_service import ScoutingService
    from src.modules.draft.draft_scout import DraftScoutAdvisor
    from src.modules.draft.scout_session import ScoutSessionService
    from src.modules.draft.snake_draft import DRAFT_ORDER as BACKEND_DRAFT_ORDER

    side = (req.acting_side or "").upper()
    if side not in ("BLUE", "RED"):
        raise HTTPException(status_code=400, detail="acting_side deve ser BLUE ou RED.")

    try:
        blue = await db.get(Team, uuid.UUID(req.blue_team_id))
        red = await db.get(Team, uuid.UUID(req.red_team_id))
        managed = await db.get(Team, uuid.UUID(req.managed_team_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="IDs de time inválidos.")

    if not blue or not red or not managed:
        raise HTTPException(status_code=404, detail="Time não encontrado.")

    managed_id = str(managed.id)
    if managed_id not in (str(blue.id), str(red.id)):
        raise HTTPException(
            status_code=400,
            detail="managed_team_id deve ser blue_team_id ou red_team_id.",
        )

    turn = max(0, min(int(req.current_turn or 0), 19))
    state = _build_draft_state(req, turn)
    if state.is_complete:
        raise HTTPException(status_code=400, detail="Draft já completo.")

    expected = BACKEND_DRAFT_ORDER[turn]
    expected_side = expected[1]
    acting = DraftTeam.BLUE if side == "BLUE" else DraftTeam.RED
    if expected_side != acting:
        logger.info(
            "scout-advice fora de turno: turn=%s expected=%s got=%s",
            turn,
            expected_side.value,
            side,
        )

    my_team = blue if acting == DraftTeam.BLUE else red
    opp_team = red if acting == DraftTeam.BLUE else blue
    if str(my_team.id) != managed_id:
        my_team, opp_team = opp_team, my_team
        acting = DraftTeam.BLUE if my_team.id == blue.id else DraftTeam.RED

    patch_bias, patch_version = await _load_patch_context(db)

    champs_result = await db.execute(select(Champion))
    champs = list(champs_result.scalars().all())
    champions_by_name = {c.name: c for c in champs}

    # Conhecimento de scouting do manager sobre o oponente
    knowledge = await ScoutingService(db).get_knowledge(managed_id)

    advisor = DraftScoutAdvisor(
        patch_bias=patch_bias or {},
        patch_version=patch_version or "—",
        champions_by_name=champions_by_name,
    )

    try:
        payload = advisor.advise(
            draft_state=state,
            team_side=acting,
            my_team=my_team,
            opponent_team=opp_team,
            staffs=list(getattr(my_team, "staffs", []) or []),
            focus_role=req.focus_role,
            limit=max(1, min(int(req.limit or 5), 8)),
            opponent_knowledge=knowledge,
        )
    except Exception as e:
        logger.error(f"DraftScout falhou: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Draft scout error: {e}")

    # Sessão de histórico de dicas
    session_svc = ScoutSessionService()
    session = await session_svc.ensure_session(
        req.session_id,
        managed_team_id=managed_id,
        blue_team_id=str(blue.id),
        red_team_id=str(red.id),
        managed_side=acting.value,
        patch_version=patch_version,
        scout_name=(payload.get("scout") or {}).get("name"),
    )
    session_id = session["session_id"]
    compact_recs = [
        {
            "champion": r.get("champion"),
            "role": r.get("role"),
            "priority": r.get("priority"),
            "score": r.get("score"),
            "pool_tier": r.get("pool_tier"),
        }
        for r in (payload.get("recommendations") or [])[:5]
    ]
    await session_svc.append_tip(
        session_id,
        {
            "current_turn": turn,
            "action": payload.get("action"),
            "recommendations": compact_recs,
            "scout_name": (payload.get("scout") or {}).get("name"),
            "patch_version": patch_version,
        },
    )

    payload["source"] = "draft_scout"
    payload["managed_team_id"] = managed_id
    payload["session_id"] = session_id
    return payload


@router.post("/draft/scout-session/action", status_code=status.HTTP_200_OK)
async def draft_scout_session_action(req: DraftScoutActionRequest):
    """Registra o ban/pick do manager (seguiu o scout?)."""
    from src.modules.draft.scout_session import ScoutSessionService

    svc = ScoutSessionService()
    try:
        session = await svc.record_action(
            req.session_id,
            current_turn=int(req.current_turn),
            action=req.action,
            champion=req.champion,
            role=req.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "session_id": req.session_id,
        "actions_count": len(session.get("actions") or []),
        "last_action": (session.get("actions") or [])[-1] if session.get("actions") else None,
    }


@router.get("/draft/scout-session/{session_id}", status_code=status.HTTP_200_OK)
async def get_draft_scout_session(session_id: str):
    from src.modules.draft.scout_session import ScoutSessionService

    session = await ScoutSessionService().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão de scout não encontrada.")
    return session


@router.post("/draft/scout-session/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_draft_scout_session(
    req: DraftScoutEvaluateRequest, db: AsyncSession = Depends(get_db)
):
    """Avalia dicas do scout vs draft final (manual / pós-partida)."""
    from src.modules.draft.scout_session import ScoutSessionService

    svc = ScoutSessionService()
    session = await svc.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão de scout não encontrada.")

    managed_side = (req.managed_side or session.get("managed_side") or "BLUE").upper()
    if managed_side == "BLUE":
        my_bans, opp_bans = list(req.blue_bans or []), list(req.red_bans or [])
        my_picks, opp_picks = list(req.blue_picks or []), list(req.red_picks or [])
        opp_team_id = session.get("red_team_id")
    else:
        my_bans, opp_bans = list(req.red_bans or []), list(req.blue_bans or [])
        my_picks, opp_picks = list(req.red_picks or []), list(req.blue_picks or [])
        opp_team_id = session.get("blue_team_id")

    opp_pools = []
    if opp_team_id:
        try:
            opp = await db.get(Team, uuid.UUID(str(opp_team_id)))
            if opp:
                for p in opp.get_starters():
                    opp_pools.append(
                        {
                            "name": p.name,
                            "champion_pool": p.champion_pool
                            if isinstance(p.champion_pool, list)
                            else [],
                        }
                    )
        except Exception:
            pass

    evaluation = await svc.evaluate_and_store(
        req.session_id,
        my_bans=my_bans,
        opp_bans=opp_bans,
        my_picks=my_picks,
        opp_picks=opp_picks,
        opp_starters_pools=opp_pools,
        winner_side=req.winner_side,
    )
    return {"session_id": req.session_id, "evaluation": evaluation}


@router.get("/teams/{team_id}/scout-history", status_code=status.HTTP_200_OK)
async def get_team_scout_history(team_id: str):
    """Histórico de avaliações do scout na carreira."""
    from src.modules.draft.scout_session import ScoutSessionService

    history = await ScoutSessionService().get_history(team_id)
    return {"team_id": team_id, "history": history, "count": len(history)}
