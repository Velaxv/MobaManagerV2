# -*- coding: utf-8 -*-
"""
Táticas pré-partida: estilo de jogo, coach comms e lineup.

Estilos:
  EARLY    — prioriza rotas e early (boost early, debuff late)
  MID      — objetivos e mid game
  LATE     — scaling / late teamfights
  BALANCED — sem viés
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
import uuid

GAME_STYLES = ("BALANCED", "EARLY", "MID", "LATE")

# Multiplicadores de score/ouro por fase para o lado que usa o estilo
# (valores relativos; 1.0 = neutro)
STYLE_PHASE_MULT: Dict[str, Dict[str, float]] = {
    "BALANCED": {"EARLY_GAME": 1.0, "MID_GAME": 1.0, "LATE_GAME": 1.0},
    "EARLY": {"EARLY_GAME": 1.10, "MID_GAME": 1.00, "LATE_GAME": 0.92},
    "MID": {"EARLY_GAME": 0.97, "MID_GAME": 1.10, "LATE_GAME": 0.98},
    "LATE": {"EARLY_GAME": 0.93, "MID_GAME": 1.02, "LATE_GAME": 1.12},
}


def normalize_style(style: Optional[str]) -> str:
    s = (style or "BALANCED").upper().strip()
    return s if s in GAME_STYLES else "BALANCED"


def clamp_coach_comms(n: Optional[int]) -> int:
    try:
        return max(0, min(6, int(n if n is not None else 2)))
    except (TypeError, ValueError):
        return 2


def style_phase_multiplier(style: str, phase_name: str) -> float:
    style = normalize_style(style)
    phase = (phase_name or "EARLY_GAME").upper()
    return STYLE_PHASE_MULT.get(style, STYLE_PHASE_MULT["BALANCED"]).get(phase, 1.0)


def apply_style_to_phase_result(phase_result, blue_style: str, red_style: str):
    """
    Ajusta scores/ouro da fase conforme estilo de cada lado.
    Mutates phase_result in place e recalcula gold_difference.
    """
    b_mult = style_phase_multiplier(blue_style, phase_result.phase_name)
    r_mult = style_phase_multiplier(red_style, phase_result.phase_name)

    if b_mult != 1.0:
        phase_result.blue_state.phase_score *= b_mult
        phase_result.blue_state.gold_earned *= b_mult
        if b_mult > 1.0:
            phase_result.blue_state.active_buffs.append(f"STYLE_{normalize_style(blue_style)}")
        else:
            phase_result.blue_state.active_debuffs.append(f"STYLE_{normalize_style(blue_style)}")

    if r_mult != 1.0:
        phase_result.red_state.phase_score *= r_mult
        phase_result.red_state.gold_earned *= r_mult
        if r_mult > 1.0:
            phase_result.red_state.active_buffs.append(f"STYLE_{normalize_style(red_style)}")
        else:
            phase_result.red_state.active_debuffs.append(f"STYLE_{normalize_style(red_style)}")

    phase_result.gold_difference = (
        phase_result.blue_state.gold_earned - phase_result.red_state.gold_earned
    )
    phase_result.score_difference = (
        phase_result.blue_state.phase_score - phase_result.red_state.phase_score
    )
    return phase_result


@dataclass
class PreMatchTactics:
    game_style: str = "BALANCED"
    coach_comms: int = 2
    starter_ids: Optional[List[str]] = None  # 5 player UUIDs (opcional)

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PreMatchTactics":
        data = data or {}
        starters = data.get("starter_ids") or data.get("lineup") or None
        if starters is not None:
            starters = [str(s) for s in starters][:5]
        return cls(
            game_style=normalize_style(data.get("game_style") or data.get("style")),
            coach_comms=clamp_coach_comms(data.get("coach_comms")),
            starter_ids=starters,
        )


class TeamLineupProxy:
    """Proxy de Team que sobrescreve get_starters com lineup escolhido."""

    def __init__(self, team: Any, ordered_starters: Sequence[Any]) -> None:
        self._team = team
        self._starters = list(ordered_starters)

    def get_starters(self) -> list:
        return self._starters

    def __getattr__(self, name: str) -> Any:
        return getattr(self._team, name)


def build_lineup_proxy(team: Any, starter_ids: Optional[List[str]]) -> Any:
    """
    Se starter_ids tiver 5 ids válidos (1 por role preferencialmente),
    retorna proxy com esses titulares; senão o time original.
    """
    if not starter_ids or len(starter_ids) < 5:
        return team

    by_id = {str(p.id): p for p in (team.players or [])}
    ordered = []
    for sid in starter_ids[:5]:
        p = by_id.get(str(sid))
        if p:
            ordered.append(p)
    if len(ordered) < 5:
        # completa com get_starters original
        for p in team.get_starters():
            if p not in ordered:
                ordered.append(p)
            if len(ordered) >= 5:
                break
    if len(ordered) < 5:
        return team
    return TeamLineupProxy(team, ordered[:5])
