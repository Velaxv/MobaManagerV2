"""
Sistema de Coach Comms (Comunicações do Treinador).

Implementa o evento de Early Game onde o treinador pode emitir comandos
para reverter situações de desvantagem (tilt por draft ruim, mau início de rota).

Regras de Negócio:
    - Cada comunicação faz um teste matemático: random() < (coachability + teamwork) / 40
    - Sucesso: reduz penalidade de draft ruim em 30-50%
    - Mais de 3 comunicações: risco crescente de confusão mental
    - Confusão: debuff temporário em 'focus' do jogador durante a partida
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from src.core.config import get_settings
from src.shared.math_utils import clamp, roll_check

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CoachCommResult:
    """Resultado de uma comunicação do treinador com um jogador."""
    player_name: str
    comm_number: int           # Número sequencial da comunicação nesta partida
    success: bool              # Comunicação foi bem recebida?
    confusion_triggered: bool  # Causou confusão mental?
    
    # Efeitos no desempenho do jogador
    draft_penalty_reduction: float = 0.0  # Redução na penalidade de draft (0.0 a 0.5)
    focus_debuff: float = 0.0             # Penalidade em foco por confusão (0.0 a 3.0)
    
    message: str = ""
    
    @property
    def net_effect(self) -> float:
        """
        Efeito líquido da comunicação na performance do jogador.
        Positivo = bônus, Negativo = penalidade.
        """
        if self.confusion_triggered:
            return -self.focus_debuff
        if self.success:
            return self.draft_penalty_reduction
        return 0.0


@dataclass
class CoachCommsSession:
    """
    Sessão de comunicações do treinador durante uma partida.
    Rastreia o histórico de comunicações e acumula efeitos.
    """
    team_name: str
    max_before_confusion: int = field(default_factory=lambda: settings.coach_comms_max_before_confusion)
    
    total_comms: int = 0
    successful_comms: int = 0
    confusion_count: int = 0
    total_draft_penalty_reduction: float = 0.0
    total_focus_debuff: float = 0.0
    history: list[CoachCommResult] = field(default_factory=list)
    
    @property
    def is_overloaded(self) -> bool:
        """Verifica se o número de comunicações excedeu o limite seguro."""
        return self.total_comms > self.max_before_confusion
    
    @property
    def effective_draft_penalty_factor(self) -> float:
        """
        Fator multiplicador resultante das comunicações no draft penalty.
        1.0 = sem redução, 0.5 = 50% de redução na penalidade.
        """
        return clamp(1.0 - self.total_draft_penalty_reduction, 0.0, 1.0)
    
    @property
    def cumulative_focus_debuff(self) -> float:
        """Penalidade total em foco acumulada por confusões."""
        return self.total_focus_debuff


class CoachCommsEngine:
    """
    Motor de processamento das comunicações do treinador.
    
    Cada chamada a `process_comm()` simula uma comunicação entre
    o treinador e o jogador durante o Early Game.
    """
    
    def __init__(self, rng: Optional[np.random.Generator] = None):
        # Usa RNG fornecido (para testes determinísticos) ou cria um novo
        self.rng = rng or np.random.default_rng()
    
    def process_comm(
        self,
        player,
        session: CoachCommsSession,
        draft_penalty_active: bool = False,
        coach_communication: float = 10.0,
    ) -> CoachCommResult:
        """
        Processa uma comunicação do treinador com um jogador específico.
        
        Args:
            player: Instância do modelo Player.
            session: Sessão ativa de comunicações da partida.
            draft_penalty_active: Indica se há penalidade de draft a ser revertida.
            coach_communication: Atributo de comunicação do treinador (1.0 a 20.0).
        
        Returns:
            CoachCommResult com os efeitos da comunicação.
        """
        session.total_comms += 1
        comm_number = session.total_comms
        
        logger.info(
            f"[CoachComms] Comunicação #{comm_number} do treinador de "
            f"{session.team_name} para {player.name}."
        )
        
        # --- Etapa 1: Teste de confusão (se acima do limite ou estocástico) ---
        confusion_result = self._check_confusion(player, session, comm_number)
        
        if confusion_result.confusion_triggered:
            session.confusion_count += 1
            session.total_focus_debuff += confusion_result.focus_debuff
            session.history.append(confusion_result)
            return confusion_result
        
        # --- Etapa 2: Teste de sucesso da comunicação ---
        success_result = self._check_success(
            player, session, comm_number, draft_penalty_active, coach_communication
        )
        
        if success_result.success:
            session.successful_comms += 1
            session.total_draft_penalty_reduction = clamp(
                session.total_draft_penalty_reduction + success_result.draft_penalty_reduction,
                0.0, 0.75,  # Máximo de 75% de redução acumulada
            )
        
        session.history.append(success_result)
        return success_result
    
    def _check_confusion(
        self,
        player,
        session: CoachCommsSession,
        comm_number: int,
    ) -> CoachCommResult:
        """
        Verifica se a comunicação causa confusão mental no jogador.
        
        Fórmula: chance = (comm_number - max_safe) * base_chance
        Exemplo com max_safe=3, base_chance=0.15:
            Comm #4: 15% de confusão
            Comm #5: 30% de confusão
            Comm #6: 45% de confusão
        """
        if comm_number <= session.max_before_confusion:
            # Dentro do limite seguro, sem risco de confusão
            return CoachCommResult(
                player_name=player.name,
                comm_number=comm_number,
                success=False,
                confusion_triggered=False,
                message="",
            )
        
        # Calcula chance de confusão crescente (influenciada negativamente por foco baixo)
        excess_comms = comm_number - session.max_before_confusion
        focus_factor = (20.0 - player.focus) / 10.0 # Se focus=5 -> 1.5, se focus=20 -> 0.0
        confusion_chance = excess_comms * settings.coach_comms_confusion_base_chance * max(0.5, focus_factor)
        confusion_chance = clamp(confusion_chance, 0.0, 0.85)  # Cap em 85%
        
        if roll_check(confusion_chance, self.rng):
            # Confusão ativada — debuff em foco proporcional ao excesso de comunicações e foco baixo
            focus_debuff = self.rng.uniform(1.0, min(1.0 + excess_comms + (20.0 - player.focus)/4.0, 6.0))
            focus_debuff = round(focus_debuff, 2)
            
            message = (
                f"⚠️  Confusão mental! {player.name} ficou distraído com excesso de comandos. "
                f"Foco reduzido em {focus_debuff:.1f} pontos."
            )
            logger.warning(f"[CoachComms] {message}")
            
            return CoachCommResult(
                player_name=player.name,
                comm_number=comm_number,
                success=False,
                confusion_triggered=True,
                focus_debuff=focus_debuff,
                message=message,
            )
        
        # Sorte — sem confusão desta vez
        return CoachCommResult(
            player_name=player.name,
            comm_number=comm_number,
            success=False,
            confusion_triggered=False,
            message=f"Comunicação #{comm_number} acima do limite, mas sem confusão desta vez.",
        )
    
    def _check_success(
        self,
        player,
        session: CoachCommsSession,
        comm_number: int,
        draft_penalty_active: bool,
        coach_communication: float,
    ) -> CoachCommResult:
        """
        Verifica se o jogador responde positivamente à comunicação do treinador.
        Influenciado pela comunicação do coach (1.0 a 20.0).
        """
        # Sucesso base depende de coachability + teamwork do jogador
        base_threshold = (player.coachability + player.teamwork) / 40.0
        
        # Multiplicador do coach: comunicação 20 maximiza, 1 reduz pela metade
        coach_factor = coach_communication / 20.0 # range [0.05, 1.0]
        success_threshold = base_threshold * (0.5 + 0.5 * coach_factor)
        success_threshold = clamp(success_threshold, 0.05, 0.95)
        
        # Aplica penalidade se acima do limite (mas sem confusão)
        if session.is_overloaded:
            overload_penalty = (comm_number - session.max_before_confusion) * 0.05
            success_threshold = clamp(success_threshold - overload_penalty, 0.05, 0.95)
        
        success = roll_check(success_threshold, self.rng)
        
        if success and draft_penalty_active:
            # Sucesso reverte 30-50% da penalidade de draft
            reduction = self.rng.uniform(0.30, 0.50)
            reduction = round(reduction, 3)
            
            message = (
                f"✅ {player.name} respondeu ao coach! Draft penalty reduzido em "
                f"{reduction:.0%}. (Coachability: {player.coachability:.1f}, "
                f"Teamwork: {player.teamwork:.1f})"
            )
            logger.info(f"[CoachComms] {message}")
            
            return CoachCommResult(
                player_name=player.name,
                comm_number=comm_number,
                success=True,
                confusion_triggered=False,
                draft_penalty_reduction=reduction,
                message=message,
            )
        
        elif success:
            # Sucesso sem draft penalty ativa — pequeno bônus de foco
            message = f"✅ {player.name} recebeu o comando positivamente."
            return CoachCommResult(
                player_name=player.name,
                comm_number=comm_number,
                success=True,
                confusion_triggered=False,
                message=message,
            )
        
        else:
            # Falha — jogador não respondeu
            message = (
                f"❌ {player.name} não respondeu ao coach. "
                f"(Coachability: {player.coachability:.1f}, threshold: {success_threshold:.0%})"
            )
            logger.info(f"[CoachComms] {message}")
            
            return CoachCommResult(
                player_name=player.name,
                comm_number=comm_number,
                success=False,
                confusion_triggered=False,
                message=message,
            )
    
    def create_session(self, team_name: str) -> CoachCommsSession:
        """Cria uma nova sessão de comunicações para uma partida."""
        return CoachCommsSession(team_name=team_name)
    
    def get_summary(self, session: CoachCommsSession) -> dict:
        """Retorna um resumo da sessão de comunicações."""
        return {
            "team": session.team_name,
            "total_comms": session.total_comms,
            "successful_comms": session.successful_comms,
            "confusion_events": session.confusion_count,
            "draft_penalty_reduction": f"{session.total_draft_penalty_reduction:.0%}",
            "effective_draft_penalty_factor": session.effective_draft_penalty_factor,
            "cumulative_focus_debuff": session.cumulative_focus_debuff,
            "was_overloaded": session.is_overloaded,
        }


# Instância singleton do motor de coach comms
coach_comms_engine = CoachCommsEngine()
