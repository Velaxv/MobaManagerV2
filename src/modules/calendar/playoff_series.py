# -*- coding: utf-8 -*-
"""
Séries multi-map de playoffs (BO3/BO5) com fearless light e momentum.

Regras:
  - wins_needed = best_of // 2 + 1
  - Map 1: home (seed maior) = Blue
  - Maps seguintes: vencedor do map anterior fica Blue (momentum de side)
  - Fearless: campeões pickados em qualquer map da série ficam bloqueados
  - Série completa só quando um lado atinge wins_needed
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def wins_needed(best_of: int) -> int:
    bo = max(1, int(best_of or 1))
    return bo // 2 + 1


def ensure_series_multi_map(series: Dict[str, Any]) -> Dict[str, Any]:
    """Garante campos multi-map em séries legadas (BO1 implícito antigo)."""
    if "score" not in series or not isinstance(series.get("score"), dict):
        series["score"] = {"home": 0, "away": 0}
    series.setdefault("maps", [])
    series.setdefault("fearless_used", [])
    series.setdefault("momentum_team_id", None)
    series.setdefault("current_map", 1)
    # Se série já complete sem maps (legado BO1), ok
    if series.get("status") == "complete" and series.get("winner_team_id"):
        sc = series["score"]
        if sc.get("home", 0) == 0 and sc.get("away", 0) == 0:
            # reconstrói placar mínimo
            w = str(series["winner_team_id"])
            home = str((series.get("home") or {}).get("team_id") or "")
            if w == home:
                series["score"] = {"home": 1, "away": 0}
            else:
                series["score"] = {"home": 0, "away": 1}
    return series


def series_score_tuple(series: Dict[str, Any]) -> Tuple[int, int]:
    ensure_series_multi_map(series)
    sc = series["score"]
    return int(sc.get("home") or 0), int(sc.get("away") or 0)


def series_is_complete_by_score(series: Dict[str, Any]) -> bool:
    ensure_series_multi_map(series)
    need = wins_needed(int(series.get("best_of") or 1))
    h, a = series_score_tuple(series)
    return h >= need or a >= need


def side_for_next_map(series: Dict[str, Any]) -> Tuple[str, str]:
    """
    Retorna (blue_team_id, red_team_id) para o próximo map.
    Map 1: home = blue. Depois: momentum (último vencedor) = blue.
    """
    ensure_series_multi_map(series)
    home_id = str((series.get("home") or {}).get("team_id") or "")
    away_id = str((series.get("away") or {}).get("team_id") or "")
    maps = series.get("maps") or []
    if not maps:
        return home_id, away_id
    mom = series.get("momentum_team_id")
    if mom and str(mom) in (home_id, away_id):
        blue = str(mom)
        red = away_id if blue == home_id else home_id
        return blue, red
    # fallback: home blue
    return home_id, away_id


def extract_picks(draft: Optional[List[Dict[str, str]]]) -> List[str]:
    out = []
    for p in draft or []:
        ch = p.get("champion") or p.get("name")
        if ch:
            out.append(str(ch))
    return out


def record_map_result(
    series: Dict[str, Any],
    *,
    winner_team_id: str,
    blue_team_id: str,
    red_team_id: str,
    blue_draft: Optional[List[Dict[str, str]]] = None,
    red_draft: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Registra um map na série. Não propaga bracket (só score/fearless).
    Retorna dict com series_complete, score, map_index, fearless_used.
    """
    ensure_series_multi_map(series)
    if series.get("status") == "complete":
        return {
            "series_complete": True,
            "already_complete": True,
            "score": series["score"],
            "winner_team_id": series.get("winner_team_id"),
        }

    home_id = str((series.get("home") or {}).get("team_id") or "")
    away_id = str((series.get("away") or {}).get("team_id") or "")
    winner = str(winner_team_id)
    if winner not in (home_id, away_id):
        raise ValueError(f"Vencedor {winner} não está na série")

    blue_picks = extract_picks(blue_draft)
    red_picks = extract_picks(red_draft)
    used = list(series.get("fearless_used") or [])
    for ch in blue_picks + red_picks:
        if ch and ch not in used and ch.lower() not in {u.lower() for u in used}:
            used.append(ch)
    series["fearless_used"] = used

    map_index = len(series.get("maps") or []) + 1
    series.setdefault("maps", []).append(
        {
            "map_index": map_index,
            "blue_team_id": str(blue_team_id),
            "red_team_id": str(red_team_id),
            "winner_team_id": winner,
            "blue_picks": blue_picks,
            "red_picks": red_picks,
        }
    )
    series["momentum_team_id"] = winner
    series["current_map"] = map_index + 1

    if winner == home_id:
        series["score"]["home"] = int(series["score"].get("home") or 0) + 1
    else:
        series["score"]["away"] = int(series["score"].get("away") or 0) + 1

    complete = series_is_complete_by_score(series)
    if complete:
        # Não marca complete ainda — apply_series_result propaga o bracket
        series["status"] = "awaiting_close"
        series["winner_team_id"] = winner
    else:
        series["status"] = "in_progress"
        series["winner_team_id"] = None

    h, a = series_score_tuple(series)
    return {
        "series_complete": complete,
        "already_complete": False,
        "score": {"home": h, "away": a},
        "score_display": f"{h}-{a}",
        "map_index": map_index,
        "winner_team_id": winner if complete else None,
        "map_winner_team_id": winner,
        "fearless_used": used,
        "next_blue_team_id": None if complete else side_for_next_map(series)[0],
        "next_red_team_id": None if complete else side_for_next_map(series)[1],
        "wins_needed": wins_needed(int(series.get("best_of") or 1)),
        "best_of": int(series.get("best_of") or 1),
    }


def series_public_view(series: Dict[str, Any]) -> Dict[str, Any]:
    ensure_series_multi_map(series)
    h, a = series_score_tuple(series)
    blue, red = side_for_next_map(series)
    return {
        "score": {"home": h, "away": a},
        "score_display": f"{h}-{a}",
        "maps_played": len(series.get("maps") or []),
        "current_map": series.get("current_map") or (len(series.get("maps") or []) + 1),
        "fearless_used": list(series.get("fearless_used") or []),
        "momentum_team_id": series.get("momentum_team_id"),
        "wins_needed": wins_needed(int(series.get("best_of") or 1)),
        "best_of": int(series.get("best_of") or 1),
        "next_blue_team_id": blue if series.get("status") != "complete" else None,
        "next_red_team_id": red if series.get("status") != "complete" else None,
    }
