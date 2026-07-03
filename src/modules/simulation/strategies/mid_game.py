"""
Estratégia de Mid Game (Controle de Objetivos — 15 a 25 minutos).

Esta fase simula:
    - Disputa por dragões (acumulação de almas elementais)
    - Controle do Rift Herald e plantação de torres
    - Rotações e fights de 5v5 em torno de objetivos
    - Influência da vantagem do Early Game no resultado

Fórmula de Mid Game Score:
    team_score = teamwork_score * objective_control * scaling_factor
                 + early_advantage_bonus
                 + resilience_reversal_factor  (para o time perdedor)
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
)
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Objetivos do Mid Game e seus bônus de ouro
MID_GAME_OBJECTIVES = {
    "dragon_2": 1200,    # Segundo dragão (começa a criar stacks de alma)
    "dragon_3": 1400,    # Terceiro dragão (próximo da alma)
    "herald_tower": 800,  # Torre destruída com auxílio do Herald
    "mid_lane_tower": 600, # Torre central
    "outer_towers": 1800,  # Torres externas (3 torres × 600)
}

# Buffs de dragão e seus efeitos nos scores
DRAGON_SOUL_BUFFS = {
    "infernal": {"mechanics_bonus": 0.08},  # Aumenta dano
    "mountain": {"resilience_bonus": 0.06}, # Aumenta tanque
    "ocean":    {"focus_bonus": 0.05},      # Regen de recursos
    "cloud":    {"teamwork_bonus": 0.07},   # Velocidade de movimento
    "hextech":  {"mechanics_bonus": 0.06, "teamwork_bonus": 0.04},  # Dano + utilidade
    "chemtech": {"resilience_bonus": 0.05, "focus_bonus": 0.04},    # Sustain
}


class MidGameStrategy(MatchPhaseStrategy):
    """
    Estratégia de Mid Game (Controle de Objetivos).
    
    Usa os resultados do Early Game como base (vantagem de ouro),
    calcula rotações em torno de objetivos e teamfights 5v5 iniciais.
    """
    
    def get_phase_name(self) -> str:
        return "MID_GAME"
    
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
        Calcula o Mid Game a partir do estado do Early Game.
        """
        logger.info(
            f"[MidGame] Calculando Mid Game: {blue_team.name} vs {red_team.name} | "
            f"Playoff: {is_playoff}"
        )
        
        phase_log = []
        
        # Inicializa estados com ouro do early game
        early_gold_diff = previous_result.gold_difference if previous_result else 0.0
        blue_base_gold = previous_result.blue_state.gold_earned if previous_result else 8000
        red_base_gold = previous_result.red_state.gold_earned if previous_result else 8000
        
        blue_state = TeamMatchState(
            team_id=str(blue_team.id),
            team_name=blue_team.name,
            gold_earned=blue_base_gold,
        )
        red_state = TeamMatchState(
            team_id=str(red_team.id),
            team_name=red_team.name,
            gold_earned=red_base_gold,
        )
        
        # Log do estado herdado do Early Game
        phase_log.append(
            f"📥 Herdado do Early: {blue_team.name} com {early_gold_diff:+.0f}g de vantagem."
        )
        
        # --- Etapa 1: Calcular teamwork e controle de objetivos ---
        blue_objective_score = self._calculate_objective_control_score(
            team=blue_team,
            rng=rng,
            is_playoff=is_playoff,
            draft=blue_draft,
            champion_patch_meta=champion_patch_meta,
        )
        red_objective_score = self._calculate_objective_control_score(
            team=red_team,
            rng=rng,
            is_playoff=is_playoff,
            draft=red_draft,
            champion_patch_meta=champion_patch_meta,
        )
        
        phase_log.append(
            f"🎯 Controle de Objetivos: {blue_team.name} {blue_objective_score:.3f} "
            f"vs {red_team.name} {red_objective_score:.3f}"
        )
        
        # --- Etapa 2: Fator de reversão (resiliência do time perdedor) ---
        reversal_log = self._apply_resilience_reversal(
            early_gold_diff=early_gold_diff,
            blue_team=blue_team,
            red_team=red_team,
            blue_state=blue_state,
            red_state=red_state,
            rng=rng,
            phase_log=phase_log,
        )
        
        # --- Etapa 3: Distribuição de objetivos do Mid Game ---
        blue_obj_ratio = blue_objective_score / (blue_objective_score + red_objective_score + 1e-9)
        
        for objective, gold_value in MID_GAME_OBJECTIVES.items():
            # Usa o score de objetivos ajustado pela vantagem de ouro
            adjusted_ratio = clamp(blue_obj_ratio + early_gold_diff / 20000, 0.10, 0.90)
            
            if rng.random() < adjusted_ratio:
                blue_state.gold_earned += gold_value
                blue_state.objectives_taken.append(objective)
                phase_log.append(
                    f"🏆 {blue_team.name} (Blue) → {objective.replace('_', ' ').title()}"
                )
            else:
                red_state.gold_earned += gold_value
                red_state.objectives_taken.append(objective)
                phase_log.append(
                    f"🏆 {red_team.name} (Red) → {objective.replace('_', ' ').title()}"
                )
        
        # --- Etapa 4: Simulação de Dragon Soul ---
        dragon_soul_log = self._simulate_dragon_soul(
            blue_state=blue_state,
            red_state=red_state,
            blue_objectives_count=len(blue_state.objectives_taken),
            red_objectives_count=len(red_state.objectives_taken),
            rng=rng,
        )
        phase_log.extend(dragon_soul_log)
        
        # --- Etapa 5: Kills no Mid Game ---
        total_mid_kills = int(rng.integers(5, 12))
        mid_kill_ratio = blue_obj_ratio
        blue_mid_kills = int(total_mid_kills * mid_kill_ratio)
        red_mid_kills = total_mid_kills - blue_mid_kills
        
        blue_state.kills = (previous_result.blue_state.kills if previous_result else 0) + blue_mid_kills
        blue_state.deaths = (previous_result.blue_state.deaths if previous_result else 0) + red_mid_kills
        red_state.kills = (previous_result.red_state.kills if previous_result else 0) + red_mid_kills
        red_state.deaths = (previous_result.red_state.deaths if previous_result else 0) + blue_mid_kills
        
        # Score de fase
        blue_state.phase_score = blue_objective_score
        red_state.phase_score = red_objective_score
        
        gold_difference = blue_state.gold_earned - red_state.gold_earned
        score_difference = blue_state.phase_score - red_state.phase_score
        
        leading = blue_team.name if gold_difference > 0 else red_team.name
        phase_log.append(
            f"📊 Mid Game encerrado: {leading} lidera com {abs(gold_difference):.0f}g | "
            f"Kills totais: {blue_state.kills}-{red_state.kills}"
        )
        
        logger.info(
            f"[MidGame] Resultado: Gold diff {gold_difference:+.0f}g | "
            f"Obj Blue: {len(blue_state.objectives_taken)} | "
            f"Obj Red: {len(red_state.objectives_taken)}"
        )
        
        return PhaseResult(
            phase_name=self.get_phase_name(),
            blue_state=blue_state,
            red_state=red_state,
            gold_difference=gold_difference,
            score_difference=score_difference,
            phase_log=phase_log,
        )
    
    def _calculate_objective_control_score(
        self,
        team,
        rng: np.random.Generator,
        is_playoff: bool,
        draft: List[dict],
        champion_patch_meta: Optional[dict] = None,
    ) -> float:
        """
        Calcula o score de controle de objetivos de um time.
        Incorpora os multiplicadores de utilidade e sobrevivência dos campeões draftados no patch.
        """
        starters = team.get_starters()
        if not starters:
            return 0.1
        
        # Calcula médias dos atributos dos titulares
        avg_teamwork = sum(p.teamwork for p in starters) / len(starters)
        avg_focus = sum(p.focus for p in starters) / len(starters)
        avg_ca = sum(p.current_ability for p in starters) / len(starters)
        avg_consistency = sum(p.consistency for p in starters) / len(starters)
        
        # Score base ponderado (teamwork > focus > CA nesta fase)
        base_score = weighted_average(
            values=[
                normalize_attribute(avg_teamwork),        # 0-1
                normalize_attribute(avg_focus),           # 0-1
                avg_ca / 200.0,                          # 0-1
            ],
            weights=[0.40, 0.30, 0.30],
        )
        
        # Multiplicador do patch dos campeões draftados
        patch_multiplier = 1.0
        if champion_patch_meta and draft:
            total_utility = 0.0
            total_survivability = 0.0
            for item in draft:
                champ_name = item.get("champion", "")
                role = item.get("player_role", "")
                key = f"{champ_name.lower()}:{role.lower()}"
                stats = champion_patch_meta.get(key)
                
                # Se não encontrar, assume padrão 5.0 (escala 0-10)
                total_utility += stats.get("utility", 5.0) if stats else 5.0
                total_survivability += stats.get("survivability", 5.0) if stats else 5.0
                
            avg_utility = total_utility / len(draft)
            avg_survivability = total_survivability / len(draft)
            
            # No Mid Game, utilidade vale 60% e sobrevivência vale 40%
            patch_multiplier = ((avg_utility / 5.0) * 0.6) + ((avg_survivability / 5.0) * 0.4)
        
        # Ruído estocástico controlado pela consistência média e patch
        objective_score = stochastic_roll(base_score, avg_consistency, rng) * patch_multiplier
        
        # Bônus de Big Match Aptitude em playoffs
        if is_playoff:
            avg_bma = sum(p.big_match_aptitude for p in starters) / len(starters)
            bma_bonus = normalize_attribute(avg_bma) * 0.08
            objective_score += bma_bonus
        
        return clamp(objective_score, 0.05, 1.20)
    
    def _apply_resilience_reversal(
        self,
        early_gold_diff: float,
        blue_team,
        red_team,
        blue_state: TeamMatchState,
        red_state: TeamMatchState,
        rng: np.random.Generator,
        phase_log: list,
    ) -> None:
        """
        Aplica o mecanismo de reversão baseado em Resiliência.
        
        Se um time está muito atrás no Early Game (>2000 de ouro),
        sua Resiliência pode gerar uma "virada" parcial.
        
        Fórmula do reversal:
            if abs(gold_diff) > 2000:
                reversal_chance = avg_resilience / 20 * 0.45
                if roll_check(reversal_chance):
                    losing_team gains 20-40% da diferença de ouro de volta
        """
        REVERSAL_GOLD_THRESHOLD = 2000
        
        if abs(early_gold_diff) < REVERSAL_GOLD_THRESHOLD:
            return  # Jogo equilibrado, sem reversão
        
        # Identifica o time perdedor
        losing_team = blue_team if early_gold_diff < 0 else red_team
        losing_state = blue_state if early_gold_diff < 0 else red_state
        winning_state = red_state if early_gold_diff < 0 else blue_state
        
        starters = losing_team.get_starters()
        avg_resilience = sum(p.resilience for p in starters) / len(starters) if starters else 10
        
        # Probabilidade de reversão baseada na resiliência
        reversal_chance = normalize_attribute(avg_resilience) * 0.45
        
        if roll_check(reversal_chance, rng):
            # Reversão bem-sucedida!
            reversal_percentage = rng.uniform(0.20, 0.40)
            reversal_gold = abs(early_gold_diff) * reversal_percentage
            
            losing_state.gold_earned += reversal_gold
            losing_state.active_buffs.append("resilience_reversal")
            
            phase_log.append(
                f"💪 REVERSÃO! {losing_team.name} usou a Resiliência do time para "
                f"recuperar {reversal_gold:.0f}g da desvantagem! "
                f"(Resiliência: {avg_resilience:.1f}, Chance: {reversal_chance:.0%})"
            )
            logger.info(
                f"[MidGame] Reversão ativada para {losing_team.name}: +{reversal_gold:.0f}g"
            )
        else:
            phase_log.append(
                f"😔 {losing_team.name} tentou reagir mas não conseguiu reverter. "
                f"(Resiliência: {avg_resilience:.1f}, Chance: {reversal_chance:.0%})"
            )
    
    def _simulate_dragon_soul(
        self,
        blue_state: TeamMatchState,
        red_state: TeamMatchState,
        blue_objectives_count: int,
        red_objectives_count: int,
        rng: np.random.Generator,
    ) -> list[str]:
        """
        Simula se algum time atingiu a Alma do Dragão no Mid Game.
        3 dragões = alma, bônus significativo para o Late Game.
        """
        log = []
        dragon_types = list(DRAGON_SOUL_BUFFS.keys())
        
        # Time com mais objetivos tem mais dragões
        blue_dragons = min(blue_objectives_count, 3)
        red_dragons = min(red_objectives_count, 3)
        
        if blue_dragons >= 3:
            soul_type = rng.choice(dragon_types)
            blue_state.active_buffs.append(f"dragon_soul_{soul_type}")
            log.append(
                f"🐉 ALMA DO DRAGÃO! {blue_state.team_name} conquistou a "
                f"Alma {soul_type.title()}! Bônus permanente para o Late Game."
            )
        
        if red_dragons >= 3:
            soul_type = rng.choice(dragon_types)
            red_state.active_buffs.append(f"dragon_soul_{soul_type}")
            log.append(
                f"🐉 ALMA DO DRAGÃO! {red_state.team_name} conquistou a "
                f"Alma {soul_type.title()}! Bônus permanente para o Late Game."
            )
        
        return log
