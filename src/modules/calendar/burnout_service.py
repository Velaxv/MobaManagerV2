"""
Serviço de Burnout e Fadiga dos Jogadores do LoL Manager.

Regras de Negócio implementadas:
  - Cada tipo de dia aplica delta específico de burnout, fadiga visual e mental
  - Dias de DESCANSO recuperam todos os medidores de fadiga
  - Dias de TREINO aplicam penalidade leve (cansaço normal de prática)
  - Dias de SCRIM aplicam penalidade intermediária (treino competitivo)
  - Dias de PARTIDA aplicam penalidade máxima + incrementa games_played
  - Fadiga visual > visual_fatigue_mechanics_debuff_threshold → debuff de mecânica ativo
  - Burnout > burnout_critical_threshold → chance crescente de mental break
  - Mental break pode resultar em: pedido de transferência, queda de atributos ou licença médica

Dependências:
  - src.models.player.Player (SQLAlchemy model)
  - src.models.team.Team (SQLAlchemy model)
  - src.core.config.get_settings (configurações tunáveis)
  - src.shared.enums (CalendarDayType, BurnoutLevel)
  - src.shared.math_utils.clamp (utilitário de clamp numérico)
"""
import logging
import random
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.models.player import Player
from src.models.team import Team
from src.core.config import get_settings
from src.shared.enums import CalendarDayType, BurnoutLevel
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)
settings = get_settings()


class BurnoutService:
    """
    Processa os efeitos de fadiga e burnout em jogadores ao final de cada dia.

    Cada método retorna uma lista de eventos de burnout para rastreabilidade
    e geração de notificações no front-end.

    O commit da sessão é responsabilidade do chamador (CalendarService)
    para garantir que todos os updates do dia sejam atômicos.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Args:
            db: Sessão assíncrona do SQLAlchemy (compartilhada com CalendarService).
        """
        self.db = db

    async def process_end_of_day(
        self,
        team: Team,
        day_type: str,
        is_match_day: bool,
    ) -> list[dict]:
        """
        Processa burnout para todos os jogadores de um time ao final do dia.

        Itera pelo roster do time e aplica os efeitos de fadiga conforme
        o tipo de dia. Não faz commit — o chamador é responsável.

        Args:
            team: Entidade do time com relacionamento `players` carregado.
            day_type: Tipo do dia (CalendarDayType.*).
            is_match_day: Flag adicional de partida (para casos de override).

        Returns:
            Lista de eventos de burnout ocorridos (pode ser vazia).
        """
        events: list[dict] = []

        # Garante que o roster está carregado (pode ser lazy se não tiver joinedload)
        players = getattr(team, "players", [])
        if not players:
            logger.debug(f"[BurnoutService] Time '{team.name}' sem jogadores no roster.")
            return events

        for player in players:
            player_events = await self._process_player_burnout(
                player=player,
                day_type=day_type,
                is_match_day=is_match_day,
            )
            events.extend(player_events)

        return events

    async def _process_player_burnout(
        self,
        player: Player,
        day_type: str,
        is_match_day: bool,
    ) -> list[dict]:
        """
        Aplica a lógica de burnout para um jogador específico.

        Lógica por tipo de dia:
          REST      → recuperação de burnout, visual e mental
          TRAINING  → penalidade leve (treino normal)
          SCRIM     → penalidade intermediária (treino competitivo)
          MATCH_DAY → penalidade máxima + incrementa partidas jogadas
          OUTRO     → penalidade base padrão + warning

        Após calcular os novos valores, verifica:
          1. Debuff de fadiga visual ativo (visual_fatigue > threshold)?
          2. Burnout crítico (burnout_meter > critical_threshold)?
             → Se sim, rola dado para mental break.

        Args:
            player: Entidade do jogador.
            day_type: Tipo do dia (string de CalendarDayType).
            is_match_day: Flag override (True força tratamento de match day).

        Returns:
            Lista de eventos gerados para este jogador.
        """
        events: list[dict] = []
        updates: dict = {}

        # ── Cálculo de deltas por tipo de dia ──────────────────────────────

        if day_type == CalendarDayType.REST:
            # Dia de descanso: recuperação de todos os medidores
            new_burnout = clamp(
                float(player.burnout_meter) - settings.burnout_recovery_per_rest,
                0.0,
                100.0,
            )
            new_visual = clamp(float(player.visual_fatigue) - 8.0, 0.0, 100.0)
            new_mental = clamp(float(player.mental_fatigue) - 6.0, 0.0, 100.0)

            updates = {
                "burnout_meter": new_burnout,
                "visual_fatigue": new_visual,
                "mental_fatigue": new_mental,
            }
            logger.debug(
                f"[BurnoutService] {player.name} | REST | "
                f"Burnout: {float(player.burnout_meter):.1f} → {new_burnout:.1f}"
            )

        elif day_type == CalendarDayType.TRAINING:
            # Dia de treino: cansaço normal de prática
            new_burnout = clamp(float(player.burnout_meter) + 3.0, 0.0, 100.0)
            new_visual = clamp(
                float(player.visual_fatigue) + 5.0, 0.0, 100.0,
            )  # Horas na tela
            new_mental = clamp(float(player.mental_fatigue) + 2.0, 0.0, 100.0)

            updates = {
                "burnout_meter": new_burnout,
                "visual_fatigue": new_visual,
                "mental_fatigue": new_mental,
            }
            logger.debug(
                f"[BurnoutService] {player.name} | TRAINING | "
                f"Burnout +3 → {new_burnout:.1f}"
            )

        elif day_type == CalendarDayType.SCRIM:
            # Dia de scrim: intermediário entre treino e partida
            new_burnout = clamp(float(player.burnout_meter) + 4.0, 0.0, 100.0)
            new_visual = clamp(float(player.visual_fatigue) + 8.0, 0.0, 100.0)
            new_mental = clamp(float(player.mental_fatigue) + 4.0, 0.0, 100.0)

            updates = {
                "burnout_meter": new_burnout,
                "visual_fatigue": new_visual,
                "mental_fatigue": new_mental,
            }
            logger.debug(
                f"[BurnoutService] {player.name} | SCRIM | "
                f"Burnout +4 → {new_burnout:.1f}"
            )

        elif day_type == CalendarDayType.MATCH_DAY or is_match_day:
            # Dia de partida: máxima penalidade + fadiga visual e mental intensas
            # Adrenalina + concentração prolongada + estresse competitivo
            new_burnout = clamp(
                float(player.burnout_meter) + settings.burnout_daily_penalty,
                0.0,
                100.0,
            )
            new_visual = clamp(
                float(player.visual_fatigue) + 12.0, 0.0, 100.0,
            )  # Concentração máxima por horas
            new_mental = clamp(
                float(player.mental_fatigue) + 8.0, 0.0, 100.0,
            )  # Estresse competitivo elevado

            updates = {
                "burnout_meter": new_burnout,
                "visual_fatigue": new_visual,
                "mental_fatigue": new_mental,
                # Incrementa o contador de partidas jogadas no split
                "games_played_this_split": player.games_played_this_split + 1,
            }

            # Registra evento de fadiga por partida
            events.append({
                "type": "MATCH_DAY_FATIGUE",
                "player_id": str(player.id),
                "player_name": player.name,
                "burnout_before": float(player.burnout_meter),
                "burnout_after": new_burnout,
                "visual_after": new_visual,
                "mental_after": new_mental,
            })
            logger.debug(
                f"[BurnoutService] {player.name} | MATCH_DAY | "
                f"Burnout +{settings.burnout_daily_penalty} → {new_burnout:.1f}"
            )

        else:
            # Tipo de dia não reconhecido: aplica penalidade base como fallback
            new_burnout = clamp(
                float(player.burnout_meter) + settings.burnout_daily_penalty,
                0.0,
                100.0,
            )
            updates = {"burnout_meter": new_burnout}

            logger.warning(
                f"[BurnoutService] {player.name} | TIPO_DESCONHECIDO ({day_type!r}) | "
                f"Penalidade base aplicada: +{settings.burnout_daily_penalty} burnout."
            )
            events.append({
                "type": "UNKNOWN_DAY_TYPE_PENALTY",
                "player_id": str(player.id),
                "player_name": player.name,
                "day_type": day_type,
                "penalty": settings.burnout_daily_penalty,
            })

        # ── Verificação de debuff de fadiga visual ─────────────────────────

        final_visual = updates.get("visual_fatigue", float(player.visual_fatigue))
        if final_visual > settings.visual_fatigue_mechanics_debuff_threshold:
            # Debuff ativo: registra evento com multiplicador calculado
            # O multiplicador é lido pelo match engine na simulação
            multiplier = self._calculate_visual_debuff_multiplier(final_visual)
            events.append({
                "type": "VISUAL_FATIGUE_DEBUFF_ACTIVE",
                "player_id": str(player.id),
                "player_name": player.name,
                "visual_fatigue": final_visual,
                "mechanics_multiplier": multiplier,
                "debuff_percentage": round((1.0 - multiplier) * 100, 1),
            })
            logger.debug(
                f"[BurnoutService] {player.name} | Fadiga visual {final_visual:.1f} > "
                f"threshold {settings.visual_fatigue_mechanics_debuff_threshold} | "
                f"Multiplicador de mecânica: {multiplier:.3f}"
            )

        # ── Verificação de burnout crítico (mental break) ──────────────────

        final_burnout = updates.get("burnout_meter", float(player.burnout_meter))
        if final_burnout > settings.burnout_critical_threshold:
            mental_break_event = await self._check_mental_break(
                player=player,
                burnout=final_burnout,
                updates=updates,
            )
            if mental_break_event:
                events.append(mental_break_event)

        # ── Aplica todas as atualizações no banco de dados ─────────────────

        if updates:
            await self.db.execute(
                update(Player)
                .where(Player.id == player.id)
                .values(**updates)
            )

        return events

    def _calculate_visual_debuff_multiplier(self, visual_fatigue: float) -> float:
        """
        Calcula o multiplicador de penalidade em mecânica por fadiga visual.

        Curva linear:
          - visual_fatigue ≤ threshold (70) → multiplicador = 1.0 (sem penalidade)
          - visual_fatigue = 100           → multiplicador = 0.75 (25% de redução)

        Cada ponto acima do threshold reduz ~0.83% de mecânica, limitado a 25%.

        Args:
            visual_fatigue: Valor atual de fadiga visual (0–100).

        Returns:
            Multiplicador entre 0.75 e 1.0.
        """
        threshold = settings.visual_fatigue_mechanics_debuff_threshold

        if visual_fatigue <= threshold:
            return 1.0

        # Normaliza o excesso: 0 no threshold, 1 em 100
        excess_ratio = (visual_fatigue - threshold) / (100.0 - threshold)

        # Debuff máximo de 25%
        max_debuff = 0.25
        debuff = excess_ratio * max_debuff

        return clamp(1.0 - debuff, 0.75, 1.0)

    async def _check_mental_break(
        self,
        player: Player,
        burnout: float,
        updates: dict,
    ) -> Optional[dict]:
        """
        Verifica se o jogador sofre colapso mental (mental break).

        Chance escalonada:
          - burnout_critical_threshold (80): 0% de chance
          - burnout = 100: 15% de chance
          - Cresce linearmente entre esses pontos

        Consequências possíveis (escolhidas aleatoriamente):
          - "transfer_request": Jogador pede transferência (flag no banco)
          - "performance_drop": Redução temporária de focus e resilience
          - "sick_leave":       Jogador entra em licença médica (is_active=False temporário)

        Args:
            player: Entidade do jogador.
            burnout: Valor final de burnout após aplicar penalidade do dia.
            updates: Dict de atualizações já computados (mutável — pode adicionar campos).

        Returns:
            Dict do evento de mental break, ou None se não ocorreu.
        """
        threshold = settings.burnout_critical_threshold

        # Chance: 0% no threshold, 15% em burnout=100
        chance = ((burnout - threshold) / (100.0 - threshold)) * 0.15

        if random.random() >= chance:
            return None  # Mental break não ocorreu

        logger.warning(
            f"[BURNOUT CRÍTICO] {player.name} sofreu um colapso mental! "
            f"Burnout: {burnout:.1f} | Chance: {chance:.1%}"
        )

        # Seleciona consequência aleatória com pesos diferentes
        consequence = random.choices(
            population=["transfer_request", "performance_drop", "sick_leave"],
            weights=[0.25, 0.50, 0.25],  # Performance drop é mais comum
            k=1,
        )[0]

        if consequence == "performance_drop":
            # Redução permanente (até recuperação via REST) de atributos mentais
            new_focus = clamp(player.focus - 2, 1, 20)
            new_resilience = clamp(player.resilience - 1, 1, 20)
            # Adiciona ao dict de updates para ser aplicado junto com o restante
            updates["focus"] = new_focus
            updates["resilience"] = new_resilience
            logger.info(
                f"[BurnoutService] {player.name} | performance_drop | "
                f"focus {player.focus} → {new_focus} | "
                f"resilience {player.resilience} → {new_resilience}"
            )

        elif consequence == "sick_leave":
            # Jogador entra em licença médica temporária
            updates["is_active"] = False
            logger.info(
                f"[BurnoutService] {player.name} | sick_leave | "
                f"Jogador marcado como inativo."
            )

        # transfer_request: não altera dados do player, apenas gera o evento
        # O módulo de gestão de elenco processará a flag

        return {
            "type": "MENTAL_BREAK",
            "player_id": str(player.id),
            "player_name": player.name,
            "burnout": burnout,
            "chance": round(chance, 4),
            "consequence": consequence,
        }

    async def apply_rest_day_recovery(self, player_id: str) -> dict:
        """
        Aplica recuperação de descanso manualmente para um jogador.

        Usado quando o GM programa um dia de descanso extra via interface,
        fora do ciclo normal do calendário.

        Args:
            player_id: UUID do jogador como string.

        Returns:
            Dict com valores de burnout antes e após a recuperação.

        Raises:
            ValueError: Se o jogador não for encontrado.
        """
        result = await self.db.execute(
            select(Player).where(Player.id == player_id)
        )
        player = result.scalar_one_or_none()

        if player is None:
            raise ValueError(
                f"Jogador {player_id!r} não encontrado no banco de dados."
            )

        new_burnout = clamp(
            float(player.burnout_meter) - settings.burnout_recovery_per_rest,
            0.0,
            100.0,
        )
        new_visual = clamp(float(player.visual_fatigue) - 8.0, 0.0, 100.0)
        new_mental = clamp(float(player.mental_fatigue) - 6.0, 0.0, 100.0)

        await self.db.execute(
            update(Player)
            .where(Player.id == player.id)
            .values(
                burnout_meter=new_burnout,
                visual_fatigue=new_visual,
                mental_fatigue=new_mental,
            )
        )
        await self.db.commit()

        logger.info(
            f"[BurnoutService] Descanso manual aplicado para {player.name} | "
            f"Burnout {float(player.burnout_meter):.1f} → {new_burnout:.1f}"
        )

        return {
            "player_id": player_id,
            "player_name": player.name,
            "burnout_before": float(player.burnout_meter),
            "burnout_after": new_burnout,
            "visual_before": float(player.visual_fatigue),
            "visual_after": new_visual,
            "mental_before": float(player.mental_fatigue),
            "mental_after": new_mental,
        }

    async def get_burnout_snapshot(self, team: Team) -> list[dict]:
        """
        Retorna um snapshot atual de burnout de todos os jogadores de um time.

        Útil para exibição no dashboard e para o burnout_snapshot das partidas.

        Args:
            team: Entidade do time com relacionamento `players` carregado.

        Returns:
            Lista de dicts com o estado de burnout de cada jogador.
        """
        snapshot = []
        for player in getattr(team, "players", []):
            burnout = float(player.burnout_meter)
            visual = float(player.visual_fatigue)
            mental = float(player.mental_fatigue)

            # Calcula nível de burnout para exibição
            level = self._get_burnout_level(burnout)

            snapshot.append({
                "player_id": str(player.id),
                "player_name": player.name,
                "nickname": player.nickname,
                "role": player.role,
                "burnout_meter": burnout,
                "visual_fatigue": visual,
                "mental_fatigue": mental,
                "burnout_level": level,
                "mechanics_multiplier": self._calculate_visual_debuff_multiplier(visual),
                "is_critical": burnout > settings.burnout_critical_threshold,
                "visual_debuff_active": visual > settings.visual_fatigue_mechanics_debuff_threshold,
            })

        return snapshot

    @staticmethod
    def _get_burnout_level(burnout: float) -> str:
        """
        Classifica o nível de burnout em categorias para exibição.

        Ranges:
          0–30:   LOW
          31–60:  MODERATE
          61–80:  HIGH
          81–100: CRITICAL

        Args:
            burnout: Valor de burnout_meter (0–100).

        Returns:
            String do nível de burnout (BurnoutLevel.*).
        """
        if burnout <= 30.0:
            return BurnoutLevel.LOW
        if burnout <= 60.0:
            return BurnoutLevel.MODERATE
        if burnout <= 80.0:
            return BurnoutLevel.HIGH
        return BurnoutLevel.CRITICAL
