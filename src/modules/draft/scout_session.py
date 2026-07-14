# -*- coding: utf-8 -*-
"""
Sessão de dicas do Draft Scout + avaliação pós-partida.

Redis:
  draft:scout:session:{session_id}
  career:scout:history:{team_id}  (lista das últimas avaliações)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.redis_client import redis_client
from src.shared.enums import ChampionPoolTier

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20


def _norm(name: str) -> str:
    return (name or "").strip().lower()


class ScoutSessionService:
    def __init__(self) -> None:
        pass

    def _session_key(self, session_id: str) -> str:
        return f"draft:scout:session:{session_id}"

    def _history_key(self, team_id: str) -> str:
        return f"career:scout:history:{team_id}"

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        data = await redis_client.get_generic(self._session_key(session_id))
        return data if isinstance(data, dict) else None

    async def ensure_session(
        self,
        session_id: Optional[str],
        *,
        managed_team_id: str,
        blue_team_id: str,
        red_team_id: str,
        managed_side: str,
        patch_version: Optional[str] = None,
        scout_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        sid = session_id or str(uuid.uuid4())
        existing = await self.get_session(sid)
        if existing:
            return existing
        session = {
            "session_id": sid,
            "managed_team_id": str(managed_team_id),
            "blue_team_id": str(blue_team_id),
            "red_team_id": str(red_team_id),
            "managed_side": (managed_side or "BLUE").upper(),
            "patch_version": patch_version,
            "scout_name": scout_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tips": [],  # dicas oferecidas por turno
            "actions": [],  # ações do manager
            "evaluation": None,
        }
        await redis_client.set_generic(self._session_key(sid), session)
        return session

    async def append_tip(
        self,
        session_id: str,
        tip: Dict[str, Any],
    ) -> Dict[str, Any]:
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Sessão de scout não encontrada.")
        tips = list(session.get("tips") or [])
        # Substitui tip do mesmo turno se reconsultar
        turn = tip.get("current_turn")
        tips = [t for t in tips if t.get("current_turn") != turn]
        tips.append(tip)
        tips.sort(key=lambda t: int(t.get("current_turn") or 0))
        session["tips"] = tips
        if tip.get("scout_name"):
            session["scout_name"] = tip["scout_name"]
        if tip.get("patch_version"):
            session["patch_version"] = tip["patch_version"]
        await redis_client.set_generic(self._session_key(session_id), session)
        return session

    async def record_action(
        self,
        session_id: str,
        *,
        current_turn: int,
        action: str,
        champion: str,
        role: Optional[str] = None,
        followed_priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Sessão de scout não encontrada.")

        tip = next(
            (t for t in (session.get("tips") or []) if t.get("current_turn") == current_turn),
            None,
        )
        followed = False
        followed_priority = followed_priority
        if tip and champion:
            recs = tip.get("recommendations") or []
            for rec in recs:
                if _norm(rec.get("champion") or "") == _norm(champion):
                    followed = True
                    if followed_priority is None:
                        followed_priority = rec.get("priority")
                    break

        entry = {
            "current_turn": int(current_turn),
            "action": (action or "").upper(),
            "champion": champion,
            "role": role,
            "followed_scout": followed,
            "followed_priority": followed_priority,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        actions = list(session.get("actions") or [])
        actions = [a for a in actions if a.get("current_turn") != current_turn]
        actions.append(entry)
        actions.sort(key=lambda a: int(a.get("current_turn") or 0))
        session["actions"] = actions
        await redis_client.set_generic(self._session_key(session_id), session)
        return session

    async def bind_match(self, session_id: str, match_id: str) -> None:
        session = await self.get_session(session_id)
        if not session:
            return
        session["match_id"] = match_id
        await redis_client.set_generic(self._session_key(session_id), session)

    def evaluate_session(
        self,
        session: Dict[str, Any],
        *,
        my_bans: List[str],
        opp_bans: List[str],
        my_picks: List[Dict[str, str]],
        opp_picks: List[Dict[str, str]],
        opp_starters_pools: Optional[List[Dict[str, Any]]] = None,
        winner_side: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Avalia dicas vs draft final.

        BAN hit:
          - Scout top-3 recomendou ban X e manager baniu X e X era MAIN/SECONDARY do oponente
          - OU scout top-1 era MAIN do oponente e foi banido
        BAN miss:
          - Scout top-1 MAIN do oponente e manager não baniu e oponente pickou
        PICK hit:
          - Manager pickou campeão que estava no top-3 do scout naquele turno / role
        """
        managed_side = (session.get("managed_side") or "BLUE").upper()
        tips = session.get("tips") or []
        actions = session.get("actions") or []
        action_by_turn = {int(a["current_turn"]): a for a in actions if "current_turn" in a}

        my_ban_set = {_norm(c) for c in my_bans}
        opp_pick_names = {_norm(p.get("champion") or p.get("name") or "") for p in opp_picks}
        my_pick_names = {_norm(p.get("champion") or p.get("name") or "") for p in my_picks}

        # Pool oponente: champ -> best tier
        opp_pool: Dict[str, str] = {}
        for starter in opp_starters_pools or []:
            pool = starter.get("champion_pool") or starter.get("championPool") or []
            for item in pool:
                if not isinstance(item, dict):
                    continue
                ch = item.get("champion")
                tier = item.get("tier") or ChampionPoolTier.SECONDARY.value
                if not ch:
                    continue
                key = _norm(ch)
                prev = opp_pool.get(key)
                if prev == ChampionPoolTier.MAIN.value:
                    continue
                if tier == ChampionPoolTier.MAIN.value or not prev:
                    opp_pool[key] = tier

        verdicts: List[Dict[str, Any]] = []
        hits = 0
        misses = 0
        partials = 0
        followed_count = 0
        actionable = 0

        for tip in tips:
            turn = int(tip.get("current_turn") or 0)
            action = (tip.get("action") or "").upper()
            recs = tip.get("recommendations") or []
            if not recs:
                continue
            top = recs[0]
            top_champs = [_norm(r.get("champion") or "") for r in recs[:3]]
            player_act = action_by_turn.get(turn)
            chosen = _norm((player_act or {}).get("champion") or "")
            followed = bool((player_act or {}).get("followed_scout"))

            if followed:
                followed_count += 1
            actionable += 1

            if action == "BAN":
                top_name = top.get("champion") or ""
                top_key = _norm(top_name)
                tier = opp_pool.get(top_key)
                banned = top_key in my_ban_set or (chosen and chosen == top_key)
                opp_picked = top_key in opp_pick_names

                if banned and tier in (
                    ChampionPoolTier.MAIN.value,
                    ChampionPoolTier.SECONDARY.value,
                ):
                    status = "HIT"
                    hits += 1
                    detail = f"Ban em {top_name} acertou pool {tier} do oponente"
                elif banned and not tier:
                    status = "PARTIAL"
                    partials += 1
                    detail = f"Ban em {top_name} (não era pool prioritário conhecido)"
                elif not banned and opp_picked and tier == ChampionPoolTier.MAIN.value:
                    status = "MISS"
                    misses += 1
                    detail = f"Scout pediu ban de {top_name} (MAIN) e oponente pickou"
                elif followed and banned:
                    status = "PARTIAL"
                    partials += 1
                    detail = f"Seguiu ban de {top_name}"
                else:
                    status = "NEUTRAL"
                    detail = f"Dica de ban {top_name} sem impacto claro"
                verdicts.append(
                    {
                        "turn": turn,
                        "action": "BAN",
                        "champion": top_name,
                        "status": status,
                        "detail": detail,
                        "followed": followed,
                    }
                )
            else:
                # PICK
                top_name = top.get("champion") or ""
                role = top.get("role")
                # match by pick in same role from top-3
                hit_champ = None
                for r in recs[:3]:
                    ck = _norm(r.get("champion") or "")
                    if ck and ck in my_pick_names:
                        hit_champ = r.get("champion")
                        break
                if hit_champ and followed:
                    status = "HIT"
                    hits += 1
                    detail = f"Pick de {hit_champ} alinhado ao scout"
                elif hit_champ:
                    status = "HIT"
                    hits += 1
                    detail = f"Comp acabou com {hit_champ} (no top-3 do scout)"
                elif chosen and chosen in top_champs:
                    status = "HIT"
                    hits += 1
                    detail = f"Seguiu pick {player_act.get('champion')}"
                elif followed:
                    status = "PARTIAL"
                    partials += 1
                    detail = "Seguiu dica mas contexto mudou"
                else:
                    status = "NEUTRAL"
                    detail = f"Pick sugerido {top_name} não usado"
                    if role:
                        # se a role foi preenchida com off-suggestion
                        my_role_pick = next(
                            (
                                p
                                for p in my_picks
                                if (p.get("role") or p.get("role_hint")) == role
                            ),
                            None,
                        )
                        if my_role_pick and _norm(my_role_pick.get("champion") or "") not in top_champs:
                            if any(
                                opp_pool.get(_norm(r.get("champion") or ""))
                                == ChampionPoolTier.MAIN.value
                                for r in recs[:1]
                            ):
                                status = "MISS"
                                misses += 1
                                detail = f"Ignorou {top_name} sugerido para {role}"
                verdicts.append(
                    {
                        "turn": turn,
                        "action": "PICK",
                        "champion": top_name,
                        "status": status,
                        "detail": detail,
                        "followed": followed,
                        "role": role,
                    }
                )

        total_scored = hits + misses + partials
        accuracy = (
            round((hits + 0.5 * partials) / total_scored, 3) if total_scored else None
        )
        follow_rate = (
            round(followed_count / actionable, 3) if actionable else None
        )

        grade = "C"
        if accuracy is None:
            grade = "—"
        elif accuracy >= 0.75:
            grade = "A"
        elif accuracy >= 0.55:
            grade = "B"
        elif accuracy >= 0.35:
            grade = "C"
        else:
            grade = "D"

        managed_won = None
        if winner_side:
            managed_won = (winner_side or "").upper() == managed_side

        summary_bits = []
        if hits:
            summary_bits.append(f"{hits} acerto(s)")
        if misses:
            summary_bits.append(f"{misses} erro(s)")
        if partials:
            summary_bits.append(f"{partials} parcial(is)")
        if not summary_bits:
            summary_bits.append("sem dicas avaliáveis")

        evaluation = {
            "session_id": session.get("session_id"),
            "managed_team_id": session.get("managed_team_id"),
            "scout_name": session.get("scout_name"),
            "patch_version": session.get("patch_version"),
            "hits": hits,
            "misses": misses,
            "partials": partials,
            "neutral": max(0, actionable - hits - misses - partials),
            "accuracy": accuracy,
            "follow_rate": follow_rate,
            "followed_count": followed_count,
            "actionable_tips": actionable,
            "grade": grade,
            "verdicts": verdicts,
            "managed_won": managed_won,
            "winner_side": winner_side,
            "summary": (
                f"Scout {session.get('scout_name') or 'da casa'}: "
                + ", ".join(summary_bits)
                + (f" · grade {grade}" if grade != "—" else "")
                + (f" · precisão {int(accuracy * 100)}%" if accuracy is not None else "")
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
        return evaluation

    async def finalize(
        self,
        session_id: str,
        evaluation: Dict[str, Any],
    ) -> Dict[str, Any]:
        session = await self.get_session(session_id)
        if not session:
            session = {"session_id": session_id}
        session["evaluation"] = evaluation
        await redis_client.set_generic(self._session_key(session_id), session)

        team_id = session.get("managed_team_id") or evaluation.get("managed_team_id")
        if team_id:
            hist = await redis_client.get_generic(self._history_key(str(team_id)))
            if not isinstance(hist, list):
                hist = []
            # compact history entry
            hist.insert(
                0,
                {
                    "session_id": session_id,
                    "match_id": session.get("match_id"),
                    "grade": evaluation.get("grade"),
                    "accuracy": evaluation.get("accuracy"),
                    "hits": evaluation.get("hits"),
                    "misses": evaluation.get("misses"),
                    "partials": evaluation.get("partials"),
                    "summary": evaluation.get("summary"),
                    "scout_name": evaluation.get("scout_name"),
                    "patch_version": evaluation.get("patch_version"),
                    "managed_won": evaluation.get("managed_won"),
                    "evaluated_at": evaluation.get("evaluated_at"),
                },
            )
            hist = hist[:HISTORY_LIMIT]
            await redis_client.set_generic(self._history_key(str(team_id)), hist)
        return evaluation

    async def get_history(self, team_id: str) -> List[Dict[str, Any]]:
        hist = await redis_client.get_generic(self._history_key(str(team_id)))
        return hist if isinstance(hist, list) else []

    async def evaluate_and_store(
        self,
        session_id: str,
        *,
        my_bans: List[str],
        opp_bans: List[str],
        my_picks: List[Dict[str, str]],
        opp_picks: List[Dict[str, str]],
        opp_starters_pools: Optional[List[Dict[str, Any]]] = None,
        winner_side: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        session = await self.get_session(session_id)
        if not session:
            return None
        if session.get("evaluation"):
            return session["evaluation"]
        evaluation = self.evaluate_session(
            session,
            my_bans=my_bans,
            opp_bans=opp_bans,
            my_picks=my_picks,
            opp_picks=opp_picks,
            opp_starters_pools=opp_starters_pools,
            winner_side=winner_side,
        )
        await self.finalize(session_id, evaluation)
        return evaluation
