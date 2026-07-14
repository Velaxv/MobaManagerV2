# -*- coding: utf-8 -*-
"""
Grade semanal do hub (SEG–DOM) sincronizada com o round-robin da liga.

Match days da regular season: Quarta (2) e Sábado (5).
Quando `managed_team_id` é informado, o evento do dia mostra o adversário real.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from src.shared.enums import CalendarDayType
from src.shared.round_robin import get_round_pairs, match_day_round_index

DAY_LABELS = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]

# Regular season: Qua/Sáb = match day; Dom = rest
_REGULAR_WEEK_TYPES = [
    CalendarDayType.TRAINING,
    CalendarDayType.TRAINING,
    CalendarDayType.MATCH_DAY,
    CalendarDayType.SCRIM,
    CalendarDayType.TRAINING,
    CalendarDayType.MATCH_DAY,
    CalendarDayType.REST,
]

# Playoffs: Qui/Dom = match day (alinhado à SM)
_PLAYOFF_WEEK_TYPES = [
    CalendarDayType.TRAINING,
    CalendarDayType.REST,
    CalendarDayType.TRAINING,
    CalendarDayType.TRAINING,
    CalendarDayType.MATCH_DAY,
    CalendarDayType.TRAINING,
    CalendarDayType.MATCH_DAY,
]

_OFFSEASON_WEEK_TYPES = [
    CalendarDayType.TRAINING,
    CalendarDayType.TRAINING,
    CalendarDayType.SCRIM,
    CalendarDayType.TRAINING,
    CalendarDayType.TRAINING,
    CalendarDayType.REST,
    CalendarDayType.REST,
]


def _week_types_for_phase(phase: str) -> List[CalendarDayType]:
    p = (phase or "").upper()
    if p == "PLAYOFFS":
        return _PLAYOFF_WEEK_TYPES
    if p in ("OFFSEASON", "PRESEASON"):
        return _OFFSEASON_WEEK_TYPES
    return _REGULAR_WEEK_TYPES


def _ordered_team_ids(teams: Sequence[Dict[str, Any]]) -> List[str]:
    """Ordem estável idêntica ao dispatch de match day (nome, id)."""
    sorted_rows = sorted(
        teams,
        key=lambda t: (str(t.get("name") or ""), str(t.get("id") or "")),
    )
    return [str(t["id"]) for t in sorted_rows]


def _team_lookup(teams: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(t["id"]): t for t in teams if t.get("id") is not None}


def _match_event_for_manager(
    home_id: str,
    away_id: str,
    lookup: Dict[str, Dict[str, Any]],
    managed_team_id: str,
) -> Dict[str, Any]:
    home = lookup.get(home_id, {})
    away = lookup.get(away_id, {})
    home_abbr = home.get("abbreviation") or home.get("name") or "?"
    away_abbr = away.get("abbreviation") or away.get("name") or "?"
    home_name = home.get("name") or home_abbr
    away_name = away.get("name") or away_abbr

    is_home = managed_team_id == home_id
    if is_home:
        opponent_id = away_id
        opponent_name = away_name
        opponent_abbr = away_abbr
        side_label = "casa"
        event_name = f"vs {away_abbr} (casa)"
    else:
        opponent_id = home_id
        opponent_name = home_name
        opponent_abbr = home_abbr
        side_label = "fora"
        event_name = f"vs {home_abbr} (fora)"

    return {
        "eventName": event_name,
        "opponentId": opponent_id,
        "opponentName": opponent_name,
        "opponentAbbr": opponent_abbr,
        "isHome": is_home,
        "sideLabel": side_label,
        "homeTeamId": home_id,
        "awayTeamId": away_id,
        "homeTeamAbbr": home_abbr,
        "awayTeamAbbr": away_abbr,
        "homeTeamName": home_name,
        "awayTeamName": away_name,
    }


def _round_summary_event(
    pairs: List[tuple],
    lookup: Dict[str, Dict[str, Any]],
    round_index: int,
) -> Dict[str, Any]:
    labels = []
    for home_id, away_id in pairs:
        h = lookup.get(str(home_id), {})
        a = lookup.get(str(away_id), {})
        ha = h.get("abbreviation") or "?"
        aa = a.get("abbreviation") or "?"
        labels.append(f"{ha}×{aa}")
    summary = " · ".join(labels) if labels else "Sem jogos"
    return {
        "eventName": f"Rodada {round_index + 1}: {summary}",
        "opponentId": None,
        "opponentName": None,
        "opponentAbbr": None,
        "isHome": None,
        "sideLabel": None,
        "homeTeamId": None,
        "awayTeamId": None,
        "homeTeamAbbr": None,
        "awayTeamAbbr": None,
        "homeTeamName": None,
        "awayTeamName": None,
    }


def build_week_calendar(
    current_day_of_week: int,
    current_week: int,
    phase: str,
    teams: Optional[Sequence[Dict[str, Any]]] = None,
    managed_team_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Monta a grade semanal com adversário real nos match days (quando possível).

    Args:
        current_day_of_week: 0=SEG … 6=DOM (dia “hoje”).
        current_week: semana da fase (mesma convenção da SM / round-robin).
        phase: REGULAR_SEASON | PLAYOFFS | OFFSEASON | PRESEASON.
        teams: lista de dicts com id, name, abbreviation (ordem livre; será estabilizada).
        managed_team_id: UUID do time do manager (opcional).

    Returns:
        Lista de 7 dias com eventName e metadados de confronto.
    """
    week_types = _week_types_for_phase(phase)
    team_rows = list(teams or [])
    lookup = _team_lookup(team_rows)
    ordered_ids = _ordered_team_ids(team_rows) if team_rows else []
    managed = str(managed_team_id) if managed_team_id else None
    phase_upper = (phase or "").upper()
    use_rr = phase_upper == "REGULAR_SEASON" and len(ordered_ids) >= 2

    days: List[Dict[str, Any]] = []
    for i, label in enumerate(DAY_LABELS):
        day_type = week_types[i]
        event: Optional[str] = None
        extra: Dict[str, Any] = {
            "opponentId": None,
            "opponentName": None,
            "opponentAbbr": None,
            "isHome": None,
            "sideLabel": None,
            "homeTeamId": None,
            "awayTeamId": None,
            "homeTeamAbbr": None,
            "awayTeamAbbr": None,
            "homeTeamName": None,
            "awayTeamName": None,
            "roundIndex": None,
            "allMatches": [],
        }

        if day_type == CalendarDayType.MATCH_DAY and use_rr:
            round_idx = match_day_round_index(int(current_week), i)
            pairs = get_round_pairs(ordered_ids, round_idx)
            extra["roundIndex"] = round_idx
            extra["allMatches"] = [
                {
                    "homeTeamId": str(h),
                    "awayTeamId": str(a),
                    "homeTeamAbbr": (lookup.get(str(h)) or {}).get("abbreviation"),
                    "awayTeamAbbr": (lookup.get(str(a)) or {}).get("abbreviation"),
                    "homeTeamName": (lookup.get(str(h)) or {}).get("name"),
                    "awayTeamName": (lookup.get(str(a)) or {}).get("name"),
                }
                for h, a in pairs
            ]

            manager_pair = None
            if managed:
                for h, a in pairs:
                    if managed in (str(h), str(a)):
                        manager_pair = (str(h), str(a))
                        break

            if manager_pair:
                extra.update(
                    _match_event_for_manager(
                        manager_pair[0], manager_pair[1], lookup, managed
                    )
                )
                event = extra["eventName"]
            else:
                summary = _round_summary_event(pairs, lookup, round_idx)
                extra.update(summary)
                event = summary["eventName"]

        elif day_type == CalendarDayType.MATCH_DAY:
            event = f"CBLOL — Rodada (Semana {current_week})"
        elif day_type == CalendarDayType.REST:
            event = "Descanso obrigatório"
        elif day_type == CalendarDayType.SCRIM:
            event = "Scrim agendado"

        days.append(
            {
                "dayIndex": i,
                "dayOfWeek": label,
                "week": current_week,
                "type": day_type.value,
                "eventName": event,
                "isToday": i == (int(current_day_of_week) % 7),
                "phase": phase,
                **extra,
            }
        )
    return days
