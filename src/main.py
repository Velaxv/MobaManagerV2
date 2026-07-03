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
    Semeia o banco de dados com a estrutura oficial do CBLOL 2026:
    - 1 Liga (CBLOL 2026)
    - 10 Times brasileiros com jogadores reais e comissões técnicas (Head Coaches obrigatórios).
    - 15 Campeões icônicos com flex picks e atributos por role.
    - 2 Patches competitivos com datas de vigor e modificadores de patch (ChampionPatchMeta).
    """
    try:
        logger.info("Recriando tabelas no banco de dados para semeadura limpa...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Iniciando semeadura do CBLOL 2026...")
        
        # 1. Cria a Liga CBLOL 2026
        cblol = League(
            id=uuid.uuid4(),
            name="Campeonato Brasileiro de League of Legends 2026",
            abbreviation="CBLOL",
            league_type=LeagueType.LEC, # Regulamento exige idade >= 18 anos
            region=Region.CBLOL,
            current_phase=SplitPhase.REGULAR_SEASON,
            current_week=1,
            current_day=1,
            regular_season_weeks=9,
            matches_per_week=2,
            playoff_teams=6,
            prize_pool={"1st": 100000.0, "2nd": 60000.0, "3rd": 40000.0},
            total_prize_pool=Decimal("200000.00")
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

        # 4. Dados dos Times e Elencos do CBLOL 2026
        # paiN, LOUD, RED, Keyd, KaBuM e FURIA têm times Academy (11 players).
        # Fluxo, INTZ, Liberty e Los Grandes não têm (6 players).
        teams_data = [
            # (name, tag, has_academy, budget_millions, monthly_rev, coach_name, strategic_coach_name, players_list)
            ("paiN Gaming", "PNG", True, 4.5, 120, "Sarkis", "Xypherz", [
                ("Wizer", PlayerRole.TOP, 148, 175, 16.0, 15.0),
                ("Cariok", PlayerRole.JUNGLE, 142, 165, 14.5, 16.0),
                ("dyruyo", PlayerRole.MID, 145, 180, 15.0, 14.0),
                ("TitaN", PlayerRole.BOT, 150, 185, 16.5, 13.0),
                ("Kuri", PlayerRole.SUPPORT, 138, 160, 14.0, 15.0),
            ]),
            ("LOUD", "LLL", True, 5.0, 130, "Stardust", None, [
                ("Robo", PlayerRole.TOP, 152, 170, 15.5, 17.0),
                ("Croc", PlayerRole.JUNGLE, 144, 162, 14.0, 15.0),
                ("tinowns", PlayerRole.MID, 151, 175, 16.0, 16.0),
                ("Route", PlayerRole.BOT, 153, 180, 17.0, 13.0),
                ("Ceos", PlayerRole.SUPPORT, 149, 172, 15.0, 16.0),
            ]),
            ("RED Canids Kalunga", "RED", True, 3.8, 100, "Coelho", "Aoshi", [
                ("fNb", PlayerRole.TOP, 146, 170, 15.5, 15.0),
                ("Aegis", PlayerRole.JUNGLE, 141, 165, 14.0, 14.0),
                ("Grevthar", PlayerRole.MID, 136, 160, 13.5, 16.5),
                ("Brance", PlayerRole.BOT, 143, 175, 15.0, 14.5),
                ("JoJo", PlayerRole.SUPPORT, 139, 162, 14.0, 14.0),
            ]),
            ("Vivo Keyd Stars", "VKS", True, 4.0, 110, "SeeEl", None, [
                ("Guigo", PlayerRole.TOP, 143, 168, 14.5, 15.0),
                ("Disamis", PlayerRole.JUNGLE, 140, 172, 14.5, 13.0),
                ("Toucouille", PlayerRole.MID, 148, 170, 16.0, 15.5),
                ("SMILEY", PlayerRole.BOT, 142, 165, 14.5, 14.0),
                ("ProDelta", PlayerRole.SUPPORT, 141, 175, 15.0, 14.5),
            ]),
            ("KaBuM! Esports", "KBM", True, 4.2, 115, "von", "Kury", [
                ("Lonely", PlayerRole.TOP, 144, 168, 15.0, 14.0),
                ("Malrang", PlayerRole.JUNGLE, 147, 170, 15.0, 15.0),
                ("Hauz", PlayerRole.MID, 141, 165, 14.5, 14.0),
                ("Netuno", PlayerRole.BOT, 146, 178, 15.5, 14.0),
                ("Redbert", PlayerRole.SUPPORT, 138, 158, 13.5, 15.0),
            ]),
            ("FURIA Esports", "FUR", True, 3.5, 95, "Maestro", None, [
                ("Tay", PlayerRole.TOP, 139, 160, 14.0, 14.5),
                ("Goot", PlayerRole.JUNGLE, 137, 164, 14.0, 13.5),
                ("Tutsz", PlayerRole.MID, 140, 168, 14.5, 14.0),
                ("Ayu", PlayerRole.BOT, 142, 175, 15.0, 14.0),
                ("Cavalo", PlayerRole.SUPPORT, 135, 160, 13.5, 14.0),
            ]),
            ("Fluxo", "FX", False, 3.0, 80, "Turtle", None, [
                ("Kiari", PlayerRole.TOP, 135, 160, 13.5, 14.0),
                ("Shini", PlayerRole.JUNGLE, 138, 158, 13.5, 14.5),
                ("FuLgOr", PlayerRole.MID, 132, 155, 13.0, 13.5),
                ("Trigo", PlayerRole.BOT, 140, 168, 14.5, 14.0),
                ("scylla", PlayerRole.SUPPORT, 134, 155, 13.0, 13.5),
            ]),
            ("INTZ", "ITZ", False, 2.5, 70, "Maestro_Base", None, [
                ("Boal", PlayerRole.TOP, 134, 158, 13.5, 13.5),
                ("Yampi", PlayerRole.JUNGLE, 139, 162, 14.0, 14.0),
                ("Dioge", PlayerRole.MID, 133, 156, 13.0, 14.0),
                ("NinjaKiwi", PlayerRole.BOT, 137, 162, 14.0, 13.0),
                ("Damage", PlayerRole.SUPPORT, 136, 158, 13.5, 14.0),
            ]),
            ("Liberty", "LBR", False, 2.2, 65, "BeellzY", None, [
                ("Makes", PlayerRole.TOP, 136, 162, 14.0, 13.5),
                ("Drakehero", PlayerRole.JUNGLE, 135, 165, 14.0, 13.0),
                ("Piloto", PlayerRole.MID, 139, 168, 14.5, 14.0),
                ("Raven", PlayerRole.BOT, 134, 158, 13.0, 13.5),
                ("Destruge", PlayerRole.SUPPORT, 131, 155, 13.0, 13.0),
            ]),
            ("Los Grandes", "LOS", False, 2.8, 75, "Medonho", None, [
                ("SuperCleber", PlayerRole.TOP, 137, 165, 14.0, 14.0),
                ("Seize", PlayerRole.JUNGLE, 138, 160, 13.5, 14.0),
                ("Envy", PlayerRole.MID, 141, 166, 14.5, 14.5),
                ("Celo", PlayerRole.BOT, 136, 160, 13.5, 13.5),
                ("Ranger", PlayerRole.SUPPORT, 138, 158, 13.0, 15.0),
            ]),
        ]

        champions_pool_mock = [
            {"champion": "Azir", "tier": "MAIN"},
            {"champion": "Viktor", "tier": "MAIN"},
            {"champion": "Jax", "tier": "SECONDARY"},
            {"champion": "Aatrox", "tier": "SECONDARY"},
            {"champion": "Kai'Sa", "tier": "MAIN"},
        ]

        teams_list = []
        three_seasons_later = today + timedelta(days=180 * 3)

        for name, tag, has_academy, budget, revenue, coach_name, strat_coach_name, starters in teams_data:
            team_id = uuid.uuid4()
            team = Team(
                id=team_id,
                name=name,
                abbreviation=tag,
                region=Region.CBLOL,
                budget=Decimal(f"{budget * 1000000:.2f}"),
                monthly_revenue=Decimal(f"{revenue * 1000:.2f}")
            )
            db.add(team)
            teams_list.append(team)

            # 4.1. Associa Time à Liga
            lt = LeagueTeam(
                id=uuid.uuid4(),
                league_id=cblol.id,
                team_id=team_id,
                wins=0,
                losses=0,
                points=0
            )
            db.add(lt)

            # 4.2. Cadastra Head Coach (Obrigatório)
            head_coach = Staff(
                id=uuid.uuid4(),
                team_id=team_id,
                name=f"Coach {coach_name}",
                role="HEAD_COACH",
                communication=float(random.randint(12, 19)),
                meta_reading=float(random.randint(12, 19))
            )
            db.add(head_coach)

            # 4.3. Cadastra Strategic Coach (Opcional)
            if strat_coach_name:
                strat_coach = Staff(
                    id=uuid.uuid4(),
                    team_id=team_id,
                    name=f"Coach {strat_coach_name}",
                    role="STRATEGIC_COACH",
                    communication=float(random.randint(10, 17)),
                    meta_reading=float(random.randint(13, 19))
                )
                db.add(strat_coach)

            # 4.4. Cadastra Titulares Reais
            for p_name, role, ca, pa, mech, fcs in starters:
                player_id = uuid.uuid4()
                p = Player(
                    id=player_id,
                    name=p_name,
                    date_of_birth=date(1998 + random.randint(0, 5), 1, 1), # Idade >= 18
                    nationality="Brazil",
                    role=role,
                    region=Region.CBLOL,
                    is_rookie=False,
                    current_ability=ca,
                    potential_ability=pa,
                    mechanics=mech,
                    focus=fcs,
                    resilience=float(random.randint(12, 18)),
                    coachability=float(random.randint(12, 18)),
                    teamwork=float(random.randint(12, 18)),
                    consistency=float(random.randint(12, 18)),
                    big_match_aptitude=float(random.randint(12, 18)),
                    champion_pool=champions_pool_mock,
                    burnout_meter=0.0,
                    visual_fatigue=0.0,
                    mental_fatigue=0.0,
                    team_id=team_id
                )
                db.add(p)
                
                # Contrato
                contract = Contract(
                    id=uuid.uuid4(),
                    player_id=player_id,
                    team_id=team_id,
                    start_date=today,
                    end_date=three_seasons_later,
                    seasons_duration=3,
                    monthly_salary=Decimal(f"{random.randint(4000, 18000)}.00"),
                    status=ContractStatus.ACTIVE,
                    has_rookie_clause=False,
                    rookie_games_played=0,
                    rookie_total_league_games=cblol.total_regular_season_matches
                )
                db.add(contract)

            # 4.5. Cadastra Reservas/Base (Academy)
            # Para cumprir a regra rígida de elencos:
            # Se has_academy=True -> no mínimo 11 no total (5 titulares + 6 academy/reservas)
            # Se has_academy=False -> no mínimo 6 no total (5 titulares + 1 reserva)
            num_reserves = 6 if has_academy else 1
            roles_list = [PlayerRole.TOP, PlayerRole.JUNGLE, PlayerRole.MID, PlayerRole.BOT, PlayerRole.SUPPORT]
            
            for i in range(num_reserves):
                reserve_role = roles_list[i % len(roles_list)]
                player_id = uuid.uuid4()
                p = Player(
                    id=player_id,
                    name=f"{tag} Academy {reserve_role.value} {i+1}",
                    date_of_birth=date(2007 + random.randint(0, 2), 1, 1), # idade >= 16 anos (ERL/Academy)
                    nationality="Brazil",
                    role=reserve_role,
                    region=Region.CBLOL,
                    is_rookie=True,
                    current_ability=random.randint(85, 115),
                    potential_ability=random.randint(135, 160),
                    mechanics=float(random.randint(10, 14)),
                    focus=float(random.randint(9, 14)),
                    resilience=float(random.randint(9, 14)),
                    coachability=float(random.randint(11, 16)),
                    teamwork=float(random.randint(10, 15)),
                    consistency=float(random.randint(9, 14)),
                    big_match_aptitude=float(random.randint(9, 14)),
                    champion_pool=champions_pool_mock,
                    burnout_meter=0.0,
                    visual_fatigue=0.0,
                    mental_fatigue=0.0,
                    team_id=team_id
                )
                db.add(p)
                
                # Contrato
                contract = Contract(
                    id=uuid.uuid4(),
                    player_id=player_id,
                    team_id=team_id,
                    start_date=today,
                    end_date=three_seasons_later,
                    seasons_duration=3,
                    monthly_salary=Decimal(f"{random.randint(1500, 3500)}.00"),
                    status=ContractStatus.ACTIVE,
                    has_rookie_clause=True, # Rookies ganham cláusula
                    rookie_games_played=0,
                    rookie_total_league_games=cblol.total_regular_season_matches
                )
                db.add(contract)

        await db.commit()
        logger.info("Semeadura do CBLOL 2026 concluída com sucesso!")
        
        return {
            "message": "Banco de dados semeado com o CBLOL 2026 com sucesso!",
            "league_id": str(cblol.id),
            "teams": {t.abbreviation: str(t.id) for t in teams_list}
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro na semeadura do CBLOL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno de semeadura: {e}")


# --- Calendário / Rotina Diária ---
@app.get("/calendar", status_code=status.HTTP_200_OK)
async def get_calendar_state(db: AsyncSession = Depends(get_db)):
    """
    Retorna o estado atual do calendário (liga ativa).
    """
    league_query = await db.execute(select(League).limit(1))
    league = league_query.scalar_one_or_none()
    if not league:
        return {"current_day": 1, "current_week": 1, "current_phase": "OFFSEASON"}
    
    return {
        "current_day": league.current_day,
        "current_week": league.current_week,
        "current_phase": league.current_phase.value
    }

@app.post("/calendar/advance", status_code=status.HTTP_200_OK)
async def advance_calendar(db: AsyncSession = Depends(get_db)):
    """
    Avança um dia no calendário do jogo.
    Processa a State Machine do calendário e roda o BurnoutService
    para aplicar penalidades de fadiga e burnout aos jogadores.
    """
    calendar_service = CalendarService(db)
    results = await calendar_service.advance_all_leagues()
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

    # Valida roster mínimo
    try:
        blue_team.validate_roster_size(settings.min_roster_size)
        red_team.validate_roster_size(settings.min_roster_size)
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
    """Busca os jogadores de uma equipe específica."""
    query = await db.execute(select(Player).where(Player.team_id == uuid.UUID(team_id)))
    players = query.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "role": p.role.value,
            "region": p.region.value if p.region else None,
            "isRookie": p.is_rookie,
            "currentAbility": p.current_ability,
            "potentialAbility": p.potential_ability,
            "mechanics": p.mechanics,
            "championPool": p.champion_pool,
            "focus": p.focus,
            "resilience": p.resilience,
            "coachability": p.coachability,
            "teamwork": p.teamwork,
            "consistency": p.consistency,
            "bigMatchAptitude": p.big_match_aptitude,
            "burnoutMeter": p.burnout_meter,
            "visualFatigue": p.visual_fatigue,
            "mentalFatigue": p.mental_fatigue,
            "hasRookieClause": False, # Na interface antiga
            "participationRate": 1.0
        }
        for p in players
    ]

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
            "win_rate": f"{lt.win_rate * 100:.1f}%"
        })
    
    # Ordena por pontos e depois vitórias
    standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)
    return standings


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

    # Carrega nomes dos times
    b_team_query = await db.execute(select(Team).where(Team.id == match_obj.blue_team_id))
    b_name = b_team_query.scalar_one().name
    r_team_query = await db.execute(select(Team).where(Team.id == match_obj.red_team_id))
    r_name = r_team_query.scalar_one().name

    return {
        "source": "database",
        "data": {
            "match_id": str(match_obj.id),
            "blue_team": b_name,
            "red_team": r_name,
            "winner_team_id": str(match_obj.winner_team_id),
            "blue_result": match_obj.blue_result.value if match_obj.blue_result else None,
            "red_result": match_obj.red_result.value if match_obj.red_result else None,
            "duration": match_obj.match_duration_minutes,
            "blue_win_probability": match_obj.blue_win_probability,
            "early_game": match_obj.early_game_log,
            "mid_game": match_obj.mid_game_log,
            "late_game": match_obj.late_game_log,
            "draft": match_obj.draft_log
        }
    }


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

class CoachCommRequest(BaseModel):
    team_side: str  # "BLUE" ou "RED"

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
    
    # Inicializa simulação
    live_state = await match_engine_service.start_live_simulation(
        match_id=match_id,
        league_id=str(league.id),
        split_week=req.split_week,
        is_playoff=req.is_playoff,
        blue_team=blue_team,
        red_team=red_team,
        blue_draft=req.blue_draft,
        red_draft=req.red_draft
    )
    
    return {
        "message": "Simulação de partida ao vivo iniciada com sucesso!",
        "match_id": match_id,
        "state": live_state.dict()
    }

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
