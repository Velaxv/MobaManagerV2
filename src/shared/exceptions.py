"""
Exceções customizadas do sistema LoL Manager.
Todas herdam de LolManagerException para facilitar o tratamento centralizado.
"""


class LolManagerException(Exception):
    """Exceção base do sistema LoL Manager."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(code={self.code!r}, message={self.message!r})>"


class PlayerAgeViolation(LolManagerException):
    """
    Lançada quando um jogador não atende ao requisito de idade mínima da liga.
    Exemplo: LEC exige 18+ anos, ERL exige 16+ anos.
    """

    def __init__(
        self,
        player_name: str,
        player_age: int,
        required_age: int,
        league_name: str,
        code: str = "PLAYER_AGE_VIOLATION",
    ):
        message = (
            f"Jogador '{player_name}' tem {player_age} anos e não atende à idade mínima "
            f"de {required_age} anos exigida pela liga '{league_name}'."
        )
        super().__init__(message, code)
        self.player_name = player_name
        self.player_age = player_age
        self.required_age = required_age
        self.league_name = league_name


class RosterSizeViolation(LolManagerException):
    """
    Lançada quando o time não possui o número mínimo ou máximo de jogadores exigido.
    Regra padrão: mínimo de 11 jogadores (5 titulares + 6 reservas/base).
    """

    def __init__(
        self,
        message: str = "O roster do time não atende ao tamanho mínimo exigido.",
        code: str = "ROSTER_SIZE_VIOLATION",
    ):
        super().__init__(message, code)


class ContractDurationViolation(LolManagerException):
    """
    Lançada quando a duração de um contrato excede o limite máximo permitido.
    Regra: máximo de 4 temporadas (≈ 2 anos).
    """

    def __init__(
        self,
        message: str = "A duração do contrato excede o máximo de 4 temporadas.",
        code: str = "CONTRACT_TOO_LONG",
    ):
        super().__init__(message, code)


class InvalidDraftAction(LolManagerException):
    """
    Lançada quando uma ação de draft inválida é tentada.
    Exemplos: pick/ban fora do turno correto, posição de draft inválida.
    """

    def __init__(
        self,
        action: str,
        reason: str,
        code: str = "INVALID_DRAFT_ACTION",
    ):
        message = f"Ação de draft inválida '{action}': {reason}"
        super().__init__(message, code)
        self.action = action
        self.reason = reason


class ChampionAlreadyBanned(LolManagerException):
    """
    Lançada quando se tenta banir um campeão que já está banido neste draft.
    """

    def __init__(
        self,
        champion_name: str,
        code: str = "CHAMPION_ALREADY_BANNED",
    ):
        message = f"O campeão '{champion_name}' já foi banido neste draft."
        super().__init__(message, code)
        self.champion_name = champion_name


class ChampionAlreadyPicked(LolManagerException):
    """
    Lançada quando se tenta selecionar um campeão que já foi escolhido neste draft.
    """

    def __init__(
        self,
        champion_name: str,
        code: str = "CHAMPION_ALREADY_PICKED",
    ):
        message = f"O campeão '{champion_name}' já foi escolhido neste draft."
        super().__init__(message, code)
        self.champion_name = champion_name


class CalendarStateError(LolManagerException):
    """
    Lançada quando uma operação inválida é tentada no estado atual do calendário.
    Exemplo: agendar uma partida em um dia de descanso obrigatório.
    """

    def __init__(
        self,
        current_state: str,
        attempted_action: str,
        code: str = "CALENDAR_STATE_ERROR",
    ):
        message = (
            f"Ação '{attempted_action}' não é permitida no estado atual do calendário: '{current_state}'."
        )
        super().__init__(message, code)
        self.current_state = current_state
        self.attempted_action = attempted_action


class BurnoutCriticalEvent(LolManagerException):
    """
    Lançada quando o burnout de um jogador atinge nível crítico ou total.
    Pode ser usada para disparar eventos de jogo (lesão, saída do time, etc.).
    """

    def __init__(
        self,
        player_name: str,
        burnout_value: float,
        code: str = "BURNOUT_CRITICAL",
    ):
        message = (
            f"Jogador '{player_name}' atingiu nível crítico de burnout: {burnout_value:.1f}/100. "
            f"Intervenção imediata necessária."
        )
        super().__init__(message, code)
        self.player_name = player_name
        self.burnout_value = burnout_value


class InsufficientBudget(LolManagerException):
    """
    Lançada quando o time não possui orçamento suficiente para uma operação.
    Exemplos: assinar contrato, contratar staff, pagar taxa de participação.
    """

    def __init__(
        self,
        required_amount: float,
        available_amount: float,
        operation: str = "operação",
        code: str = "INSUFFICIENT_BUDGET",
    ):
        message = (
            f"Orçamento insuficiente para '{operation}': "
            f"necessário €{required_amount:,.2f}, disponível €{available_amount:,.2f}."
        )
        super().__init__(message, code)
        self.required_amount = required_amount
        self.available_amount = available_amount
        self.operation = operation
