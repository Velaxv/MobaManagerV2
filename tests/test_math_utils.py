"""
Testes unitários para as funções matemáticas do LoL Manager.
"""

import numpy as np
import pytest
from src.shared.math_utils import (
    clamp,
    normalize_attribute,
    stochastic_roll,
    sigmoid,
    weighted_average,
    gold_advantage_to_probability,
    calculate_player_rating,
)

def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10
    assert clamp(5.5, 5.0, 6.0) == 5.5

def test_normalize_attribute():
    # Atributo no meio (10.5)
    assert normalize_attribute(10.5, 1.0, 20.0) == (10.5 - 1.0) / 19.0
    # Limites
    assert normalize_attribute(1.0, 1.0, 20.0) == 0.0
    assert normalize_attribute(20.0, 1.0, 20.0) == 1.0

def test_sigmoid():
    # Centralizado deve ser 0.50
    assert abs(sigmoid(0.0) - 0.50) < 1e-6
    # Extremidades devem ser limitadas
    assert sigmoid(100.0) <= 0.95
    assert sigmoid(-100.0) >= 0.05

def test_weighted_average():
    values = [10.0, 20.0, 30.0]
    weights = [1.0, 2.0, 1.0]
    # (10*1 + 20*2 + 30*1) / 4 = (10 + 40 + 30) / 4 = 80 / 4 = 20.0
    assert weighted_average(values, weights) == 20.0

    with pytest.raises(ValueError):
        weighted_average([10], [1, 2])

def test_stochastic_roll():
    rng = np.random.default_rng(seed=42)
    # Consistência alta (20.0) -> ruído mínimo (std_dev = 0)
    # A fórmula no código é std_dev = (20.0 - consistency) / 40.0
    # Se consistency = 20.0, std_dev = 0.0, logo noise = 1.0, retorna base
    val_high = stochastic_roll(100.0, 20.0, rng)
    assert abs(val_high - 100.0) < 1e-9

    # Consistência baixa (1.0) -> ruído maior
    val_lows = [stochastic_roll(100.0, 1.0, rng) for _ in range(100)]
    assert any(v != 100.0 for v in val_lows)
    # Todos devem estar dentro do clamp [0.3 * base, 1.7 * base]
    assert all(30.0 <= v <= 170.0 for v in val_lows)

def test_gold_advantage_to_probability():
    # 0 de diferença -> 50% de chance
    assert abs(gold_advantage_to_probability(0.0) - 0.50) < 1e-2
    # Vantagem azul grande -> chance alta para o azul
    assert gold_advantage_to_probability(10000.0) > 0.85
    # Vantagem vermelha grande (gold_diff negativo) -> chance baixa para o azul (alta vermelha)
    assert gold_advantage_to_probability(-10000.0) < 0.15

def test_calculate_player_rating():
    # CA=100, mechanics=10.0, focus=10.0, burnout=0.0
    rating_fresh = calculate_player_rating(
        current_ability=100,
        mechanics=10.0,
        focus=10.0,
        burnout_meter=0.0
    )
    
    # Rating cansado deve ser menor por causa do burnout
    rating_tired = calculate_player_rating(
        current_ability=100,
        mechanics=10.0,
        focus=10.0,
        burnout_meter=50.0
    )
    assert rating_tired < rating_fresh
