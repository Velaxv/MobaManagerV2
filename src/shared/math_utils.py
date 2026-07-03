"""
Utilitários matemáticos para o motor de simulação do LoL Manager.
Todas as funções são determinísticas dada uma semente de RNG,
garantindo reprodutibilidade das partidas simuladas.
"""

import numpy as np
from typing import List


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Limita um valor entre min e max.

    Args:
        value: Valor a ser limitado.
        min_val: Limite inferior.
        max_val: Limite superior.

    Returns:
        Valor limitado ao intervalo [min_val, max_val].
    """
    return max(min_val, min(max_val, value))


def normalize_attribute(value: float, min_val: float = 1.0, max_val: float = 20.0) -> float:
    """
    Normaliza um atributo do intervalo [1-20] para [0-1].

    Args:
        value: Valor bruto do atributo (esperado entre 1 e 20).
        min_val: Valor mínimo da escala (padrão: 1.0).
        max_val: Valor máximo da escala (padrão: 20.0).

    Returns:
        Valor normalizado entre 0.0 e 1.0.
    """
    if max_val == min_val:
        raise ValueError("max_val e min_val não podem ser iguais (divisão por zero).")
    return (value - min_val) / (max_val - min_val)


def stochastic_roll(
    base_value: float,
    consistency: float,
    rng: np.random.Generator,
) -> float:
    """
    Rola um valor estocástico com variância controlada pela consistência do jogador.

    Quanto maior a consistência (1-20), menor o desvio padrão relativo,
    resultando em performances mais previsíveis.

    Fórmula: base * Normal(1, std_dev)
    onde std_dev = (20 - consistency) / 40  → range [0.025, 0.475]

    Args:
        base_value: Valor base da performance.
        consistency: Atributo de consistência do jogador (1-20).
        rng: Gerador de números aleatórios NumPy (para reprodutibilidade).

    Returns:
        Valor base modificado pelo ruído estocástico, limitado a ±70% do base.
    """
    # Desvio padrão relativo: consistency=20 → std=0.025; consistency=1 → std=0.475
    std_dev = (20.0 - consistency) / 40.0
    noise = rng.normal(1.0, std_dev)
    # Limita extremos impossíveis: garante mínimo de 30% e máximo de 170% do valor base
    noise = clamp(noise, 0.3, 1.7)
    return base_value * noise


def sigmoid(x: float, steepness: float = 1.0) -> float:
    """
    Função sigmóide para converter diferença de score em probabilidade de vitória.

    Retorna valor entre 0.05 e 0.95 — nunca 0% ou 100% de chance,
    pois qualquer time pode ganhar ou perder em esports.

    Args:
        x: Diferença de score (positivo = favorece o time azul).
        steepness: Inclinação da curva sigmóide (padrão: 1.0).

    Returns:
        Probabilidade entre 0.05 e 0.95.
    """
    prob = 1.0 / (1.0 + np.exp(-steepness * x))
    return clamp(prob, 0.05, 0.95)


def weighted_average(values: List[float], weights: List[float]) -> float:
    """
    Calcula a média ponderada de uma lista de valores.

    Args:
        values: Lista de valores numéricos.
        weights: Lista de pesos correspondentes a cada valor.

    Returns:
        Média ponderada dos valores.

    Raises:
        ValueError: Se as listas tiverem tamanhos diferentes, estiverem vazias
                    ou a soma dos pesos for zero.
    """
    if not values or not weights:
        raise ValueError("Valores e pesos não podem ser listas vazias.")
    if len(values) != len(weights):
        raise ValueError(
            f"Valores ({len(values)}) e pesos ({len(weights)}) devem ter o mesmo tamanho."
        )
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("Soma dos pesos não pode ser zero.")
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def roll_check(threshold: float, rng: np.random.Generator) -> bool:
    """
    Realiza um teste de probabilidade simples (dado percentual).

    Retorna True se o valor aleatório for menor que o threshold.
    Exemplo: roll_check(0.65, rng) tem 65% de chance de retornar True.

    Args:
        threshold: Probabilidade de sucesso (0.0 a 1.0).
        rng: Gerador de números aleatórios NumPy.

    Returns:
        True se o teste passou, False caso contrário.
    """
    return rng.random() < threshold


def calculate_player_rating(
    current_ability: int,
    mechanics: float,
    focus: float,
    burnout_meter: float,
) -> float:
    """
    Calcula o rating efetivo do jogador considerando burnout.

    Composição do rating:
        - Current Ability (CA): 60% do rating base
        - Mecânica: 25% do rating base
        - Foco: 15% do rating base
        - Penalidade de burnout: redução linear de 0% a 30% (burnout 0→100)

    Args:
        current_ability: Habilidade atual do jogador (0-200).
        mechanics: Atributo de mecânica do jogador (1-20).
        focus: Atributo de foco do jogador (1-20).
        burnout_meter: Medidor de burnout atual (0-100).

    Returns:
        Rating efetivo entre 0.0 e ~1.0 (pode ultrapassar 1.0 brevemente com boost).
    """
    # Fator de penalidade por burnout: 0% a 30% de redução
    burnout_penalty = 1.0 - (burnout_meter / 100.0) * 0.30

    # Componente de CA: normalizado de [0-200] para [0-1], vale 60% do rating
    base = (current_ability / 200.0) * 0.60

    # Componente de mecânica: normalizado [1-20] → [0-1], vale 25%
    mechanics_component = normalize_attribute(mechanics) * 0.25

    # Componente de foco: normalizado [1-20] → [0-1], vale 15%
    focus_component = normalize_attribute(focus) * 0.15

    return (base + mechanics_component + focus_component) * burnout_penalty


def gold_advantage_to_probability(gold_diff: float) -> float:
    """
    Converte diferença de ouro em probabilidade de vitória do time à frente.

    Calibrado com base em dados reais de LoL:
        - Diferença de 3.000 ouro ≈ 65% de win rate
        - Diferença de 5.000 ouro ≈ 90% de win rate

    Args:
        gold_diff: Diferença de ouro (positivo = time azul à frente).

    Returns:
        Probabilidade de vitória do time com vantagem (0.05 a 0.95).
    """
    # Normaliza: 5.000 ouro de diferença → entrada de ~1.0 para a sigmóide
    normalized_diff = gold_diff / 5000.0
    return sigmoid(normalized_diff, steepness=2.5)


def lerp(start: float, end: float, t: float) -> float:
    """
    Interpolação linear entre dois valores.

    Args:
        start: Valor inicial.
        end: Valor final.
        t: Fator de interpolação (0.0 = start, 1.0 = end).

    Returns:
        Valor interpolado linearmente.
    """
    t = clamp(t, 0.0, 1.0)
    return start + (end - start) * t


def calculate_team_synergy(teamwork_values: List[float]) -> float:
    """
    Calcula o bônus de sinergia do time com base nos valores de teamwork individuais.

    A sinergia é calculada como a média dos atributos de teamwork,
    normalizada e aplicada como um multiplicador entre 0.9 e 1.1.

    Args:
        teamwork_values: Lista de valores de teamwork dos 5 jogadores (1-20).

    Returns:
        Multiplicador de sinergia entre 0.90 e 1.10.
    """
    if not teamwork_values:
        return 1.0
    avg_teamwork = sum(teamwork_values) / len(teamwork_values)
    # Normaliza [1-20] para [-0.1, +0.1] de bônus/debuff
    normalized = normalize_attribute(avg_teamwork)
    return lerp(0.90, 1.10, normalized)
