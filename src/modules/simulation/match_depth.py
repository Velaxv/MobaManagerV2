# -*- coding: utf-8 -*-
"""
Profundidade de partida (Sprint E híbrido):
  - Chemistry / duo synergy → bônus de duelo
  - Pressão de lane + torres no estado
  - Ratings 0–10 pós-partida
  - Win reasons legíveis
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.shared.enums import PlayerRole

# Torres: T1+T2+T3 por lane (9) — inhibs e nexus separados
DEFAULT_LANE_TOWERS = 3
DEFAULT_INHIBS = 3
DEFAULT_NEXUS = 1


def default_map_structures() -> Dict[str, Any]:
    """Estruturas vivas por lado (fonte da verdade do motor)."""
    return {
        "blue": {
            "top": DEFAULT_LANE_TOWERS,
            "mid": DEFAULT_LANE_TOWERS,
            "bot": DEFAULT_LANE_TOWERS,
            "inhibs": DEFAULT_INHIBS,
            "nexus": DEFAULT_NEXUS,
            "towers_total": DEFAULT_LANE_TOWERS * 3,
        },
        "red": {
            "top": DEFAULT_LANE_TOWERS,
            "mid": DEFAULT_LANE_TOWERS,
            "bot": DEFAULT_LANE_TOWERS,
            "inhibs": DEFAULT_INHIBS,
            "nexus": DEFAULT_NEXUS,
            "towers_total": DEFAULT_LANE_TOWERS * 3,
        },
    }


def default_lane_pressure() -> Dict[str, float]:
    """Pressão de lane: positivo = vantagem Blue (−100…+100)."""
    return {"TOP": 0.0, "JUNGLE": 0.0, "MID": 0.0, "BOT": 0.0}


def default_role_contrib() -> Dict[str, Dict[str, float]]:
    """Acumuladores por role/side para ratings."""
    roles = ["TOP", "JUNGLE", "MID", "BOT", "SUPPORT"]
    blank = {"kills": 0.0, "obj": 0.0, "farm": 0.0, "deaths": 0.0, "pressure": 0.0}
    return {
        "BLUE": {r: dict(blank) for r in roles},
        "RED": {r: dict(blank) for r in roles},
    }


def location_to_lane_key(location: str) -> str:
    loc = (location or "MID_LANE").upper()
    if "TOP" in loc:
        return "top"
    if "BOT" in loc:
        return "bot"
    return "mid"


def destroy_tower(
    structures: Dict[str, Any],
    *,
    attacker_side: str,
    location: str,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Atacante derruba a próxima torre do defensor na lane.
    Retorna (structures, label da estrutura ou None se não havia).
    """
    atk = (attacker_side or "BLUE").upper()
    defender = "red" if atk == "BLUE" else "blue"
    lane = location_to_lane_key(location)
    side = structures.get(defender) or {}
    towers = int(side.get(lane, 0) or 0)
    if towers > 0:
        side[lane] = towers - 1
        side["towers_total"] = max(0, int(side.get("towers_total", 0) or 0) - 1)
        structures[defender] = side
        tier = DEFAULT_LANE_TOWERS - towers + 1  # 1,2,3
        return structures, f"{defender.upper()} {lane.upper()} T{tier}"
    # Sem torres na lane → tenta inhib
    inhibs = int(side.get("inhibs", 0) or 0)
    if inhibs > 0:
        side["inhibs"] = inhibs - 1
        structures[defender] = side
        return structures, f"{defender.upper()} INHIB {lane.upper()}"
    return structures, None


def snowball_structures(structures: Dict[str, Any], winner_side: str) -> Dict[str, Any]:
    """Snowball: derruba mid/base do perdedor (inhib + torres mid)."""
    win = (winner_side or "BLUE").upper()
    lose = "red" if win == "BLUE" else "blue"
    side = structures.get(lose) or {}
    side["mid"] = 0
    side["inhibs"] = max(0, int(side.get("inhibs", 0) or 0) - 1)
    side["towers_total"] = int(side.get("top", 0) or 0) + int(side.get("bot", 0) or 0)
    structures[lose] = side
    return structures


def open_nexus(structures: Dict[str, Any], winner_side: str) -> Dict[str, Any]:
    lose = "red" if (winner_side or "BLUE").upper() == "BLUE" else "blue"
    side = structures.get(lose) or {}
    side["nexus"] = 0
    side["inhibs"] = 0
    side["top"] = 0
    side["mid"] = 0
    side["bot"] = 0
    side["towers_total"] = 0
    structures[lose] = side
    return structures


def chemistry_duel_bonus(
    role: PlayerRole,
    *,
    chemistry: float = 55.0,
    bot_synergy: float = 50.0,
    jg_mid_synergy: float = 50.0,
    teamwork: float = 10.0,
) -> float:
    """
    Bônus absoluto adicionado ao score de duelo (mesma escala do stochastic_roll ~0–100).
    Chemistry 50 ≈ neutro; 100 ≈ +6; 0 ≈ −4.
    Duos empurram BOT/SUP e JG/MID.
    """
    chem = float(chemistry)
    base = (chem - 50.0) / 50.0 * 5.0  # −5 … +5
    team = (float(teamwork) - 10.0) / 10.0 * 1.5  # leve
    duo = 0.0
    if role in (PlayerRole.BOT, PlayerRole.SUPPORT):
        duo = (float(bot_synergy) - 50.0) / 50.0 * 3.5
    elif role in (PlayerRole.JUNGLE, PlayerRole.MID):
        duo = (float(jg_mid_synergy) - 50.0) / 50.0 * 3.5
    elif role == PlayerRole.TOP:
        duo = (chem - 50.0) / 50.0 * 1.0  # top mais isolado
    return base + team + duo


def clamp_pressure(v: float) -> float:
    return max(-100.0, min(100.0, v))


def add_lane_pressure(
    pressure: Dict[str, float],
    role: PlayerRole,
    delta_blue: float,
) -> Dict[str, float]:
    key = "BOT" if role == PlayerRole.SUPPORT else role.value
    if key not in pressure:
        key = "MID"
    pressure[key] = clamp_pressure(float(pressure.get(key, 0.0)) + delta_blue)
    return pressure


def bump_contrib(
    contrib: Dict[str, Dict[str, float]],
    side: str,
    role: PlayerRole,
    *,
    kills: float = 0.0,
    obj: float = 0.0,
    farm: float = 0.0,
    deaths: float = 0.0,
    pressure: float = 0.0,
) -> None:
    s = (side or "BLUE").upper()
    r = role.value if isinstance(role, PlayerRole) else str(role).upper()
    if r == "SUPPORT":
        pass
    bucket = contrib.setdefault(s, {}).setdefault(
        r, {"kills": 0.0, "obj": 0.0, "farm": 0.0, "deaths": 0.0, "pressure": 0.0}
    )
    bucket["kills"] += kills
    bucket["obj"] += obj
    bucket["farm"] += farm
    bucket["deaths"] += deaths
    bucket["pressure"] += pressure


def compute_player_ratings(
    *,
    blue_starters: List[Any],
    red_starters: List[Any],
    blue_draft: List[Dict[str, str]],
    red_draft: List[Dict[str, str]],
    contrib: Dict[str, Dict[str, float]],
    winner_side: Optional[str],
    blue_team_name: str,
    red_team_name: str,
) -> List[Dict[str, Any]]:
    """Monta ratings 0–10 por jogador titular."""
    ratings: List[Dict[str, Any]] = []

    def champ_for(draft: List[Dict[str, str]], role: str) -> str:
        for p in draft or []:
            if str(p.get("role", "")).upper() == role:
                return str(p.get("champion") or "—")
        return "—"

    def rate_side(side: str, starters: List[Any], draft: List[Dict[str, str]], team_name: str) -> None:
        side_c = contrib.get(side) or {}
        won = (winner_side or "").upper() == side
        for p in starters or []:
            role = getattr(p, "role", None)
            role_s = role.value if isinstance(role, PlayerRole) else str(role or "MID").upper()
            c = side_c.get(role_s) or {}
            kills = float(c.get("kills") or 0)
            obj = float(c.get("obj") or 0)
            farm = float(c.get("farm") or 0)
            deaths = float(c.get("deaths") or 0)
            press = float(c.get("pressure") or 0)
            ca = float(getattr(p, "current_ability", 100) or 100)
            burnout = float(getattr(p, "burnout_meter", 0) or 0)

            # Base 5.5 + contribuições + CA leve
            score = 5.5
            score += min(2.5, kills * 0.55)
            score += min(1.8, obj * 0.4)
            score += min(1.0, farm * 0.08)
            score += min(1.2, max(-1.2, press * 0.03))
            score -= min(1.5, deaths * 0.45)
            score += (ca - 120) / 200.0  # ~±0.4
            score -= burnout / 100.0 * 0.6
            if won:
                score += 0.35
            else:
                score -= 0.25
            # BMA em playoff-like pressure (sempre leve)
            bma = float(getattr(p, "big_match_aptitude", 10) or 10)
            score += (bma - 10) / 20.0 * 0.4

            score = max(0.0, min(10.0, score))
            # arredonda 0.5
            score_r = round(score * 2) / 2.0

            note = _rating_note(score_r, kills, obj, deaths, won)
            ratings.append(
                {
                    "player_id": str(getattr(p, "id", "")),
                    "name": getattr(p, "name", "—"),
                    "role": role_s,
                    "side": side,
                    "team_name": team_name,
                    "champion": champ_for(draft, role_s),
                    "rating": score_r,
                    "note": note,
                    "stats": {
                        "kills_share": round(kills, 1),
                        "objectives": round(obj, 1),
                        "farm": round(farm, 1),
                        "deaths_share": round(deaths, 1),
                    },
                }
            )

    rate_side("BLUE", blue_starters, blue_draft, blue_team_name)
    rate_side("RED", red_starters, red_draft, red_team_name)
    # MVP = maior rating
    if ratings:
        mvp = max(ratings, key=lambda r: r["rating"])
        for r in ratings:
            r["mvp"] = r["player_id"] == mvp["player_id"] and r["rating"] == mvp["rating"]
    return ratings


def _rating_note(score: float, kills: float, obj: float, deaths: float, won: bool) -> str:
    if score >= 9.0:
        return "Partida monstro"
    if score >= 8.0:
        return "Destaque da equipe" if kills >= 2 or obj >= 2 else "Muito sólido"
    if score >= 7.0:
        return "Boa performance"
    if score >= 6.0:
        return "Dentro do esperado"
    if score >= 5.0:
        return "Irregular" if deaths >= 1 else "Apagado"
    if score >= 4.0:
        return "Abaixo" if not won else "Sobreviveu ao caos"
    return "Noite difícil"


def win_reason_from_state(
    *,
    reason_code: str,
    winner_side: str,
    winner_name: str,
    gold_diff: int,
    blue_dragons: int,
    red_dragons: int,
    blue_barons: int,
    red_barons: int,
    blue_towers: int,
    red_towers: int,
    minute: int,
) -> Dict[str, Any]:
    """Monta win_reason legível para o FE."""
    code = (reason_code or "GOLD_LEAD").upper()
    win = (winner_side or "BLUE").upper()
    d_drag = blue_dragons - red_dragons if win == "BLUE" else red_dragons - blue_dragons
    d_bar = blue_barons - red_barons if win == "BLUE" else red_barons - blue_barons
    d_tow = (
        (9 - red_towers) - (9 - blue_towers)
        if win == "BLUE"
        else (9 - blue_towers) - (9 - red_towers)
    )
    # towers destroyed by winner ≈ 9 - enemy remaining
    labels = {
        "SNOWBALL": f"{winner_name} fechou com snowball de ouro ({gold_diff:+d}g) e base aberta",
        "NEXUS": f"{winner_name} destruiu o nexus após vantagem de mapa",
        "BARON_SIEGE": f"{winner_name} converteu Baron em pressão decisiva",
        "DRAGON_SOUL": f"{winner_name} dominou objetivos neutros (drakes {d_drag:+d})",
        "TOWER_DIFF": f"{winner_name} venceu no cerco e torres (Δ torres ~{abs(d_tow)})",
        "GOLD_LEAD": f"{winner_name} venceu por vantagem de recursos ({gold_diff:+d}g aos {minute}')",
        "TEAMFIGHT": f"{winner_name} decidiu nas teamfights do late game",
        "TIME_LIMIT": f"{winner_name} levou nos critérios de ouro ao fim do relógio",
    }
    summary = labels.get(code, labels["GOLD_LEAD"])
    factors = []
    if abs(gold_diff) >= 3000:
        factors.append(f"Ouro {gold_diff:+d}")
    if d_drag != 0:
        factors.append(f"Drakes {d_drag:+d}")
    if d_bar != 0:
        factors.append(f"Barons {d_bar:+d}")
    if d_tow != 0:
        factors.append(f"Torres {d_tow:+d}")
    return {
        "code": code,
        "summary": summary,
        "factors": factors,
        "winner_side": win,
        "minute": minute,
    }


def pick_win_reason_code(
    *,
    forced: Optional[str] = None,
    gold_diff: int,
    blue_barons: int,
    red_barons: int,
    blue_dragons: int,
    red_dragons: int,
    structures: Optional[Dict[str, Any]] = None,
    minute: int = 40,
) -> str:
    if forced:
        return forced
    win_blue = gold_diff >= 0
    if structures:
        lose = "red" if win_blue else "blue"
        side = structures.get(lose) or {}
        if int(side.get("nexus", 1) or 0) == 0:
            return "NEXUS"
        if int(side.get("inhibs", 3) or 0) <= 1 and abs(gold_diff) >= 8000:
            return "SNOWBALL"
    b_bar = blue_barons if win_blue else red_barons
    if b_bar >= 1 and abs(gold_diff) >= 4000:
        return "BARON_SIEGE"
    b_dr = blue_dragons if win_blue else red_dragons
    o_dr = red_dragons if win_blue else blue_dragons
    if b_dr >= o_dr + 2:
        return "DRAGON_SOUL"
    if structures:
        win_s = "blue" if win_blue else "red"
        lose_s = "red" if win_blue else "blue"
        wt = int((structures.get(win_s) or {}).get("towers_total", 9) or 9)
        lt = int((structures.get(lose_s) or {}).get("towers_total", 9) or 9)
        if lt <= wt - 3:
            return "TOWER_DIFF"
    if minute >= 40:
        return "TIME_LIMIT"
    return "GOLD_LEAD"
