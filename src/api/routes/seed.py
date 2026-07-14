"""Semente CBLOL 2026 (drop + recreate)."""

import logging
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db, engine
from src.models import Base, Player, Team, Contract, League, LeagueTeam, Champion, ChampionRoleStats, Patch, ChampionPatchMeta, Staff
from src.shared.enums import PlayerRole, Region, LeagueType, SplitPhase, ContractStatus
from src.shared.champions_data import ALL_CHAMPIONS
from src.shared.cblol_2026_data import CBLOL_2026_TEAMS, KNOWN_SUBS, POOLS_BY_ROLE, LEAGUE_META

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["seed"])


@router.post("/db/seed", status_code=status.HTTP_201_CREATED)
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


