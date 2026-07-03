"""
Estratégias base do Motor de Simulação de Partida.

Define a interface Strategy (padrão Strategy) que todas as fases
do jogo devem implementar.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass
class TeamMatchState:
    """
    Estado de desempenho de um time em uma fase da partida.
    Acumula scores e modificadores ao longo da simulação.
    """
    team_id: str
    team_name: str
    
    # Score cumulativo da fase (calculado pela estratégia)
    phase_score: float = 0.0
    
    # Ouro simulado (proxy de vantagem)
    gold_earned: float = 0.0
    
    # Objetivos conquistados na fase
    objectives_taken: List[str] = field(default_factory=list)
    
    # Kills simuladas na fase
    kills: int = 0
    deaths: int = 0
    
    # Modificadores ativos (positivos e negativos)
    active_buffs: List[str] = field(default_factory=list)
    active_debuffs: List[str] = field(default_factory=list)
    
    # Log narrativo dos eventos da fase
    event_log: List[str] = field(default_factory=list)
    
    def add_event(self, event: str) -> None:
        self.event_log.append(event)
    
    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "phase_score": round(self.phase_score, 4),
            "gold_earned": round(self.gold_earned, 0),
            "objectives_taken": self.objectives_taken,
            "kills": self.kills,
            "deaths": self.deaths,
            "active_buffs": self.active_buffs,
            "active_debuffs": self.active_debuffs,
            "events": self.event_log,
        }


@dataclass
class PhaseResult:
    """
    Resultado de uma fase do motor de simulação.
    Encapsula os estados de ambos os times após a fase.
    """
    phase_name: str
    
    blue_state: TeamMatchState
    red_state: TeamMatchState
    
    # Vantagem acumulada (positivo = Blue vantagem, negativo = Red vantagem)
    gold_difference: float = 0.0
    score_difference: float = 0.0
    
    # Log narrativo da fase
    phase_log: List[str] = field(default_factory=list)
    
    def get_leading_team(self) -> str:
        """Retorna qual time está à frente após esta fase."""
        if self.gold_difference > 500:
            return f"{self.blue_state.team_name} (Blue)"
        elif self.gold_difference < -500:
            return f"{self.red_state.team_name} (Red)"
        return "EVEN"
    
    def to_dict(self) -> dict:
        return {
            "phase": self.phase_name,
            "blue": self.blue_state.to_dict(),
            "red": self.red_state.to_dict(),
            "gold_difference": round(self.gold_difference, 0),
            "score_difference": round(self.score_difference, 4),
            "leading_team": self.get_leading_team(),
            "phase_log": self.phase_log,
        }


class MatchPhaseStrategy(ABC):
    """
    Interface base para estratégias de fase do Match Engine.
    
    Cada fase (Early, Mid, Late) é uma implementação concreta desta classe.
    A separação em Strategy permite substituir ou estender fases individualmente.
    """
    
    @abstractmethod
    def get_phase_name(self) -> str:
        """Retorna o nome da fase."""
        ...
    
    @abstractmethod
    def calculate(
        self,
        blue_team,
        red_team,
        blue_draft: List[dict],
        red_draft: List[dict],
        rng: "np.random.Generator",
        previous_result: Optional[PhaseResult] = None,
        is_playoff: bool = False,
        **kwargs,
    ) -> PhaseResult:
        """
        Executa o cálculo matemático da fase.
        
        Args:
            blue_team: Time do Blue Side com jogadores carregados.
            red_team: Time do Red Side com jogadores carregados.
            blue_draft: Lista de campeões escolhidos pelo Blue Side.
            red_draft: Lista de campeões escolhidos pelo Red Side.
            rng: Gerador de números aleatórios (seed controlado).
            previous_result: Resultado da fase anterior (para encadeamento).
            is_playoff: Ativa modificadores de big match aptitude.
        
        Returns:
            PhaseResult com os estados de ambos os times após a fase.
        """
        ...
    
    def _get_starters_with_champions(
        self, team, draft_picks: List[dict]
    ) -> List[tuple]:
        """
        Emparelha cada jogador titular com o campeão do draft.
        Retorna lista de (player, champion_name) na ordem de role.
        """
        from src.shared.enums import PlayerRole
        
        role_order = [
            PlayerRole.TOP,
            PlayerRole.JUNGLE,
            PlayerRole.MID,
            PlayerRole.BOT,
            PlayerRole.SUPPORT,
        ]
        
        # Ordena os picks por índice no draft (ordem de pick)
        starters = team.get_starters()
        
        # Emparelha por posição na lista (ordem: TOP, JG, MID, BOT, SUP)
        pairs = []
        for i, role in enumerate(role_order):
            player = next((p for p in starters if p.role == role), None)
            champion = draft_picks[i]["champion"] if i < len(draft_picks) else "Unknown"
            if player:
                pairs.append((player, champion))
        
        return pairs
