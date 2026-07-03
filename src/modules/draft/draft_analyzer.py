import logging
from typing import List, Dict, Any
from src.models.champion import Champion
from src.shared.enums import DamageType, ClassType

logger = logging.getLogger(__name__)

class DraftAnalyzer:
    """
    Serviço responsável por analisar a composição de campeões (5 picks) de um time,
    avaliando o balanço de dano, presença de frontline e a curva de poder (snowball vs scaling).
    """
    
    def analyze_composition(self, champions: List[Champion]) -> Dict[str, Any]:
        """
        Recebe uma lista de 5 instâncias de Champion e retorna o relatório detalhado da composição.
        
        Fórmulas de penalidade:
        - Full AD / Full AP (>= 4 do mesmo tipo): 15% de penalidade de dano (damage_penalty = 0.15)
        - Sem Frontline (0 tanks/bruisers): 15% de penalidade de sobrevivência (survivability_penalty = 0.15)
        """
        if not champions or len(champions) != 5:
            raise ValueError("Uma composição completa de equipe deve conter exatamente 5 campeões.")
            
        # 1. Balanço de Dano
        ad_count = sum(1 for c in champions if c.damage_type == DamageType.AD)
        ap_count = sum(1 for c in champions if c.damage_type == DamageType.AP)
        
        is_balanced = True
        damage_penalty = 0.0
        damage_classification = "BALANCED"
        
        if ad_count >= 4:
            is_balanced = False
            damage_penalty = 0.15
            damage_classification = "FULL_AD"
        elif ap_count >= 4:
            is_balanced = False
            damage_penalty = 0.15
            damage_classification = "FULL_AP"
            
        # 2. Presença de Frontline
        # Frontline definida por TANK_ENGAGE, TANK_WARDEN ou BRUISER
        frontline_classes = {
            ClassType.TANK_ENGAGE.value, 
            ClassType.TANK_WARDEN.value, 
            ClassType.BRUISER.value,
            # Também aceita enums puras se comparado diretamente
            ClassType.TANK_ENGAGE, 
            ClassType.TANK_WARDEN, 
            ClassType.BRUISER
        }
        
        frontline_count = sum(1 for c in champions if c.class_type in frontline_classes)
        has_frontline = frontline_count >= 1
        survivability_penalty = 0.0 if has_frontline else 0.15
        
        # 3. Curva de Poder
        early_game_sum = sum(c.early_game_power for c in champions)
        late_game_sum = sum(c.late_game_scaling for c in champions)
        
        avg_early = early_game_sum / 5.0
        avg_late = late_game_sum / 5.0
        
        # Composição Snowball, Scaling ou Equilibrada
        if avg_early > avg_late + 5.0:
            power_curve = "SNOWBALL"
        elif avg_late > avg_early + 5.0:
            power_curve = "SCALING"
        else:
            power_curve = "BALANCED"
            
        logger.info(
            f"[DraftAnalyzer] Comp analisada | "
            f"Dano: {damage_classification} (AD: {ad_count}, AP: {ap_count}) | "
            f"Frontline: {has_frontline} (tanks/bruisers: {frontline_count}) | "
            f"Curva: {power_curve} (Early: {avg_early:.1f}, Late: {avg_late:.1f})"
        )
            
        return {
            "damage_balance": {
                "is_balanced": is_balanced,
                "damage_classification": damage_classification,
                "ad_count": ad_count,
                "ap_count": ap_count,
                "damage_penalty": damage_penalty
            },
            "frontline": {
                "has_frontline": has_frontline,
                "frontline_count": frontline_count,
                "survivability_penalty": survivability_penalty
            },
            "power_curve": {
                "archetype": power_curve,
                "average_early_power": round(avg_early, 1),
                "average_late_scaling": round(avg_late, 1)
            }
        }
