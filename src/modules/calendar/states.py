"""
Máquina de Estados do Calendário do LoL Manager.

Estados possíveis e transições:
  OFFSEASON (28d) → PRESEASON (14d) → REGULAR_SEASON (9 semanas) → PLAYOFFS (21d) → OFFSEASON

Cada estado encapsula sua própria lógica de duração, dias de partida
e condições de transição. O contexto compartilhado (CalendarContext)
persiste no Redis com a chave: calendar:league:{id}:state

Padrão de design: State Pattern (GoF).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from src.modules.calendar.state_machine import CalendarStateMachine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Contexto compartilhado da State Machine
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CalendarContext:
    """
    Contexto mutável compartilhado entre todos os estados da State Machine.

    Este objeto é serializado/deserializado do Redis a cada persistência.
    Todos os campos precisam ser serializáveis via dataclasses.asdict().
    """

    # Identificador único da liga à qual este calendário pertence
    league_id: str

    # Nome do estado atual (usado para desserialização a partir do Redis)
    current_state_name: str

    # Semana atual dentro do estado (reinicia ao mudar de estado)
    current_week: int = 0

    # Dia da semana atual: 0=Segunda, 1=Terça, ..., 6=Domingo
    current_day_of_week: int = 0

    # Total de dias simulados desde o início desta temporada (nunca reinicia)
    total_days_elapsed: int = 0

    # Configuração: número de semanas na temporada regular
    regular_season_weeks: int = 9

    # Configuração: número de rodadas nos playoffs
    playoff_rounds: int = 3

    # Partidas agendadas na semana corrente (para controle de balanceamento)
    matches_scheduled_this_week: int = 0

    # Flags de tipo de dia (atualizadas a cada advance_day)
    is_match_day: bool = False
    is_rest_day: bool = False

    # Lista de eventos ocorridos no dia atual (limpa a cada advance_day)
    events: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serializa o contexto para persistência no Redis (JSON)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CalendarContext":
        """Desserializa o contexto a partir de um dict recuperado do Redis."""
        return cls(**data)


# ─────────────────────────────────────────────────────────────────────────────
# Interface base dos estados
# ─────────────────────────────────────────────────────────────────────────────

class CalendarState(ABC):
    """
    Interface abstrata para todos os estados do calendário.

    Cada estado concreto implementa:
      - get_name()      → nome canônico do estado (usado no Redis e nos logs)
      - on_enter()      → hook executado ao entrar no estado
      - on_exit()       → hook executado ao sair do estado
      - advance_day()   → avança um dia; retorna próximo estado se houver transição
      - get_day_type()  → retorna o tipo do dia (REST, TRAINING, MATCH_DAY, SCRIM)
    """

    @abstractmethod
    def get_name(self) -> str:
        """Retorna o nome canônico do estado."""
        ...

    @abstractmethod
    def on_enter(self, ctx: CalendarContext) -> None:
        """
        Hook executado ao entrar no estado.
        Use para registrar eventos de início, resetar contadores, etc.
        """
        ...

    @abstractmethod
    def on_exit(self, ctx: CalendarContext) -> None:
        """
        Hook executado ao sair do estado.
        Use para registrar eventos de encerramento, fechar janelas, etc.
        """
        ...

    @abstractmethod
    def advance_day(self, ctx: CalendarContext) -> Optional["CalendarState"]:
        """
        Avança um dia no estado atual.

        Incrementa os contadores de dia e verifica condições de transição.
        Retorna uma instância do próximo estado se houver transição,
        ou None para permanecer no estado atual.
        """
        ...

    @abstractmethod
    def get_day_type(self, ctx: CalendarContext) -> str:
        """
        Retorna o tipo de dia atual baseado no estado e dia da semana.
        Possíveis valores: REST, TRAINING, MATCH_DAY, SCRIM
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Estado: Offseason
# ─────────────────────────────────────────────────────────────────────────────

class OffseasonState(CalendarState):
    """
    Estado de Offseason — período entre temporadas.

    Duração fixa: 28 dias (4 semanas).

    Atividades permitidas:
      - Janela de transferências aberta (compra/venda de jogadores)
      - Renovação de contratos
      - Recrutamento de talentos da academia
      - Negociações de patrocínio

    Dias de partida: Nenhum.
    Descanso obrigatório: Domingos.
    """

    DURATION_DAYS: int = 28

    def get_name(self) -> str:
        return "OFFSEASON"

    def on_enter(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] Entrando na Offseason. "
            f"Janela de transferências aberta. Dia: {ctx.total_days_elapsed}"
        )
        ctx.current_week = 0
        ctx.is_match_day = False
        ctx.is_rest_day = False
        # Registra evento de abertura da janela de transferências
        ctx.events.append({
            "type": "TRANSFER_WINDOW_OPEN",
            "day": ctx.total_days_elapsed,
        })

    def on_exit(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] Encerrando Offseason. "
            f"Janela de transferências fechada. Dia: {ctx.total_days_elapsed}"
        )
        ctx.events.append({
            "type": "TRANSFER_WINDOW_CLOSE",
            "day": ctx.total_days_elapsed,
        })

    def advance_day(self, ctx: CalendarContext) -> Optional[CalendarState]:
        """
        Avança um dia na Offseason.
        Transição para PreseasonState após DURATION_DAYS dias.
        """
        ctx.total_days_elapsed += 1
        ctx.current_day_of_week = (ctx.current_day_of_week + 1) % 7
        ctx.is_rest_day = ctx.current_day_of_week == 6

        # Início de nova semana
        if ctx.current_day_of_week == 0:
            ctx.current_week += 1

        # Após 28 dias acumulados neste estado, transita para Pré-temporada
        # A verificação usa módulo para ser agnóstica ao total de dias global
        offseason_day = ctx.total_days_elapsed % self.DURATION_DAYS
        if offseason_day == 0 and ctx.total_days_elapsed > 0:
            return PreseasonState()

        return None

    def get_day_type(self, ctx: CalendarContext) -> str:
        """Domingos são descanso obrigatório; demais dias são de treino livre."""
        from src.shared.enums import CalendarDayType

        if ctx.current_day_of_week == 6:
            return CalendarDayType.REST
        return CalendarDayType.TRAINING


# ─────────────────────────────────────────────────────────────────────────────
# Estado: Preseason
# ─────────────────────────────────────────────────────────────────────────────

class PreseasonState(CalendarState):
    """
    Estado de Pré-temporada — preparação para a temporada regular.

    Duração fixa: 14 dias (2 semanas).

    Atividades:
      - Scrims (treinos contra outros times)
      - Definição de meta e picks & bans
      - Ajustes de roster finais
      - Integração de novos contratados

    Dias de scrim: Quarta-feira (2) e Sábado (5).
    Descanso obrigatório: Domingos.
    """

    DURATION_DAYS: int = 14

    def get_name(self) -> str:
        return "PRESEASON"

    def on_enter(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] Iniciando Pré-temporada. "
            f"Scrims liberados. Dia: {ctx.total_days_elapsed}"
        )
        ctx.current_week = 0
        ctx.is_match_day = False
        ctx.events.append({
            "type": "PRESEASON_START",
            "day": ctx.total_days_elapsed,
        })

    def on_exit(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] Encerrando Pré-temporada. "
            f"Iniciando temporada regular. Dia: {ctx.total_days_elapsed}"
        )
        ctx.events.append({
            "type": "PRESEASON_END",
            "day": ctx.total_days_elapsed,
        })

    def advance_day(self, ctx: CalendarContext) -> Optional[CalendarState]:
        """
        Avança um dia na Pré-temporada.
        Transição para RegularSeasonState após DURATION_DAYS dias.
        """
        ctx.total_days_elapsed += 1
        ctx.current_day_of_week = (ctx.current_day_of_week + 1) % 7
        ctx.is_rest_day = ctx.current_day_of_week == 6
        ctx.is_match_day = False  # Pré-temporada não tem partidas oficiais

        if ctx.current_day_of_week == 0:
            ctx.current_week += 1

        # Calcula dias dentro deste estado específico
        # Total de dias antes da pré-temporada = OFFSEASON_DURATION (28)
        preseason_day = (ctx.total_days_elapsed - OffseasonState.DURATION_DAYS) % self.DURATION_DAYS
        if preseason_day == 0 and ctx.total_days_elapsed > OffseasonState.DURATION_DAYS:
            return RegularSeasonState()

        return None

    def get_day_type(self, ctx: CalendarContext) -> str:
        """
        Domingo = descanso.
        Quarta (2) e Sábado (5) = scrims.
        Demais dias = treino.
        """
        from src.shared.enums import CalendarDayType

        if ctx.current_day_of_week == 6:
            return CalendarDayType.REST
        if ctx.current_day_of_week in (2, 5):
            return CalendarDayType.SCRIM
        return CalendarDayType.TRAINING


# ─────────────────────────────────────────────────────────────────────────────
# Estado: Regular Season
# ─────────────────────────────────────────────────────────────────────────────

class RegularSeasonState(CalendarState):
    """
    Estado de Temporada Regular.

    Duração: regular_season_weeks semanas (padrão: 9 = 63 dias).

    Estrutura de dias por semana:
      - Segunda (0): Início de semana, revisão de análise
      - Terça  (1): Treino
      - Quarta (2): PARTIDA OFICIAL
      - Quinta (3): Treino / Análise de replay
      - Sexta  (4): Treino
      - Sábado (5): PARTIDA OFICIAL
      - Domingo(6): DESCANSO OBRIGATÓRIO

    Transição para PlayoffsState ao final da semana regular_season_weeks.
    """

    def get_name(self) -> str:
        return "REGULAR_SEASON"

    def on_enter(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] Iniciando Temporada Regular. "
            f"Semana {ctx.current_week + 1}/{ctx.regular_season_weeks}. "
            f"Dia: {ctx.total_days_elapsed}"
        )
        ctx.current_week = 0
        ctx.matches_scheduled_this_week = 0
        ctx.events.append({
            "type": "REGULAR_SEASON_START",
            "day": ctx.total_days_elapsed,
        })

    def on_exit(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] Encerrando Temporada Regular. "
            f"Total de semanas: {ctx.current_week}. Dia: {ctx.total_days_elapsed}"
        )
        ctx.events.append({
            "type": "REGULAR_SEASON_END",
            "week": ctx.current_week,
            "day": ctx.total_days_elapsed,
        })

    def advance_day(self, ctx: CalendarContext) -> Optional[CalendarState]:
        """
        Avança um dia na Temporada Regular.

        Lógica de transição:
          - Início de nova semana (Segunda) → incrementa semana
          - Após regular_season_weeks semanas → transita para Playoffs
        """
        ctx.total_days_elapsed += 1
        ctx.current_day_of_week = (ctx.current_day_of_week + 1) % 7

        # Segunda-feira: início de nova semana de competição
        if ctx.current_day_of_week == 0:
            ctx.current_week += 1
            ctx.matches_scheduled_this_week = 0
            ctx.events.append({
                "type": "NEW_WEEK",
                "week": ctx.current_week,
                "day": ctx.total_days_elapsed,
            })

        # Atualiza flags de tipo de dia
        ctx.is_match_day = self._is_match_day(ctx)
        ctx.is_rest_day = ctx.current_day_of_week == 6

        # Registra evento se for dia de partida
        if ctx.is_match_day:
            ctx.matches_scheduled_this_week += 1
            ctx.events.append({
                "type": "MATCH_DAY",
                "week": ctx.current_week,
                "day": ctx.total_days_elapsed,
                "day_of_week": ctx.current_day_of_week,
            })

        # Verifica condição de transição para Playoffs
        if ctx.current_week > ctx.regular_season_weeks:
            return PlayoffsState()

        return None

    def _is_match_day(self, ctx: CalendarContext) -> bool:
        """
        Partidas oficiais acontecem às Quartas (2) e Sábados (5).
        Cada time joga 2 partidas por semana neste formato.
        """
        return ctx.current_day_of_week in (2, 5)

    def get_day_type(self, ctx: CalendarContext) -> str:
        """
        Domingo = descanso obrigatório.
        Quarta e Sábado = dia de partida.
        Demais dias = treino/análise.
        """
        from src.shared.enums import CalendarDayType

        if ctx.current_day_of_week == 6:
            return CalendarDayType.REST
        if ctx.current_day_of_week in (2, 5):
            return CalendarDayType.MATCH_DAY
        return CalendarDayType.TRAINING


# ─────────────────────────────────────────────────────────────────────────────
# Estado: Playoffs
# ─────────────────────────────────────────────────────────────────────────────

class PlayoffsState(CalendarState):
    """
    Estado de Playoffs — fase eliminatória.

    Formato: 6 times, eliminatória simples (Quartas → Semifinal → Final).
    Formato das séries: Best of 5 (simulado pelo match engine).

    Duração total: ~21 dias (3 semanas).
      - Quartas-de-final: semana 1
      - Semifinais: semana 2
      - Final: semana 3

    Dias de partida: Quinta (4) e Domingo (6).
    Descanso obrigatório: Segunda (0) após cada rodada.

    Após os playoffs, retorna ao estado OFFSEASON para iniciar novo split.
    """

    DURATION_DAYS: int = 21

    def get_name(self) -> str:
        return "PLAYOFFS"

    def on_enter(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] PLAYOFFS iniciados! "
            f"Quartas-de-final começam. Dia: {ctx.total_days_elapsed}"
        )
        ctx.current_week = 0
        ctx.is_match_day = False
        ctx.events.append({
            "type": "PLAYOFFS_START",
            "day": ctx.total_days_elapsed,
        })

    def on_exit(self, ctx: CalendarContext) -> None:
        logger.info(
            f"[Liga {ctx.league_id}] Playoffs encerrados. "
            f"Temporada completa! Dia: {ctx.total_days_elapsed}"
        )
        # Registra evento de fim de temporada completa
        ctx.events.append({
            "type": "SEASON_END",
            "day": ctx.total_days_elapsed,
        })

    def advance_day(self, ctx: CalendarContext) -> Optional[CalendarState]:
        """
        Avança um dia nos Playoffs.

        Transição para OffseasonState após DURATION_DAYS dias.
        Dias de partida: Quinta (4) e Domingo (6).
        Descanso: Segunda (0) — período de recuperação pós-série.
        """
        ctx.total_days_elapsed += 1
        ctx.current_day_of_week = (ctx.current_day_of_week + 1) % 7

        # Segunda-feira: início de nova rodada dos playoffs
        if ctx.current_day_of_week == 0:
            ctx.current_week += 1
            ctx.events.append({
                "type": "PLAYOFF_ROUND_START",
                "round": ctx.current_week,
                "day": ctx.total_days_elapsed,
            })

        # Atualiza flags
        ctx.is_match_day = ctx.current_day_of_week in (4, 6)  # Quinta e Domingo
        ctx.is_rest_day = ctx.current_day_of_week == 1  # Descanso na Terça pós-partida

        if ctx.is_match_day:
            ctx.events.append({
                "type": "PLAYOFF_MATCH_DAY",
                "week": ctx.current_week,
                "day": ctx.total_days_elapsed,
            })

        # Verifica condição de encerramento dos playoffs
        # Usa a data absoluta do início dos playoffs para calcular duração
        # Simplificação: verifica se passaram DURATION_DAYS desde o último múltiplo
        playoffs_day_in_state = (
            ctx.total_days_elapsed
            - OffseasonState.DURATION_DAYS
            - PreseasonState.DURATION_DAYS
            - (ctx.regular_season_weeks * 7)
        )
        if playoffs_day_in_state >= self.DURATION_DAYS:
            return OffseasonState()

        return None

    def get_day_type(self, ctx: CalendarContext) -> str:
        """
        Terça = descanso pós-série.
        Quinta e Domingo = dia de partida de playoffs.
        Demais dias = treino/preparação.
        """
        from src.shared.enums import CalendarDayType

        if ctx.current_day_of_week == 1:
            return CalendarDayType.REST
        if ctx.current_day_of_week in (4, 6):
            return CalendarDayType.MATCH_DAY
        return CalendarDayType.TRAINING


# ─────────────────────────────────────────────────────────────────────────────
# Mapa de deserialização e factory function
# ─────────────────────────────────────────────────────────────────────────────

# Mapa que relaciona nome canônico → classe do estado
# Usado para restaurar o estado a partir de strings salvas no Redis
STATE_MAP: dict[str, type[CalendarState]] = {
    "OFFSEASON": OffseasonState,
    "PRESEASON": PreseasonState,
    "REGULAR_SEASON": RegularSeasonState,
    "PLAYOFFS": PlayoffsState,
}


def state_from_name(name: str) -> CalendarState:
    """
    Instancia um estado pelo nome canônico.

    Usado ao restaurar o estado do Redis, onde apenas o nome está armazenado.

    Args:
        name: Nome canônico do estado (ex: "OFFSEASON", "PLAYOFFS")

    Returns:
        Instância do estado correspondente.

    Raises:
        ValueError: Se o nome não corresponder a nenhum estado registrado.
    """
    state_class = STATE_MAP.get(name)
    if state_class is None:
        raise ValueError(
            f"Estado desconhecido: {name!r}. "
            f"Estados válidos: {list(STATE_MAP.keys())}"
        )
    return state_class()
