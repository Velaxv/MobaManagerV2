"""
Match Engine Principal — Orquestrador do Motor de Simulação.

Coordena as 3 fases do jogo usando o padrão Strategy:
    1. EarlyGameStrategy  → Fase de Rotas (0-15min)
    2. MidGameStrategy    → Controle de Objetivos (15-25min)
    3. LateGameStrategy   → Teamfights e Fechamento (25+min)

Fluxo completo de uma partida:
    Draft → Early → Mid → Late → Resultado Final

O MatchEngine é o único ponto de entrada para simular uma partida.
Retorna um MatchResult completo com logs de cada fase e todos os dados
necessários para persistência no banco.
"""

import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import numpy as np

from src.modules.simulation.strategies.base import PhaseResult
from src.modules.simulation.strategies.early_game import EarlyGameStrategy
from src.modules.simulation.strategies.mid_game import MidGameStrategy
from src.modules.simulation.strategies.late_game import LateGameStrategy
from src.modules.simulation.tactics import apply_style_to_phase_result, normalize_style
from src.shared.enums import MatchResult
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class MatchInput:
    """
    Dados de entrada para simular uma partida.
    Encapsula tudo que o MatchEngine precisa para rodar a simulação.
    """
    blue_team: Any           # Instância do modelo Team com jogadores carregados
    red_team: Any            # Instância do modelo Team com jogadores carregados
    blue_draft: List[dict]   # Lista de {champion: str, player_role: str} do Blue Side
    red_draft: List[dict]    # Lista de {champion: str, player_role: str} do Red Side
    
    # Parâmetros de contexto
    is_playoff: bool = False
    match_id: Optional[str] = None
    
    # Parâmetros de Coach Comms (decisão do gerente antes da partida)
    blue_coach_comms: int = 0   # Número de comunicações do coach do Blue (0-6)
    red_coach_comms: int = 0    # Número de comunicações do coach do Red (0-6)
    
    # Penalidades de draft (calculadas pela análise do draft)
    blue_draft_penalty: float = 0.0  # 0.0 a 1.0
    red_draft_penalty: float = 0.0   # 0.0 a 1.0

    # Táticas pré-partida (estilo Early/Mid/Late)
    blue_game_style: str = "BALANCED"
    red_game_style: str = "BALANCED"
    
    # Modificadores de status por campeão do patch ativo
    champion_patch_meta: Optional[dict] = None
    
    # Seed para reproducibilidade (None = aleatório)
    random_seed: Optional[int] = None


@dataclass
class MatchSimulationResult:
    """
    Resultado completo de uma simulação de partida.
    Contém todos os dados para persistência e visualização.
    """
    match_id: str
    
    # Times
    blue_team_id: str
    blue_team_name: str
    red_team_id: str
    red_team_name: str
    
    # Resultado final
    winner_team_id: str
    winner_side: str          # "BLUE" ou "RED"
    blue_result: MatchResult
    red_result: MatchResult
    
    # Estatísticas
    match_duration_minutes: float
    blue_win_probability: float
    total_kills_blue: int
    total_kills_red: int
    final_gold_diff: float
    
    # Logs detalhados por fase (para persistir no banco)
    draft_log: dict = field(default_factory=dict)
    early_game_log: dict = field(default_factory=dict)
    mid_game_log: dict = field(default_factory=dict)
    late_game_log: dict = field(default_factory=dict)
    
    # Narrativa completa da partida
    full_narrative: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Serializa para dict (usado no cache Redis e persistência no banco)."""
        return {
            "match_id": self.match_id,
            "blue_team_id": self.blue_team_id,
            "blue_team_name": self.blue_team_name,
            "red_team_id": self.red_team_id,
            "red_team_name": self.red_team_name,
            "winner_team_id": self.winner_team_id,
            "winner_side": self.winner_side,
            "blue_result": self.blue_result.value,
            "red_result": self.red_result.value,
            "match_duration_minutes": self.match_duration_minutes,
            "blue_win_probability": round(self.blue_win_probability, 4),
            "total_kills_blue": self.total_kills_blue,
            "total_kills_red": self.total_kills_red,
            "final_gold_diff": round(self.final_gold_diff, 0),
            "draft_log": self.draft_log,
            "early_game_log": self.early_game_log,
            "mid_game_log": self.mid_game_log,
            "late_game_log": self.late_game_log,
        }


class MatchEngine:
    """
    Motor de Simulação de Partidas do LoL Manager.
    
    Implementa o padrão Strategy para separar o cálculo em 3 fases independentes.
    Cada fase recebe o resultado da anterior, criando uma cadeia de estados.
    
    Uso:
        engine = MatchEngine()
        result = engine.simulate(match_input)
    """
    
    def __init__(self):
        # Inicializa as 3 estratégias
        self._early_strategy = EarlyGameStrategy()
        self._mid_strategy = MidGameStrategy()
        self._late_strategy = LateGameStrategy()
        
        logger.info("[MatchEngine] Motor de simulação inicializado com 3 estratégias.")
    
    def simulate(self, match_input: MatchInput) -> MatchSimulationResult:
        """
        Executa a simulação completa de uma partida.
        
        Fluxo:
            1. Valida os inputs
            2. Inicializa o RNG com seed controlado
            3. Executa Early Game → captura PhaseResult
            4. Executa Mid Game com estado do Early → captura PhaseResult
            5. Executa Late Game com estado do Mid → determina vencedor
            6. Agrega resultados e retorna MatchSimulationResult
        
        Args:
            match_input: Dados completos da partida (times, draft, configurações).
        
        Returns:
            MatchSimulationResult com resultado, estatísticas e logs.
        
        Raises:
            ValueError: Se os times não tiverem jogadores suficientes.
        """
        match_id = match_input.match_id or str(uuid.uuid4())
        
        logger.info(
            f"[MatchEngine] ═══════════════════════════════════════════════\n"
            f"[MatchEngine] 🎮 SIMULANDO PARTIDA {match_id[:8]}...\n"
            f"[MatchEngine]    Blue: {match_input.blue_team.name}\n"
            f"[MatchEngine]    Red:  {match_input.red_team.name}\n"
            f"[MatchEngine]    Playoff: {match_input.is_playoff}\n"
            f"[MatchEngine] ═══════════════════════════════════════════════"
        )
        
        # --- Validação ---
        self._validate_inputs(match_input)
        
        # --- Inicializa RNG ---
        # Seed controlado permite reproducibilidade (testes, replays)
        rng = np.random.default_rng(seed=match_input.random_seed)
        
        # --- FASE 1: EARLY GAME ---
        logger.info(f"[MatchEngine] ▶ FASE 1 — Early Game iniciando...")
        blue_style = normalize_style(getattr(match_input, "blue_game_style", "BALANCED"))
        red_style = normalize_style(getattr(match_input, "red_game_style", "BALANCED"))

        early_result: PhaseResult = self._early_strategy.calculate(
            blue_team=match_input.blue_team,
            red_team=match_input.red_team,
            blue_draft=match_input.blue_draft,
            red_draft=match_input.red_draft,
            rng=rng,
            previous_result=None,
            is_playoff=match_input.is_playoff,
            blue_coach_comms=match_input.blue_coach_comms,
            red_coach_comms=match_input.red_coach_comms,
            blue_draft_penalty=match_input.blue_draft_penalty,
            red_draft_penalty=match_input.red_draft_penalty,
            champion_patch_meta=match_input.champion_patch_meta,
        )
        apply_style_to_phase_result(early_result, blue_style, red_style)
        logger.info(
            f"[MatchEngine] ✓ Early Game concluído | "
            f"Gold diff: {early_result.gold_difference:+.0f}"
        )
        
        # --- FASE 2: MID GAME ---
        logger.info(f"[MatchEngine] ▶ FASE 2 — Mid Game iniciando...")
        mid_result: PhaseResult = self._mid_strategy.calculate(
            blue_team=match_input.blue_team,
            red_team=match_input.red_team,
            blue_draft=match_input.blue_draft,
            red_draft=match_input.red_draft,
            rng=rng,
            previous_result=early_result,
            is_playoff=match_input.is_playoff,
            champion_patch_meta=match_input.champion_patch_meta,
        )
        apply_style_to_phase_result(mid_result, blue_style, red_style)
        logger.info(
            f"[MatchEngine] ✓ Mid Game concluído | "
            f"Gold diff: {mid_result.gold_difference:+.0f}"
        )
        
        # --- FASE 3: LATE GAME (determina vencedor) ---
        logger.info(f"[MatchEngine] ▶ FASE 3 — Late Game (resolução final)...")
        late_result: PhaseResult = self._late_strategy.calculate(
            blue_team=match_input.blue_team,
            red_team=match_input.red_team,
            blue_draft=match_input.blue_draft,
            red_draft=match_input.red_draft,
            rng=rng,
            previous_result=mid_result,
            is_playoff=match_input.is_playoff,
            champion_patch_meta=match_input.champion_patch_meta,
        )
        apply_style_to_phase_result(late_result, blue_style, red_style)
        
        # --- Extrai resultado do Late Game ---
        simulation_result = self._aggregate_result(
            match_id=match_id,
            match_input=match_input,
            early_result=early_result,
            mid_result=mid_result,
            late_result=late_result,
        )
        
        logger.info(
            f"[MatchEngine] 🏆 PARTIDA ENCERRADA: "
            f"{simulation_result.winner_side} ({simulation_result.winner_team_id[:8]}...) "
            f"venceu em {simulation_result.match_duration_minutes:.1f} minutos!"
        )
        
        return simulation_result
    
    def _validate_inputs(self, match_input: MatchInput) -> None:
        """Valida os dados de entrada antes de iniciar a simulação."""
        blue_starters = match_input.blue_team.get_starters()
        red_starters = match_input.red_team.get_starters()
        
        if len(blue_starters) < 5:
            raise ValueError(
                f"Time Blue '{match_input.blue_team.name}' não tem 5 titulares. "
                f"Encontrado: {len(blue_starters)}"
            )
        
        if len(red_starters) < 5:
            raise ValueError(
                f"Time Red '{match_input.red_team.name}' não tem 5 titulares. "
                f"Encontrado: {len(red_starters)}"
            )
        
        if len(match_input.blue_draft) < 5:
            raise ValueError(
                f"Draft do Blue Side incompleto. "
                f"Esperado: 5 campeões, encontrado: {len(match_input.blue_draft)}"
            )
        
        if len(match_input.red_draft) < 5:
            raise ValueError(
                f"Draft do Red Side incompleto. "
                f"Esperado: 5 campeões, encontrado: {len(match_input.red_draft)}"
            )
        
        if not (0 <= match_input.blue_coach_comms <= 6):
            raise ValueError(
                f"blue_coach_comms deve estar entre 0 e 6. "
                f"Recebido: {match_input.blue_coach_comms}"
            )
        
        if not (0.0 <= match_input.blue_draft_penalty <= 1.0):
            raise ValueError(
                f"blue_draft_penalty deve estar entre 0.0 e 1.0. "
                f"Recebido: {match_input.blue_draft_penalty}"
            )
    
    def _aggregate_result(
        self,
        match_id: str,
        match_input: MatchInput,
        early_result: PhaseResult,
        mid_result: PhaseResult,
        late_result: PhaseResult,
    ) -> MatchSimulationResult:
        """
        Agrega os resultados das 3 fases em um MatchSimulationResult final.
        Extrai dados do Late Game (onde o vencedor é determinado).
        """
        # Extrai metadados do Late Game (armazenados no event_log do blue_state)
        win_probability = 0.50
        match_duration = 30.0
        winner_side = "BLUE"
        
        for event in late_result.blue_state.event_log:
            if event.startswith("win_probability:"):
                win_probability = float(event.split(":")[1])
            elif event.startswith("match_duration:"):
                match_duration = float(event.split(":")[1])
            elif event.startswith("winner:"):
                winner_side = event.split(":")[1]
        
        # Determina IDs do vencedor e perdedor
        if winner_side == "BLUE":
            winner_team_id = str(match_input.blue_team.id)
            blue_result = MatchResult.WIN
            red_result = MatchResult.LOSS
        else:
            winner_team_id = str(match_input.red_team.id)
            blue_result = MatchResult.LOSS
            red_result = MatchResult.WIN
        
        # Monta narrativa completa (concatena logs das 3 fases)
        full_narrative = (
            ["═" * 50, "📋 FASE 1: EARLY GAME (0-15 min)"]
            + early_result.phase_log
            + ["", "═" * 50, "📋 FASE 2: MID GAME (15-25 min)"]
            + mid_result.phase_log
            + ["", "═" * 50, "📋 FASE 3: LATE GAME (25+ min)"]
            + late_result.phase_log
        )
        
        return MatchSimulationResult(
            match_id=match_id,
            blue_team_id=str(match_input.blue_team.id),
            blue_team_name=match_input.blue_team.name,
            red_team_id=str(match_input.red_team.id),
            red_team_name=match_input.red_team.name,
            winner_team_id=winner_team_id,
            winner_side=winner_side,
            blue_result=blue_result,
            red_result=red_result,
            match_duration_minutes=match_duration,
            blue_win_probability=win_probability,
            total_kills_blue=late_result.blue_state.kills,
            total_kills_red=late_result.red_state.kills,
            final_gold_diff=late_result.gold_difference,
            draft_log={},  # Preenchido pelo DraftEngine externo
            early_game_log=early_result.to_dict(),
            mid_game_log=mid_result.to_dict(),
            late_game_log=late_result.to_dict(),
            full_narrative=full_narrative,
        )
    
    def simulate_batch(
        self, match_inputs: List[MatchInput]
    ) -> List[MatchSimulationResult]:
        """
        Simula múltiplas partidas em sequência.
        Útil para processar a semana completa de matches de uma liga.
        """
        results = []
        for i, match_input in enumerate(match_inputs, 1):
            logger.info(f"[MatchEngine] Processando partida {i}/{len(match_inputs)}...")
            result = self.simulate(match_input)
            results.append(result)
        
        logger.info(f"[MatchEngine] Batch concluído: {len(results)} partidas simuladas.")
        return results


# Instância singleton do MatchEngine
match_engine = MatchEngine()
