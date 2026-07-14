"""Simulação batch, live match e detalhes de partida."""

import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CreateMatchRequest,
    StartLiveMatchRequest,
    CoachCommRequest,
    LiveSpeedRequest,
)
from src.core.database import get_db
from src.core.redis_client import redis_client
from src.models import Team, Contract, League, LeagueTeam, Match
from src.modules.draft.snake_draft import SnakeDraft, DraftTeam, DraftAction
from src.modules.draft.draft_ai import DraftAI, calculate_draft_penalties
from src.modules.simulation.match_engine import MatchEngine, MatchInput, MatchSimulationResult
from src.modules.simulation.match_engine_service import MatchEngineService
from src.shared.enums import SplitPhase, ContractStatus

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["matches"])

# Singleton: estado live em memória (MockRedis + tasks)
match_engine_service = MatchEngineService()


@router.post("/matches/simulate", status_code=status.HTTP_200_OK)
async def simulate_match(req: CreateMatchRequest, db: AsyncSession = Depends(get_db)):
    """
    Simula uma partida completa:
    1. Carrega times e seus jogadores titulares.
    2. Inicializa o Snake Draft competitivo (10 bans, 10 picks).
    3. Executa a IA de Draft (DraftAI) com counter-picking inteligente.
    4. Analisa o draft para calcular as penalidades de draft de ambos os lados.
    5. Executa o MatchEngine estocástico (Strategies: Early/Mid/Late Game).
    6. Atualiza a classificação da liga e aplica estatísticas aos jogadores.
    7. Persiste a partida e os logs detalhados de simulação.
    """
    g2_query = await db.execute(select(Team).where(Team.id == uuid.UUID(req.blue_team_id)))
    blue_team = g2_query.scalar_one_or_none()
    fnc_query = await db.execute(select(Team).where(Team.id == uuid.UUID(req.red_team_id)))
    red_team = fnc_query.scalar_one_or_none()

    if not blue_team or not red_team:
        raise HTTPException(status_code=404, detail="Um ou ambos os times não foram encontrados.")

    try:
        blue_team.validate_roster_size()
        red_team.validate_roster_size()
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

    match_uuid = uuid.uuid4()
    draft = SnakeDraft(match_id=str(match_uuid))
    draft.initialize()
    draft_ai = DraftAI()

    logger.info(f"Iniciando Snake Draft automático para a partida {match_uuid}...")

    while not draft.get_current_state().is_complete:
        expected = draft.get_expected_action()
        current_team_side = DraftTeam(expected["team"])

        active_team = blue_team if current_team_side == DraftTeam.BLUE else red_team
        passive_team = red_team if current_team_side == DraftTeam.BLUE else blue_team

        chosen_champ, role = draft_ai.make_decision(
            draft_state=draft.get_current_state(),
            team_side=current_team_side,
            team_obj=active_team,
            opponent_team_obj=passive_team,
        )

        draft.process_action(
            team=current_team_side,
            action=DraftAction(expected["action"]),
            champion=chosen_champ,
            role_hint=role.value if role else None,
        )

    draft_state = draft.get_current_state()

    blue_penalty, red_penalty = calculate_draft_penalties(
        blue_picks=draft_state.blue_picks,
        red_picks=draft_state.red_picks,
        blue_team=blue_team,
        red_team=red_team,
    )

    from datetime import date
    from src.modules.simulation.patch_service import PatchService

    active_patch_meta = await redis_client.get_generic("patch:current:meta")
    if not active_patch_meta:
        patch_service = PatchService(db)
        await patch_service.update_patch_cache(date.today())
        active_patch_meta = await redis_client.get_generic("patch:current:meta") or {}

    match_engine_input = MatchInput(
        blue_team=blue_team,
        red_team=red_team,
        blue_draft=draft_state.blue_picks,
        red_draft=draft_state.red_picks,
        is_playoff=req.is_playoff,
        match_id=str(match_uuid),
        blue_coach_comms=req.blue_coach_comms,
        red_coach_comms=req.red_coach_comms,
        blue_draft_penalty=blue_penalty,
        red_draft_penalty=red_penalty,
        champion_patch_meta=active_patch_meta,
    )

    engine_instance = MatchEngine()
    sim_result: MatchSimulationResult = engine_instance.simulate(match_input=match_engine_input)

    sim_result.draft_log = draft.to_match_log()

    winner_id = uuid.UUID(sim_result.winner_team_id)
    loser_id = (
        uuid.UUID(req.red_team_id)
        if winner_id == uuid.UUID(req.blue_team_id)
        else uuid.UUID(req.blue_team_id)
    )

    await db.execute(
        update(LeagueTeam)
        .where(LeagueTeam.league_id == uuid.UUID(req.league_id), LeagueTeam.team_id == winner_id)
        .values(wins=LeagueTeam.wins + 1, points=LeagueTeam.points + 3)
    )

    await db.execute(
        update(LeagueTeam)
        .where(LeagueTeam.league_id == uuid.UUID(req.league_id), LeagueTeam.team_id == loser_id)
        .values(losses=LeagueTeam.losses + 1)
    )

    for player in (blue_team.players + red_team.players):
        contract_query = await db.execute(
            select(Contract)
            .where(Contract.player_id == player.id, Contract.status == ContractStatus.ACTIVE)
        )
        contract = contract_query.scalar_one_or_none()
        if contract:
            contract.rookie_games_played += 1
            contract.check_and_trigger_rookie_extension()

    db_match = Match(
        id=match_uuid,
        league_id=uuid.UUID(req.league_id),
        split_week=req.week,
        split_phase=SplitPhase.REGULAR_SEASON,
        is_playoff=req.is_playoff,
        scheduled_at=datetime.utcnow(),
        blue_team_id=blue_team.id,
        red_team_id=red_team.id,
        winner_team_id=winner_id,
        blue_result=sim_result.blue_result,
        red_result=sim_result.red_result,
        match_duration_minutes=sim_result.match_duration_minutes,
        blue_win_probability=sim_result.blue_win_probability,
        early_game_log=sim_result.early_game_log,
        mid_game_log=sim_result.mid_game_log,
        late_game_log=sim_result.late_game_log,
        draft_log=sim_result.draft_log,
    )
    db.add(db_match)
    await db.commit()

    await redis_client.cache_match_result(str(match_uuid), sim_result.to_dict())

    return {
        "message": "Partida simulada e registrada com sucesso!",
        "match_id": str(match_uuid),
        "winner": blue_team.name if winner_id == blue_team.id else red_team.name,
        "winner_side": sim_result.winner_side,
        "duration": f"{sim_result.match_duration_minutes} min",
        "kills": f"{sim_result.total_kills_blue} - {sim_result.total_kills_red}",
        "win_probability_blue": f"{sim_result.blue_win_probability * 100:.2f}%",
        "draft_penalties": {
            "blue": blue_penalty,
            "red": red_penalty,
        },
    }


@router.get("/matches/{match_id}", status_code=status.HTTP_200_OK)
async def get_match_details(match_id: str, db: AsyncSession = Depends(get_db)):
    """
    Busca os detalhes completos de uma partida (tenta primeiro no Redis, depois no Postgres).
    """
    cached = await redis_client.get_match_result(match_id)
    if cached:
        logger.info(f"Resultado da partida {match_id} recuperado do Redis Cache!")
        return {"source": "cache", "data": cached}

    query = await db.execute(select(Match).where(Match.id == uuid.UUID(match_id)))
    match_obj = query.scalar_one_or_none()

    if not match_obj:
        raise HTTPException(status_code=404, detail="Partida não encontrada.")

    blue = await db.get(Team, match_obj.blue_team_id)
    red = await db.get(Team, match_obj.red_team_id)
    b_name = blue.name if blue else "Blue"
    r_name = red.name if red else "Red"

    def _clip_logs(logs, n=8):
        if not logs or not isinstance(logs, list):
            return []
        return logs[-n:]

    winner_id = match_obj.winner_team_id
    winner_name = None
    if winner_id and blue and winner_id == blue.id:
        winner_name = b_name
    elif winner_id and red and winner_id == red.id:
        winner_name = r_name

    return {
        "source": "database",
        "data": {
            "match_id": str(match_obj.id),
            "blue_team": b_name,
            "red_team": r_name,
            "blue_team_id": str(match_obj.blue_team_id),
            "red_team_id": str(match_obj.red_team_id),
            "blue_team_abbr": blue.abbreviation if blue else None,
            "red_team_abbr": red.abbreviation if red else None,
            "winner_team_id": str(winner_id) if winner_id else None,
            "winner_name": winner_name,
            "blue_result": match_obj.blue_result.value if match_obj.blue_result else None,
            "red_result": match_obj.red_result.value if match_obj.red_result else None,
            "duration": match_obj.match_duration_minutes,
            "blue_win_probability": match_obj.blue_win_probability,
            "split_week": match_obj.split_week,
            "is_playoff": bool(match_obj.is_playoff),
            "early_game": match_obj.early_game_log,
            "mid_game": match_obj.mid_game_log,
            "late_game": match_obj.late_game_log,
            "draft": match_obj.draft_log,
            "log_preview": (
                _clip_logs(match_obj.early_game_log, 3)
                + _clip_logs(match_obj.mid_game_log, 3)
                + _clip_logs(match_obj.late_game_log, 4)
            ),
        },
    }


@router.post("/matches/live/start", status_code=status.HTTP_201_CREATED)
async def start_live_match(req: StartLiveMatchRequest, db: AsyncSession = Depends(get_db)):
    """
    Inicializa e dispara a simulação assíncrona baseada em ticks no Redis Simulado.
    """
    blue_team = await db.get(Team, uuid.UUID(req.blue_team_id))
    red_team = await db.get(Team, uuid.UUID(req.red_team_id))
    if not blue_team or not red_team:
        raise HTTPException(status_code=404, detail="Um ou ambos os times não foram encontrados.")

    league_query = await db.execute(select(League).limit(1))
    league = league_query.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=404, detail="Nenhuma liga cadastrada. Rode o seed antes.")

    match_id = str(uuid.uuid4())

    is_playoff = bool(req.is_playoff) or (
        league.current_phase == SplitPhase.PLAYOFFS
    )

    from src.modules.simulation.tactics import (
        PreMatchTactics,
        build_lineup_proxy,
        normalize_style,
        clamp_coach_comms,
    )

    tactics = PreMatchTactics.from_dict(
        {
            "game_style": req.game_style,
            "coach_comms": req.coach_comms,
            "starter_ids": req.starter_ids,
        }
    )
    managed = str(req.managed_team_id) if req.managed_team_id else None
    blue_style, red_style = "BALANCED", "BALANCED"
    blue_comms, red_comms = 2, 2
    if managed and managed == str(blue_team.id):
        blue_style = tactics.game_style
        blue_comms = tactics.coach_comms
        blue_team = build_lineup_proxy(blue_team, tactics.starter_ids)
    elif managed and managed == str(red_team.id):
        red_style = tactics.game_style
        red_comms = tactics.coach_comms
        red_team = build_lineup_proxy(red_team, tactics.starter_ids)
    else:
        blue_style = normalize_style(req.game_style)
        blue_comms = clamp_coach_comms(req.coach_comms)
        if req.starter_ids:
            blue_team = build_lineup_proxy(blue_team, req.starter_ids)

    live_state = await match_engine_service.start_live_simulation(
        match_id=match_id,
        league_id=str(league.id),
        split_week=req.split_week,
        is_playoff=is_playoff,
        blue_team=blue_team,
        red_team=red_team,
        blue_draft=req.blue_draft,
        red_draft=req.red_draft,
        speed=req.speed or "2x",
        blue_game_style=blue_style,
        red_game_style=red_style,
        blue_coach_comms_max=blue_comms,
        red_coach_comms_max=red_comms,
    )

    state_payload = live_state.model_dump()
    return {
        "message": "Simulação de partida ao vivo iniciada com sucesso!",
        "match_id": match_id,
        "state": state_payload,
    }


@router.post("/matches/live/{match_id}/speed", status_code=status.HTTP_200_OK)
async def set_live_match_speed(match_id: str, req: LiveSpeedRequest):
    """Altera a velocidade da partida em andamento (1x, 2x, 4x, instant)."""
    res = await match_engine_service.set_live_speed(match_id, req.speed)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/matches/live/{match_id}/state", status_code=status.HTTP_200_OK)
async def get_live_match_state(match_id: str):
    """
    Retorna o estado mutável em tempo real da partida ao vivo a partir do Redis virtual.
    """
    state = await match_engine_service.get_live_state(match_id)
    if not state:
        raise HTTPException(status_code=404, detail="Partida ao vivo não encontrada ou já encerrada.")
    return state


@router.post("/matches/live/{match_id}/coach-comm", status_code=status.HTTP_200_OK)
async def live_coach_comm(match_id: str, req: CoachCommRequest):
    """
    Envia comandos táticos (Coach Comms) do treinador em tempo real durante o Early Game.
    """
    res = await match_engine_service.apply_coach_comm(match_id, req.team_side)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res
