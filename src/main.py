"""
Ponto de Entrada Principal (FastAPI) para o LoL Manager Backend.

Inicializa as conexões com o PostgreSQL (SQLAlchemy) e Redis.
Expõe rotas HTTP para:
    - Semear o banco de dados com times, jogadores, ligas e contratos fictícios (Seed).
    - Avançar o calendário diário (Calendar State Machine + Burnout Service).
    - Simular partidas oficiais do calendário (Snake Draft + Match Engine).
    - Consultar standings, times, jogadores e logs de partidas.
"""

import logging
import random
import uuid
from datetime import date, timedelta, datetime
from typing import List, Dict, Optional
from decimal import Decimal

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.database import get_db, engine
from src.core.redis_client import redis_client
from src.shared.enums import PlayerRole, Region, LeagueType, SplitPhase, CalendarDayType, MatchResult, ContractStatus, ChampionPoolTier
from src.models import Base, Player, Team, Contract, League, LeagueTeam, Match, Champion, ChampionRoleStats, Patch, ChampionPatchMeta, Staff

# Motores e serviços
from src.modules.calendar.calendar_service import CalendarService
from src.modules.calendar.state_machine import CalendarStateMachine
from src.modules.draft.snake_draft import SnakeDraft, DraftTeam, DraftAction
from src.modules.draft.draft_ai import DraftAI, calculate_draft_penalties
from src.modules.simulation.match_engine import MatchEngine, MatchInput, MatchSimulationResult
from src.shared.champions_data import ALL_CHAMPIONS
from src.shared.cblol_2026_data import CBLOL_2026_TEAMS, KNOWN_SUBS, POOLS_BY_ROLE, LEAGUE_META

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lol_manager_api")
settings = get_settings()

app = FastAPI(
    title="League of Legends Manager Backend",
    description="Engine e Simulador de Gestão de Esports de alta performance matemática.",
    version="1.0.0",
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em prod, limitar para a URL do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Lifespan Events ---
@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando conexões do sistema...")
    await redis_client.connect()
    logger.info("Redis conectado com sucesso.")
    
    # Auto-criação de tabelas no banco de dados SQLite (Zero Dependency Mode)
    if settings.database_url.startswith("sqlite"):
        logger.info("Iniciando auto-criação de tabelas no SQLite local...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tabelas SQLite auto-criadas com sucesso.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Fechando conexões do sistema...")
    await redis_client.disconnect()
    logger.info("Redis desconectado.")


# --- DTOs Pydantic para APIs ---
class CreateMatchRequest(BaseModel):
    blue_team_id: str
    red_team_id: str
    league_id: str
    week: int
    is_playoff: bool = False
    blue_coach_comms: int = 0
    red_coach_comms: int = 0


class SignPlayerRequest(BaseModel):
    team_id: str
    player_id: str
    transfer_fee: float = 250000.0
    monthly_salary: float = 5000.0
    seasons: int = 2


def _serialize_player(player: Player, contract: Optional[Contract] = None) -> dict:
    """Serializa jogador + contrato ativo para o frontend."""
    active_contract = contract
    if active_contract is None and getattr(player, "contracts", None):
        for c in player.contracts:
            if c.status in (ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED, ContractStatus.PENDING_RENEWAL):
                active_contract = c
                break

    champion_pool = player.champion_pool if isinstance(player.champion_pool, list) else []
    return {
        "id": str(player.id),
        "name": player.name,
        "age": player.get_age(),
        "nationality": player.nationality,
        "role": player.role.value,
        "region": player.region.value if player.region else None,
        "teamId": str(player.team_id) if player.team_id else None,
        "isRookie": player.is_rookie,
        "currentAbility": player.current_ability,
        "potentialAbility": player.potential_ability,
        "mechanics": player.mechanics,
        "championPool": champion_pool,
        "focus": player.focus,
        "resilience": player.resilience,
        "coachability": player.coachability,
        "teamwork": player.teamwork,
        "consistency": player.consistency,
        "bigMatchAptitude": player.big_match_aptitude,
        "burnoutMeter": player.burnout_meter,
        "visualFatigue": player.visual_fatigue,
        "mentalFatigue": player.mental_fatigue,
        "gamesPlayedThisSplit": player.games_played_this_split or 0,
        "hasRookieClause": bool(active_contract.has_rookie_clause) if active_contract else False,
        "participationRate": (
            active_contract.rookie_participation_rate if active_contract else 0.0
        ),
        "contractExpirySeasons": (
            active_contract.remaining_seasons if active_contract else 0
        ),
        "monthlySalary": float(active_contract.monthly_salary) if active_contract else 0.0,
    }


async def _teams_for_week_calendar(db: AsyncSession, league_id) -> list:
    """Times da liga no formato usado por build_week_calendar (ordem livre)."""
    from src.models.league import LeagueTeam

    result = await db.execute(
        select(Team)
        .join(LeagueTeam, LeagueTeam.team_id == Team.id)
        .where(LeagueTeam.league_id == league_id)
    )
    return [
        {"id": str(t.id), "name": t.name, "abbreviation": t.abbreviation}
        for t in result.scalars().all()
    ]


async def _build_week_calendar_for_league(
    db: AsyncSession,
    league: League,
    managed_team_id: Optional[str] = None,
) -> dict:
    """
    Estado do calendário + grade semanal com adversário real do round-robin.
    Prefere a State Machine (Redis) quando disponível para week/day_of_week.
    """
    from src.shared.week_calendar import build_week_calendar

    phase = league.current_phase.value if league.current_phase else "OFFSEASON"
    day_of_week = max(0, (int(league.current_day or 1) - 1) % 7)
    current_week = int(league.current_week or 0)
    current_day = int(league.current_day or 0)

    # Usa a SM da liga já carregada (evita re-query UUID string vs UUID column)
    calendar_service = CalendarService(db)
    sm = await calendar_service._get_or_create_sm(league)
    if sm.is_initialized and sm.context is not None:
        ctx = sm.context
        day_of_week = int(ctx.current_day_of_week or 0)
        current_week = int(ctx.current_week or 0)
        current_day = int(ctx.total_days_elapsed or current_day)
        if ctx.current_state_name:
            phase = ctx.current_state_name

    team_rows = await _teams_for_week_calendar(db, league.id)
    week_calendar = build_week_calendar(
        current_day_of_week=day_of_week,
        current_week=current_week,
        phase=phase,
        teams=team_rows,
        managed_team_id=managed_team_id,
    )

    # Próximo confronto do manager na semana atual (match day futuro ou hoje)
    next_match = None
    today = day_of_week % 7
    for day in week_calendar:
        if day.get("type") != CalendarDayType.MATCH_DAY.value:
            continue
        if day.get("dayIndex", 0) < today:
            continue
        if managed_team_id and day.get("opponentAbbr"):
            next_match = day
            break
        if not managed_team_id and day.get("eventName"):
            next_match = day
            break

    return {
        "current_day": current_day,
        "current_week": current_week,
        "current_phase": phase,
        "day_of_week": day_of_week,
        "league_id": str(league.id),
        "league_name": league.name,
        "week_calendar": week_calendar,
        "next_match": {
            "dayIndex": next_match["dayIndex"],
            "dayOfWeek": next_match["dayOfWeek"],
            "eventName": next_match.get("eventName"),
            "opponentAbbr": next_match.get("opponentAbbr"),
            "opponentName": next_match.get("opponentName"),
            "isHome": next_match.get("isHome"),
            "roundIndex": next_match.get("roundIndex"),
        }
        if next_match
        else None,
    }


# --- Rotas Auxiliares / Admin ---
@app.get("/")
def read_root():
    return {
        "status": "online",
        "game": "League of Legends Manager",
        "engine_version": "1.0.0",
        "environment": settings.environment
    }


@app.post("/db/seed", status_code=status.HTTP_201_CREATED)
async def seed_database(db: AsyncSession = Depends(get_db)):
    """
    Semeia o banco com o CBLOL 2026 Split 1 oficial (8 times):
    RED, FURIA, VKS, LØS, Fluxo W7M, LOUD, paiN, Leviatán.
    Sem times de fora (G2/T1/LEC) e sem orgs fora do circuito 2026 (KaBuM/INTZ/Liberty).
    """
    try:
        logger.info("Recriando tabelas no banco de dados para semeadura limpa...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Iniciando semeadura do CBLOL 2026 (8 times oficiais)...")
        
        # 1. Cria a Liga CBLOL 2026
        cblol = League(
            id=uuid.uuid4(),
            name=LEAGUE_META["name"],
            abbreviation=LEAGUE_META["abbreviation"],
            league_type=LeagueType.LEC,  # liga principal (idade mínima 18+ no elenco titular)
            region=Region.CBLOL,
            current_phase=SplitPhase.REGULAR_SEASON,
            current_week=1,
            current_day=1,
            regular_season_weeks=LEAGUE_META["regular_season_weeks"],
            matches_per_week=LEAGUE_META["matches_per_week"],
            playoff_teams=LEAGUE_META["playoff_teams"],
            prize_pool=LEAGUE_META["prize_pool"],
            total_prize_pool=Decimal(LEAGUE_META["total_prize_pool"]),
        )
        db.add(cblol)

        # 2. Cria Campeões e Flex Picks por Role
        champions_data = ALL_CHAMPIONS
        
        champions_instances = {}
        role_stats_instances = {}
        for name, is_disabled, p_role, s_role, c_type, d_type, early, late, diff, utl_val, syn, cnt, stats_list in champions_data:
            champ = Champion(
                id=uuid.uuid4(),
                name=name,
                is_disabled_for_rework=is_disabled,
                primary_role=p_role,
                secondary_role=s_role,
                class_type=c_type,
                damage_type=d_type,
                early_game_power=early,
                late_game_scaling=late,
                mechanical_difficulty=diff,
                utility=utl_val,
                synergies=syn,
                counters=cnt
            )
            db.add(champ)
            champions_instances[name] = champ
            
            for role, dmg, utl, surv in stats_list:
                role_stats = ChampionRoleStats(
                    id=uuid.uuid4(),
                    champion_id=champ.id,
                    role=role,
                    base_damage=dmg,
                    base_utility=utl,
                    base_survivability=surv
                )
                db.add(role_stats)
                role_stats_instances[f"{name}:{role}"] = role_stats

        # 3. Cria Patches
        today = date.today()
        # Patch 16.1 lançado há 3 dias (vigor daqui a 4 dias)
        patch1 = Patch(
            id=uuid.uuid4(),
            version="16.1",
            release_date=today - timedelta(days=3),
            effective_date=today + timedelta(days=4)
        )
        # Patch 16.2 lançado daqui a 4 dias (vigor daqui a 11 dias)
        patch2 = Patch(
            id=uuid.uuid4(),
            version="16.2",
            release_date=today + timedelta(days=4),
            effective_date=today + timedelta(days=11)
        )
        db.add(patch1)
        db.add(patch2)

        # ChampionPatchMeta (Modificadores do Patch)
        # Patch 16.1: Buffa Azir no Mid (+10% dano) e nerfa K'Sante no Top (-10% sobrevivência)
        meta_azir_16_1 = ChampionPatchMeta(
            id=uuid.uuid4(),
            patch_id=patch1.id,
            champion_role_stats_id=role_stats_instances["Azir:MID"].id,
            damage_modifier=1.10,
            utility_modifier=1.0,
            survivability_modifier=1.0
        )
        meta_ksante_16_1 = ChampionPatchMeta(
            id=uuid.uuid4(),
            patch_id=patch1.id,
            champion_role_stats_id=role_stats_instances["K'Sante:TOP"].id,
            damage_modifier=1.0,
            utility_modifier=1.0,
            survivability_modifier=0.90
        )
        db.add(meta_azir_16_1)
        db.add(meta_ksante_16_1)

        # 4. Times e elencos oficiais do CBLOL 2026 Split 1 (8 orgs)
        teams_list = []
        three_seasons_later = today + timedelta(days=180 * 3)
        roles_cycle = [PlayerRole.TOP, PlayerRole.JUNGLE, PlayerRole.MID, PlayerRole.BOT, PlayerRole.SUPPORT]

        def _add_player(
            *,
            team_id,
            p_name,
            role,
            ca,
            pa,
            mech,
            fcs,
            nationality,
            is_rookie,
            salary_range,
            has_rookie_clause,
        ):
            player_id = uuid.uuid4()
            # Titulares 18–27; academy/rookie 16–19
            if is_rookie:
                birth_year = 2007 + random.randint(0, 2)
            else:
                birth_year = 1998 + random.randint(0, 8)
            pool = list(POOLS_BY_ROLE.get(role, POOLS_BY_ROLE[PlayerRole.MID]))
            p = Player(
                id=player_id,
                name=p_name,
                date_of_birth=date(birth_year, random.randint(1, 12), random.randint(1, 28)),
                nationality=nationality,
                role=role,
                region=Region.CBLOL,
                is_rookie=is_rookie,
                current_ability=ca,
                potential_ability=max(pa, ca),
                mechanics=mech,
                focus=fcs,
                resilience=float(random.randint(12, 18)),
                coachability=float(random.randint(12, 18)),
                teamwork=float(random.randint(12, 18)),
                consistency=float(random.randint(12, 18)),
                big_match_aptitude=float(random.randint(12, 18)),
                champion_pool=pool,
                burnout_meter=0.0,
                visual_fatigue=0.0,
                mental_fatigue=0.0,
                team_id=team_id,
            )
            db.add(p)
            lo, hi = salary_range
            contract = Contract(
                id=uuid.uuid4(),
                player_id=player_id,
                team_id=team_id,
                start_date=today,
                end_date=three_seasons_later,
                seasons_duration=3,
                monthly_salary=Decimal(f"{random.randint(lo, hi)}.00"),
                status=ContractStatus.ACTIVE,
                has_rookie_clause=has_rookie_clause,
                rookie_games_played=0,
                rookie_total_league_games=cblol.total_regular_season_matches,
            )
            db.add(contract)
            return p

        for name, tag, has_academy, budget, revenue, coach_name, strat_coach_name, starters in CBLOL_2026_TEAMS:
            team_id = uuid.uuid4()
            team = Team(
                id=team_id,
                name=name,
                abbreviation=tag,
                region=Region.CBLOL,
                budget=Decimal(f"{budget * 1000000:.2f}"),
                monthly_revenue=Decimal(f"{revenue * 1000:.2f}"),
            )
            db.add(team)
            teams_list.append(team)

            lt = LeagueTeam(
                id=uuid.uuid4(),
                league_id=cblol.id,
                team_id=team_id,
                wins=0,
                losses=0,
                points=0,
            )
            db.add(lt)

            head_coach = Staff(
                id=uuid.uuid4(),
                team_id=team_id,
                name=f"Coach {coach_name}",
                role="HEAD_COACH",
                communication=float(random.randint(13, 19)),
                meta_reading=float(random.randint(13, 19)),
            )
            db.add(head_coach)

            if strat_coach_name:
                strat_coach = Staff(
                    id=uuid.uuid4(),
                    team_id=team_id,
                    name=f"Coach {strat_coach_name}",
                    role="STRATEGIC_COACH",
                    communication=float(random.randint(11, 17)),
                    meta_reading=float(random.randint(13, 19)),
                )
                db.add(strat_coach)

            # Titulares oficiais
            for p_name, role, ca, pa, mech, fcs, nationality in starters:
                _add_player(
                    team_id=team_id,
                    p_name=p_name,
                    role=role,
                    ca=ca,
                    pa=pa,
                    mech=mech,
                    fcs=fcs,
                    nationality=nationality,
                    is_rookie=False,
                    salary_range=(5000, 20000),
                    has_rookie_clause=False,
                )

            # Subs conhecidos (se houver) contam como reserva
            known = list(KNOWN_SUBS.get(tag, []))
            for p_name, role, ca, pa, mech, fcs, nationality in known:
                _add_player(
                    team_id=team_id,
                    p_name=p_name,
                    role=role,
                    ca=ca,
                    pa=pa,
                    mech=mech,
                    fcs=fcs,
                    nationality=nationality,
                    is_rookie=False,
                    salary_range=(2500, 6000),
                    has_rookie_clause=False,
                )

            # Completa roster: academy (11 total) ou 1 reserva (6 total)
            current_count = 5 + len(known)
            target = 11 if has_academy else 6
            for i in range(max(0, target - current_count)):
                reserve_role = roles_cycle[i % len(roles_cycle)]
                _add_player(
                    team_id=team_id,
                    p_name=f"{tag} Academy {reserve_role.value} {i + 1}",
                    role=reserve_role,
                    ca=random.randint(90, 118),
                    pa=random.randint(135, 160),
                    mech=float(random.randint(10, 14)),
                    fcs=float(random.randint(10, 14)),
                    nationality="Brazil",
                    is_rookie=True,
                    salary_range=(1500, 3500),
                    has_rookie_clause=True,
                )

        await db.commit()
        logger.info(
            "Semeadura do CBLOL 2026 concluída: %s times (%s).",
            len(teams_list),
            ", ".join(t.abbreviation for t in teams_list),
        )
        
        return {
            "message": "Banco semeado com CBLOL 2026 Split 1 (8 times oficiais).",
            "league_id": str(cblol.id),
            "teams": {t.abbreviation: str(t.id) for t in teams_list},
            "team_count": len(teams_list),
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro na semeadura do CBLOL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno de semeadura: {e}")


# --- Calendário / Rotina Diária ---
@app.get("/calendar", status_code=status.HTTP_200_OK)
async def get_calendar_state(
    managed_team_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o estado atual do calendário (liga ativa) + grade semanal.

    Query param opcional:
      managed_team_id — personaliza match days com adversário real do round-robin.
    """
    from src.shared.week_calendar import build_week_calendar

    league_query = await db.execute(select(League).limit(1))
    league = league_query.scalar_one_or_none()
    if not league:
        return {
            "current_day": 1,
            "current_week": 0,
            "current_phase": "OFFSEASON",
            "day_of_week": 0,
            "league_id": None,
            "week_calendar": build_week_calendar(0, 0, "OFFSEASON"),
            "next_match": None,
        }

    return await _build_week_calendar_for_league(
        db, league, managed_team_id=managed_team_id
    )

@app.post("/calendar/advance", status_code=status.HTTP_200_OK)
async def advance_calendar(
    managed_team_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Avança um dia no calendário do jogo.
    Processa a State Machine do calendário e roda o BurnoutService
    para aplicar penalidades de fadiga e burnout aos jogadores.

    Query param opcional:
      managed_team_id — partidas desse time ficam para o jogador (não auto-simula).
    """
    calendar_service = CalendarService(db)
    results = await calendar_service.advance_all_leagues(managed_team_id=managed_team_id)
    return {
        "message": "Calendário avançado em 1 dia.",
        "results": results
    }


# --- Simulação de Partida (Draft + Match Engine) ---
@app.post("/matches/simulate", status_code=status.HTTP_200_OK)
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
    # 1. Carrega times do banco de dados
    g2_query = await db.execute(select(Team).where(Team.id == uuid.UUID(req.blue_team_id)))
    blue_team = g2_query.scalar_one_or_none()
    fnc_query = await db.execute(select(Team).where(Team.id == uuid.UUID(req.red_team_id)))
    red_team = fnc_query.scalar_one_or_none()

    if not blue_team or not red_team:
        raise HTTPException(status_code=404, detail="Um ou ambos os times não foram encontrados.")

    # Valida roster mínimo (academy=11, sem academy=6)
    try:
        blue_team.validate_roster_size()
        red_team.validate_roster_size()
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

    # 2. Inicializa e roda o Snake Draft usando a IA de Draft
    match_uuid = uuid.uuid4()
    draft = SnakeDraft(match_id=str(match_uuid))
    draft.initialize()
    draft_ai = DraftAI()

    logger.info(f"Iniciando Snake Draft automático para a partida {match_uuid}...")
    
    # Executa a simulação do draft de 20 turnos (10 bans + 10 picks)
    while not draft.get_current_state().is_complete:
        expected = draft.get_expected_action()
        current_team_side = DraftTeam(expected["team"])
        
        # Decide quem é o time e o oponente na ação do draft
        active_team = blue_team if current_team_side == DraftTeam.BLUE else red_team
        passive_team = red_team if current_team_side == DraftTeam.BLUE else blue_team

        # IA toma decisão
        chosen_champ, role = draft_ai.make_decision(
            draft_state=draft.get_current_state(),
            team_side=current_team_side,
            team_obj=active_team,
            opponent_team_obj=passive_team
        )

        # Processa a ação no draft
        draft.process_action(
            team=current_team_side,
            action=DraftAction(expected["action"]),
            champion=chosen_champ,
            role_hint=role.value if role else None
        )

    draft_state = draft.get_current_state()

    # 3. Analisa o draft para calcular as penalidades
    blue_penalty, red_penalty = calculate_draft_penalties(
        blue_picks=draft_state.blue_picks,
        red_picks=draft_state.red_picks,
        blue_team=blue_team,
        red_team=red_team
    )

    # Carrega dados consolidados do patch ativo do Redis virtual
    from src.core.redis_client import redis_client
    from src.modules.simulation.patch_service import PatchService
    from datetime import date
    
    active_patch_meta = await redis_client.get_generic("patch:current:meta")
    if not active_patch_meta:
        # Fallback rápido se não houver cache
        patch_service = PatchService(db)
        await patch_service.update_patch_cache(date.today())
        active_patch_meta = await redis_client.get_generic("patch:current:meta") or {}

    # 4. Executa o Match Engine (Strategies Early, Mid, Late)
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
        champion_patch_meta=active_patch_meta
    )

    engine_instance = MatchEngine()
    sim_result: MatchSimulationResult = engine_instance.simulate(match_input=match_engine_input)

    # Adiciona o log do draft ao resultado da partida
    sim_result.draft_log = draft.to_match_log()

    # 5. Atualiza Standings da Liga
    winner_id = uuid.UUID(sim_result.winner_team_id)
    loser_id = uuid.UUID(req.red_team_id) if winner_id == uuid.UUID(req.blue_team_id) else uuid.UUID(req.blue_team_id)

    # Atualiza standings do Vencedor
    await db.execute(
        update(LeagueTeam)
        .where(LeagueTeam.league_id == uuid.UUID(req.league_id), LeagueTeam.team_id == winner_id)
        .values(wins=LeagueTeam.wins + 1, points=LeagueTeam.points + 3)
    )

    # Atualiza standings do Perdedor
    await db.execute(
        update(LeagueTeam)
        .where(LeagueTeam.league_id == uuid.UUID(req.league_id), LeagueTeam.team_id == loser_id)
        .values(losses=LeagueTeam.losses + 1)
    )

    # 6. Atualiza número de partidas dos jogadores no split e aplica regras rookie
    for player in (blue_team.players + red_team.players):
        # Encontra o contrato ativo do jogador
        contract_query = await db.execute(
            select(Contract)
            .where(Contract.player_id == player.id, Contract.status == ContractStatus.ACTIVE)
        )
        contract = contract_query.scalar_one_or_none()
        if contract:
            # Incrementa jogos jogados no split pelo rookie se jogou
            contract.rookie_games_played += 1
            # Roda verificação da cláusula rookie
            contract.check_and_trigger_rookie_extension()

    # 7. Persiste a partida simulada no banco
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
        draft_log=sim_result.draft_log
    )
    db.add(db_match)
    await db.commit()

    # Salva resultado no cache Redis
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
            "red": red_penalty
        },
    }


# --- Consultas Base de Dados (Read) ---

@app.get("/teams", status_code=status.HTTP_200_OK)
async def get_teams(db: AsyncSession = Depends(get_db)):
    """Busca todas as equipes cadastradas."""
    query = await db.execute(select(Team))
    teams = query.scalars().all()
    return [{
        "id": str(t.id), 
        "name": t.name, 
        "abbreviation": t.abbreviation,
        "budget": float(t.budget),
        "monthlyRevenue": float(t.monthly_revenue),
        "region": t.region.value if t.region else None
    } for t in teams]

@app.get("/teams/{team_id}/players", status_code=status.HTTP_200_OK)
async def get_team_players(team_id: str, db: AsyncSession = Depends(get_db)):
    """Busca os jogadores de uma equipe específica (com contrato e pool)."""
    from sqlalchemy.orm import selectinload

    query = await db.execute(
        select(Player)
        .options(selectinload(Player.contracts))
        .where(Player.team_id == uuid.UUID(team_id))
    )
    players = query.scalars().all()
    return [_serialize_player(p) for p in players]


@app.get("/leagues", status_code=status.HTTP_200_OK)
async def get_leagues(db: AsyncSession = Depends(get_db)):
    """Lista ligas ativas (seed atual = 1 CBLOL)."""
    query = await db.execute(select(League))
    leagues = query.scalars().all()
    return [
        {
            "id": str(lg.id),
            "name": lg.name,
            "abbreviation": lg.abbreviation,
            "region": lg.region.value if lg.region else None,
            "current_phase": lg.current_phase.value if lg.current_phase else None,
            "current_week": lg.current_week,
            "current_day": lg.current_day,
        }
        for lg in leagues
    ]


@app.get("/market/players", status_code=status.HTTP_200_OK)
async def get_market_players(
    exclude_team_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Mercado: jogadores de outros times + agentes livres.
    exclude_team_id remove o elenco do manager da listagem.
    """
    from sqlalchemy.orm import selectinload

    query = select(Player).options(selectinload(Player.contracts))
    if exclude_team_id:
        query = query.where(
            (Player.team_id != uuid.UUID(exclude_team_id)) | (Player.team_id.is_(None))
        )
    result = await db.execute(query)
    players = result.scalars().all()
    return [_serialize_player(p) for p in players]


@app.post("/transfers/sign", status_code=status.HTTP_200_OK)
async def sign_player(req: SignPlayerRequest, db: AsyncSession = Depends(get_db)):
    """
    Contrata jogador para o time do manager:
    - Debita taxa de transferência do orçamento
    - Encerra contrato anterior (se houver)
    - Cria novo contrato ACTIVE
    """
    from datetime import date as dt_date, timedelta

    team = await db.get(Team, uuid.UUID(req.team_id))
    player = await db.get(Player, uuid.UUID(req.player_id))
    if not team or not player:
        raise HTTPException(status_code=404, detail="Time ou jogador não encontrado.")

    if player.team_id and str(player.team_id) == req.team_id:
        raise HTTPException(status_code=400, detail="Jogador já pertence a este time.")

    # Idade mínima CBLOL/LEC-like: 16+ (academy); 18+ seria filtro no FE
    if player.get_age() < settings.min_age_erl:
        raise HTTPException(
            status_code=400,
            detail=f"Jogador com {player.get_age()} anos é inelegível (mínimo {settings.min_age_erl}).",
        )

    fee = Decimal(str(req.transfer_fee))
    try:
        team.deduct_budget(fee, operation="transferência")
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

    # Encerra contratos ativos anteriores
    contracts_q = await db.execute(
        select(Contract).where(
            Contract.player_id == player.id,
            Contract.status.in_([ContractStatus.ACTIVE, ContractStatus.ROOKIE_EXTENDED]),
        )
    )
    for old in contracts_q.scalars().all():
        old.terminate()

    seasons = max(1, min(4, int(req.seasons)))
    today = dt_date.today()
    new_contract = Contract(
        id=uuid.uuid4(),
        player_id=player.id,
        team_id=team.id,
        start_date=today,
        end_date=today + timedelta(days=180 * seasons),
        seasons_duration=seasons,
        monthly_salary=Decimal(str(req.monthly_salary)),
        status=ContractStatus.ACTIVE,
        has_rookie_clause=player.is_rookie,
        rookie_games_played=0,
        rookie_total_league_games=0,
    )
    player.team_id = team.id
    db.add(new_contract)
    await db.flush()

    return {
        "message": f"{player.name} contratado por {team.name}.",
        "team_budget": float(team.budget),
        "player": _serialize_player(player, new_contract),
    }

@app.get("/champions", status_code=status.HTTP_200_OK)
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
            "utility": c.utility
        }
        for c in champs
    ]


@app.get("/leagues/{league_id}/standings", status_code=status.HTTP_200_OK)
async def get_league_standings(league_id: str, db: AsyncSession = Depends(get_db)):
    """Busca a tabela de classificação (standings) de uma liga."""
    query = await db.execute(
        select(LeagueTeam)
        .where(LeagueTeam.league_id == uuid.UUID(league_id))
    )
    teams = query.scalars().all()
    
    standings = []
    for lt in teams:
        # Carrega o nome do time
        team_query = await db.execute(select(Team).where(Team.id == lt.team_id))
        t = team_query.scalar_one()
        standings.append({
            "team_id": str(lt.team_id),
            "team_name": t.name,
            "wins": lt.wins,
            "losses": lt.losses,
            "points": lt.points,
            "win_rate": f"{lt.win_rate * 100:.1f}%",
            "is_in_playoffs": bool(lt.is_in_playoffs),
            "playoff_seed": lt.playoff_seed,
            "final_placement": lt.final_placement,
            "prize_earned": float(lt.prize_earned or 0),
        })
    
    # Ordena: placements finais (pós-playoffs) ou points/wins
    if any(s.get("final_placement") for s in standings):
        standings.sort(
            key=lambda x: (
                x["final_placement"] is None,
                x["final_placement"] if x["final_placement"] is not None else 99,
                -x["points"],
                -x["wins"],
            )
        )
    else:
        standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)
    return standings


@app.get("/leagues/{league_id}/playoffs", status_code=status.HTTP_200_OK)
async def get_league_playoffs(league_id: str, db: AsyncSession = Depends(get_db)):
    """
    Bracket de playoffs (top 6). Gera sob demanda se a fase já for PLAYOFFS.
    """
    from src.modules.calendar.playoff_service import PlayoffService

    league = await db.get(League, uuid.UUID(league_id))
    if not league:
        raise HTTPException(status_code=404, detail="Liga não encontrada.")

    ps = PlayoffService(db)
    bracket = await ps.get_bracket(league_id)

    if not bracket and league.current_phase == SplitPhase.PLAYOFFS:
        try:
            bracket = await ps.ensure_bracket(league)
            await db.commit()
        except Exception as e:
            logger.error(f"Falha ao gerar bracket: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    if not bracket:
        return {
            "status": "not_started",
            "message": "Playoffs ainda não iniciados. Avance a temporada regular até o fim.",
            "bracket": None,
        }

    return {"status": bracket.get("status", "active"), "bracket": bracket}


@app.post("/leagues/{league_id}/playoffs/start", status_code=status.HTTP_201_CREATED)
async def force_start_playoffs(league_id: str, db: AsyncSession = Depends(get_db)):
    """
    Dev/playtest: força PLAYOFFS + bracket top 6 sem avançar semanas.
    """
    from src.modules.calendar.playoff_service import PlayoffService

    league = await db.get(League, uuid.UUID(league_id))
    if not league:
        raise HTTPException(status_code=404, detail="Liga não encontrada.")

    calendar_service = CalendarService(db)
    sm = await calendar_service._get_or_create_sm(league)
    await sm.force_transition_to("PLAYOFFS")

    league.current_phase = SplitPhase.PLAYOFFS
    league.current_week = 0

    await redis_client.delete_playoff_state(str(league.id))
    ps = PlayoffService(db)
    bracket = await ps.initialize_from_standings(league)
    await db.commit()

    return {
        "message": "Playoffs iniciados (forçado).",
        "league_id": str(league.id),
        "bracket": bracket,
    }


def _match_summary_row(match_obj: Match, blue: Team, red: Team) -> dict:
    """Serializa partida para lista de resultados da rodada."""
    winner_id = str(match_obj.winner_team_id) if match_obj.winner_team_id else None
    winner_name = None
    if winner_id == str(blue.id):
        winner_name = blue.name
    elif winner_id == str(red.id):
        winner_name = red.name
    return {
        "match_id": str(match_obj.id),
        "blue_team_id": str(blue.id),
        "blue_team_name": blue.name,
        "blue_team_abbr": blue.abbreviation,
        "red_team_id": str(red.id),
        "red_team_name": red.name,
        "red_team_abbr": red.abbreviation,
        "winner_team_id": winner_id,
        "winner_name": winner_name,
        "duration": match_obj.match_duration_minutes,
        "split_week": match_obj.split_week,
        "split_phase": match_obj.split_phase.value if match_obj.split_phase else None,
        "is_playoff": bool(match_obj.is_playoff),
        "scheduled_at": match_obj.scheduled_at.isoformat() if match_obj.scheduled_at else None,
        "status": "complete" if winner_id else "pending",
    }


@app.get("/leagues/{league_id}/matches", status_code=status.HTTP_200_OK)
async def list_league_matches(
    league_id: str,
    week: Optional[int] = None,
    is_playoff: Optional[bool] = None,
    latest_round: bool = True,
    limit: int = 40,
    db: AsyncSession = Depends(get_db),
):
    """
    Lista partidas da liga (resultados da rodada).

    - latest_round=true (default): só a semana mais recente que tem jogos.
    - week=: filtra semana específica (ignora latest_round).
    """
    league = await db.get(League, uuid.UUID(league_id))
    if not league:
        raise HTTPException(status_code=404, detail="Liga não encontrada.")

    limit = max(1, min(int(limit or 40), 100))
    base = select(Match).where(Match.league_id == uuid.UUID(league_id))

    if is_playoff is not None:
        base = base.where(Match.is_playoff == is_playoff)

    if week is not None:
        base = base.where(Match.split_week == int(week))
    elif latest_round:
        # Semana mais recente com partidas (mesmo filtro playoff se houver)
        sub = select(Match.split_week).where(Match.league_id == uuid.UUID(league_id))
        if is_playoff is not None:
            sub = sub.where(Match.is_playoff == is_playoff)
        sub = sub.order_by(Match.split_week.desc(), Match.scheduled_at.desc()).limit(1)
        latest = (await db.execute(sub)).scalar_one_or_none()
        if latest is not None:
            base = base.where(Match.split_week == latest)

    query = await db.execute(
        base.order_by(Match.scheduled_at.desc()).limit(limit)
    )
    matches = list(query.scalars().all())

    # Prefetch times
    team_ids = set()
    for m in matches:
        team_ids.add(m.blue_team_id)
        team_ids.add(m.red_team_id)
    teams_map: Dict[uuid.UUID, Team] = {}
    if team_ids:
        tq = await db.execute(select(Team).where(Team.id.in_(list(team_ids))))
        for t in tq.scalars().all():
            teams_map[t.id] = t

    rows = []
    for m in matches:
        blue = teams_map.get(m.blue_team_id)
        red = teams_map.get(m.red_team_id)
        if not blue or not red:
            continue
        rows.append(_match_summary_row(m, blue, red))

    # Exibe ordem da rodada (mais antigas primeiro na UI)
    rows.reverse()

    return {
        "league_id": league_id,
        "count": len(rows),
        "week": rows[0]["split_week"] if rows else week,
        "matches": rows,
    }


@app.get("/matches/{match_id}", status_code=status.HTTP_200_OK)
async def get_match_details(match_id: str, db: AsyncSession = Depends(get_db)):
    """
    Busca os detalhes completos de uma partida (tenta primeiro no Redis, depois no Postgres).
    """
    # 1. Tenta no Redis
    cached = await redis_client.get_match_result(match_id)
    if cached:
        logger.info(f"Resultado da partida {match_id} recuperado do Redis Cache!")
        return {"source": "cache", "data": cached}

    # 2. Tenta no Banco de Dados
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
        }
    }


# --- Draft AI (turno a turno, oponente no FE) ---
class DraftAIDecisionRequest(BaseModel):
    blue_team_id: str
    red_team_id: str
    acting_side: str  # BLUE | RED
    current_turn: int = 0
    blue_bans: List[str] = []
    red_bans: List[str] = []
    blue_picks: List[Dict[str, str]] = []  # {champion, role}
    red_picks: List[Dict[str, str]] = []


@app.post("/draft/ai-decision", status_code=status.HTTP_200_OK)
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


# --- Offseason / novo split ---
class RenewContractRequest(BaseModel):
    team_id: str
    player_id: str
    seasons: int = 1
    monthly_salary: Optional[float] = None


class ReleasePlayerRequest(BaseModel):
    team_id: str
    player_id: str


@app.get("/offseason/status", status_code=status.HTTP_200_OK)
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


@app.post("/offseason/start", status_code=status.HTTP_201_CREATED)
async def force_start_offseason(db: AsyncSession = Depends(get_db)):
    """Dev/playtest: força fase OFFSEASON."""
    from src.modules.career.offseason_service import OffseasonService

    try:
        return await OffseasonService(db).force_offseason()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/offseason/contracts", status_code=status.HTTP_200_OK)
async def offseason_contracts(team_id: str, db: AsyncSession = Depends(get_db)):
    """Lista contratos do time para renovação."""
    from src.modules.career.offseason_service import OffseasonService

    try:
        rows = await OffseasonService(db).list_team_contracts(team_id)
        return {"team_id": team_id, "contracts": rows}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/offseason/renew", status_code=status.HTTP_200_OK)
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


@app.post("/offseason/release", status_code=status.HTTP_200_OK)
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


@app.post("/offseason/new-split", status_code=status.HTTP_200_OK)
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


# --- Save / Load de carreira ---
class CareerSaveRequest(BaseModel):
    slot: str = "slot1"
    manager_name: str
    team_id: str
    label: Optional[str] = None


@app.get("/career/saves", status_code=status.HTTP_200_OK)
async def list_career_saves():
    """Lista saves JSON em disco (pasta saves/)."""
    from src.modules.career.save_service import list_save_files

    return {"saves": list_save_files()}


@app.post("/career/save", status_code=status.HTTP_201_CREATED)
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


@app.post("/career/load/{slot}", status_code=status.HTTP_200_OK)
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


@app.delete("/career/saves/{slot}", status_code=status.HTTP_200_OK)
async def delete_career_save(slot: str):
    from src.modules.career.save_service import CareerSaveService

    ok = CareerSaveService.delete_save_static(slot)
    if not ok:
        raise HTTPException(status_code=404, detail="Save não encontrado.")
    return {"message": f"Save '{slot}' removido."}


# --- Simulação de Partida em Tempo Real (Live Match Engine) ---
from src.modules.simulation.match_engine_service import MatchEngineService

match_engine_service = MatchEngineService()

class StartLiveMatchRequest(BaseModel):
    blue_team_id: str
    red_team_id: str
    is_playoff: bool = False
    split_week: int = 1
    blue_draft: List[Dict[str, str]]
    red_draft: List[Dict[str, str]]
    # Velocidade: 1x (2s/min) | 2x | 4x | instant
    speed: str = "2x"

class CoachCommRequest(BaseModel):
    team_side: str  # "BLUE" ou "RED"

class LiveSpeedRequest(BaseModel):
    speed: str  # 1x | 2x | 4x | instant

@app.post("/matches/live/start", status_code=status.HTTP_201_CREATED)
async def start_live_match(req: StartLiveMatchRequest, db: AsyncSession = Depends(get_db)):
    """
    Inicializa e dispara a simulação assíncrona baseada em ticks no Redis Simulado.
    """
    blue_team = await db.get(Team, uuid.UUID(req.blue_team_id))
    red_team = await db.get(Team, uuid.UUID(req.red_team_id))
    if not blue_team or not red_team:
        raise HTTPException(status_code=404, detail="Um ou ambos os times não foram encontrados.")
        
    # Obtém a liga ativa da tabela
    league_query = await db.execute(select(League).limit(1))
    league = league_query.scalar_one_or_none()
    if not league:
        raise HTTPException(status_code=404, detail="Nenhuma liga cadastrada. Rode o seed antes.")
        
    # Cria ID único de partida
    match_id = str(uuid.uuid4())

    # Playoffs: marca série se a liga já está na fase (mesmo que o FE esqueça o flag)
    is_playoff = bool(req.is_playoff) or (
        league.current_phase == SplitPhase.PLAYOFFS
    )
    
    # Inicializa simulação
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
    )
    
    state_payload = live_state.model_dump() if hasattr(live_state, "model_dump") else live_state.dict()
    return {
        "message": "Simulação de partida ao vivo iniciada com sucesso!",
        "match_id": match_id,
        "state": state_payload,
    }


@app.post("/matches/live/{match_id}/speed", status_code=status.HTTP_200_OK)
async def set_live_match_speed(match_id: str, req: LiveSpeedRequest):
    """Altera a velocidade da partida em andamento (1x, 2x, 4x, instant)."""
    res = await match_engine_service.set_live_speed(match_id, req.speed)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@app.get("/matches/live/{match_id}/state", status_code=status.HTTP_200_OK)
async def get_live_match_state(match_id: str):
    """
    Retorna o estado mutável em tempo real da partida ao vivo a partir do Redis virtual.
    """
    state = await match_engine_service.get_live_state(match_id)
    if not state:
        raise HTTPException(status_code=404, detail="Partida ao vivo não encontrada ou já encerrada.")
    return state

@app.post("/matches/live/{match_id}/coach-comm", status_code=status.HTTP_200_OK)
async def live_coach_comm(match_id: str, req: CoachCommRequest):
    """
    Envia comandos táticos (Coach Comms) do treinador em tempo real durante o Early Game.
    """
    res = await match_engine_service.apply_coach_comm(match_id, req.team_side)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res
