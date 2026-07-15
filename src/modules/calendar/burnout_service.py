"""
Serviço de Burnout e Fadiga dos Jogadores do LoL Manager.

Regras:
  - REST / treino leve / mídia: recuperação com recovery_mult (forma, moral, board, staff)
  - MATCH: titulares sofrem carga; banco recupera levemente
  - SCRIM / treino HARD: carga
  - Fadiga visual > threshold → debuff de mecânica
  - Burnout > critical → chance de mental break

Cálculos de delta em fatigue_recovery.py (funções puras testáveis).
"""
import logging
import random
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.models.player import Player
from src.models.team import Team
from src.core.config import get_settings
from src.modules.calendar.fatigue_recovery import (
    RecoveryContext,
    apply_deltas_to_meters,
    apply_recovery_quality,
    base_day_deltas,
    is_recovery_oriented,
    recovery_multiplier,
)
from src.shared.enums import CalendarDayType, BurnoutLevel
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)
settings = get_settings()


class BurnoutService:
    """
    Processa os efeitos de fadiga e burnout em jogadores ao final de cada dia.

    O commit da sessão é responsabilidade do chamador (CalendarService).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process_end_of_day(
        self,
        team: Team,
        day_type: str,
        is_match_day: bool,
    ) -> list[dict]:
        """
        Processa burnout para todos os jogadores de um time ao final do dia.
        """
        events: list[dict] = []

        players = getattr(team, "players", [])
        if not players:
            logger.debug(f"[BurnoutService] Time '{team.name}' sem jogadores no roster.")
            return events

        team_ctx = await self._load_team_recovery_context(team)

        for player in players:
            player_events = await self._process_player_burnout(
                player=player,
                day_type=day_type,
                is_match_day=is_match_day,
                team_ctx=team_ctx,
            )
            events.extend(player_events)

        return events

    async def _load_team_recovery_context(self, team: Team) -> Dict[str, Any]:
        """Carrega moral, board, staff e intensidade de treino do time (Redis/DB)."""
        team_id = str(team.id)
        team_morale = 62.0
        board_confidence = 62.0
        staff_bonus = 0.0
        intensity = "NORMAL"
        forms: Dict[str, Dict[str, Any]] = {}

        try:
            from src.modules.career.morale_service import MoraleService

            morale_state = await MoraleService(self.db).get_state(team_id)
            team_morale = float(morale_state.get("team_morale") or 62.0)
        except Exception as exc:
            logger.debug(f"[BurnoutService] morale skip: {exc}")

        try:
            from src.modules.career.org_service import OrgService

            org = await OrgService(self.db).get_public(team_id)
            board_confidence = float(org.get("board_confidence") or 62.0)
        except Exception as exc:
            logger.debug(f"[BurnoutService] org skip: {exc}")

        try:
            from src.modules.career.staff_service import StaffService

            power = await StaffService(self.db).get_team_power(team_id)
            staff_bonus = float(power.get("burnout_recovery_bonus") or 0.0)
        except Exception as exc:
            logger.debug(f"[BurnoutService] staff skip: {exc}")

        try:
            from src.modules.career.training_service import TrainingService

            plan = await TrainingService(self.db).get_plan(team_id)
            intensity = str(plan.get("intensity") or "NORMAL")
        except Exception as exc:
            logger.debug(f"[BurnoutService] training plan skip: {exc}")

        try:
            from src.modules.career.form_service import FormService

            fs = FormService(self.db)
            pids = [str(p.id) for p in getattr(team, "players", []) or []]
            forms = await fs.get_forms_bulk(pids)
        except Exception as exc:
            logger.debug(f"[BurnoutService] form skip: {exc}")
            forms = {}

        return {
            "team_morale": team_morale,
            "board_confidence": board_confidence,
            "staff_recovery_bonus": staff_bonus,
            "intensity": intensity,
            "forms": forms,
        }

    def _player_recovery_context(
        self,
        player: Player,
        team_ctx: Dict[str, Any],
    ) -> RecoveryContext:
        form = (team_ctx.get("forms") or {}).get(str(player.id)) or {}
        last_rating = form.get("last_rating")
        if last_rating is None and form.get("avg") is not None:
            last_rating = form.get("avg")
        return RecoveryContext(
            last_rating=float(last_rating) if last_rating is not None else None,
            form_avg=float(form["avg"]) if form.get("avg") is not None else None,
            team_morale=float(team_ctx.get("team_morale") or 62.0),
            discontent=float(form.get("discontent") or 0.0),
            board_confidence=float(team_ctx.get("board_confidence") or 62.0),
            staff_recovery_bonus=float(team_ctx.get("staff_recovery_bonus") or 0.0),
            intensity=str(team_ctx.get("intensity") or "NORMAL"),
        )

    async def _process_player_burnout(
        self,
        player: Player,
        day_type: str,
        is_match_day: bool,
        team_ctx: Optional[Dict[str, Any]] = None,
    ) -> list[dict]:
        events: list[dict] = []
        team_ctx = team_ctx or {}
        is_starter = bool(getattr(player, "is_starter", False))
        intensity = str(team_ctx.get("intensity") or "NORMAL")

        base = base_day_deltas(
            day_type,
            is_match_day=is_match_day,
            is_starter=is_starter,
            intensity=intensity,
            match_starter_burnout=float(settings.burnout_daily_penalty),
            rest_burnout=float(settings.burnout_recovery_per_rest),
            rest_visual=float(getattr(settings, "visual_recovery_per_rest", 10)),
            rest_mental=float(getattr(settings, "mental_recovery_per_rest", 8)),
        )

        ctx = self._player_recovery_context(player, team_ctx)
        recovering = is_recovery_oriented(base)
        mult = recovery_multiplier(ctx, is_recovery_day=recovering)

        deltas = apply_recovery_quality(base, mult) if recovering else base

        before_b = float(player.burnout_meter)
        before_v = float(player.visual_fatigue)
        before_m = float(player.mental_fatigue)

        new_burnout, new_visual, new_mental = apply_deltas_to_meters(
            before_b, before_v, before_m, deltas
        )

        updates: dict = {
            "burnout_meter": new_burnout,
            "visual_fatigue": new_visual,
            "mental_fatigue": new_mental,
        }

        if deltas.games_played_delta:
            updates["games_played_this_split"] = (
                int(player.games_played_this_split or 0) + deltas.games_played_delta
            )

        # Eventos legíveis
        if deltas.event_type in (
            "MATCH_DAY_FATIGUE",
            "BENCH_RECOVERY",
            "FATIGUE_RECOVERY",
            "POOR_RECOVERY",
            "UNKNOWN_DAY_TYPE_PENALTY",
        ):
            # Só emite recovery se havia fadiga relevante ou match/bench
            emit = True
            if deltas.event_type in ("FATIGUE_RECOVERY", "POOR_RECOVERY"):
                emit = before_b >= 25 or before_v >= 25 or before_m >= 25
            if emit:
                events.append({
                    "type": deltas.event_type,
                    "player_id": str(player.id),
                    "player_name": player.name,
                    "day_type": day_type,
                    "is_starter": is_starter,
                    "recovery_mult": round(mult, 3),
                    "burnout_before": before_b,
                    "burnout_after": new_burnout,
                    "visual_before": before_v,
                    "visual_after": new_visual,
                    "mental_before": before_m,
                    "mental_after": new_mental,
                    "delta_burnout": round(deltas.burnout, 2),
                    "delta_visual": round(deltas.visual, 2),
                    "delta_mental": round(deltas.mental, 2),
                })

        logger.debug(
            f"[BurnoutService] {player.name} | {day_type} | starter={is_starter} | "
            f"mult={mult:.2f} | burn {before_b:.1f}→{new_burnout:.1f}"
        )

        # Debuff de fadiga visual
        if new_visual > settings.visual_fatigue_mechanics_debuff_threshold:
            multiplier = self._calculate_visual_debuff_multiplier(new_visual)
            events.append({
                "type": "VISUAL_FATIGUE_DEBUFF_ACTIVE",
                "player_id": str(player.id),
                "player_name": player.name,
                "visual_fatigue": new_visual,
                "mechanics_multiplier": multiplier,
                "debuff_percentage": round((1.0 - multiplier) * 100, 1),
            })

        # Burnout crítico
        if new_burnout > settings.burnout_critical_threshold:
            mental_break_event = await self._check_mental_break(
                player=player,
                burnout=new_burnout,
                updates=updates,
            )
            if mental_break_event:
                events.append(mental_break_event)

        if updates:
            await self.db.execute(
                update(Player)
                .where(Player.id == player.id)
                .values(**updates)
            )

        return events

    def _calculate_visual_debuff_multiplier(self, visual_fatigue: float) -> float:
        threshold = settings.visual_fatigue_mechanics_debuff_threshold

        if visual_fatigue <= threshold:
            return 1.0

        excess_ratio = (visual_fatigue - threshold) / (100.0 - threshold)
        max_debuff = 0.25
        debuff = excess_ratio * max_debuff

        return clamp(1.0 - debuff, 0.75, 1.0)

    async def _check_mental_break(
        self,
        player: Player,
        burnout: float,
        updates: dict,
    ) -> Optional[dict]:
        threshold = settings.burnout_critical_threshold
        chance = ((burnout - threshold) / (100.0 - threshold)) * 0.15

        if random.random() >= chance:
            return None

        logger.warning(
            f"[BURNOUT CRÍTICO] {player.name} sofreu um colapso mental! "
            f"Burnout: {burnout:.1f} | Chance: {chance:.1%}"
        )

        consequence = random.choices(
            population=["transfer_request", "performance_drop", "sick_leave"],
            weights=[0.25, 0.50, 0.25],
            k=1,
        )[0]

        if consequence == "performance_drop":
            new_focus = clamp(player.focus - 2, 1, 20)
            new_resilience = clamp(player.resilience - 1, 1, 20)
            updates["focus"] = new_focus
            updates["resilience"] = new_resilience
        elif consequence == "sick_leave":
            updates["is_active"] = False

        return {
            "type": "MENTAL_BREAK",
            "player_id": str(player.id),
            "player_name": player.name,
            "burnout": burnout,
            "chance": round(chance, 4),
            "consequence": consequence,
        }

    async def apply_rest_day_recovery(self, player_id: str) -> dict:
        """Recuperação manual de descanso (fora do ciclo do calendário)."""
        result = await self.db.execute(
            select(Player).where(Player.id == player_id)
        )
        player = result.scalar_one_or_none()

        if player is None:
            raise ValueError(
                f"Jogador {player_id!r} não encontrado no banco de dados."
            )

        base = base_day_deltas(
            CalendarDayType.REST,
            rest_burnout=float(settings.burnout_recovery_per_rest),
            rest_visual=float(getattr(settings, "visual_recovery_per_rest", 10)),
            rest_mental=float(getattr(settings, "mental_recovery_per_rest", 8)),
        )
        # Manual rest: mult neutro bom
        deltas = apply_recovery_quality(base, 1.0)
        new_burnout, new_visual, new_mental = apply_deltas_to_meters(
            float(player.burnout_meter),
            float(player.visual_fatigue),
            float(player.mental_fatigue),
            deltas,
        )

        before_b = float(player.burnout_meter)
        before_v = float(player.visual_fatigue)
        before_m = float(player.mental_fatigue)

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
            f"Burnout {before_b:.1f} → {new_burnout:.1f}"
        )

        return {
            "player_id": player_id,
            "player_name": player.name,
            "burnout_before": before_b,
            "burnout_after": new_burnout,
            "visual_before": before_v,
            "visual_after": new_visual,
            "mental_before": before_m,
            "mental_after": new_mental,
        }

    async def get_burnout_snapshot(self, team: Team) -> list[dict]:
        snapshot = []
        alert_threshold = float(
            getattr(settings, "fatigue_alert_threshold", 70)
        )
        for player in getattr(team, "players", []):
            burnout = float(player.burnout_meter)
            visual = float(player.visual_fatigue)
            mental = float(player.mental_fatigue)

            snapshot.append({
                "player_id": str(player.id),
                "player_name": player.name,
                "nickname": player.nickname if hasattr(player, "nickname") else player.name,
                "role": player.role,
                "burnout_meter": burnout,
                "visual_fatigue": visual,
                "mental_fatigue": mental,
                "burnout_level": self._get_burnout_level(burnout),
                "mechanics_multiplier": self._calculate_visual_debuff_multiplier(visual),
                "is_critical": burnout > settings.burnout_critical_threshold,
                "visual_debuff_active": visual > settings.visual_fatigue_mechanics_debuff_threshold,
                "fatigue_alert": burnout > alert_threshold or visual > alert_threshold,
            })

        return snapshot

    @staticmethod
    def _get_burnout_level(burnout: float) -> str:
        if burnout <= 30.0:
            return BurnoutLevel.LOW
        if burnout <= 60.0:
            return BurnoutLevel.MODERATE
        if burnout <= 80.0:
            return BurnoutLevel.HIGH
        return BurnoutLevel.CRITICAL
