"""
Funções puras de recuperação de fadiga (testáveis sem DB).

Três eixos: burnout_meter, visual_fatigue, mental_fatigue.
Carga sobe com match/scrim/treino HARD; desce com REST, micro-recovery e banco.
Qualidade da recuperação: recovery_mult (0.0–1.4) por forma, moral, board, staff, intensidade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.shared.enums import CalendarDayType
from src.shared.math_utils import clamp


@dataclass(frozen=True)
class FatigueDeltas:
    """Deltas a aplicar (negativo = recuperação)."""

    burnout: float
    visual: float
    mental: float
    games_played_delta: int = 0
    event_type: Optional[str] = None  # FATIGUE_RECOVERY | POOR_RECOVERY | MATCH_DAY_FATIGUE | BENCH_RECOVERY


@dataclass(frozen=True)
class RecoveryContext:
    """Contexto de qualidade de recuperação para um jogador num dia."""

    last_rating: Optional[float] = None
    form_avg: Optional[float] = None
    team_morale: float = 62.0
    discontent: float = 0.0
    board_confidence: float = 62.0
    staff_recovery_bonus: float = 0.0  # tipicamente 0–0.15
    intensity: str = "NORMAL"  # LIGHT | NORMAL | HARD


# Bases tunáveis (espelham Settings com defaults seguros)
DEFAULT_REST = {"burnout": -12.0, "visual": -10.0, "mental": -8.0}
DEFAULT_MATCH_STARTER = {"burnout": 5.0, "visual": 12.0, "mental": 8.0}
DEFAULT_MATCH_BENCH = {"burnout": -1.5, "visual": -2.0, "mental": -1.0}
DEFAULT_SCRIM = {"burnout": 2.5, "visual": 5.0, "mental": 2.5}
DEFAULT_MEDIA = {"burnout": -0.5, "visual": -1.0, "mental": 0.5}
DEFAULT_TRAINING_LIGHT = {"burnout": -1.5, "visual": -2.5, "mental": -1.0}
DEFAULT_TRAINING_NORMAL = {"burnout": -0.5, "visual": -1.0, "mental": 0.0}
DEFAULT_TRAINING_HARD = {"burnout": 2.5, "visual": 4.0, "mental": 2.0}
DEFAULT_UNKNOWN = {"burnout": 2.0, "visual": 1.0, "mental": 1.0}


def normalize_intensity(intensity: Optional[str]) -> str:
    i = (intensity or "NORMAL").upper().strip()
    return i if i in ("LIGHT", "NORMAL", "HARD") else "NORMAL"


def recovery_multiplier(ctx: RecoveryContext, *, is_recovery_day: bool = True) -> float:
    """
    Multiplicador de qualidade da recuperação (0.0–1.4).

    Em dias de carga (não recovery), o valor ainda é calculado mas o caller
    pode usá-lo só para eventos / micro-recovery.
    """
    rating = ctx.last_rating if ctx.last_rating is not None else ctx.form_avg

    # Performance: nota baixa freia; nota alta acelera
    if rating is None:
        performance_factor = 1.0
    elif rating < 5.0:
        performance_factor = 0.45
    elif rating < 6.0:
        performance_factor = 0.75
    elif rating >= 7.5:
        performance_factor = 1.2
    elif rating >= 7.0:
        performance_factor = 1.1
    else:
        performance_factor = 1.0

    # Moral + discontent individual
    morale = float(ctx.team_morale)
    disc = float(ctx.discontent)
    if morale < 35 or disc >= 55:
        morale_factor = 0.55
    elif morale < 50 or disc >= 35:
        morale_factor = 0.8
    elif morale >= 75 and disc < 20:
        morale_factor = 1.15
    else:
        morale_factor = 1.0

    # Pressão do board
    conf = float(ctx.board_confidence)
    if conf < 35:
        pressure_factor = 0.5
    elif conf < 50:
        pressure_factor = 0.75
    elif conf >= 70:
        pressure_factor = 1.12
    else:
        pressure_factor = 1.0

    # Staff (Performance Coach) — bonus ~0.05–0.15 → +5–15%
    staff_factor = 1.0 + clamp(float(ctx.staff_recovery_bonus), 0.0, 0.25)

    # Intensidade do plano de treino no mesmo dia
    intensity = normalize_intensity(ctx.intensity)
    if intensity == "HARD":
        intensity_factor = 0.65
    elif intensity == "LIGHT":
        intensity_factor = 1.12
    else:
        intensity_factor = 1.0

    mult = (
        1.0
        * performance_factor
        * morale_factor
        * pressure_factor
        * staff_factor
        * intensity_factor
    )

    # Regra de ouro: mau desempenho + moral/pressão ruins → quase zero recovery
    poor_form = rating is not None and rating < 5.0
    bad_vibes = morale < 40 or conf < 40 or disc >= 50
    if is_recovery_day and poor_form and bad_vibes:
        mult = min(mult, 0.05)

    return clamp(mult, 0.0, 1.4)


def base_day_deltas(
    day_type: str,
    *,
    is_match_day: bool = False,
    is_starter: bool = True,
    intensity: str = "NORMAL",
    match_starter_burnout: float = 5.0,
    rest_burnout: float = 12.0,
    rest_visual: float = 10.0,
    rest_mental: float = 8.0,
) -> FatigueDeltas:
    """
    Deltas base por tipo de dia (antes do recovery_mult).

    MATCH: titulares sofrem carga; banco recupera levemente.
    """
    intensity = normalize_intensity(intensity)
    dt = day_type or ""

    if dt == CalendarDayType.REST or dt == "REST":
        return FatigueDeltas(
            burnout=-abs(rest_burnout),
            visual=-abs(rest_visual),
            mental=-abs(rest_mental),
            event_type="FATIGUE_RECOVERY",
        )

    if dt == CalendarDayType.MATCH_DAY or dt == "MATCH_DAY" or is_match_day:
        if is_starter:
            return FatigueDeltas(
                burnout=float(match_starter_burnout),
                visual=DEFAULT_MATCH_STARTER["visual"],
                mental=DEFAULT_MATCH_STARTER["mental"],
                games_played_delta=1,
                event_type="MATCH_DAY_FATIGUE",
            )
        return FatigueDeltas(
            burnout=DEFAULT_MATCH_BENCH["burnout"],
            visual=DEFAULT_MATCH_BENCH["visual"],
            mental=DEFAULT_MATCH_BENCH["mental"],
            games_played_delta=0,
            event_type="BENCH_RECOVERY",
        )

    if dt == CalendarDayType.SCRIM or dt == "SCRIM":
        return FatigueDeltas(
            burnout=DEFAULT_SCRIM["burnout"],
            visual=DEFAULT_SCRIM["visual"],
            mental=DEFAULT_SCRIM["mental"],
        )

    if dt == CalendarDayType.MEDIA or dt == "MEDIA":
        return FatigueDeltas(
            burnout=DEFAULT_MEDIA["burnout"],
            visual=DEFAULT_MEDIA["visual"],
            mental=DEFAULT_MEDIA["mental"],
            event_type="FATIGUE_RECOVERY",
        )

    if dt == CalendarDayType.TRAINING or dt == "TRAINING":
        if intensity == "HARD":
            return FatigueDeltas(
                burnout=DEFAULT_TRAINING_HARD["burnout"],
                visual=DEFAULT_TRAINING_HARD["visual"],
                mental=DEFAULT_TRAINING_HARD["mental"],
            )
        if intensity == "LIGHT":
            return FatigueDeltas(
                burnout=DEFAULT_TRAINING_LIGHT["burnout"],
                visual=DEFAULT_TRAINING_LIGHT["visual"],
                mental=DEFAULT_TRAINING_LIGHT["mental"],
                event_type="FATIGUE_RECOVERY",
            )
        return FatigueDeltas(
            burnout=DEFAULT_TRAINING_NORMAL["burnout"],
            visual=DEFAULT_TRAINING_NORMAL["visual"],
            mental=DEFAULT_TRAINING_NORMAL["mental"],
            event_type="FATIGUE_RECOVERY",
        )

    return FatigueDeltas(
        burnout=DEFAULT_UNKNOWN["burnout"],
        visual=DEFAULT_UNKNOWN["visual"],
        mental=DEFAULT_UNKNOWN["mental"],
        event_type="UNKNOWN_DAY_TYPE_PENALTY",
    )


def is_recovery_oriented(deltas: FatigueDeltas) -> bool:
    """True se o dia tende a baixar fadiga (soma de deltas < 0)."""
    return (deltas.burnout + deltas.visual + deltas.mental) < 0


def apply_recovery_quality(
    deltas: FatigueDeltas,
    mult: float,
    *,
    force_poor_mental_spike: bool = False,
) -> FatigueDeltas:
    """
    Ajusta deltas de recuperação pelo multiplicador.

    - recovery (deltas negativos): multiplica magnitude (mult alto → recupera mais)
    - carga (deltas positivos): HARD já está na base; mult baixo não aumenta carga
    - mult ~0 em recovery: quase zero recovery; mental pode subir levemente
    """
    if not is_recovery_oriented(deltas):
        return deltas

    if mult <= 0.08 or force_poor_mental_spike:
        return FatigueDeltas(
            burnout=0.0,
            visual=0.0,
            mental=1.5,  # "não desliga a cabeça"
            games_played_delta=deltas.games_played_delta,
            event_type="POOR_RECOVERY",
        )

    # deltas negativos * mult: mult=1.2 e burnout=-10 → -12
    new_b = deltas.burnout * mult
    new_v = deltas.visual * mult
    new_m = deltas.mental * mult

    event = deltas.event_type
    if mult < 0.8:
        event = "POOR_RECOVERY"
    elif event is None:
        event = "FATIGUE_RECOVERY"

    return FatigueDeltas(
        burnout=new_b,
        visual=new_v,
        mental=new_m,
        games_played_delta=deltas.games_played_delta,
        event_type=event,
    )


def apply_deltas_to_meters(
    burnout: float,
    visual: float,
    mental: float,
    deltas: FatigueDeltas,
) -> tuple[float, float, float]:
    """Aplica deltas e clampa 0–100."""
    return (
        clamp(float(burnout) + deltas.burnout, 0.0, 100.0),
        clamp(float(visual) + deltas.visual, 0.0, 100.0),
        clamp(float(mental) + deltas.mental, 0.0, 100.0),
    )


def fatigue_alert_active(
    burnout: float,
    visual: float,
    *,
    threshold: float = 70.0,
) -> bool:
    """Alerta de hub: burnout ou visual acima do limiar."""
    return float(burnout) > threshold or float(visual) > threshold
