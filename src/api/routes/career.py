"""Save / load de carreira + nova carreira do zero."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import CareerSaveRequest, NewCareerRequest
from src.core.database import get_db

logger = logging.getLogger("lol_manager_api")
router = APIRouter(tags=["career"])


@router.post("/career/new", status_code=status.HTTP_201_CREATED)
async def start_new_career(req: NewCareerRequest, db: AsyncSession = Depends(get_db)):
    """
    Inicia uma **nova carreira do zero**:

    1. Limpa Redis (calendário, moral, forma, live matches, draft, playoffs…)
    2. Re-seed forçado do CBLOL 2026 (drop_all + dados limpos: semana 1, dia 1)
    3. Reativa cache de patch
    4. Resolve o time pela **abreviação** (IDs mudam no reseed)

    Saves em disco (`saves/*.json`) **não** são apagados — use DELETE /career/saves/{slot}.
    """
    from src.api.routes.seed import seed_database
    from src.core.redis_client import redis_client
    from src.models.team import Team
    from src.modules.simulation.patch_service import PatchService

    manager_name = (req.manager_name or "").strip()
    abbr = (req.team_abbreviation or "").strip().upper()

    if len(manager_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome do treinador deve ter ao menos 2 caracteres.",
        )
    if not abbr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="team_abbreviation é obrigatório (ex.: PNG, FUR, RED).",
        )

    try:
        redis_cleared = await redis_client.flush_game_state()
        logger.info(f"[Career] Nova carreira — Redis limpo ({redis_cleared} chaves).")

        force = bool(req.force_reseed)
        seed_result = await seed_database(db=db, force=force)

        # Sessão pode estar stale após drop_all; garante leitura fresca
        try:
            db.expire_all()
        except Exception:
            pass

        teams = list((await db.execute(select(Team))).scalars().all())
        team = next(
            (t for t in teams if (t.abbreviation or "").upper() == abbr),
            None,
        )
        if team is None:
            available = sorted({(t.abbreviation or "?") for t in teams})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Time '{abbr}' não encontrado após seed. "
                    f"Disponíveis: {', '.join(available)}"
                ),
            )

        # Cache de patch (16.1) para draft/meta
        try:
            await PatchService(db).update_patch_cache(date.today())
        except Exception as pe:
            logger.warning(f"[Career] patch cache pós-new: {pe}")

        from src.models.league import League

        league_q = await db.execute(select(League).limit(1))
        league = league_q.scalar_one_or_none()

        logger.info(
            f"[Career] Nova carreira OK — coach={manager_name} team={team.abbreviation} "
            f"id={team.id} seed_skipped={seed_result.get('skipped')}"
        )
        return {
            "message": "Nova carreira iniciada do zero.",
            "manager_name": manager_name,
            "team_id": str(team.id),
            "team_name": team.name,
            "team_abbreviation": team.abbreviation,
            "league_id": str(league.id) if league else seed_result.get("league_id"),
            "phase": league.current_phase.value if league and league.current_phase else "REGULAR_SEASON",
            "week": int(league.current_week or 1) if league else 1,
            "day": int(league.current_day or 1) if league else 1,
            "redis_keys_cleared": redis_cleared,
            "seed": {
                "skipped": bool(seed_result.get("skipped")),
                "forced": force,
                "team_count": seed_result.get("team_count"),
                "league_id": seed_result.get("league_id"),
            },
            "teams": {t.abbreviation: str(t.id) for t in teams},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao iniciar nova carreira: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao iniciar nova carreira: {e}",
        )


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
