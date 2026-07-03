import pytest
from src.modules.draft.draft_analyzer import DraftAnalyzer
from src.shared.enums import ClassType, DamageType

class MockChampion:
    """Mock simples de Champion para evitar bater no banco SQLite nos testes unitários."""
    def __init__(self, name: str, class_type: str, damage_type: str, early: int, late: int):
        self.name = name
        self.class_type = class_type
        self.damage_type = damage_type
        self.early_game_power = early
        self.late_game_scaling = late

def test_draft_analyzer_balanced_comp():
    analyzer = DraftAnalyzer()
    
    # Comp equilibrada: 3 AP, 2 AD. Possui frontline (Ornn e Lee Sin). Curva focada em Scaling.
    champions = [
        MockChampion("Ornn", ClassType.TANK_ENGAGE.value, DamageType.AP.value, 40, 90),
        MockChampion("Lee Sin", ClassType.BRUISER.value, DamageType.AD.value, 90, 40),
        MockChampion("Orianna", ClassType.MAGE_CONTROL.value, DamageType.AP.value, 50, 85),
        MockChampion("Jinx", ClassType.MARKSMAN_HYPERCARRY.value, DamageType.AD.value, 35, 95),
        MockChampion("Thresh", ClassType.TANK_ENGAGE.value, DamageType.AP.value, 70, 60),
    ]
    
    result = analyzer.analyze_composition(champions)
    
    # Balanço de Dano
    assert result["damage_balance"]["is_balanced"] is True
    assert result["damage_balance"]["damage_classification"] == "BALANCED"
    assert result["damage_balance"]["damage_penalty"] == 0.0
    
    # Frontline
    assert result["frontline"]["has_frontline"] is True
    assert result["frontline"]["frontline_count"] == 3  # Ornn, Lee Sin, Thresh
    assert result["frontline"]["survivability_penalty"] == 0.0
    
    # Curva de Poder (Média Early: 57.0 | Média Late: 74.0) -> SCALING
    assert result["power_curve"]["archetype"] == "SCALING"
    assert result["power_curve"]["average_early_power"] == 57.0
    assert result["power_curve"]["average_late_scaling"] == 74.0

def test_draft_analyzer_full_ad_no_frontline():
    analyzer = DraftAnalyzer()
    
    # Comp desbalanceada: 5 AD, sem frontline (todos assassinos/marksmen de papel)
    champions = [
        MockChampion("Zed", ClassType.ASSASSIN.value, DamageType.AD.value, 75, 70),
        MockChampion("Talon", ClassType.ASSASSIN.value, DamageType.AD.value, 85, 50),
        MockChampion("Yasuo", ClassType.ASSASSIN.value, DamageType.AD.value, 50, 85),
        MockChampion("Jinx", ClassType.MARKSMAN_HYPERCARRY.value, DamageType.AD.value, 35, 95),
        MockChampion("Ashe", ClassType.MARKSMAN_UTILITY.value, DamageType.AD.value, 70, 70),
    ]
    
    result = analyzer.analyze_composition(champions)
    
    # Balanço de Dano
    assert result["damage_balance"]["is_balanced"] is False
    assert result["damage_balance"]["damage_classification"] == "FULL_AD"
    assert result["damage_balance"]["damage_penalty"] == 0.15
    
    # Frontline
    assert result["frontline"]["has_frontline"] is False
    assert result["frontline"]["frontline_count"] == 0
    assert result["frontline"]["survivability_penalty"] == 0.15
    
    # Curva de Poder (Média Early: 60.0 | Média Late: 74.0) -> SCALING
    assert result["power_curve"]["archetype"] == "SCALING"

def test_draft_analyzer_snowball_comp():
    analyzer = DraftAnalyzer()
    
    # Comp Snowball: Média Early: 82.0 | Média Late: 47.0 (Diferença > 5.0) -> SNOWBALL
    champions = [
        MockChampion("Renekton", ClassType.BRUISER.value, DamageType.AD.value, 85, 45),
        MockChampion("Elise", ClassType.ASSASSIN.value, DamageType.AP.value, 95, 35),
        MockChampion("Ahri", ClassType.MAGE_BURST.value, DamageType.AP.value, 70, 65),
        MockChampion("Ashe", ClassType.MARKSMAN_UTILITY.value, DamageType.AD.value, 70, 70),
        MockChampion("Thresh", ClassType.TANK_ENGAGE.value, DamageType.AP.value, 90, 20),
    ]
    
    result = analyzer.analyze_composition(champions)
    
    assert result["power_curve"]["archetype"] == "SNOWBALL"
    assert result["power_curve"]["average_early_power"] == 82.0
    assert result["power_curve"]["average_late_scaling"] == 47.0
