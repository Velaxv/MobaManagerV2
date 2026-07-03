"""
Estratégia de Early Game (Fase de Rotas — 0 a 15 minutos).

Esta fase simula:
    - Confrontos 1v1 de laning por posição (TOP, JG, MID, BOT, SUP)
    - Evento de Coach Comms: treinador tenta reverter tilt de draft ruim
    - Cálculo de vantagem de ouro das rotas
    - Primeiros objetivos: Rift Herald e Primeiro Dragão

Fórmula de Lane Score por jogador:
    lane_score = calculate_player_rating(CA, mechanics, focus, burnout)
                 * champion_pool_multiplier
                 * stochastic_noise(consistency)
                 * visual_fatigue_multiplier
"""

import logging
from typing import List, Optional
import numpy as np

from src.modules.simulation.strategies.base import (
    MatchPhaseStrategy,
    PhaseResult,
    TeamMatchState,
)
from src.modules.simulation.champion_pool_validator import ChampionPoolValidator
from src.modules.simulation.coach_comms import CoachCommsEngine, CoachCommsSession
from src.shared.math_utils import (
    calculate_player_rating,
    stochastic_roll,
    clamp,
    normalize_attribute,
)
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Pesos por posição na fase de laning (soma = 1.0)
# JG e MID têm mais impacto no early game
LANE_WEIGHTS = {
    "TOP":     0.17,
    "JUNGLE":  0.23,
    "MID":     0.25,
    "BOT":     0.20,
    "SUPPORT": 0.15,
}

# Objetivos do Early Game e seus bônus de ouro
EARLY_OBJECTIVES = {
    "first_dragon":       1200,   # Alma de dragão prioridade no início
    "rift_herald":        1500,   # Precursor do Baron
    "first_tower":        500,    # Primeira torre + bônus global de 400
    "first_blood":        400,    # Assassinato inaugural da partida
}


class EarlyGameStrategy(MatchPhaseStrategy):
    """
    Estratégia de Early Game (Fase de Rotas).
    
    Calcula o desempenho individual de cada jogador nas rotas,
    aplica o evento de Coach Comms e determina a vantagem inicial.
    """
    
    def __init__(self):
        self.pool_validator = ChampionPoolValidator()
        self.comms_engine = CoachCommsEngine()
    
    def get_phase_name(self) -> str:
        return "EARLY_GAME"
    
    def calculate(
        self,
        blue_team,
        red_team,
        blue_draft: List[dict],
        red_draft: List[dict],
        rng: np.random.Generator,
        previous_result: Optional[PhaseResult] = None,
        is_playoff: bool = False,
        # Parâmetros específicos do Early Game
        blue_coach_comms: int = 0,       # Número de coach comms enviados pelo Blue
        red_coach_comms: int = 0,        # Número de coach comms enviados pelo Red
        blue_draft_penalty: float = 0.0, # Penalidade por draft ruim (0.0 a 1.0)
        red_draft_penalty: float = 0.0,  # Penalidade por draft ruim (0.0 a 1.0)
        champion_patch_meta: Optional[dict] = None, # Status dos campeões modificados pelo patch
        **kwargs,
    ) -> PhaseResult:
        """
        Executa a simulação do Early Game.
        """
        logger.info(
            f"[EarlyGame] Iniciando simulação: {blue_team.name} (Blue) "
            f"vs {red_team.name} (Red)"
        )
        
        # Inicializa estados dos times
        blue_state = TeamMatchState(
            team_id=str(blue_team.id),
            team_name=blue_team.name,
        )
        red_state = TeamMatchState(
            team_id=str(red_team.id),
            team_name=red_team.name,
        )
        phase_log = []
        
        # Dicionários de debuffs de foco por jogador aplicados na partida
        blue_focus_debuffs = {}
        red_focus_debuffs = {}
        
        # --- Etapa 1: Processar Coach Comms ---
        blue_draft_penalty = self._process_coach_comms(
            team=blue_team,
            session=self.comms_engine.create_session(blue_team.name),
            num_comms=blue_coach_comms,
            draft_penalty=blue_draft_penalty,
            rng=rng,
            phase_log=phase_log,
            player_focus_debuffs=blue_focus_debuffs,
        )
        red_draft_penalty = self._process_coach_comms(
            team=red_team,
            session=self.comms_engine.create_session(red_team.name),
            num_comms=red_coach_comms,
            draft_penalty=red_draft_penalty,
            rng=rng,
            phase_log=phase_log,
            player_focus_debuffs=red_focus_debuffs,
        )
        
        # --- Etapa 2: Emparelhar jogadores com campeões ---
        blue_pairs = self._get_starters_with_champions(blue_team, blue_draft)
        red_pairs = self._get_starters_with_champions(red_team, red_draft)
        
        # --- Etapa 3: Calcular lane scores por posição ---
        role_names = ["TOP", "JUNGLE", "MID", "BOT", "SUPPORT"]
        
        blue_lane_total = 0.0
        red_lane_total = 0.0
        
        for i, role in enumerate(role_names):
            if i >= len(blue_pairs) or i >= len(red_pairs):
                break
            
            blue_player, blue_champion = blue_pairs[i]
            red_player, red_champion = red_pairs[i]
            weight = LANE_WEIGHTS[role]
            
            # Obtém status do patch para cada campeão/role
            blue_champ_key = f"{blue_champion.lower()}:{role.lower()}"
            red_champ_key = f"{red_champion.lower()}:{role.lower()}"
            
            blue_patch_stats = champion_patch_meta.get(blue_champ_key) if champion_patch_meta else None
            red_patch_stats = champion_patch_meta.get(red_champ_key) if champion_patch_meta else None
            
            # Calcula score individual de cada jogador na rota (injetando debuff de foco e patch meta)
            blue_score = self._calculate_lane_score(
                player=blue_player,
                champion=blue_champion,
                draft_penalty=blue_draft_penalty,
                is_playoff=is_playoff,
                rng=rng,
                focus_debuff=blue_focus_debuffs.get(str(blue_player.id), 0.0),
                champion_patch_stats=blue_patch_stats,
            )
            red_score = self._calculate_lane_score(
                player=red_player,
                champion=red_champion,
                draft_penalty=red_draft_penalty,
                is_playoff=is_playoff,
                rng=rng,
                focus_debuff=red_focus_debuffs.get(str(red_player.id), 0.0),
                champion_patch_stats=red_patch_stats,
            )
            
            # Acumula scores ponderados
            blue_lane_total += blue_score * weight
            red_lane_total += red_score * weight
            
            # Log de confronto de rota
            winner = blue_player.name if blue_score > red_score else red_player.name
            margin = abs(blue_score - red_score)
            lane_log = (
                f"[{role}] {blue_player.name} ({blue_champion}) "
                f"{'🔵' if blue_score > red_score else '🔴'} "
                f"vs {red_player.name} ({red_champion}) | "
                f"Winner: {winner} (+{margin:.3f})"
            )
            phase_log.append(lane_log)
            logger.debug(lane_log)
        
        # Score bruto de fase
        blue_state.phase_score = blue_lane_total
        red_state.phase_score = red_lane_total
        
        # --- Etapa 4: Distribui kills e ouro base das rotas ---
        total_early_gold = 8000  # Ouro base distribuído no early game (por time)
        score_ratio_blue = blue_lane_total / (blue_lane_total + red_lane_total + 1e-9)
        
        blue_state.gold_earned = total_early_gold * score_ratio_blue
        red_state.gold_earned = total_early_gold * (1 - score_ratio_blue)
        
        # Kills estimadas (early game ~8-15 kills totais)
        total_early_kills = int(rng.integers(6, 15))
        blue_kills = int(total_early_kills * score_ratio_blue)
        red_kills = total_early_kills - blue_kills
        blue_state.kills = blue_kills
        blue_state.deaths = red_kills
        red_state.kills = red_kills
        red_state.deaths = blue_kills
        
        # --- Etapa 5: Distribuição de objetivos do Early Game ---
        objective_log = self._distribute_early_objectives(
            blue_state=blue_state,
            red_state=red_state,
            score_ratio_blue=score_ratio_blue,
            rng=rng,
        )
        phase_log.extend(objective_log)
        
        # Diferença final de ouro
        gold_difference = blue_state.gold_earned - red_state.gold_earned
        score_difference = blue_state.phase_score - red_state.phase_score
        
        leading = blue_team.name if gold_difference > 0 else red_team.name
        phase_log.append(
            f"📊 Early Game encerrado: {leading} com vantagem de "
            f"{abs(gold_difference):.0f} de ouro e "
            f"{blue_state.kills}-{red_state.kills} em kills."
        )
        
        logger.info(
            f"[EarlyGame] Resultado: {blue_team.name} {blue_state.gold_earned:.0f}g "
            f"vs {red_team.name} {red_state.gold_earned:.0f}g | "
            f"Gold diff: {gold_difference:+.0f}"
        )
        
        return PhaseResult(
            phase_name=self.get_phase_name(),
            blue_state=blue_state,
            red_state=red_state,
            gold_difference=gold_difference,
            score_difference=score_difference,
            phase_log=phase_log,
        )
    
    def _calculate_lane_score(
        self,
        player,
        champion: str,
        draft_penalty: float,
        is_playoff: bool,
        rng: np.random.Generator,
    ) -> float:
        """
        Calcula o score de um jogador na sua rota para o Early Game.
        
        Fórmula:
            base_rating = calculate_player_rating(CA, mechanics, focus, burnout)
            pool_multiplier = champion_pool_validator(player, champion)
            visual_multiplier = _visual_fatigue_debuff(visual_fatigue)
            noise = stochastic_roll(1.0, consistency, rng)
            draft_factor = 1 - draft_penalty
            score = base_rating * pool_multiplier * visual_multiplier * noise * draft_factor
        """
    def _calculate_lane_score(
        self,
        player,
        champion: str,
        draft_penalty: float,
        is_playoff: bool,
        rng: np.random.Generator,
        focus_debuff: float = 0.0,
        champion_patch_stats: Optional[dict] = None,
    ) -> float:
        """
        Calcula o score de rota de um jogador individual considerando:
            - rating base (CA, mecânica, foco efetivo [foco - focus_debuff], burnout)
            - pool de campeões do jogador
            - fadiga visual
            - playoffs
            - penalidade de draft
            - modificadores do patch do campeão
        """
        # Rating base do jogador deduzindo o debuff de foco da partida
        effective_focus = max(1.0, player.focus - focus_debuff)
        base_rating = calculate_player_rating(
            current_ability=player.current_ability,
            mechanics=player.mechanics,
            focus=effective_focus,
            burnout_meter=player.burnout_meter,
        )
        
        # Validação do champion pool → multiplicador de mecânica
        pool_result = self.pool_validator.validate(player, champion)
        pool_multiplier = pool_result.mechanics_multiplier
        
        # Debuff de fadiga visual
        visual_multiplier = self._calculate_visual_fatigue_multiplier(player.visual_fatigue)
        
        # Ruído estocástico controlado pela consistência do jogador
        noisy_rating = stochastic_roll(base_rating, player.consistency, rng)
        
        # Bônus de big match aptitude em playoffs (oculto ao jogador)
        playoff_bonus = 1.0
        if is_playoff:
            bma_normalized = normalize_attribute(player.big_match_aptitude)
            playoff_bonus = 1.0 + bma_normalized * 0.10  # Até +10% em playoffs
        
        # Penalidade de draft (reduzida por Coach Comms)
        draft_factor = 1.0 - clamp(draft_penalty, 0.0, 0.40)
        
        # Multiplicador do patch do campeão (dano vale 70% e utilidade 30% na rota)
        patch_multiplier = 1.0
        if champion_patch_stats:
            dmg_factor = champion_patch_stats.get("damage", 5.0) / 5.0
            utl_factor = champion_patch_stats.get("utility", 5.0) / 5.0
            patch_multiplier = (dmg_factor * 0.7) + (utl_factor * 0.3)
        
        # Score final da rota
        final_score = (
            noisy_rating
            * pool_multiplier
            * visual_multiplier
            * playoff_bonus
            * draft_factor
            * patch_multiplier
        )
        
        return clamp(final_score, 0.01, 1.5)
    
    def _calculate_visual_fatigue_multiplier(self, visual_fatigue: float) -> float:
        """
        Calcula o multiplicador por fadiga visual.
        Fadiga ≤ 70: sem debuff (1.0)
        Fadiga > 70: redução linear até 0.75 em fadiga 100
        """
        threshold = settings.visual_fatigue_mechanics_debuff_threshold  # 70
        if visual_fatigue <= threshold:
            return 1.0
        excess = visual_fatigue - threshold
        debuff = (excess / 30.0) * 0.25
        return clamp(1.0 - debuff, 0.75, 1.0)
    
    def _process_coach_comms(
        self,
        team,
        session: CoachCommsSession,
        num_comms: int,
        draft_penalty: float,
        rng: np.random.Generator,
        phase_log: list,
        player_focus_debuffs: dict,
    ) -> float:
        """
        Processa as comunicações do treinador e retorna a penalidade de draft ajustada.
        Incorpora atributos de comunicação do Head Coach e debuffs de foco no jogador.
        """
        if num_comms == 0:
            return draft_penalty
        
        # Obtém o Head Coach do relacionamento staffs do time
        head_coach = next((s for s in team.staffs if s.role == "HEAD_COACH"), None)
        coach_comm_attr = head_coach.communication if head_coach else 10.0
        
        if head_coach:
            phase_log.append(f"👨‍🏫 {team.name} Head Coach: {head_coach.name} orientando a equipe (Comunicação: {head_coach.communication:.1f})")
        
        # Usa o RNG controlado para as comunicações
        comms_engine = CoachCommsEngine(rng=rng)
        starters = team.get_starters()
        
        for comm_idx in range(num_comms):
            # Comunica com o jogador de maior coachability (melhor receptor)
            target_player = max(
                starters, 
                key=lambda p: p.coachability + p.teamwork,
                default=None
            )
            if not target_player:
                break
            
            result = comms_engine.process_comm(
                player=target_player,
                session=session,
                draft_penalty_active=(draft_penalty > 0),
                coach_communication=coach_comm_attr,
            )
            
            if result.confusion_triggered:
                # Acumula o debuff de foco para o jogador
                player_focus_debuffs[str(target_player.id)] = player_focus_debuffs.get(str(target_player.id), 0.0) + result.focus_debuff
                
            phase_log.append(f"📣 {team.name} Coach Comm #{comm_idx + 1}: {result.message}")
        
        # Retorna a penalidade reduzida pelas comms bem-sucedidas
        reduced_penalty = draft_penalty * session.effective_draft_penalty_factor
        
        # Aplica penalidade de foco por confusão mental (se houver)
        if session.cumulative_focus_debuff > 0:
            phase_log.append(
                f"⚠️  {team.name}: Confusão mental acumulada! "
                f"Foco total reduzido em {session.cumulative_focus_debuff:.1f} pontos na partida."
            )
        
        return reduced_penalty
    
    def _distribute_early_objectives(
        self,
        blue_state: TeamMatchState,
        red_state: TeamMatchState,
        score_ratio_blue: float,
        rng: np.random.Generator,
    ) -> list[str]:
        """
        Distribui os objetivos do early game baseado no score de cada time.
        Cada objetivo tem uma probabilidade determinada pelo score ratio,
        com alguma aleatoriedade (RNG).
        """
        log = []
        
        for objective, gold_value in EARLY_OBJECTIVES.items():
            # Probabilidade proporcional ao score do Blue, com ruído
            blue_prob = clamp(score_ratio_blue + rng.uniform(-0.10, 0.10), 0.1, 0.9)
            
            if rng.random() < blue_prob:
                blue_state.gold_earned += gold_value
                blue_state.objectives_taken.append(objective)
                blue_state.active_buffs.append(objective)
                log.append(f"🏆 {blue_state.team_name} (Blue) conquistou: {objective.replace('_', ' ').title()}")
            else:
                red_state.gold_earned += gold_value
                red_state.objectives_taken.append(objective)
                red_state.active_buffs.append(objective)
                log.append(f"🏆 {red_state.team_name} (Red) conquistou: {objective.replace('_', ' ').title()}")
        
        return log
