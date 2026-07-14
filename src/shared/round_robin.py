# -*- coding: utf-8 -*-
"""
Gerador de tabela round-robin (método do círculo).

Para N times (par):
  - Single RR: N-1 rodadas, N/2 jogos por rodada
  - Cada time joga todos os outros exatamente uma vez
  - Ciclos extras espelham mando (home/away invertido)

Ordem de entrada deve ser estável (ex.: sorted por id/nome) para
calendário determinístico entre restarts.
"""

from __future__ import annotations
from typing import List, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")


def generate_single_round_robin(
    teams: Sequence[T],
) -> List[List[Tuple[T, T]]]:
    """
    Gera rodadas de single round-robin.

    Returns:
        Lista de rodadas; cada rodada é lista de pares (home, away).
        Se len(teams) < 2, retorna [].
        Se ímpar, um time fica de bye por rodada (não entra nos pares).
    """
    items: List[Optional[T]] = list(teams)
    if len(items) < 2:
        return []

    if len(items) % 2 == 1:
        items.append(None)  # bye

    n = len(items)
    rounds: List[List[Tuple[T, T]]] = []

    # Cópia mutável para rotação
    arr: List[Optional[T]] = items[:]

    for r in range(n - 1):
        pairs: List[Tuple[T, T]] = []
        for i in range(n // 2):
            a, b = arr[i], arr[n - 1 - i]
            if a is None or b is None:
                continue
            # Alterna mando por rodada para equilibrar home/away
            if r % 2 == 0:
                pairs.append((a, b))
            else:
                pairs.append((b, a))
        rounds.append(pairs)
        # Rotaciona mantendo o primeiro fixo
        arr = [arr[0], arr[-1], *arr[1:-1]]

    return rounds


def get_round_pairs(
    teams: Sequence[T],
    round_index: int,
) -> List[Tuple[T, T]]:
    """
    Retorna os confrontos da rodada `round_index` (0-based).

    Se round_index >= len(single_rr), repete o ciclo invertendo mando
    (double RR e além).
    """
    base_rounds = generate_single_round_robin(teams)
    if not base_rounds:
        return []

    n = len(base_rounds)
    cycle = round_index // n
    idx = round_index % n
    pairs = base_rounds[idx]

    if cycle % 2 == 1:
        return [(away, home) for home, away in pairs]
    return list(pairs)


def match_day_round_index(week: int, day_of_week: int) -> int:
    """
    Mapeia semana + dia da semana do calendário para índice de rodada.

    Convenção do RegularSeasonState:
      - Partidas: Quarta (2) e Sábado (5)
      - week: semana da fase (0-based ou 1-based — usamos max(0, week))

    Quarta = rodada 2*W, Sábado = 2*W+1
    """
    w = max(0, int(week))
    # Se a SM reporta week 1-based no day_info, ainda funciona com offset
    slot = 0 if int(day_of_week) <= 2 else 1
    # day_of_week 2 → slot 0; 5 → slot 1; outros default 0
    if int(day_of_week) == 5:
        slot = 1
    elif int(day_of_week) == 2:
        slot = 0
    return w * 2 + slot
