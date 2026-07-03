"""
Estratégia de Late Game (Teamfights e Fechamento — 25+ minutos).

Esta fase simula:
    - Teamfights 5v5 em torno do Baron Nashor e Elder Dragon
    - Influência máxima de Big Match Aptitude (crítico em playoffs)
    - Cálculo da probabilidade final de vitória via função sigmoid
    - Geração da duração estimada da partida
    - Resultado final (vitória Blue Side / Red Side)

Fórmula de Late Game Score:
    teamfight_score = CA * mechanics * resilience * [bma_bonus se playoff]
    baron_control = teamfight_score + gold_advantage_factor
    win_probability = sigmoid(total_score_diff / scaling_factor)
"""

import logging
from typing import List, Optional
import numpy as np

from src.modules.simulation.strategies.base import (
    MatchPhaseStrategy,
    PhaseResult,
    TeamMatchState,
)
from src.shared.math_utils import (
    stochastic_roll,
    normalize_attribute,
    weighted_average,
    clamp,
    roll_check,
    gold_advantage_to_probability,
    sigmoid,
    calculate_player_rating,
)
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Objetivos do Late Game e valores
LATE_GAME_OBJECTIVES = {
    "baron_nashor": 1500,  # Buff de Baron (também facilita turrets)
    "elder_dragon": 2000,  # Mega bônus de dano
    "inhibitor": 1200,     # Inibidor destruído
    "base_towers": 600,    # Torres de base
}

# Escala de duração da partida por nível de desequilíbrio (minutos)
MATCH_DURATION_RANGES = {
    "stomp":       (20, 28),   # Gold diff > 10000
    "decisive":    (28, 35),   # Gold diff 5000-10000
    "competitive": (35, 42),   # Gold diff 2000-5000
    "close":       (42, 50),   # Gold diff < 2000
    "epic":        (45, 60),   # Partida extremamente equilibrada (comebacks)
}


class LateGameStrategy(MatchPhaseStrategy):
    """
    Estratégia de Late Game (Teamfights e Fechamento).
    
    Determina o resultado final da partida com base na vantagem acumulada
    e nos atributos de teamfight (CA, mechanics, resilience).
    Em playoffs, o atributo oculto Big Match Aptitude tem influência máxima.
    """
    
    def get_phase_name(self) -> str:
        return "LATE_GAME"
    
    def calculate(
        self,
        blue_team,
        red_team,
        blue_draft: List[dict],
        red_draft: List[dict],
        rng: np.random.Generator,
        previous_result: Optional[PhaseResult] = None,
        is_playoff: bool = False,
        champion_patch_meta: Optional[dict] = None,
        **kwargs,
    ) -> PhaseResult:
        """
        Calcula o Late Game e determina o vencedor final.
        
        1. Calcula teamfight score de cada time
        2. Distribui Baron/Elder com base nos scores
        3. Aplica Dragon Soul se conquistada no Mid Game
        4. Calcula probabilidade de vitória via sigmoid
        5. Determina vencedor, kills finais e duração da partida
        """
        logger.info(
            f"[LateGame] Resolvendo partida final: "
            f"{blue_team.name} vs {red_team.name} | "
            f"Playoff: {is_playoff}"
        )
        
        phase_log = []
        
        # Herda gold e estado do Mid Game
        mid_gold_diff = previous_result.gold_difference if previous_result else 0.0
        blue_gold = previous_result.blue_state.gold_earned if previous_result else 8000
        red_gold = previous_result.red_state.gold_earned if previous_result else 8000
        blue_prev_buffs = previous_result.blue_state.active_buffs if previous_result else []
        red_prev_buffs = previous_result.red_state.active_buffs if previous_result else []
        
        blue_state = TeamMatchState(
            team_id=str(blue_team.id),
            team_name=blue_team.name,
            gold_earned=blue_gold,
            active_buffs=list(blue_prev_buffs),
        )
        red_state = TeamMatchState(
            team_id=str(red_team.id),
            team_name=red_team.name,
            gold_earned=red_gold,
            active_buffs=list(red_prev_buffs),
        )
        
        phase_log.append(
            f"📥 Estado do Mid Game: {blue_team.name} {mid_gold_diff:+.0f}g de vantagem."
        )
        
        # --- Etapa 1: Calcular Teamfight Score ---
        blue_tf_score = self._calculate_teamfight_score(
            team=blue_team,
            active_buffs=blue_state.active_buffs,
            is_playoff=is_playoff,
            rng=rng,
            draft=blue_draft,
            champion_patch_meta=champion_patch_meta,
        )
        red_tf_score = self._calculate_teamfight_score(
            team=red_team,
            active_buffs=red_state.active_buffs,
            is_playoff=is_playoff,
            rng=rng,
            draft=red_draft,
            champion_patch_meta=champion_patch_meta,
        )
        
        phase_log.append(
            f"⚔️  Teamfight Score: {blue_team.name} {blue_tf_score:.3f} "
            f"vs {red_team.name} {red_tf_score:.3f}"
        )
        
        blue_state.phase_score = blue_tf_score
        red_state.phase_score = red_tf_score
        
        # --- Etapa 2: Distribuição de objetivos Baron/Elder ---
        tf_ratio_blue = blue_tf_score / (blue_tf_score + red_tf_score + 1e-9)
        
        # Combina vantagem de teamfight com vantagem de ouro
        gold_factor = clamp(mid_gold_diff / 15000, -0.25, 0.25)
        adjusted_ratio = clamp(tf_ratio_blue + gold_factor, 0.10, 0.90)
        
        for objective, gold_value in LATE_GAME_OBJECTIVES.items():
            if rng.random() < adjusted_ratio:
                blue_state.gold_earned += gold_value
                blue_state.objectives_taken.append(objective)
                phase_log.append(
                    f"🏆 {blue_team.name} (Blue) → {objective.replace('_', ' ').title()}"
                )
                if objective == "baron_nashor":
                    blue_state.active_buffs.append("baron_empowered")
                    phase_log.append(
                        f"⚡ {blue_team.name} ativou o Bônus de Baron! "
                        f"Vantagem de empurrada massiva."
                    )
            else:
                red_state.gold_earned += gold_value
                red_state.objectives_taken.append(objective)
                phase_log.append(
                    f"🏆 {red_team.name} (Red) → {objective.replace('_', ' ').title()}"
                )
                if objective == "baron_nashor":
                    red_state.active_buffs.append("baron_empowered")
        
        # --- Etapa 3: Calcular probabilidade final de vitória ---
        final_gold_diff = blue_state.gold_earned - red_state.gold_earned
        
        # Probabilidade baseada em ouro
        gold_win_prob = gold_advantage_to_probability(final_gold_diff)
        
        # Score de teamfight como fator adicional
        tf_win_component = sigmoid((blue_tf_score - red_tf_score) / 0.3, steepness=3.0)
        
        # Probabilidade final: 70% peso do ouro, 30% peso do teamfight
        blue_win_probability = (gold_win_prob * 0.70) + (tf_win_component * 0.30)
        blue_win_probability = clamp(blue_win_probability, 0.05, 0.95)
        
        phase_log.append(
            f"🎲 Probabilidade de vitória Blue ({blue_team.name}): "
            f"{blue_win_probability:.1%} | Red ({red_team.name}): "
            f"{1 - blue_win_probability:.1%}"
        )
        
        # --- Etapa 4: Determinar vencedor ---
        blue_wins = roll_check(blue_win_probability, rng)
        
        # Kills finais da partida
        total_kills = int(rng.integers(15, 40))
        blue_total_kills = int(total_kills * adjusted_ratio)
        red_total_kills = total_kills - blue_total_kills
        
        blue_state.kills = blue_total_kills
        blue_state.deaths = red_total_kills
        red_state.kills = red_total_kills
        red_state.deaths = blue_total_kills
        
        # Marca o vencedor
        if blue_wins:
            blue_state.active_buffs.append("VICTORY")
            red_state.active_debuffs.append("DEFEAT")
            phase_log.append(
                f"🏆 VITÓRIA! {blue_team.name} (Blue Side) venceu a partida!"
            )
        else:
            red_state.active_buffs.append("VICTORY")
            blue_state.active_debuffs.append("DEFEAT")
            phase_log.append(
                f"🏆 VITÓRIA! {red_team.name} (Red Side) venceu a partida!"
            )
        
        # --- Etapa 5: Duração estimada da partida ---
        match_duration = self._calculate_match_duration(
            gold_diff=abs(final_gold_diff),
            blue_wins=blue_wins,
            blue_had_dragon_soul=any("dragon_soul" in b for b in blue_state.active_buffs),
            rng=rng,
        )
        
        phase_log.append(
            f"⏱️  Duração da partida: {match_duration:.1f} minutos | "
            f"Placar final: {blue_total_kills}-{red_total_kills}"
        )
        
        logger.info(
            f"[LateGame] RESULTADO FINAL: "
            f"{'Blue' if blue_wins else 'Red'} venceu! "
            f"Gold diff: {final_gold_diff:+.0f}g | "
            f"Duração: {match_duration:.1f}min | "
            f"Win prob foi: {blue_win_probability:.1%}"
        )
        
        # Armazena probabilidade e duração no estado para o MatchEngine
        blue_state.event_log.append(f"win_probability:{blue_win_probability:.4f}")
        blue_state.event_log.append(f"match_duration:{match_duration:.1f}")
        blue_state.event_log.append(f"winner:{'BLUE' if blue_wins else 'RED'}")
        
        gold_difference = blue_state.gold_earned - red_state.gold_earned
        score_difference = blue_state.phase_score - red_state.phase_score
        
        return PhaseResult(
            phase_name=self.get_phase_name(),
            blue_state=blue_state,
            red_state=red_state,
            gold_difference=gold_difference,
            score_difference=score_difference,
            phase_log=phase_log,
        )
    
    def _calculate_teamfight_score(
        self,
        team,
        active_buffs: List[str],
        is_playoff: bool,
        rng: np.random.Generator,
        draft: List[dict],
        champion_patch_meta: Optional[dict] = None,
    ) -> float:
        """
        Calcula o score de teamfight de um time no Late Game.
        Incorpora os multiplicadores de dano e sobrevivência dos campeões draftados no patch.
        """
        starters = team.get_starters()
        if not starters:
            return 0.1
        
        # Calcula médias dos atributos de teamfight
        avg_ca = sum(p.current_ability for p in starters) / len(starters)
        avg_mechanics = sum(p.mechanics for p in starters) / len(starters)
        avg_resilience = sum(p.resilience for p in starters) / len(starters)
        avg_consistency = sum(p.consistency for p in starters) / len(starters)
        avg_bma = sum(p.big_match_aptitude for p in starters) / len(starters)
        
        # Score base ponderado (CA e Mechanics dominam no Late Game)
        base_score = weighted_average(
            values=[
                avg_ca / 200.0,                         # CA normalizado [0-1]
                normalize_attribute(avg_mechanics),     # Mecânica normalizada [0-1]
                normalize_attribute(avg_resilience),    # Resiliência normalizada [0-1]
            ],
            weights=[0.40, 0.35, 0.25],
        )
        
        # Multiplicador do patch dos campeões draftados
        patch_multiplier = 1.0
        if champion_patch_meta and draft:
            total_damage = 0.0
            total_survivability = 0.0
            for item in draft:
                champ_name = item.get("champion", "")
                role = item.get("player_role", "")
                key = f"{champ_name.lower()}:{role.lower()}"
                stats = champion_patch_meta.get(key)
                
                # Se não encontrar, assume padrão 5.0 (escala 0-10)
                total_damage += stats.get("damage", 5.0) if stats else 5.0
                total_survivability += stats.get("survivability", 5.0) if stats else 5.0
                
            avg_damage = total_damage / len(draft)
            avg_survivability = total_survivability / len(draft)
            
            # No Late Game/Teamfights, dano vale 50% e sobrevivência vale 50%
            patch_multiplier = ((avg_damage / 5.0) * 0.5) + ((avg_survivability / 5.0) * 0.5)
        
        # Ruído estocástico — mais dramático no Late Game (menor redução de std) e patch
        tf_score = stochastic_roll(base_score, avg_consistency, rng) * patch_multiplier
        
        # --- Bônus de Big Match Aptitude (SOMENTE EM PLAYOFFS) ---
        if is_playoff:
            # BMA tem impacto máximo em partidas decisivas
            bma_normalized = normalize_attribute(avg_bma)
            bma_bonus = bma_normalized * 0.15  # Até +15% em playoffs
            tf_score += bma_bonus
            logger.debug(
                f"[LateGame] {team.name} BMA playoff bonus: "
                f"+{bma_bonus:.3f} (avg BMA: {avg_bma:.1f})"
            )
        
        # --- Bônus de objetivos ativos ---
        if any("dragon_soul" in buff for buff in active_buffs):
            tf_score += 0.08  # Dragon Soul: vantagem significativa de stats
        
        if "baron_empowered" in active_buffs:
            tf_score += 0.05  # Buff de Baron: pressão de empurrada
        
        return clamp(tf_score, 0.05, 1.50)
    
    def _calculate_match_duration(
        self,
        gold_diff: float,
        blue_wins: bool,
        blue_had_dragon_soul: bool,
        rng: np.random.Generator,
    ) -> float:
        """
        Estima a duração da partida em minutos baseada no desequilíbrio de ouro.
        
        Partidas com grande diferença de ouro tendem a terminar mais rápido.
        Dragon Soul pode acelerar o fechamento da partida.
        """
        if gold_diff > 10000:
            duration_range = MATCH_DURATION_RANGES["stomp"]
        elif gold_diff > 5000:
            duration_range = MATCH_DURATION_RANGES["decisive"]
        elif gold_diff > 2000:
            duration_range = MATCH_DURATION_RANGES["competitive"]
        else:
            # Partida muito equilibrada: pode ser épica
            epic_chance = 0.30
            if roll_check(epic_chance, rng):
                duration_range = MATCH_DURATION_RANGES["epic"]
            else:
                duration_range = MATCH_DURATION_RANGES["close"]
        
        duration = rng.uniform(*duration_range)
        
        # Dragon Soul acelera o fechamento (-3 a 5 minutos)
        if blue_had_dragon_soul:
            duration -= rng.uniform(3.0, 5.0)
            duration = max(duration, 20.0)
        
        return round(duration, 1)
