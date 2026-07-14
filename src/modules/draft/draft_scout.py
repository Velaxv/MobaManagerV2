# -*- coding: utf-8 -*-
"""
Draft Scout Advisor — recomenda bans e picks para o manager no Champion Select.

Considera:
  - Maestria do elenco (MAIN / SECONDARY / OFF_POOL)
  - Força no patch ativo (buff/nerf)
  - Função / role do campeão
  - Presença global (proxy de partidas no mundo + meta competitivo)
  - Counter vs oponente e ameaça dos mains inimigos
  - Balanço de composição (dano / frontline)
  - Qualidade do staff (meta_reading) → confiança e ruído

Não toma a decisão final (isso é do jogador); entrega top-N com razões legíveis.
"""

from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.models.champion import Champion
from src.models.player import Player
from src.models.staff import Staff
from src.models.team import Team
from src.modules.draft.draft_ai import CHAMPIONS_BY_ROLE, COUNTER_MAP
from src.modules.draft.snake_draft import DraftState
from src.shared.enums import ChampionPoolTier, DraftAction, DraftTeam, PlayerRole
from src.shared.global_meta_data import get_champion_meta
from src.shared.math_utils import clamp

logger = logging.getLogger(__name__)

ROLE_ORDER = [
    PlayerRole.TOP,
    PlayerRole.JUNGLE,
    PlayerRole.MID,
    PlayerRole.BOT,
    PlayerRole.SUPPORT,
]

# Classes com presença competitiva tipicamente alta no pro-play
_PRO_META_CLASS_BOOST = {
    "TANK_ENGAGE": 1.12,
    "TANK_WARDEN": 1.08,
    "BRUISER": 1.06,
    "MAGE_CONTROL": 1.10,
    "ENCHANTER": 1.05,
    "ASSASSIN": 0.98,
    "MARKSMAN_HYPERCARRY": 1.04,
    "MARKSMAN_UTILITY": 1.02,
    "MAGE_BURST": 1.00,
}

TIER_SCORE = {
    ChampionPoolTier.MAIN.value: 1.0,
    ChampionPoolTier.SECONDARY.value: 0.62,
    ChampionPoolTier.OFF_POOL.value: 0.12,
}


@dataclass
class ScoreBreakdown:
    mastery: float = 0.0
    patch: float = 0.0
    role_fit: float = 0.0
    global_meta: float = 0.0
    counter: float = 0.0
    threat: float = 0.0
    composition: float = 0.0
    total: float = 0.0
    reasons: List[Dict[str, Any]] = field(default_factory=list)


def _norm_name(name: str) -> str:
    return (name or "").strip().lower()


def _stable_unit(seed: str) -> float:
    """0..1 determinístico a partir de string."""
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class DraftScoutAdvisor:
    """
    Gera recomendações de ban/pick com contexto de patch e elenco.
    """

    def __init__(
        self,
        *,
        patch_bias: Optional[Dict[str, float]] = None,
        patch_version: Optional[str] = None,
        champions_by_name: Optional[Dict[str, Champion]] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.patch_bias = {k.lower(): float(v) for k, v in (patch_bias or {}).items()}
        self.patch_version = patch_version or "unknown"
        self.champions_by_name = {
            _norm_name(k): v for k, v in (champions_by_name or {}).items()
        }
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def advise(
        self,
        draft_state: DraftState,
        team_side: DraftTeam,
        my_team: Team,
        opponent_team: Team,
        staffs: Optional[List[Staff]] = None,
        *,
        focus_role: Optional[str] = None,
        limit: int = 5,
        opponent_knowledge: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        opponent_knowledge: mapa player_id -> entry de ScoutingService (progresso no hub).
        Quando o manager scoutou estrelas do oponente, bans nos mains delas sobem.
        """
        current = draft_state.current_action
        if not current:
            return self._empty_payload("Draft já concluído.")

        _phase, side, action = current
        if side != team_side:
            return self._empty_payload(
                f"Não é o turno de {team_side.value} (turno atual: {side.value})."
            )

        staff_info = self._pick_scout(staffs or list(getattr(my_team, "staffs", []) or []))
        meta_reading = float(staff_info["meta_reading"])
        confidence_base = clamp(0.35 + (meta_reading / 20.0) * 0.55, 0.35, 0.92)

        unavailable = draft_state.unavailable_champions
        my_starters = my_team.get_starters()
        opp_starters = opponent_team.get_starters()
        star_map = self._build_star_map(opp_starters, opponent_knowledge or {})

        if action == DraftAction.BAN:
            scored = self._score_bans(
                draft_state=draft_state,
                team_side=team_side,
                opp_starters=opp_starters,
                my_starters=my_starters,
                unavailable=unavailable,
                focus_role=focus_role,
                star_map=star_map,
            )
        else:
            scored = self._score_picks(
                draft_state=draft_state,
                team_side=team_side,
                my_starters=my_starters,
                opp_starters=opp_starters,
                unavailable=unavailable,
                focus_role=focus_role,
            )

        # Ruído proporcional à fraqueza do scout (meta_reading baixo)
        noise_amp = clamp(1.0 - meta_reading / 20.0, 0.05, 0.55)
        for item in scored:
            noise = (self.rng.random() - 0.5) * 18.0 * noise_amp
            item["score"] = round(clamp(item["score"] + noise, 0.0, 100.0), 1)
            item["confidence"] = round(
                clamp(confidence_base * (0.75 + item["score"] / 200.0), 0.2, 0.95),
                2,
            )

        scored.sort(key=lambda x: (-x["score"], x["champion"]))
        top = scored[: max(1, min(limit, 8))]
        for i, rec in enumerate(top, start=1):
            rec["priority"] = i
            rec["action"] = action.value if hasattr(action, "value") else str(action)

        intel = self._intel_note(meta_reading, action, self.patch_version, star_map)

        factors = [
            "maestria do elenco",
            "força no patch",
            "função do campeão",
            "presença global / win rate seed",
            "counters e ameaça inimiga",
            "balanço da composição",
        ]
        if star_map:
            factors.insert(0, "scouting de estrelas do oponente")

        return {
            "action": action.value if hasattr(action, "value") else str(action),
            "team": team_side.value,
            "current_turn": draft_state.current_turn,
            "scout": staff_info,
            "patch": {
                "version": self.patch_version,
                "bias_applied": bool(self.patch_bias),
            },
            "recommendations": top,
            "intel_note": intel,
            "factors": factors,
            "opponent_stars": [
                {
                    "player_id": pid,
                    "player_name": info["name"],
                    "star_score": info["star_score"],
                    "label": info["label"],
                    "scouting_progress": info["progress"],
                }
                for pid, info in sorted(
                    star_map.items(), key=lambda x: -x[1]["star_score"]
                )[:5]
            ],
        }

    # ------------------------------------------------------------------
    # Ban scoring
    # ------------------------------------------------------------------

    def _score_bans(
        self,
        *,
        draft_state: DraftState,
        team_side: DraftTeam,
        opp_starters: List[Player],
        my_starters: List[Player],
        unavailable: Set[str],
        focus_role: Optional[str],
        star_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        candidates: Set[str] = set()
        star_map = star_map or {}

        # Mains e secondary do oponente
        opp_mains: Dict[str, List[str]] = {}  # champ -> [player names]
        opp_main_players: Dict[str, List[Player]] = {}  # champ -> players
        for player in opp_starters:
            pool = player.champion_pool if isinstance(player.champion_pool, list) else []
            for item in pool:
                if not isinstance(item, dict):
                    continue
                champ = item.get("champion")
                tier = item.get("tier")
                if not champ or _norm_name(champ) in unavailable:
                    continue
                if tier in (ChampionPoolTier.MAIN.value, ChampionPoolTier.SECONDARY.value):
                    candidates.add(champ)
                    if tier == ChampionPoolTier.MAIN.value:
                        opp_mains.setdefault(champ, []).append(player.name)
                        opp_main_players.setdefault(champ, []).append(player)

        # Meta forte no patch + champs pro-play por role
        for role, champs in CHAMPIONS_BY_ROLE.items():
            for c in champs:
                if _norm_name(c) not in unavailable:
                    candidates.add(c)

        for name, bias in self.patch_bias.items():
            if bias > 0.02:
                # Resolve casing from champions map or capitalize
                resolved = self._resolve_champion_name(name)
                if resolved and _norm_name(resolved) not in unavailable:
                    candidates.add(resolved)

        # Também campeões carregados do DB
        for key, champ in self.champions_by_name.items():
            if key in unavailable:
                continue
            if champ.is_disabled_for_rework:
                continue
            candidates.add(champ.name)

        results: List[Dict[str, Any]] = []
        focus = (focus_role or "").upper() or None

        for champ_name in candidates:
            if _norm_name(champ_name) in unavailable:
                continue
            bd = self._base_meta_scores(champ_name, focus_role=focus)

            # Threat: main do oponente
            threat = 0.0
            owners = opp_mains.get(champ_name) or []
            # case-insensitive lookup
            if not owners:
                for k, v in opp_mains.items():
                    if _norm_name(k) == _norm_name(champ_name):
                        owners = v
                        break
            if owners:
                threat = 38.0
                bd.reasons.append(
                    {
                        "code": "OPP_MAIN",
                        "label": f"Main de {', '.join(owners[:2])}",
                        "weight": round(threat, 1),
                    }
                )
            else:
                # Secondary do oponente
                for player in opp_starters:
                    tier = player.get_champion_pool_tier(champ_name)
                    if tier == ChampionPoolTier.SECONDARY.value:
                        threat = 18.0
                        bd.reasons.append(
                            {
                                "code": "OPP_SECONDARY",
                                "label": f"Pool secundária de {player.name}",
                                "weight": threat,
                            }
                        )
                        break

            # Scouting de estrelas: se scoutamos o dono do main, prioriza ban
            star_boost = 0.0
            owners_players = opp_main_players.get(champ_name) or []
            if not owners_players:
                for k, plist in opp_main_players.items():
                    if _norm_name(k) == _norm_name(champ_name):
                        owners_players = plist
                        break
            for pl in owners_players:
                pid = str(getattr(pl, "id", "") or "")
                star = star_map.get(pid)
                if not star:
                    continue
                # star_score 0–100 → boost até +28
                boost = star["star_score"] * 0.28
                if boost > star_boost:
                    star_boost = boost
                bd.reasons.append(
                    {
                        "code": "SCOUTED_STAR",
                        "label": (
                            f"Estrela scoutada: {star['name']} "
                            f"({star['label']}, {star['progress']:.0f}% intel)"
                        ),
                        "weight": round(boost, 1),
                    }
                )
            threat += star_boost

            # Não banir o que o nosso time precisa (leve desincentivo se é main nosso)
            my_main_hit = False
            for player in my_starters:
                if player.get_champion_pool_tier(champ_name) == ChampionPoolTier.MAIN.value:
                    my_main_hit = True
                    break
            if my_main_hit:
                threat -= 12.0
                bd.reasons.append(
                    {
                        "code": "SELF_MAIN",
                        "label": "Também é main do nosso elenco — ban arriscado",
                        "weight": -12.0,
                    }
                )

            # Patch: banir buffs é mais valioso
            patch_s = bd.patch
            if patch_s > 0:
                threat += patch_s * 0.35

            # Global presence: campeões hyper-jogados merecem ban priority
            threat += bd.global_meta * 0.25

            total = clamp(
                threat * 0.45
                + patch_s * 0.25
                + bd.global_meta * 0.20
                + bd.role_fit * 0.10
                + star_boost * 0.35,
                0.0,
                100.0,
            )
            bd.threat = threat
            bd.total = total

            meta = self._global_presence(champ_name)
            results.append(
                self._to_recommendation(
                    champion=champ_name,
                    role=self._primary_role_str(champ_name),
                    breakdown=bd,
                    summary=self._ban_summary(champ_name, owners, meta, star_boost > 0),
                    meta=meta,
                    for_player=owners[0] if owners else None,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Pick scoring
    # ------------------------------------------------------------------

    def _score_picks(
        self,
        *,
        draft_state: DraftState,
        team_side: DraftTeam,
        my_starters: List[Player],
        opp_starters: List[Player],
        unavailable: Set[str],
        focus_role: Optional[str],
    ) -> List[Dict[str, Any]]:
        my_picks = (
            draft_state.blue_picks
            if team_side == DraftTeam.BLUE
            else draft_state.red_picks
        )
        opp_picks = (
            draft_state.red_picks
            if team_side == DraftTeam.BLUE
            else draft_state.blue_picks
        )
        my_picked_roles = {p.get("role_hint") for p in my_picks}
        remaining = [r for r in ROLE_ORDER if r.value not in my_picked_roles]
        if not remaining:
            remaining = [PlayerRole.MID]

        # Role alvo: focus do FE ou role com counter possível / primeira aberta
        target_role = remaining[0]
        if focus_role:
            fr = focus_role.upper()
            match = next((r for r in remaining if r.value == fr), None)
            if match:
                target_role = match
        else:
            for role in remaining:
                if any(p.get("role_hint") == role.value for p in opp_picks):
                    target_role = role
                    break

        player = next((p for p in my_starters if p.role == target_role), None)
        if not player and my_starters:
            player = my_starters[0]
            target_role = player.role or target_role

        # Candidates: pool do jogador + meta da role + patch buffs da role
        candidates: Set[str] = set()
        if player:
            pool = player.champion_pool if isinstance(player.champion_pool, list) else []
            for item in pool:
                if isinstance(item, dict) and item.get("champion"):
                    candidates.add(item["champion"])

        for c in CHAMPIONS_BY_ROLE.get(target_role, []):
            candidates.add(c)

        for key, champ in self.champions_by_name.items():
            if champ.is_disabled_for_rework:
                continue
            pr = (champ.primary_role or "").upper()
            sr = (champ.secondary_role or "").upper() if champ.secondary_role else ""
            # ADC no DB às vezes; FE usa BOT
            if pr == "ADC":
                pr = "BOT"
            if sr == "ADC":
                sr = "BOT"
            if pr == target_role.value or sr == target_role.value:
                candidates.add(champ.name)

        opp_lane = next(
            (p for p in opp_picks if p.get("role_hint") == target_role.value), None
        )
        opp_champ = opp_lane.get("champion") if opp_lane else None

        # Composição atual do time
        my_champ_objs = [
            self.champions_by_name.get(_norm_name(p["champion"]))
            for p in my_picks
            if p.get("champion")
        ]
        my_champ_objs = [c for c in my_champ_objs if c is not None]
        ad_count = sum(1 for c in my_champ_objs if (c.damage_type or "").upper() == "AD")
        ap_count = sum(1 for c in my_champ_objs if (c.damage_type or "").upper() == "AP")
        frontline_n = sum(
            1
            for c in my_champ_objs
            if (c.class_type or "")
            in ("TANK_ENGAGE", "TANK_WARDEN", "BRUISER")
        )

        results: List[Dict[str, Any]] = []
        for champ_name in candidates:
            if _norm_name(champ_name) in unavailable:
                continue

            bd = self._base_meta_scores(champ_name, focus_role=target_role.value)

            # Mastery
            tier = (
                player.get_champion_pool_tier(champ_name)
                if player
                else ChampionPoolTier.OFF_POOL.value
            )
            mastery = TIER_SCORE.get(tier, 0.12) * 40.0
            bd.mastery = mastery
            if tier == ChampionPoolTier.MAIN.value:
                bd.reasons.append(
                    {
                        "code": "MASTERY_MAIN",
                        "label": f"Main de {player.name if player else 'titular'}",
                        "weight": round(mastery, 1),
                    }
                )
            elif tier == ChampionPoolTier.SECONDARY.value:
                bd.reasons.append(
                    {
                        "code": "MASTERY_SEC",
                        "label": f"Secundário de {player.name if player else 'titular'}",
                        "weight": round(mastery, 1),
                    }
                )
            else:
                bd.reasons.append(
                    {
                        "code": "MASTERY_OFF",
                        "label": "Off-pool — risco mecânico alto",
                        "weight": round(mastery, 1),
                    }
                )

            # Counter: COUNTER_MAP[X] = campeões que X countera
            counter_s = 0.0
            if opp_champ:
                # Champ atual countera o oponente?
                countered_by_us = COUNTER_MAP.get(champ_name, [])
                # case-insensitive keys
                if not countered_by_us:
                    for k, val in COUNTER_MAP.items():
                        if _norm_name(k) == _norm_name(champ_name):
                            countered_by_us = val
                            break
                if any(_norm_name(c) == _norm_name(opp_champ) for c in countered_by_us):
                    counter_s = 28.0
                    bd.reasons.append(
                        {
                            "code": "COUNTER",
                            "label": f"Counter de {opp_champ}",
                            "weight": counter_s,
                        }
                    )
                # Oponente countera a gente?
                opp_counters = COUNTER_MAP.get(opp_champ, [])
                if not opp_counters:
                    for k, val in COUNTER_MAP.items():
                        if _norm_name(k) == _norm_name(opp_champ):
                            opp_counters = val
                            break
                if any(_norm_name(c) == _norm_name(champ_name) for c in opp_counters):
                    counter_s -= 20.0
                    bd.reasons.append(
                        {
                            "code": "COUNTERED",
                            "label": f"Sofre contra {opp_champ}",
                            "weight": -20.0,
                        }
                    )
            bd.counter = counter_s

            # Composition needs
            comp_s = 0.0
            cobj = self.champions_by_name.get(_norm_name(champ_name))
            if cobj:
                dt = (cobj.damage_type or "").upper()
                if ad_count >= 3 and dt == "AP":
                    comp_s += 12.0
                    bd.reasons.append(
                        {
                            "code": "COMP_AP",
                            "label": "Equilibra dano (time já AD-heavy)",
                            "weight": 12.0,
                        }
                    )
                elif ap_count >= 3 and dt == "AD":
                    comp_s += 12.0
                    bd.reasons.append(
                        {
                            "code": "COMP_AD",
                            "label": "Equilibra dano (time já AP-heavy)",
                            "weight": 12.0,
                        }
                    )
                if frontline_n == 0 and (cobj.class_type or "") in (
                    "TANK_ENGAGE",
                    "TANK_WARDEN",
                    "BRUISER",
                ):
                    comp_s += 14.0
                    bd.reasons.append(
                        {
                            "code": "COMP_FRONT",
                            "label": "Traz frontline à composição",
                            "weight": 14.0,
                        }
                    )
            bd.composition = comp_s

            total = clamp(
                mastery * 0.95
                + bd.patch * 0.55
                + bd.role_fit * 0.35
                + bd.global_meta * 0.30
                + counter_s
                + comp_s,
                0.0,
                100.0,
            )
            # Off-pool hard cap unless extraordinary meta
            if tier == ChampionPoolTier.OFF_POOL.value:
                total = min(total, 48.0)

            bd.total = total
            meta = self._global_presence(champ_name)
            results.append(
                self._to_recommendation(
                    champion=champ_name,
                    role=target_role.value,
                    breakdown=bd,
                    summary=self._pick_summary(
                        champ_name, player, tier, opp_champ, meta
                    ),
                    meta=meta,
                    for_player=player.name if player else None,
                    pool_tier=tier,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Shared scoring helpers
    # ------------------------------------------------------------------

    def _base_meta_scores(
        self, champion: str, focus_role: Optional[str] = None
    ) -> ScoreBreakdown:
        bd = ScoreBreakdown()
        key = _norm_name(champion)
        cobj = self.champions_by_name.get(key)

        # Patch
        bias = float(self.patch_bias.get(key, 0.0) or 0.0)
        # bias típico ~ ±0.05–0.15 → scale to 0–30
        patch_s = clamp(bias * 120.0, -25.0, 30.0)
        bd.patch = patch_s
        if bias > 0.02:
            bd.reasons.append(
                {
                    "code": "PATCH_BUFF",
                    "label": f"Buff no patch {self.patch_version}",
                    "weight": round(patch_s, 1),
                }
            )
        elif bias < -0.02:
            bd.reasons.append(
                {
                    "code": "PATCH_NERF",
                    "label": f"Nerf no patch {self.patch_version}",
                    "weight": round(patch_s, 1),
                }
            )

        # Role fit
        role_fit = 12.0
        if cobj:
            pr = (cobj.primary_role or "").upper()
            sr = (cobj.secondary_role or "").upper() if cobj.secondary_role else ""
            if pr == "ADC":
                pr = "BOT"
            if sr == "ADC":
                sr = "BOT"
            fr = (focus_role or "").upper()
            if fr and pr == fr:
                role_fit = 22.0
                bd.reasons.append(
                    {
                        "code": "ROLE_PRIMARY",
                        "label": f"Função primária: {pr}",
                        "weight": role_fit,
                    }
                )
            elif fr and sr == fr:
                role_fit = 14.0
                bd.reasons.append(
                    {
                        "code": "ROLE_FLEX",
                        "label": f"Flex pick ({pr}/{sr})",
                        "weight": role_fit,
                    }
                )
            else:
                role_fit = 8.0
        bd.role_fit = role_fit

        # Global meta presence (0–30)
        meta = self._global_presence(champion)
        presence = meta["presence_score"]  # 0–100
        global_s = presence * 0.30
        bd.global_meta = global_s
        wr = meta.get("win_rate_proxy")
        pr = meta.get("pick_rate_proxy")
        src = meta.get("source") or "synthetic"
        bd.reasons.append(
            {
                "code": "GLOBAL_META",
                "label": (
                    f"{meta['games_played_world']:,} jogos · "
                    f"{pr}% PR · {wr}% WR · tier {meta['tier']}"
                    + (" (seed)" if src == "seed_meta" else "")
                ),
                "weight": round(global_s, 1),
            }
        )

        return bd

    def _global_presence(self, champion: str) -> Dict[str, Any]:
        """
        Meta global: prefere seed `global_meta_data` (win/pick rate + games);
        fallback determinístico por atributos do campeão.
        """
        key = _norm_name(champion)
        cobj = self.champions_by_name.get(key)
        unit = _stable_unit(f"{key}|{self.patch_version}")
        bias = float(self.patch_bias.get(key, 0.0) or 0.0)
        seeded = get_champion_meta(champion)

        if seeded:
            games = int(seeded.get("games_played") or 100_000)
            pick_rate = float(seeded.get("pick_rate") or 3.0)
            win_rate = float(seeded.get("win_rate") or 50.0)
            pro = float(seeded.get("pro_presence") or 0.5)
            # Presence 0–100: pick rate + pro + patch
            presence = clamp(
                pick_rate * 4.5 + pro * 35.0 + (win_rate - 50.0) * 3.0 + bias * 40.0,
                5.0,
                100.0,
            )
            # Patch move win rate levemente
            win_rate = round(clamp(win_rate + bias * 12.0, 44.0, 56.5), 1)
            source = "seed_meta"
        else:
            base = 45.0 + unit * 40.0
            if cobj:
                power = (
                    float(cobj.early_game_power or 50)
                    + float(cobj.late_game_scaling or 50)
                    + float(cobj.utility or 50)
                ) / 3.0
                base = base * 0.55 + power * 0.45
                class_boost = _PRO_META_CLASS_BOOST.get(
                    (cobj.class_type or "").upper(), 1.0
                )
                base *= class_boost
                mech = float(cobj.mechanical_difficulty or 50)
                if mech > 75:
                    base *= 0.94
            base *= 1.0 + bias * 2.5
            presence = clamp(base, 5.0, 100.0)
            games = int(80_000 + (presence / 100.0) ** 1.4 * 2_400_000 + unit * 50_000)
            pick_rate = round(presence * 0.18, 1)
            win_rate = round(
                clamp(48.0 + (presence - 50) * 0.06 + bias * 25.0, 44.0, 56.0), 1
            )
            source = "synthetic"

        if presence >= 78:
            tier = "S"
        elif presence >= 65:
            tier = "A"
        elif presence >= 50:
            tier = "B"
        elif presence >= 35:
            tier = "C"
        else:
            tier = "D"

        return {
            "games_played_world": games,
            "presence_score": round(presence, 1),
            "tier": tier,
            "pick_rate_proxy": round(float(pick_rate), 1),
            "win_rate_proxy": round(float(win_rate), 1),
            "source": source,
        }

    def _to_recommendation(
        self,
        *,
        champion: str,
        role: Optional[str],
        breakdown: ScoreBreakdown,
        summary: str,
        meta: Dict[str, Any],
        for_player: Optional[str] = None,
        pool_tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Top reasons by abs weight
        reasons = sorted(
            breakdown.reasons,
            key=lambda r: abs(float(r.get("weight") or 0)),
            reverse=True,
        )[:5]
        return {
            "champion": champion,
            "role": role,
            "score": round(breakdown.total, 1),
            "confidence": 0.5,
            "summary": summary,
            "reasons": reasons,
            "factors": {
                "mastery": round(breakdown.mastery, 1),
                "patch": round(breakdown.patch, 1),
                "role_fit": round(breakdown.role_fit, 1),
                "global_meta": round(breakdown.global_meta, 1),
                "counter": round(breakdown.counter, 1),
                "threat": round(breakdown.threat, 1),
                "composition": round(breakdown.composition, 1),
            },
            "global_meta": meta,
            "for_player": for_player,
            "pool_tier": pool_tier,
        }

    def _ban_summary(
        self,
        champion: str,
        owners: List[str],
        meta: Dict[str, Any],
        scouted_star: bool = False,
    ) -> str:
        bits = []
        if scouted_star:
            bits.append("estrela scoutada do oponente")
        if owners:
            bits.append(f"ameaça o pool de {owners[0]}")
        if meta.get("tier") in ("S", "A"):
            wr = meta.get("win_rate_proxy")
            bits.append(
                f"meta {meta['tier']} ({meta['games_played_world']:,} jogos"
                + (f", {wr}% WR" if wr is not None else "")
                + ")"
            )
        bias = float(self.patch_bias.get(_norm_name(champion), 0) or 0)
        if bias > 0.02:
            bits.append(f"buff no patch {self.patch_version}")
        elif bias < -0.02:
            bits.append("já nerfado — prioridade menor")
        if not bits:
            bits.append("presença sólida no competitivo atual")
        return f"Scout sugere banir {champion}: " + "; ".join(bits) + "."

    def _build_star_map(
        self,
        opp_starters: List[Player],
        knowledge: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Estrelas reveladas pelo scouting de hub.
        progress baixo → pouco intel; progress alto + CA/BMA altos → estrela.
        """
        stars: Dict[str, Dict[str, Any]] = {}
        for player in opp_starters:
            pid = str(getattr(player, "id", "") or "")
            if not pid:
                continue
            entry = knowledge.get(pid) or {}
            progress = float(entry.get("progress") or 0)
            # Sem scouting nenhum: só CA bruto com peso baixo
            ca = float(getattr(player, "current_ability", 100) or 100)
            ca_norm = clamp(ca / 200.0, 0.0, 1.0)

            bma = float(getattr(player, "big_match_aptitude", 10) or 10)
            consistency = float(getattr(player, "consistency", 10) or 10)
            # Só confia em BMA/consistency com progresso suficiente
            if progress < 35:
                mental = 0.45  # desconhecido
                label = "desconhecido"
            elif progress < 70:
                mental = clamp(((bma + consistency) / 2.0) / 20.0, 0.2, 1.0) * 0.7
                label = "parcialmente scoutado"
            else:
                mental = clamp(((bma + consistency) / 2.0) / 20.0, 0.2, 1.0)
                label = "scoutado" if progress < 100 else "totalmente revelado"

            # progress multiplica confiança no perfil
            conf = clamp(0.25 + progress / 100.0 * 0.75, 0.25, 1.0)
            star_score = clamp((ca_norm * 0.62 + mental * 0.38) * conf * 100.0, 0.0, 100.0)

            # Só entra no mapa se progress > 0 ou CA elite óbvio
            if progress <= 0 and ca < 155:
                continue
            if star_score < 40 and progress < 35:
                continue

            if star_score >= 78:
                label = f"estrela ({label})"
            elif star_score >= 60:
                label = f"ameaça ({label})"
            else:
                label = f"monitorado ({label})"

            stars[pid] = {
                "name": player.name,
                "star_score": round(star_score, 1),
                "progress": progress,
                "label": label,
                "ca": ca,
            }
        return stars

    def _pick_summary(
        self,
        champion: str,
        player: Optional[Player],
        tier: str,
        opp_champ: Optional[str],
        meta: Dict[str, Any],
    ) -> str:
        bits = []
        if player:
            if tier == ChampionPoolTier.MAIN.value:
                bits.append(f"conforto máximo de {player.name}")
            elif tier == ChampionPoolTier.SECONDARY.value:
                bits.append(f"bom encaixe no pool de {player.name}")
            else:
                bits.append(f"{player.name} joga off-pool (risco)")
        bias = float(self.patch_bias.get(_norm_name(champion), 0) or 0)
        if bias > 0.02:
            bits.append(f"forte no patch {self.patch_version}")
        if opp_champ:
            # check counter
            counters = [
                k
                for k, val in COUNTER_MAP.items()
                if any(_norm_name(c) == _norm_name(opp_champ) for c in val)
            ]
            if any(_norm_name(c) == _norm_name(champion) for c in counters):
                bits.append(f"counter de {opp_champ}")
        bits.append(f"presença global {meta.get('tier', '?')}")
        return f"Scout sugere pickar {champion}: " + "; ".join(bits) + "."

    def _pick_scout(self, staffs: List[Staff]) -> Dict[str, Any]:
        if not staffs:
            return {
                "name": "Scout da casa",
                "role": "STRATEGIC_COACH",
                "meta_reading": 10.0,
                "communication": 10.0,
            }
        # Prefere strategic coach com maior meta_reading
        ordered = sorted(
            staffs,
            key=lambda s: (
                1 if (s.role or "") == "STRATEGIC_COACH" else 0,
                float(s.meta_reading or 0),
            ),
            reverse=True,
        )
        s = ordered[0]
        return {
            "name": s.name,
            "role": s.role,
            "meta_reading": round(float(s.meta_reading or 10), 1),
            "communication": round(float(s.communication or 10), 1),
        }

    def _intel_note(
        self,
        meta_reading: float,
        action: DraftAction,
        patch: str,
        star_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> str:
        act = "banimentos" if action == DraftAction.BAN else "picks"
        if meta_reading >= 16:
            quality = "leitura de meta elite"
        elif meta_reading >= 12:
            quality = "boa leitura de meta"
        elif meta_reading >= 8:
            quality = "leitura de meta mediana"
        else:
            quality = "leitura de meta limitada — confie com cautela"
        note = (
            f"Comissão com {quality} (meta_reading {meta_reading:.0f}/20). "
            f"Sugestões de {act} no patch {patch}, ponderando maestria, counters, "
            f"win rate seed e presença global."
        )
        if star_map:
            top = sorted(star_map.values(), key=lambda s: -s["star_score"])[:2]
            names = ", ".join(f"{s['name']} ({s['label']})" for s in top)
            note += f" Intel de scouting: {names}."
        return note

    def _primary_role_str(self, champion: str) -> Optional[str]:
        cobj = self.champions_by_name.get(_norm_name(champion))
        if cobj and cobj.primary_role:
            r = cobj.primary_role.upper()
            return "BOT" if r == "ADC" else r
        for role, champs in CHAMPIONS_BY_ROLE.items():
            if any(_norm_name(c) == _norm_name(champion) for c in champs):
                return role.value
        return None

    def _resolve_champion_name(self, lower_name: str) -> Optional[str]:
        key = _norm_name(lower_name)
        if key in self.champions_by_name:
            return self.champions_by_name[key].name
        for role_champs in CHAMPIONS_BY_ROLE.values():
            for c in role_champs:
                if _norm_name(c) == key:
                    return c
        # Title-case fallback
        return lower_name.title() if lower_name else None

    def _empty_payload(self, message: str) -> Dict[str, Any]:
        return {
            "action": None,
            "team": None,
            "current_turn": None,
            "scout": None,
            "patch": {"version": self.patch_version, "bias_applied": bool(self.patch_bias)},
            "recommendations": [],
            "intel_note": message,
            "factors": [],
            "error": message,
        }
