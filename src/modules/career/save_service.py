# -*- coding: utf-8 -*-
"""
Save / Load de carreira (JSON em disco).

Persiste progresso do manager sobre o seed CBLOL atual:
  - Meta (nome, time, slot, versão)
  - Liga + standings (league_teams)
  - Budgets dos times
  - Estado dos jogadores (fadiga, CA, time, etc.)
  - Contratos ativos
  - Snapshot Redis: calendário SM + bracket de playoffs

Não recria o universo: exige DB semeado com os mesmos UUIDs (não rode seed
depois do save, ou o load falha com mismatch).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.redis_client import redis_client
from src.models.contract import Contract
from src.models.league import League, LeagueTeam
from src.models.player import Player
from src.models.team import Team
from src.shared.enums import ContractStatus, SplitPhase

logger = logging.getLogger(__name__)

SAVE_VERSION = 1
SEED_TAG = "cblol_2026_v1"
SLOT_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,32}$")


def saves_dir() -> Path:
    root = Path(__file__).resolve().parents[3]  # projeto root
    path = root / "saves"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slot_path(slot: str) -> Path:
    if not SLOT_RE.match(slot):
        raise ValueError(
            "Slot inválido. Use letras, números, _ ou - (máx. 32 caracteres)."
        )
    return saves_dir() / f"{slot}.json"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if hasattr(obj, "value"):  # Enum
        return obj.value
    raise TypeError(f"Não serializável: {type(obj)}")


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def list_save_files() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for path in sorted(saves_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("meta") or {}
            items.append(
                {
                    "slot": path.stem,
                    "manager_name": meta.get("manager_name"),
                    "team_id": meta.get("team_id"),
                    "team_name": meta.get("team_name"),
                    "team_abbr": meta.get("team_abbr"),
                    "saved_at": meta.get("saved_at"),
                    "phase": meta.get("phase"),
                    "week": meta.get("week"),
                    "day": meta.get("day"),
                    "save_version": data.get("save_version", 0),
                    "seed_tag": data.get("seed_tag"),
                }
            )
        except Exception as exc:
            logger.warning(f"[Career] Save corrompido {path.name}: {exc}")
            items.append(
                {
                    "slot": path.stem,
                    "error": "arquivo corrompido",
                    "saved_at": None,
                }
            )
    items.sort(key=lambda x: x.get("saved_at") or "", reverse=True)
    return items


class CareerSaveService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def list_saves(self) -> List[Dict[str, Any]]:
        return list_save_files()

    # ------------------------------------------------------------------ save
    async def save_career(
        self,
        slot: str,
        manager_name: str,
        team_id: str,
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = _slot_path(slot)
        team = await self.db.get(Team, uuid.UUID(team_id))
        if not team:
            raise ValueError("Time do manager não encontrado.")

        league_q = await self.db.execute(select(League).limit(1))
        league = league_q.scalar_one_or_none()
        if not league:
            raise ValueError("Nenhuma liga no banco. Rode o seed antes de salvar.")

        # Players
        players_q = await self.db.execute(select(Player))
        players_payload = []
        for p in players_q.scalars().all():
            players_payload.append(
                {
                    "id": str(p.id),
                    "team_id": str(p.team_id) if p.team_id else None,
                    "name": p.name,
                    "current_ability": p.current_ability,
                    "potential_ability": p.potential_ability,
                    "burnout_meter": float(p.burnout_meter or 0),
                    "visual_fatigue": float(p.visual_fatigue or 0),
                    "mental_fatigue": float(p.mental_fatigue or 0),
                    "games_played_this_split": int(p.games_played_this_split or 0),
                    "is_rookie": bool(p.is_rookie),
                    "mechanics": float(p.mechanics) if p.mechanics is not None else None,
                    "focus": float(p.focus) if p.focus is not None else None,
                    "resilience": float(p.resilience) if p.resilience is not None else None,
                    "coachability": float(p.coachability) if p.coachability is not None else None,
                    "teamwork": float(p.teamwork) if p.teamwork is not None else None,
                    "consistency": float(p.consistency) if p.consistency is not None else None,
                    "big_match_aptitude": float(p.big_match_aptitude)
                    if p.big_match_aptitude is not None
                    else None,
                    "champion_pool": p.champion_pool,
                }
            )

        # Teams (budget / revenue)
        teams_q = await self.db.execute(select(Team))
        teams_payload = []
        for t in teams_q.scalars().all():
            teams_payload.append(
                {
                    "id": str(t.id),
                    "name": t.name,
                    "abbreviation": t.abbreviation,
                    "budget": float(t.budget or 0),
                    "monthly_revenue": float(t.monthly_revenue or 0),
                }
            )

        # Contracts
        contracts_q = await self.db.execute(select(Contract))
        contracts_payload = []
        for c in contracts_q.scalars().all():
            contracts_payload.append(
                {
                    "id": str(c.id),
                    "player_id": str(c.player_id),
                    "team_id": str(c.team_id),
                    "status": c.status.value if c.status else None,
                    "start_date": c.start_date.isoformat() if c.start_date else None,
                    "end_date": c.end_date.isoformat() if c.end_date else None,
                    "seasons_duration": c.seasons_duration,
                    "monthly_salary": float(c.monthly_salary or 0),
                    "has_rookie_clause": bool(getattr(c, "has_rookie_clause", False)),
                    "rookie_games_played": int(getattr(c, "rookie_games_played", 0) or 0),
                    "rookie_total_league_games": int(
                        getattr(c, "rookie_total_league_games", 0) or 0
                    ),
                }
            )

        # Standings
        lt_q = await self.db.execute(
            select(LeagueTeam).where(LeagueTeam.league_id == league.id)
        )
        standings_payload = []
        for lt in lt_q.scalars().all():
            standings_payload.append(
                {
                    "team_id": str(lt.team_id),
                    "wins": lt.wins,
                    "losses": lt.losses,
                    "points": lt.points,
                    "is_in_playoffs": bool(lt.is_in_playoffs),
                    "playoff_seed": lt.playoff_seed,
                    "final_placement": lt.final_placement,
                    "prize_earned": float(lt.prize_earned or 0),
                }
            )

        calendar_state = await redis_client.get_calendar_state(str(league.id))
        playoff_state = await redis_client.get_playoff_state(str(league.id))

        meta = {
            "slot": slot,
            "label": label or f"Carreira {manager_name}",
            "manager_name": manager_name,
            "team_id": str(team.id),
            "team_name": team.name,
            "team_abbr": team.abbreviation,
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "phase": league.current_phase.value if league.current_phase else None,
            "week": league.current_week,
            "day": league.current_day,
            "league_id": str(league.id),
            "league_name": league.name,
        }

        payload = {
            "save_version": SAVE_VERSION,
            "seed_tag": SEED_TAG,
            "meta": meta,
            "league": {
                "id": str(league.id),
                "current_phase": league.current_phase.value if league.current_phase else None,
                "current_week": league.current_week,
                "current_day": league.current_day,
                "regular_season_weeks": league.regular_season_weeks,
                "playoff_teams": league.playoff_teams,
            },
            "teams": teams_payload,
            "players": players_payload,
            "contracts": contracts_payload,
            "standings": standings_payload,
            "redis": {
                "calendar": calendar_state,
                "playoffs": playoff_state,
            },
        }

        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )
        logger.info(f"[Career] Save gravado: {path.name} ({manager_name} / {team.abbreviation})")
        return {"slot": slot, "path": str(path), "meta": meta}

    # ------------------------------------------------------------------ load
    async def load_career(self, slot: str) -> Dict[str, Any]:
        path = _slot_path(slot)
        if not path.exists():
            raise FileNotFoundError(f"Save '{slot}' não encontrado.")

        data = json.loads(path.read_text(encoding="utf-8"))
        if int(data.get("save_version") or 0) > SAVE_VERSION:
            raise ValueError(
                f"Save de versão mais nova ({data.get('save_version')}) — atualize o jogo."
            )
        if data.get("seed_tag") and data["seed_tag"] != SEED_TAG:
            logger.warning(
                f"[Career] seed_tag diverge: save={data.get('seed_tag')} game={SEED_TAG}"
            )

        meta = data.get("meta") or {}
        league_data = data.get("league") or {}
        league_id = league_data.get("id") or meta.get("league_id")

        league_q = await self.db.execute(select(League).limit(1))
        league = league_q.scalar_one_or_none()
        if not league:
            raise ValueError("Banco sem liga. Rode o seed antes de carregar.")

        if league_id and str(league.id) != str(league_id):
            # Seed foi refeito — IDs mudaram
            raise ValueError(
                "O banco atual não corresponde a este save (liga diferente). "
                "Carregue só funciona no mesmo seed/DB em que salvou. "
                "Dica: não rode seed_runner entre save e load."
            )

        # League fields
        if league_data.get("current_phase"):
            try:
                league.current_phase = SplitPhase(league_data["current_phase"])
            except ValueError:
                pass
        if league_data.get("current_week") is not None:
            league.current_week = int(league_data["current_week"])
        if league_data.get("current_day") is not None:
            league.current_day = int(league_data["current_day"])

        # Teams
        teams_by_id = {
            str(t.id): t
            for t in (await self.db.execute(select(Team))).scalars().all()
        }
        for row in data.get("teams") or []:
            t = teams_by_id.get(str(row["id"]))
            if not t:
                continue
            t.budget = Decimal(str(row.get("budget") or 0))
            if row.get("monthly_revenue") is not None:
                t.monthly_revenue = Decimal(str(row["monthly_revenue"]))

        # Players
        players_by_id = {
            str(p.id): p
            for p in (await self.db.execute(select(Player))).scalars().all()
        }
        missing_players = 0
        for row in data.get("players") or []:
            p = players_by_id.get(str(row["id"]))
            if not p:
                missing_players += 1
                continue
            if row.get("team_id"):
                p.team_id = uuid.UUID(str(row["team_id"]))
            else:
                p.team_id = None
            if row.get("current_ability") is not None:
                p.current_ability = int(row["current_ability"])
            if row.get("potential_ability") is not None:
                # garante PA >= CA
                pa = int(row["potential_ability"])
                p.potential_ability = max(pa, int(p.current_ability or 0))
            p.burnout_meter = float(row.get("burnout_meter") or 0)
            p.visual_fatigue = float(row.get("visual_fatigue") or 0)
            p.mental_fatigue = float(row.get("mental_fatigue") or 0)
            p.games_played_this_split = int(row.get("games_played_this_split") or 0)
            if row.get("is_rookie") is not None:
                p.is_rookie = bool(row["is_rookie"])
            for attr in (
                "mechanics",
                "focus",
                "resilience",
                "coachability",
                "teamwork",
                "consistency",
                "big_match_aptitude",
            ):
                if row.get(attr) is not None and hasattr(p, attr):
                    setattr(p, attr, float(row[attr]))
            if row.get("champion_pool") is not None:
                p.champion_pool = row["champion_pool"]

        if missing_players:
            logger.warning(
                f"[Career] {missing_players} jogadores do save não existem no DB atual"
            )

        # Contracts: update by id; also handle team changes via status
        contracts_by_id = {
            str(c.id): c
            for c in (await self.db.execute(select(Contract))).scalars().all()
        }
        for row in data.get("contracts") or []:
            c = contracts_by_id.get(str(row["id"]))
            if not c:
                continue
            c.team_id = uuid.UUID(str(row["team_id"]))
            c.player_id = uuid.UUID(str(row["player_id"]))
            if row.get("status"):
                try:
                    c.status = ContractStatus(row["status"])
                except ValueError:
                    pass
            if row.get("monthly_salary") is not None:
                c.monthly_salary = Decimal(str(row["monthly_salary"]))
            if row.get("seasons_duration") is not None:
                c.seasons_duration = int(row["seasons_duration"])
            if row.get("rookie_games_played") is not None:
                c.rookie_games_played = int(row["rookie_games_played"])
            if row.get("rookie_total_league_games") is not None:
                c.rookie_total_league_games = int(row["rookie_total_league_games"])
            sd = _parse_date(row.get("start_date"))
            ed = _parse_date(row.get("end_date"))
            if sd:
                c.start_date = sd
            if ed:
                c.end_date = ed

        # Standings
        lt_q = await self.db.execute(
            select(LeagueTeam).where(LeagueTeam.league_id == league.id)
        )
        lt_by_team = {str(lt.team_id): lt for lt in lt_q.scalars().all()}
        for row in data.get("standings") or []:
            lt = lt_by_team.get(str(row["team_id"]))
            if not lt:
                continue
            lt.wins = int(row.get("wins") or 0)
            lt.losses = int(row.get("losses") or 0)
            lt.points = int(row.get("points") or 0)
            lt.is_in_playoffs = bool(row.get("is_in_playoffs"))
            lt.playoff_seed = row.get("playoff_seed")
            lt.final_placement = row.get("final_placement")
            lt.prize_earned = Decimal(str(row.get("prize_earned") or 0))

        await self.db.flush()

        # Redis restore
        redis_blob = data.get("redis") or {}
        cal = redis_blob.get("calendar")
        if cal:
            await redis_client.set_calendar_state(str(league.id), cal)
        else:
            # limpa SM se save não tinha
            await redis_client.delete_calendar_state(str(league.id))

        po = redis_blob.get("playoffs")
        if po:
            await redis_client.set_playoff_state(str(league.id), po)
        else:
            await redis_client.delete_playoff_state(str(league.id))

        logger.info(
            f"[Career] Load OK slot={slot} manager={meta.get('manager_name')} "
            f"team={meta.get('team_abbr')}"
        )
        return {
            "slot": slot,
            "meta": meta,
            "manager_name": meta.get("manager_name"),
            "team_id": meta.get("team_id"),
            "team_name": meta.get("team_name"),
            "league_id": str(league.id),
            "phase": league.current_phase.value if league.current_phase else None,
            "week": league.current_week,
            "day": league.current_day,
        }

    def delete_save(self, slot: str) -> bool:
        return self.delete_save_static(slot)

    @staticmethod
    def delete_save_static(slot: str) -> bool:
        path = _slot_path(slot)
        if path.exists():
            path.unlink()
            return True
        return False
