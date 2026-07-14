# -*- coding: utf-8 -*-
"""
Playoffs top-6 (CBLOL-style single elimination com bye para seeds 1 e 2).

Formato:
  QF1: 3 vs 6  →  vencedor enfrenta seed 2 nas semis
  QF2: 4 vs 5  →  vencedor enfrenta seed 1 nas semis
  SF1: 1 vs W(QF2)
  SF2: 2 vs W(QF1)
  Final: W(SF1) vs W(SF2)

Estado do bracket vive no Redis (chave playoffs:league:{id}).
Séries MVP: 1 partida decisiva (BO1 jogável), labels best_of para UI.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.redis_client import redis_client
from src.models.league import League, LeagueTeam
from src.models.team import Team

logger = logging.getLogger(__name__)

ROUND_QUARTER = "QUARTERFINAL"
ROUND_SEMI = "SEMIFINAL"
ROUND_FINAL = "FINAL"

# Semana da SM de playoffs → rodada
WEEK_TO_ROUND = {
    0: ROUND_QUARTER,
    1: ROUND_SEMI,
}
# week >= 2 → FINAL


def week_to_playoff_round(week: int) -> str:
    w = max(0, int(week))
    if w <= 0:
        return ROUND_QUARTER
    if w == 1:
        return ROUND_SEMI
    return ROUND_FINAL


def build_top6_bracket(
    seeds: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Monta o bracket a partir de 6 seeds ordenados (seed 1 = melhor).

    Cada item de seeds: {seed, team_id, team_name, team_abbr}
    """
    if len(seeds) < 6:
        raise ValueError(f"Playoffs top-6 exigem 6 times, recebeu {len(seeds)}")

    by_seed = {int(s["seed"]): s for s in seeds}
    for i in range(1, 7):
        if i not in by_seed:
            raise ValueError(f"Seed {i} ausente no bracket")

    def team_fields(seed_n: int) -> Dict[str, Any]:
        s = by_seed[seed_n]
        return {
            "team_id": str(s["team_id"]),
            "team_name": s.get("team_name"),
            "team_abbr": s.get("team_abbr"),
            "seed": seed_n,
        }

    def empty_side() -> Dict[str, Any]:
        return {
            "team_id": None,
            "team_name": None,
            "team_abbr": None,
            "seed": None,
        }

    series = [
        {
            "id": "qf1",
            "round": ROUND_QUARTER,
            "label": "Quartas — 3º vs 6º",
            "best_of": 3,
            "home": team_fields(3),
            "away": team_fields(6),
            "winner_team_id": None,
            "status": "ready",  # ready | pending | complete
            "feeds_into": "sf2",
            "feeds_slot": "away",
        },
        {
            "id": "qf2",
            "round": ROUND_QUARTER,
            "label": "Quartas — 4º vs 5º",
            "best_of": 3,
            "home": team_fields(4),
            "away": team_fields(5),
            "winner_team_id": None,
            "status": "ready",
            "feeds_into": "sf1",
            "feeds_slot": "away",
        },
        {
            "id": "sf1",
            "round": ROUND_SEMI,
            "label": "Semifinal — 1º vs vencedor QF",
            "best_of": 3,
            "home": team_fields(1),
            "away": empty_side(),
            "winner_team_id": None,
            "status": "pending",
            "feeds_into": "final",
            "feeds_slot": "home",
        },
        {
            "id": "sf2",
            "round": ROUND_SEMI,
            "label": "Semifinal — 2º vs vencedor QF",
            "best_of": 3,
            "home": team_fields(2),
            "away": empty_side(),
            "winner_team_id": None,
            "status": "pending",
            "feeds_into": "final",
            "feeds_slot": "away",
        },
        {
            "id": "final",
            "round": ROUND_FINAL,
            "label": "Grande Final",
            "best_of": 5,
            "home": empty_side(),
            "away": empty_side(),
            "winner_team_id": None,
            "status": "pending",
            "feeds_into": None,
            "feeds_slot": None,
        },
    ]

    return {
        "status": "active",  # active | complete
        "format": "top6_single_elim",
        "champion_team_id": None,
        "champion_name": None,
        "seeds": [by_seed[i] for i in range(1, 7)],
        "series": series,
        "current_round": ROUND_QUARTER,
        "eliminated": [],
    }


def find_series(bracket: Dict[str, Any], series_id: str) -> Optional[Dict[str, Any]]:
    for s in bracket.get("series") or []:
        if s.get("id") == series_id:
            return s
    return None


def series_involves_team(series: Dict[str, Any], team_id: str) -> bool:
    tid = str(team_id)
    home = (series.get("home") or {}).get("team_id")
    away = (series.get("away") or {}).get("team_id")
    return tid in (str(home) if home else None, str(away) if away else None)


def series_ready(series: Dict[str, Any]) -> bool:
    if series.get("status") == "complete":
        return False
    home = (series.get("home") or {}).get("team_id")
    away = (series.get("away") or {}).get("team_id")
    return bool(home and away)


def apply_series_result(
    bracket: Dict[str, Any],
    series_id: str,
    winner_team_id: str,
) -> Dict[str, Any]:
    """
    Marca série como completa, propaga vencedor e elimina perdedor.
    Retorna o bracket mutado (mesmo objeto).
    """
    series = find_series(bracket, series_id)
    if not series:
        raise ValueError(f"Série {series_id} não encontrada")
    if series.get("status") == "complete":
        return bracket

    winner_id = str(winner_team_id)
    home = series.get("home") or {}
    away = series.get("away") or {}
    home_id = str(home.get("team_id") or "")
    away_id = str(away.get("team_id") or "")
    if winner_id not in (home_id, away_id):
        raise ValueError(
            f"Vencedor {winner_id} não participa de {series_id} ({home_id} vs {away_id})"
        )

    loser_id = away_id if winner_id == home_id else home_id
    loser_name = (
        away.get("team_name") if winner_id == home_id else home.get("team_name")
    )
    winner_side = home if winner_id == home_id else away

    series["winner_team_id"] = winner_id
    series["status"] = "complete"

    eliminated = bracket.setdefault("eliminated", [])
    eliminated.append(
        {
            "team_id": loser_id,
            "team_name": loser_name,
            "eliminated_in": series.get("round"),
            "series_id": series_id,
        }
    )

    feeds = series.get("feeds_into")
    slot = series.get("feeds_slot")
    if feeds and slot in ("home", "away"):
        next_s = find_series(bracket, feeds)
        if next_s:
            next_s[slot] = {
                "team_id": winner_id,
                "team_name": winner_side.get("team_name"),
                "team_abbr": winner_side.get("team_abbr"),
                "seed": winner_side.get("seed"),
            }
            if series_ready(next_s):
                next_s["status"] = "ready"

    # Atualiza rodada corrente
    if all(
        s.get("status") == "complete"
        for s in bracket["series"]
        if s.get("round") == ROUND_QUARTER
    ):
        bracket["current_round"] = ROUND_SEMI
    if all(
        s.get("status") == "complete"
        for s in bracket["series"]
        if s.get("round") == ROUND_SEMI
    ):
        bracket["current_round"] = ROUND_FINAL

    if series.get("round") == ROUND_FINAL:
        bracket["status"] = "complete"
        bracket["champion_team_id"] = winner_id
        bracket["champion_name"] = winner_side.get("team_name")
        bracket["current_round"] = ROUND_FINAL

    return bracket


def series_for_round(bracket: Dict[str, Any], round_name: str) -> List[Dict[str, Any]]:
    return [
        s
        for s in bracket.get("series") or []
        if s.get("round") == round_name and series_ready(s) and s.get("status") != "complete"
    ]


def series_to_match_payload(series: Dict[str, Any]) -> Dict[str, Any]:
    """Payload compatível com scheduled_matches do calendar."""
    home = series.get("home") or {}
    away = series.get("away") or {}
    return {
        "blue_team_id": str(home.get("team_id")),
        "blue_team_name": home.get("team_name"),
        "blue_team_abbr": home.get("team_abbr"),
        "red_team_id": str(away.get("team_id")),
        "red_team_name": away.get("team_name"),
        "red_team_abbr": away.get("team_abbr"),
        "is_playoff": True,
        "series_id": series.get("id"),
        "playoff_round": series.get("round"),
        "series_label": series.get("label"),
        "best_of": series.get("best_of"),
        "home_seed": home.get("seed"),
        "away_seed": away.get("seed"),
    }


class PlayoffService:
    """Orquestra seeds, bracket Redis e resolução de séries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_bracket(self, league_id: str) -> Optional[Dict[str, Any]]:
        return await redis_client.get_playoff_state(str(league_id))

    async def save_bracket(self, league_id: str, bracket: Dict[str, Any]) -> None:
        await redis_client.set_playoff_state(str(league_id), bracket)

    async def ensure_bracket(self, league: League) -> Dict[str, Any]:
        """Retorna bracket existente ou cria a partir dos standings."""
        existing = await self.get_bracket(str(league.id))
        if existing and existing.get("series"):
            return existing
        return await self.initialize_from_standings(league)

    async def initialize_from_standings(self, league: League) -> Dict[str, Any]:
        """
        Top N (playoff_teams, default 6) por points/wins.
        Marca LeagueTeam.is_in_playoffs + playoff_seed.
        """
        n = int(league.playoff_teams or 6)
        n = max(2, min(n, 6))  # implementação fixa top-6 bracket

        result = await self.db.execute(
            select(LeagueTeam).where(LeagueTeam.league_id == league.id)
        )
        rows = list(result.scalars().all())
        rows.sort(key=lambda lt: (lt.points, lt.wins, -lt.losses), reverse=True)

        # Reset flags
        for lt in rows:
            lt.is_in_playoffs = False
            lt.playoff_seed = None
            lt.final_placement = None
            lt.prize_earned = Decimal("0")

        top = rows[:6]
        if len(top) < 6:
            raise ValueError(
                f"Liga precisa de pelo menos 6 times para playoffs (tem {len(rows)})"
            )

        seeds: List[Dict[str, Any]] = []
        for idx, lt in enumerate(top, start=1):
            team = await self.db.get(Team, lt.team_id)
            if not team:
                continue
            lt.qualify_for_playoffs(idx)
            seeds.append(
                {
                    "seed": idx,
                    "team_id": str(team.id),
                    "team_name": team.name,
                    "team_abbr": team.abbreviation,
                    "regular_wins": lt.wins,
                    "regular_losses": lt.losses,
                    "regular_points": lt.points,
                }
            )

        # Times fora do top 6: colocação final 7, 8, ...
        for place_offset, lt in enumerate(rows[6:], start=7):
            lt.final_placement = place_offset
            lt.is_in_playoffs = False

        bracket = build_top6_bracket(seeds)
        await self.save_bracket(str(league.id), bracket)
        await self.db.flush()
        logger.info(
            f"[PlayoffService] Bracket top-6 criado para {league.name}: "
            + ", ".join(f"#{s['seed']} {s['team_abbr']}" for s in seeds)
        )
        return bracket

    async def dispatch_match_day(
        self,
        league: League,
        day_info: dict,
        managed_team_id: Optional[str] = None,
        auto_simulate_fn=None,
    ) -> list[dict]:
        """
        Despacha séries da rodada atual (por week da SM).

        auto_simulate_fn: coroutine (blue_id, red_id, week, is_playoff) -> result dict
        """
        bracket = await self.ensure_bracket(league)
        if bracket.get("status") == "complete":
            day_info["scheduled_matches"] = []
            day_info["auto_simulated_matches"] = []
            day_info["playoff_bracket"] = bracket
            day_info["playoff_complete"] = True
            return []

        week = int(day_info.get("week") or 0)
        round_name = week_to_playoff_round(week)
        day_info["playoff_round"] = round_name

        pending = series_for_round(bracket, round_name)
        # Se a rodada da semana já acabou, tenta a próxima pronta (catch-up)
        if not pending:
            for r in (ROUND_QUARTER, ROUND_SEMI, ROUND_FINAL):
                pending = series_for_round(bracket, r)
                if pending:
                    round_name = r
                    day_info["playoff_round"] = r
                    break

        all_matches = [series_to_match_payload(s) for s in pending]
        interactive: list[dict] = []
        auto_results: list[dict] = []

        for match in all_matches:
            involves = (
                managed_team_id
                and managed_team_id
                in (match["blue_team_id"], match["red_team_id"])
            )
            if involves:
                interactive.append(match)
                continue

            if auto_simulate_fn is None:
                interactive.append({**match, "auto_sim_failed": True})
                continue

            try:
                result = await auto_simulate_fn(
                    match["blue_team_id"],
                    match["red_team_id"],
                    day_info.get("week", 0),
                    True,
                )
                winner_id = str(result.get("winner_team_id"))
                apply_series_result(bracket, match["series_id"], winner_id)
                auto_results.append({**match, **result, "series_resolved": True})
            except Exception as exc:
                logger.error(
                    f"[PlayoffService] Falha auto-sim {match.get('series_id')}: {exc}",
                    exc_info=True,
                )
                interactive.append({**match, "auto_sim_failed": True})

        # Finalizou alguma série automática → persistir + talvez crowning
        if auto_results:
            if bracket.get("status") == "complete":
                await self._apply_final_placements(league, bracket)
            await self.save_bracket(str(league.id), bracket)

        day_info["scheduled_matches"] = interactive
        day_info["auto_simulated_matches"] = auto_results
        day_info["all_matches_today"] = all_matches
        day_info["playoff_bracket"] = bracket
        day_info["is_playoff_day"] = True
        return interactive

    async def resolve_match_result(
        self,
        league_id: str,
        blue_team_id: str,
        red_team_id: str,
        winner_team_id: str,
        series_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Chamado após partida interativa de playoff."""
        bracket = await self.get_bracket(str(league_id))
        if not bracket or bracket.get("status") == "complete":
            return bracket

        target = None
        if series_id:
            target = find_series(bracket, series_id)
        if not target:
            # Inferir por pares e status ready
            for s in bracket.get("series") or []:
                if s.get("status") == "complete":
                    continue
                if not series_ready(s):
                    continue
                home = str((s.get("home") or {}).get("team_id") or "")
                away = str((s.get("away") or {}).get("team_id") or "")
                pair = {home, away}
                if {str(blue_team_id), str(red_team_id)} == pair:
                    target = s
                    break

        if not target:
            logger.warning(
                "[PlayoffService] Nenhuma série pendente para "
                f"{blue_team_id} vs {red_team_id}"
            )
            return bracket

        apply_series_result(bracket, target["id"], str(winner_team_id))

        league = await self.db.get(League, uuid.UUID(str(league_id)))
        if league and bracket.get("status") == "complete":
            await self._apply_final_placements(league, bracket)

        await self.save_bracket(str(league_id), bracket)
        await self.db.flush()
        return bracket

    async def _apply_final_placements(
        self, league: League, bracket: Dict[str, Any]
    ) -> None:
        """Define final_placement e prize_earned para todos os times."""
        champion_id = bracket.get("champion_team_id")
        if not champion_id:
            return

        # Runner-up = perdedor da final
        final = find_series(bracket, "final")
        runner_id = None
        if final:
            h = str((final.get("home") or {}).get("team_id") or "")
            a = str((final.get("away") or {}).get("team_id") or "")
            runner_id = a if champion_id == h else h

        # Semi losers → 3º/4º (sem 3rd place match: ambos 3–4)
        semi_losers: List[str] = []
        for sid in ("sf1", "sf2"):
            s = find_series(bracket, sid)
            if not s or s.get("status") != "complete":
                continue
            h = str((s.get("home") or {}).get("team_id") or "")
            a = str((s.get("away") or {}).get("team_id") or "")
            w = str(s.get("winner_team_id") or "")
            loser = a if w == h else h
            if loser:
                semi_losers.append(loser)

        # QF losers → 5–6
        qf_losers: List[str] = []
        for sid in ("qf1", "qf2"):
            s = find_series(bracket, sid)
            if not s or s.get("status") != "complete":
                continue
            h = str((s.get("home") or {}).get("team_id") or "")
            a = str((s.get("away") or {}).get("team_id") or "")
            w = str(s.get("winner_team_id") or "")
            loser = a if w == h else h
            if loser:
                qf_losers.append(loser)

        placements: Dict[str, int] = {}
        if champion_id:
            placements[str(champion_id)] = 1
        if runner_id:
            placements[str(runner_id)] = 2
        for tid in semi_losers:
            placements[tid] = 3
        for tid in qf_losers:
            placements[tid] = 5

        prize_map = league.prize_pool or {}

        def prize_for(place: int) -> Decimal:
            keys = (
                str(place),
                f"{place}st" if place == 1 else f"{place}nd" if place == 2 else f"{place}rd" if place == 3 else f"{place}th",
                "1st" if place == 1 else "2nd" if place == 2 else "3rd" if place == 3 else None,
            )
            for k in keys:
                if k and k in prize_map:
                    return Decimal(str(prize_map[k]))
            # 3–4 compartilham 3rd; 5–6 zero
            if place == 3 and "3rd" in prize_map:
                return Decimal(str(prize_map["3rd"])) / 2
            return Decimal("0")

        result = await self.db.execute(
            select(LeagueTeam).where(LeagueTeam.league_id == league.id)
        )
        for lt in result.scalars().all():
            tid = str(lt.team_id)
            if tid in placements:
                lt.final_placement = placements[tid]
                earned = prize_for(placements[tid])
                if placements[tid] == 3:
                    earned = prize_for(3)
                lt.prize_earned = earned
                # Credita budget do time
                if earned > 0:
                    team = await self.db.get(Team, lt.team_id)
                    if team:
                        team.budget = Decimal(str(team.budget or 0)) + earned

        logger.info(
            f"[PlayoffService] Campeão: {bracket.get('champion_name')} "
            f"({champion_id}). Placements aplicados."
        )
