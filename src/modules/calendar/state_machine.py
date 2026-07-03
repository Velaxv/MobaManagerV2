"""
Orquestrador da State Machine do Calendário.

Responsabilidades:
  - Inicializar o calendário de uma liga (novo ou restaurado do Redis)
  - Coordenar transições de estado com on_enter/on_exit
  - Persistir o contexto no Redis após cada avanço de dia
  - Expor a API pública usada pelo CalendarService
"""
import logging
from typing import Optional

from src.modules.calendar.states import (
    CalendarContext,
    CalendarState,
    OffseasonState,
    state_from_name,
)
from src.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class CalendarStateMachine:
    """
    Máquina de estados do calendário de uma liga específica.

    Uso típico:
        sm = CalendarStateMachine(league_id="uuid-da-liga")
        await sm.initialize()          # Restaura do Redis ou inicia do zero
        result = await sm.advance_day()  # Avança um dia e retorna informações

    O estado é persistido automaticamente no Redis após cada chamada a advance_day().
    TTL padrão: 30 dias (suficiente para a duração de um split completo).
    """

    def __init__(self, league_id: str, regular_season_weeks: int = 9) -> None:
        """
        Inicializa a SM com o ID da liga e configuração da temporada.

        Args:
            league_id: UUID da liga (como string).
            regular_season_weeks: Número de semanas na temporada regular.
        """
        self.league_id = league_id
        self.regular_season_weeks = regular_season_weeks

        # Estado e contexto são None até initialize() ser chamado
        self._current_state: Optional[CalendarState] = None
        self._context: Optional[CalendarContext] = None

    async def initialize(self) -> None:
        """
        Inicializa a State Machine.

        Comportamento:
          1. Tenta restaurar o estado salvo no Redis.
          2. Se encontrado → restaura contexto e estado.
          3. Se não encontrado → cria novo contexto em OFFSEASON e persiste.

        Deve ser chamado antes de qualquer outra operação.
        """
        saved_state = await redis_client.get_calendar_state(self.league_id)

        if saved_state:
            # Restaura a partir do Redis: desserializa contexto e instancia estado
            self._context = CalendarContext.from_dict(saved_state)
            self._current_state = state_from_name(self._context.current_state_name)
            logger.info(
                f"[SM Liga {self.league_id}] Estado restaurado do Redis: "
                f"{self._context.current_state_name} | "
                f"Semana {self._context.current_week} | "
                f"Dia total {self._context.total_days_elapsed}"
            )
        else:
            # Primeiro uso: cria contexto inicial em Regular Season
            self._context = CalendarContext(
                league_id=self.league_id,
                current_state_name="REGULAR_SEASON",
                regular_season_weeks=self.regular_season_weeks,
            )
            from src.modules.calendar.states import RegularSeasonState
            self._current_state = RegularSeasonState()

            # Dispara o hook de entrada no estado inicial
            self._current_state.on_enter(self._context)

            # Persiste o estado inicial no Redis
            await self._persist_state()

            logger.info(
                f"[SM Liga {self.league_id}] Nova SM criada. "
                f"Estado inicial: OFFSEASON."
            )

    async def advance_day(self) -> dict:
        """
        Avança o calendário por exatamente um dia.

        Sequência de operações:
          1. Captura o tipo de dia ANTES de avançar (para retorno correto).
          2. Chama advance_day() no estado atual.
          3. Se houver transição → executa on_exit() → atualiza estado → on_enter().
          4. Persiste o novo contexto no Redis.
          5. Retorna dict com todas as informações do dia processado.

        Returns:
            Dict com: league_id, state, week, day_of_week, total_days,
                      day_type, is_match_day, is_rest_day, events, state_changed.

        Raises:
            RuntimeError: Se initialize() não foi chamado antes.
        """
        if self._current_state is None or self._context is None:
            raise RuntimeError(
                f"[SM Liga {self.league_id}] State Machine não inicializada. "
                "Chame await sm.initialize() antes de advance_day()."
            )

        # Limpa eventos do dia anterior (lista fresca para o novo dia)
        self._context.events.clear()

        # Captura o tipo de dia ANTES do avanço (estado ainda não mudou)
        day_type = self._current_state.get_day_type(self._context)

        # Salva nome do estado anterior para log de transição
        previous_state_name = self._current_state.get_name()

        # Avança o dia no estado atual; pode retornar o próximo estado
        next_state = self._current_state.advance_day(self._context)

        # Processa transição de estado (se houver)
        state_changed = next_state is not None
        if state_changed:
            logger.info(
                f"[SM Liga {self.league_id}] Transição: "
                f"{previous_state_name} → {next_state.get_name()} "
                f"(Dia {self._context.total_days_elapsed})"
            )

            # Executa hook de saída do estado atual
            self._current_state.on_exit(self._context)

            # Substitui o estado atual pelo próximo
            self._current_state = next_state
            self._context.current_state_name = next_state.get_name()

            # Executa hook de entrada no novo estado
            self._current_state.on_enter(self._context)

        # Persiste o estado atualizado no Redis
        await self._persist_state()

        return {
            "league_id": self.league_id,
            "state": self._context.current_state_name,
            "week": self._context.current_week,
            "day_of_week": self._context.current_day_of_week,
            "total_days": self._context.total_days_elapsed,
            "day_type": day_type,
            "is_match_day": self._context.is_match_day,
            "is_rest_day": self._context.is_rest_day,
            "events": list(self._context.events),  # Cópia para evitar mutação externa
            "state_changed": state_changed,
            "previous_state": previous_state_name if state_changed else None,
        }

    async def force_transition_to(self, state_name: str) -> None:
        """
        Força uma transição de estado (usado em testes e operações administrativas).

        ATENÇÃO: Pula a verificação de condições de transição.
        Use apenas para administração da liga ou em ambiente de desenvolvimento.

        Args:
            state_name: Nome canônico do estado destino (ex: "PLAYOFFS").

        Raises:
            ValueError: Se o nome do estado for inválido.
            RuntimeError: Se a SM não foi inicializada.
        """
        if self._current_state is None or self._context is None:
            raise RuntimeError("State Machine não inicializada.")

        next_state = state_from_name(state_name)

        logger.warning(
            f"[SM Liga {self.league_id}] TRANSIÇÃO FORÇADA: "
            f"{self._current_state.get_name()} → {next_state.get_name()}"
        )

        self._current_state.on_exit(self._context)
        self._current_state = next_state
        self._context.current_state_name = next_state.get_name()
        self._current_state.on_enter(self._context)

        await self._persist_state()

    async def reset(self) -> None:
        """
        Reseta completamente a SM para o estado inicial (OFFSEASON).
        Remove o estado do Redis e reinicializa do zero.

        Use com cautela — perde todo o histórico do calendário.
        """
        logger.warning(
            f"[SM Liga {self.league_id}] RESET completo da State Machine."
        )
        await redis_client.delete_calendar_state(self.league_id)
        self._current_state = None
        self._context = None
        await self.initialize()

    async def _persist_state(self) -> None:
        """
        Persiste o contexto atual no Redis.

        TTL: 30 dias (86400 segundos × 30).
        A chave é gerenciada pelo redis_client com o formato:
          calendar:league:{league_id}:state
        """
        await redis_client.set_calendar_state(
            league_id=self.league_id,
            state_data=self._context.to_dict(),
            ttl=86400 * 30,  # 30 dias de TTL
        )

    # ── Propriedades de acesso ao estado atual ────────────────────────────────

    @property
    def current_state_name(self) -> str:
        """Nome canônico do estado atual. Retorna 'UNINITIALIZED' se não inicializado."""
        if self._context is None:
            return "UNINITIALIZED"
        return self._context.current_state_name

    @property
    def context(self) -> Optional[CalendarContext]:
        """Contexto completo da SM. None se não inicializado."""
        return self._context

    @property
    def is_initialized(self) -> bool:
        """Indica se a SM foi inicializada com sucesso."""
        return self._current_state is not None and self._context is not None
