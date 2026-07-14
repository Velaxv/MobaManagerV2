"""
Sistema de Snake Draft do League of Legends.

Implementa o formato oficial de draft competitivo do LoL com 4 fases rígidas:

    ┌─────────────────────────────────────────────────────────────┐
    │  FASE           │  ORDEM          │  AÇÕES                  │
    ├─────────────────┼─────────────────┼─────────────────────────┤
    │  Bans 1         │  A-B-A-B-A-B    │  3 bans por time (6)    │
    │  Picks 1        │  A-B-B-A-A-B    │  3 picks por time (6)   │
    │  Bans 2         │  B-A-B-A        │  2 bans por time (4)    │
    │  Picks 2        │  B-A-A-B        │  2 picks por time (4)   │
    └─────────────────┴─────────────────┴─────────────────────────┘

    Total: 10 bans + 10 picks = 20 ações

A ordem das 20 ações é encapsulada em DRAFT_ORDER, que define para cada
turno: (fase, time, tipo_de_ação). O estado do draft é persistido no Redis
durante a execução para suportar pausas e retomadas.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum

from src.shared.enums import DraftAction, DraftTeam
from src.shared.exceptions import (
    InvalidDraftAction,
    ChampionAlreadyBanned,
    ChampionAlreadyPicked,
)
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Sequência oficial das 20 ações do draft (formato competitivo LoL)
# Cada tupla: (fase_nome, time, tipo_acao)
# ─────────────────────────────────────────────────────────────────────────────
DRAFT_ORDER: List[Tuple[str, DraftTeam, DraftAction]] = [
    # ── Fase 1: Bans (ABABAB) ──
    ("BAN_PHASE_1", DraftTeam.BLUE, DraftAction.BAN),
    ("BAN_PHASE_1", DraftTeam.RED,  DraftAction.BAN),
    ("BAN_PHASE_1", DraftTeam.BLUE, DraftAction.BAN),
    ("BAN_PHASE_1", DraftTeam.RED,  DraftAction.BAN),
    ("BAN_PHASE_1", DraftTeam.BLUE, DraftAction.BAN),
    ("BAN_PHASE_1", DraftTeam.RED,  DraftAction.BAN),
    
    # ── Fase 2: Picks 1 (ABBAAB) ──
    ("PICK_PHASE_1", DraftTeam.BLUE, DraftAction.PICK),
    ("PICK_PHASE_1", DraftTeam.RED,  DraftAction.PICK),
    ("PICK_PHASE_1", DraftTeam.RED,  DraftAction.PICK),
    ("PICK_PHASE_1", DraftTeam.BLUE, DraftAction.PICK),
    ("PICK_PHASE_1", DraftTeam.BLUE, DraftAction.PICK),
    ("PICK_PHASE_1", DraftTeam.RED,  DraftAction.PICK),
    
    # ── Fase 3: Bans 2 (BABA) ──
    ("BAN_PHASE_2", DraftTeam.RED,  DraftAction.BAN),
    ("BAN_PHASE_2", DraftTeam.BLUE, DraftAction.BAN),
    ("BAN_PHASE_2", DraftTeam.RED,  DraftAction.BAN),
    ("BAN_PHASE_2", DraftTeam.BLUE, DraftAction.BAN),
    
    # ── Fase 4: Picks Finais (BAAB) ──
    ("PICK_PHASE_2", DraftTeam.RED,  DraftAction.PICK),
    ("PICK_PHASE_2", DraftTeam.BLUE, DraftAction.PICK),
    ("PICK_PHASE_2", DraftTeam.BLUE, DraftAction.PICK),
    ("PICK_PHASE_2", DraftTeam.RED,  DraftAction.PICK),
]

# Total: 10 bans + 10 picks = 20 turnos
assert len(DRAFT_ORDER) == 20, f"Draft order deve ter 20 ações, tem {len(DRAFT_ORDER)}"


@dataclass
class DraftState:
    """
    Estado completo do draft em um dado momento.
    Serializado e persistido no Redis durante a execução.
    """
    match_id: str
    
    # Campeões banidos (conjunto para busca O(1))
    blue_bans: List[str] = field(default_factory=list)
    red_bans: List[str] = field(default_factory=list)
    
    # Campeões escolhidos (em ordem de pick, com role associada)
    blue_picks: List[dict] = field(default_factory=list)  # [{champion, role_hint}]
    red_picks: List[dict] = field(default_factory=list)
    
    # Índice do turno atual na sequência DRAFT_ORDER (0 a 19)
    current_turn: int = 0
    
    # Flag de conclusão
    is_complete: bool = False
    
    # Log de ações
    action_log: List[str] = field(default_factory=list)

    # Fearless draft (série BO3/BO5): campeões já pickados na série
    fearless_locked: List[str] = field(default_factory=list)
    
    @property
    def all_banned(self) -> Set[str]:
        """Conjunto de todos os campeões banidos por ambos os lados."""
        return {c.lower() for c in (self.blue_bans + self.red_bans)}
    
    @property
    def all_picked(self) -> Set[str]:
        """Conjunto de todos os campeões escolhidos por ambos os lados."""
        blue = {p["champion"].lower() for p in self.blue_picks}
        red = {p["champion"].lower() for p in self.red_picks}
        return blue | red

    @property
    def all_fearless(self) -> Set[str]:
        return {c.lower() for c in (self.fearless_locked or []) if c}
    
    @property
    def unavailable_champions(self) -> Set[str]:
        """Banidos, pickados ou bloqueados por fearless da série."""
        return self.all_banned | self.all_picked | self.all_fearless
    
    @property
    def current_action(self) -> Optional[Tuple[str, DraftTeam, DraftAction]]:
        """Retorna a ação atual do draft (fase, time, tipo)."""
        if self.is_complete or self.current_turn >= len(DRAFT_ORDER):
            return None
        return DRAFT_ORDER[self.current_turn]
    
    def to_dict(self) -> dict:
        """Serializa para persistência no Redis."""
        return {
            "match_id": self.match_id,
            "blue_bans": self.blue_bans,
            "red_bans": self.red_bans,
            "blue_picks": self.blue_picks,
            "red_picks": self.red_picks,
            "current_turn": self.current_turn,
            "is_complete": self.is_complete,
            "action_log": self.action_log,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DraftState":
        """Deserializa do Redis."""
        return cls(**data)


class SnakeDraft:
    """
    Motor do Snake Draft competitivo de League of Legends.
    
    Controla o estado do draft, valida ações e registra o log completo.
    Pode ser usado em modo manual (human player) ou automático (IA).
    
    Uso:
        draft = SnakeDraft(match_id="abc123")
        draft.initialize()
        
        # Processar uma ação
        draft.process_action(team=DraftTeam.BLUE, action=DraftAction.BAN, champion="Azir")
        
        # Ou executar automaticamente com IA
        draft.auto_execute(blue_team, red_team, blue_players, red_players)
    """
    
    def __init__(self, match_id: str):
        self.match_id = match_id
        self._state: Optional[DraftState] = None
    
    def initialize(self) -> DraftState:
        """
        Inicializa um novo estado de draft.
        Chame este método antes de processar qualquer ação.
        """
        self._state = DraftState(match_id=self.match_id)
        logger.info(
            f"[SnakeDraft] Draft inicializado para partida {self.match_id}.\n"
            f"[SnakeDraft] Formato: 10 bans (ABABAB + BABA) + 10 picks (ABBAAB + BAAB)"
        )
        return self._state
    
    def process_action(
        self,
        team: DraftTeam,
        action: DraftAction,
        champion: str,
        role_hint: Optional[str] = None,
    ) -> DraftState:
        """
        Processa uma ação manual no draft.
        
        Args:
            team: Time que está executando a ação (BLUE ou RED).
            action: Tipo da ação (BAN ou PICK).
            champion: Nome do campeão a banir/escolher.
            role_hint: Role para o qual o campeão está sendo picked (opcional).
        
        Returns:
            Estado atualizado do draft.
        
        Raises:
            InvalidDraftAction: Se a ação for inválida (turno errado, etc.)
            ChampionAlreadyBanned: Se o campeão já foi banido.
            ChampionAlreadyPicked: Se o campeão já foi escolhido.
        """
        if not self._state:
            raise RuntimeError("Draft não inicializado. Chame initialize() primeiro.")
        
        if self._state.is_complete:
            raise InvalidDraftAction(
                "Draft já concluído. Não é possível processar mais ações.",
                code="DRAFT_ALREADY_COMPLETE"
            )
        
        current_action = self._state.current_action
        if not current_action:
            raise InvalidDraftAction(
                "Sem ação pendente no draft.",
                code="NO_PENDING_ACTION"
            )
        
        expected_phase, expected_team, expected_action = current_action
        
        # Valida se é o time correto
        if team != expected_team:
            raise InvalidDraftAction(
                f"É a vez do time {expected_team.value}, não {team.value}.",
                code="WRONG_TEAM_TURN"
            )
        
        # Valida se é o tipo de ação correto
        if action != expected_action:
            raise InvalidDraftAction(
                f"Ação esperada: {expected_action.value}, recebida: {action.value}.",
                code="WRONG_ACTION_TYPE"
            )
        
        # Normaliza nome do campeão
        champion = champion.strip()
        champion_lower = champion.lower()
        
        # Valida disponibilidade do campeão
        if champion_lower in self._state.all_banned:
            raise ChampionAlreadyBanned(
                f"{champion!r} já foi banido neste draft.",
                code="CHAMPION_ALREADY_BANNED"
            )
        
        if champion_lower in self._state.all_picked:
            raise ChampionAlreadyPicked(
                f"{champion!r} já foi escolhido neste draft.",
                code="CHAMPION_ALREADY_PICKED"
            )

        if champion_lower in self._state.all_fearless:
            raise ChampionAlreadyPicked(
                f"{champion!r} está bloqueado por Fearless Draft nesta série.",
                code="CHAMPION_FEARLESS_LOCKED",
            )
        
        # Processa a ação
        if action == DraftAction.BAN:
            self._apply_ban(team=team, champion=champion)
        else:
            self._apply_pick(team=team, champion=champion, role_hint=role_hint)
        
        # Log da ação
        turn_number = self._state.current_turn + 1
        log_entry = (
            f"[T{turn_number:02d}] {expected_phase} | "
            f"{team.value} {action.value}: {champion}"
            + (f" ({role_hint})" if role_hint else "")
        )
        self._state.action_log.append(log_entry)
        logger.info(f"[SnakeDraft] {log_entry}")
        
        # Avança para o próximo turno
        self._state.current_turn += 1
        
        # Verifica conclusão
        if self._state.current_turn >= len(DRAFT_ORDER):
            self._state.is_complete = True
            self._log_draft_summary()
        
        return self._state
    
    def _apply_ban(self, team: DraftTeam, champion: str) -> None:
        """Aplica um ban na lista do time correto."""
        if team == DraftTeam.BLUE:
            self._state.blue_bans.append(champion)
        else:
            self._state.red_bans.append(champion)
    
    def _apply_pick(
        self, team: DraftTeam, champion: str, role_hint: Optional[str]
    ) -> None:
        """Aplica um pick na lista do time correto."""
        pick_entry = {
            "champion": champion,
            "role_hint": role_hint or "FLEX",
        }
        if team == DraftTeam.BLUE:
            self._state.blue_picks.append(pick_entry)
        else:
            self._state.red_picks.append(pick_entry)
    
    def get_current_state(self) -> Optional[DraftState]:
        """Retorna o estado atual do draft."""
        return self._state
    
    def get_expected_action(self) -> Optional[dict]:
        """Retorna informação sobre a próxima ação esperada."""
        if not self._state or self._state.is_complete:
            return None
        
        action = self._state.current_action
        if not action:
            return None
        
        phase, team, action_type = action
        return {
            "turn": self._state.current_turn + 1,
            "phase": phase,
            "team": team.value,
            "action": action_type.value,
        }
    
    def _log_draft_summary(self) -> None:
        """Registra o resumo completo do draft concluído."""
        state = self._state
        logger.info(
            f"[SnakeDraft] ✅ DRAFT CONCLUÍDO para partida {self.match_id}\n"
            f"  Blue Bans: {', '.join(state.blue_bans)}\n"
            f"  Red Bans:  {', '.join(state.red_bans)}\n"
            f"  Blue Picks: {', '.join(p['champion'] for p in state.blue_picks)}\n"
            f"  Red Picks:  {', '.join(p['champion'] for p in state.red_picks)}"
        )
    
    def to_match_log(self) -> dict:
        """Retorna o log completo do draft para persistência."""
        if not self._state:
            return {}
        return {
            **self._state.to_dict(),
            "draft_order_summary": [
                {
                    "turn": i + 1,
                    "phase": action[0],
                    "team": action[1].value,
                    "action": action[2].value,
                }
                for i, action in enumerate(DRAFT_ORDER)
            ],
        }
