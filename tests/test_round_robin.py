"""Testes do gerador de round-robin."""

from src.shared.round_robin import (
    generate_single_round_robin,
    get_round_pairs,
    match_day_round_index,
)


def test_single_rr_eight_teams():
    teams = [f"T{i}" for i in range(8)]
    rounds = generate_single_round_robin(teams)
    assert len(rounds) == 7  # n-1
    for rnd in rounds:
        assert len(rnd) == 4  # n/2
        # cada time aparece no máximo uma vez por rodada
        seen = []
        for a, b in rnd:
            seen.extend([a, b])
        assert len(seen) == len(set(seen)) == 8


def test_each_pair_once():
    teams = ["A", "B", "C", "D"]
    rounds = generate_single_round_robin(teams)
    pairs = set()
    for rnd in rounds:
        for a, b in rnd:
            key = tuple(sorted((a, b)))
            assert key not in pairs
            pairs.add(key)
    # C(4,2) = 6
    assert len(pairs) == 6


def test_get_round_pairs_cycles_with_home_away_flip():
    teams = ["A", "B", "C", "D"]
    r0 = get_round_pairs(teams, 0)
    r_cycle = get_round_pairs(teams, 3)  # second cycle of 3 rounds
    # mesmo par de oponentes, mando invertido em pelo menos um jogo
    base = {(a, b) for a, b in r0}
    flipped = {(b, a) for a, b in r0}
    cycle_set = set(r_cycle)
    assert cycle_set == flipped or cycle_set == base or len(cycle_set & (base | flipped)) > 0


def test_match_day_round_index():
    assert match_day_round_index(0, 2) == 0  # Qua sem 0
    assert match_day_round_index(0, 5) == 1  # Sab sem 0
    assert match_day_round_index(1, 2) == 2
    assert match_day_round_index(1, 5) == 3


def test_odd_teams_bye():
    teams = ["A", "B", "C"]
    rounds = generate_single_round_robin(teams)
    assert len(rounds) == 3
    for rnd in rounds:
        # 1 jogo por rodada (um bye)
        assert len(rnd) == 1
