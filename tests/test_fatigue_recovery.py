"""
Testes do sistema de restauração de fadiga (Feature A).
"""

from src.modules.calendar.fatigue_recovery import (
    RecoveryContext,
    apply_deltas_to_meters,
    apply_recovery_quality,
    base_day_deltas,
    fatigue_alert_active,
    is_recovery_oriented,
    recovery_multiplier,
)
from src.shared.enums import CalendarDayType


def test_rest_base_is_recovery():
    d = base_day_deltas(CalendarDayType.REST, rest_burnout=12, rest_visual=10, rest_mental=8)
    assert is_recovery_oriented(d)
    assert d.burnout < 0
    assert d.visual < 0
    assert d.mental < 0
    assert d.event_type == "FATIGUE_RECOVERY"


def test_match_starter_loads_bench_recovers():
    starter = base_day_deltas(
        CalendarDayType.MATCH_DAY, is_starter=True, match_starter_burnout=5
    )
    bench = base_day_deltas(
        CalendarDayType.MATCH_DAY, is_starter=False, match_starter_burnout=5
    )
    assert starter.burnout > 0
    assert starter.games_played_delta == 1
    assert starter.event_type == "MATCH_DAY_FATIGUE"
    assert is_recovery_oriented(bench)
    assert bench.games_played_delta == 0
    assert bench.event_type == "BENCH_RECOVERY"


def test_training_intensity_light_vs_hard():
    light = base_day_deltas(CalendarDayType.TRAINING, intensity="LIGHT")
    hard = base_day_deltas(CalendarDayType.TRAINING, intensity="HARD")
    assert is_recovery_oriented(light)
    assert hard.burnout > 0
    assert not is_recovery_oriented(hard)


def test_good_recovery_mult_boosts_rest():
    ctx = RecoveryContext(
        last_rating=8.0,
        team_morale=80.0,
        discontent=0.0,
        board_confidence=75.0,
        staff_recovery_bonus=0.1,
        intensity="LIGHT",
    )
    mult = recovery_multiplier(ctx, is_recovery_day=True)
    assert mult >= 1.0
    assert mult <= 1.4

    base = base_day_deltas(CalendarDayType.REST, rest_burnout=12, rest_visual=10, rest_mental=8)
    applied = apply_recovery_quality(base, mult)
    # Mais recovery (mais negativo) que a base
    assert applied.burnout <= base.burnout


def test_poor_form_and_pressure_zero_recovery():
    ctx = RecoveryContext(
        last_rating=4.0,
        team_morale=30.0,
        discontent=60.0,
        board_confidence=30.0,
        staff_recovery_bonus=0.0,
        intensity="HARD",
    )
    mult = recovery_multiplier(ctx, is_recovery_day=True)
    assert mult <= 0.08

    base = base_day_deltas(CalendarDayType.REST)
    applied = apply_recovery_quality(base, mult)
    assert applied.event_type == "POOR_RECOVERY"
    assert applied.burnout == 0.0
    assert applied.mental > 0  # não desliga a cabeça


def test_two_rests_clear_alert_after_two_matches():
    """
    Critério UAT: após 2 partidas + REST bons, alerta some (≤2 REST com mult ≥ 0.8).
    """
    burnout, visual, mental = 40.0, 35.0, 30.0

    # 2 match days como titular
    for _ in range(2):
        d = base_day_deltas(CalendarDayType.MATCH_DAY, is_starter=True, match_starter_burnout=5)
        burnout, visual, mental = apply_deltas_to_meters(burnout, visual, mental, d)

    assert fatigue_alert_active(burnout, visual, threshold=70) or burnout >= 50

    # Simulate elevated state after matches + live spikes (set high)
    burnout, visual, mental = 78.0, 76.0, 60.0
    assert fatigue_alert_active(burnout, visual, threshold=70)

    good = RecoveryContext(
        last_rating=7.2,
        team_morale=70.0,
        board_confidence=70.0,
        intensity="LIGHT",
    )
    mult = recovery_multiplier(good, is_recovery_day=True)
    assert mult >= 0.8

    rests_needed = 0
    for _ in range(5):
        base = base_day_deltas(
            CalendarDayType.REST, rest_burnout=12, rest_visual=10, rest_mental=8
        )
        applied = apply_recovery_quality(base, mult)
        burnout, visual, mental = apply_deltas_to_meters(burnout, visual, mental, applied)
        rests_needed += 1
        if not fatigue_alert_active(burnout, visual, threshold=70):
            break

    assert rests_needed <= 2
    assert not fatigue_alert_active(burnout, visual, threshold=70)


def test_bench_recovers_while_starters_load():
    starter_b, starter_v, starter_m = 50.0, 50.0, 40.0
    bench_b, bench_v, bench_m = 50.0, 50.0, 40.0

    s = base_day_deltas(CalendarDayType.MATCH_DAY, is_starter=True, match_starter_burnout=5)
    b = base_day_deltas(CalendarDayType.MATCH_DAY, is_starter=False)

    starter_b, starter_v, starter_m = apply_deltas_to_meters(
        starter_b, starter_v, starter_m, s
    )
    bench_b, bench_v, bench_m = apply_deltas_to_meters(bench_b, bench_v, bench_m, b)

    assert starter_b > bench_b
    assert starter_v > bench_v
    assert bench_b < 50.0


def test_poor_recovery_worse_than_good():
    start = (80.0, 75.0, 60.0)
    good_ctx = RecoveryContext(last_rating=8.0, team_morale=80, board_confidence=75)
    bad_ctx = RecoveryContext(last_rating=4.0, team_morale=30, board_confidence=30, discontent=60)

    good_m = recovery_multiplier(good_ctx, is_recovery_day=True)
    bad_m = recovery_multiplier(bad_ctx, is_recovery_day=True)
    base = base_day_deltas(CalendarDayType.REST, rest_burnout=12, rest_visual=10, rest_mental=8)

    gb, gv, gm = apply_deltas_to_meters(*start, apply_recovery_quality(base, good_m))
    bb, bv, bm = apply_deltas_to_meters(*start, apply_recovery_quality(base, bad_m))

    assert gb < bb  # good recovery lowers burnout more
    assert gv < bv
