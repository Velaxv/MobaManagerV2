# -*- coding: utf-8 -*-
"""
Counter-pick score por lane (Sprint H / DR-2).

Usa COUNTER_MAP do DraftAI:
  - score por lado e role (−1…+1)
  - mult early-game para o duelo live
  - dicas legíveis para scout / pós-draft
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.modules.draft.draft_ai import COUNTER_MAP
from src.shared.enums import PlayerRole

ROLES = [
    PlayerRole.TOP,
    PlayerRole.JUNGLE,
    PlayerRole.MID,
    PlayerRole.BOT,
    PlayerRole.SUPPORT,
]

# Bônus de duelo early quando countera (e punição quando é counterado)
COUNTER_EDGE_MULT = 0.12  # +12% no valor de duelo
COUNTERED_PENALTY_MULT = 0.10


def _norm(name: str) -> str:
    return (name or "").strip().lower()


def _counters(champ: str) -> List[str]:
    """Lista de campeões que `champ` countera."""
    if not champ:
        return []
    if champ in COUNTER_MAP:
        return list(COUNTER_MAP[champ])
    # case-insensitive lookup
    for k, v in COUNTER_MAP.items():
        if _norm(k) == _norm(champ):
            return list(v)
    return []


def lane_counter_edge(my_champ: str, opp_champ: str) -> float:
    """
    +1 se my countera opp, −1 se opp countera my, 0 se neutro/ambos.
    Se ambos se counteram, retorna 0 (cancelam).
    """
    my_beats = any(_norm(c) == _norm(opp_champ) for c in _counters(my_champ))
    opp_beats = any(_norm(c) == _norm(my_champ) for c in _counters(opp_champ))
    if my_beats and not opp_beats:
        return 1.0
    if opp_beats and not my_beats:
        return -1.0
    return 0.0


def duel_multiplier_from_edge(edge: float) -> float:
    """Converte edge de lane em multiplicador de duelo (1.0 = neutro)."""
    if edge > 0:
        return 1.0 + COUNTER_EDGE_MULT * edge
    if edge < 0:
        return 1.0 - COUNTERED_PENALTY_MULT * abs(edge)
    return 1.0


def _pick_for_role(draft: List[dict], role: PlayerRole) -> Optional[str]:
    role_v = role.value
    for p in draft or []:
        rh = p.get("role_hint") or p.get("role") or ""
        if str(rh).upper() == role_v:
            return p.get("champion") or p.get("name")
    return None


def analyze_lane_counters(
    blue_draft: List[dict],
    red_draft: List[dict],
) -> Dict[str, Any]:
    """
    Relatório completo de counters lane-a-lane.
    """
    lanes: List[Dict[str, Any]] = []
    blue_score = 0.0
    red_score = 0.0
    blue_mults: Dict[str, float] = {}
    red_mults: Dict[str, float] = {}

    for role in ROLES:
        b = _pick_for_role(blue_draft, role)
        r = _pick_for_role(red_draft, role)
        edge_b = lane_counter_edge(b or "", r or "") if b and r else 0.0
        edge_r = -edge_b
        blue_score += edge_b
        red_score += edge_r
        bm = duel_multiplier_from_edge(edge_b)
        rm = duel_multiplier_from_edge(edge_r)
        blue_mults[role.value] = round(bm, 3)
        red_mults[role.value] = round(rm, 3)

        tip = "neutro"
        if edge_b > 0:
            tip = f"{b} countera {r}"
        elif edge_b < 0:
            tip = f"{r} countera {b}"

        lanes.append(
            {
                "role": role.value,
                "blue_champion": b,
                "red_champion": r,
                "blue_edge": edge_b,
                "red_edge": edge_r,
                "blue_duel_mult": bm,
                "red_duel_mult": rm,
                "tip": tip,
            }
        )

    # Normaliza score agregado −5…+5 → −1…+1
    blue_norm = max(-1.0, min(1.0, blue_score / 5.0))
    red_norm = max(-1.0, min(1.0, red_score / 5.0))

    winner = "EVEN"
    if blue_score > red_score + 0.5:
        winner = "BLUE"
    elif red_score > blue_score + 0.5:
        winner = "RED"

    tips = [ln["tip"] for ln in lanes if ln["tip"] != "neutro"]

    return {
        "lanes": lanes,
        "blue_counter_score": round(blue_score, 2),
        "red_counter_score": round(red_score, 2),
        "blue_counter_norm": round(blue_norm, 3),
        "red_counter_norm": round(red_norm, 3),
        "blue_duel_mults": blue_mults,
        "red_duel_mults": red_mults,
        "draft_edge_side": winner,
        "tips": tips,
        "summary": (
            f"Counters: Blue {blue_score:+.0f} · Red {red_score:+.0f}"
            + (f" · {'; '.join(tips[:3])}" if tips else " · matchups neutros")
        ),
    }


def early_duel_mults(
    blue_draft: List[dict],
    red_draft: List[dict],
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, Any]]:
    """Atalho para o match engine."""
    report = analyze_lane_counters(blue_draft, red_draft)
    return report["blue_duel_mults"], report["red_duel_mults"], report
