# -*- coding: utf-8 -*-
"""
Prática de pro play: Scrims e VOD Review.

SCRIM day:
  - Simula scrim vs org aleatória da liga (resultado estocástico por CA médio)
  - Relatório: resultado, notas táticas, efeito em moral/chemistry
  - Leve XP de treino

TRAINING / MEDIA:
  - VOD review: gasta o dia de análise, gera intel do próximo oponente
    (estilo de jogo, roles fracas, bans preferidos)

Redis:
  practice:team:{id}:last_scrim
  practice:team:{id}:last_vod
  practice:team:{id}:opponent_intel
"""

from __future__ import annotations

import logging
import random
import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.redis_client import redis_client
from src.models.team import Team
from src.modules.career.morale_service import MoraleService
from src.modules.draft.draft_ai import CHAMPIONS_BY_ROLE
from src.shared.enums import CalendarDayType, PlayerRole
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

STYLES = ("EARLY", "MID", "LATE", "BALANCED")
SCRIM_NOTES_WIN = [
    "Boa execução de mid-game; vision control sólido.",
    "Shotcalls de dragão funcionaram; bot lane sincronizou.",
    "Draft experimental funcionou — manter no banco de ideias.",
    "JG–MID pathing limpo; oponente não encontrou ganks.",
]
SCRIM_NOTES_LOSS = [
    "Perdemos early por trades ruins no top.",
    "Draft frágil a engage — revisar frontline.",
    "Comms confusas no objetivo; resetar protocols.",
    "Bot foi isolado sem suporte de jg; ajustar cobertura.",
]
VOD_FINDINGS = [
    "Oponente prioriza early skirmish e grubs.",
    "Mid deles é o carry; banir o main do mid ajuda.",
    "Bot duo fraco vs engage — Leona/Nautilus excelentes.",
    "Jungle path previsível no azul; invade no 3:15 funciona.",
    "Eles fecham full AD com frequência — stack de armadura.",
    "Scaling comp: forçar early e negar farm do ADC.",
]


class PracticeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.morale = MoraleService(db)

    def _scrim_key(self, team_id: str) -> str:
        return f"practice:team:{team_id}:last_scrim"

    def _vod_key(self, team_id: str) -> str:
        return f"practice:team:{team_id}:last_vod"

    def _intel_key(self, team_id: str) -> str:
        return f"practice:team:{team_id}:opponent_intel"

    async def get_status(self, team_id: str) -> Dict[str, Any]:
        scrim = await redis_client.get_generic(self._scrim_key(team_id))
        vod = await redis_client.get_generic(self._vod_key(team_id))
        intel = await redis_client.get_generic(self._intel_key(team_id))
        morale = await self.morale.get_public(team_id)
        return {
            "team_id": str(team_id),
            "last_scrim": scrim if isinstance(scrim, dict) else None,
            "last_vod": vod if isinstance(vod, dict) else None,
            "opponent_intel": intel if isinstance(intel, dict) else None,
            "morale": morale,
        }

    async def process_day_for_team(
        self,
        team: Team,
        day_type: str,
        league_teams: Sequence[Team],
        *,
        next_opponent_id: Optional[str] = None,
        next_opponent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Processa scrim ou VOD conforme tipo de dia."""
        dt = (day_type or "").upper()
        result: Dict[str, Any] = {
            "team_id": str(team.id),
            "team_name": team.name,
            "day_type": dt,
            "scrim": None,
            "vod": None,
            "morale": None,
        }

        if dt == CalendarDayType.SCRIM.value:
            result["scrim"] = await self.run_scrim(team, league_teams)
            result["morale"] = await self.morale.get_public(str(team.id))
        elif dt in (
            CalendarDayType.TRAINING.value,
            CalendarDayType.MEDIA.value,
        ):
            # VOD em treino (leve) ou mídia/análise (completo)
            full = dt == CalendarDayType.MEDIA.value
            result["vod"] = await self.run_vod_review(
                team,
                opponent_id=next_opponent_id,
                opponent_name=next_opponent_name,
                intensity="FULL" if full else "LIGHT",
            )
            result["morale"] = await self.morale.get_public(str(team.id))
        elif dt == CalendarDayType.REST.value:
            await self.morale.on_rest_day(str(team.id))
            result["morale"] = await self.morale.get_public(str(team.id))

        return result

    async def run_scrim(
        self,
        team: Team,
        league_teams: Sequence[Team],
    ) -> Dict[str, Any]:
        rng = random.Random(f"scrim-{team.id}-{random.random()}")
        opponents = [t for t in league_teams if str(t.id) != str(team.id)]
        if not opponents:
            return {"skipped": True, "reason": "Sem oponente de scrim"}

        opp = rng.choice(opponents)
        my_ca = team.get_average_ca() if hasattr(team, "get_average_ca") else 140.0
        opp_ca = opp.get_average_ca() if hasattr(opp, "get_average_ca") else 140.0
        morale_state = await self.morale.get_state(str(team.id))
        morale_mod = (float(morale_state.get("team_morale") or 50) - 50) / 200.0
        chem_mod = (float(morale_state.get("chemistry") or 50) - 50) / 250.0

        # Probabilidade de vitória
        diff = (my_ca - opp_ca) / 200.0 + morale_mod + chem_mod
        p_win = clamp(0.5 + diff * 0.9, 0.22, 0.78)
        won = rng.random() < p_win
        score_for = rng.randint(1, 2) if won else rng.randint(0, 1)
        score_against = rng.randint(0, 1) if won else rng.randint(1, 2)
        if won and score_for <= score_against:
            score_for = score_against + 1
        if not won and score_against <= score_for:
            score_against = score_for + 1

        notes = rng.choice(SCRIM_NOTES_WIN if won else SCRIM_NOTES_LOSS)
        style = rng.choice(STYLES)

        # Moral / chemistry
        if won:
            await self.morale.apply_delta(
                str(team.id),
                morale=3.5,
                chemistry=4.0,
                bot_synergy=2.0,
                jg_mid_synergy=2.0,
                event=f"Scrim vitória vs {opp.abbreviation}: {notes}",
                kind="good",
            )
        else:
            await self.morale.apply_delta(
                str(team.id),
                morale=-2.0,
                chemistry=3.0,  # scrim ruim ainda treina coesão
                bot_synergy=1.0,
                jg_mid_synergy=1.0,
                event=f"Scrim derrota vs {opp.abbreviation}: {notes}",
                kind="mixed",
            )

        # Preferências reveladas do oponente (intel fraca)
        weak_role = rng.choice(list(PlayerRole)).value
        ban_pref = rng.choice(CHAMPIONS_BY_ROLE.get(PlayerRole.MID, ["Azir", "Orianna"]))

        report = {
            "type": "SCRIM",
            "won": won,
            "result": "WIN" if won else "LOSS",
            "score": f"{score_for}-{score_against}",
            "opponent_id": str(opp.id),
            "opponent_name": opp.name,
            "opponent_abbr": opp.abbreviation,
            "our_ca": round(my_ca, 1),
            "opp_ca": round(opp_ca, 1),
            "notes": notes,
            "practice_style": style,
            "intel_gained": {
                "opponent_id": str(opp.id),
                "opponent_name": opp.name,
                "likely_style": style if not won else rng.choice(STYLES),
                "weak_role": weak_role,
                "ban_suggestion": ban_pref,
                "confidence": 0.35 if won else 0.55,
            },
            "morale_delta": 3.5 if won else -2.0,
            "chemistry_delta": 4.0 if won else 3.0,
        }
        await redis_client.set_generic(self._scrim_key(str(team.id)), report)

        # Mescla intel se for oponente conhecido
        existing = await redis_client.get_generic(self._intel_key(str(team.id)))
        if not isinstance(existing, dict):
            existing = {"targets": {}}
        targets = existing.setdefault("targets", {})
        targets[str(opp.id)] = {
            **(targets.get(str(opp.id)) or {}),
            **report["intel_gained"],
            "source": "scrim",
        }
        existing["updated_from"] = "scrim"
        await redis_client.set_generic(self._intel_key(str(team.id)), existing)

        logger.info(
            f"[Practice] Scrim {team.abbreviation} vs {opp.abbreviation}: {report['result']}"
        )
        return report

    async def run_vod_review(
        self,
        team: Team,
        *,
        opponent_id: Optional[str] = None,
        opponent_name: Optional[str] = None,
        intensity: str = "LIGHT",
    ) -> Dict[str, Any]:
        rng = random.Random(f"vod-{team.id}-{opponent_id or 'gen'}")
        full = (intensity or "LIGHT").upper() == "FULL"

        # Resolve oponente
        opp_team = None
        if opponent_id:
            try:
                opp_team = await self.db.get(Team, uuid.UUID(str(opponent_id)))
            except Exception:
                opp_team = None
        if not opp_team and not opponent_name:
            # escolhe aleatório da liga se possível
            q = await self.db.execute(select(Team).options(selectinload(Team.players)))
            others = [t for t in q.scalars().all() if str(t.id) != str(team.id)]
            if others:
                opp_team = rng.choice(others)

        opp_name = (
            (opp_team.name if opp_team else None)
            or opponent_name
            or "próximo adversário"
        )
        opp_id = str(opp_team.id) if opp_team else (str(opponent_id) if opponent_id else None)

        findings = rng.sample(VOD_FINDINGS, k=3 if full else 2)
        style = rng.choice(STYLES)
        weak = rng.choice(list(PlayerRole)).value
        ban_pool = CHAMPIONS_BY_ROLE.get(PlayerRole(weak), ["Azir"])
        ban_sug = rng.choice(ban_pool) if ban_pool else "Azir"
        conf = 0.72 if full else 0.48

        await self.morale.apply_delta(
            str(team.id),
            morale=1.0 if full else 0.5,
            chemistry=2.5 if full else 1.2,
            event=f"VOD review ({'completo' if full else 'rápido'}) vs {opp_name}",
            kind="good",
        )

        report = {
            "type": "VOD",
            "intensity": "FULL" if full else "LIGHT",
            "opponent_id": opp_id,
            "opponent_name": opp_name,
            "findings": findings,
            "summary": findings[0] if findings else "Pouco material novo.",
            "likely_style": style,
            "weak_role": weak,
            "ban_suggestion": ban_sug,
            "confidence": conf,
            "draft_tips": [
                f"Priorize ban em {ban_sug} se aberto.",
                f"Explorar fraqueza de {weak}.",
                f"Preparar contra estilo {style}.",
            ],
        }
        await redis_client.set_generic(self._vod_key(str(team.id)), report)

        if opp_id:
            existing = await redis_client.get_generic(self._intel_key(str(team.id)))
            if not isinstance(existing, dict):
                existing = {"targets": {}}
            targets = existing.setdefault("targets", {})
            prev = targets.get(opp_id) or {}
            targets[opp_id] = {
                **prev,
                "opponent_id": opp_id,
                "opponent_name": opp_name,
                "likely_style": style,
                "weak_role": weak,
                "ban_suggestion": ban_sug,
                "confidence": max(float(prev.get("confidence") or 0), conf),
                "findings": findings,
                "source": "vod",
            }
            existing["updated_from"] = "vod"
            await redis_client.set_generic(self._intel_key(str(team.id)), existing)

        logger.info(f"[Practice] VOD {team.abbreviation} → {opp_name} ({intensity})")
        return report

    async def process_league_day(
        self,
        teams: Sequence[Team],
        day_type: str,
        *,
        managed_team_id: Optional[str] = None,
        managed_next_opponent_id: Optional[str] = None,
        managed_next_opponent_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for team in teams:
            # Scrims/VOD detalhados só no manager; IA recebe moral leve
            if managed_team_id and str(team.id) != str(managed_team_id):
                if (day_type or "").upper() == CalendarDayType.SCRIM.value:
                    # IA scrim simplificado: só moral aleatória pequena
                    try:
                        await self.morale.apply_delta(
                            str(team.id),
                            morale=random.uniform(-1, 2),
                            chemistry=random.uniform(0.5, 2.5),
                        )
                    except Exception:
                        pass
                continue
            try:
                results.append(
                    await self.process_day_for_team(
                        team,
                        day_type,
                        teams,
                        next_opponent_id=managed_next_opponent_id,
                        next_opponent_name=managed_next_opponent_name,
                    )
                )
            except Exception as exc:
                logger.error(
                    f"[Practice] Erro no time {getattr(team, 'name', '?')}: {exc}",
                    exc_info=True,
                )
        return results
