"""
IA de Draft para o League of Legends Manager.

Responsável por tomar decisões inteligentes de Picks e Bans durante o draft.
Implementa lógica de:
    - Banir campeões fortes do oponente (MAIN tier dele).
    - Escolher campeões que estejam na Champion Pool dos jogadores do time.
    - Aplicar Counter-Picks com base nas escolhas já reveladas pelo adversário.
    - Calcular a penalidade final de draft para o Match Engine.
"""

import logging
import random
from typing import List, Dict, Set, Optional, Tuple

from src.shared.enums import DraftAction, DraftTeam, PlayerRole, ChampionPoolTier
from src.modules.draft.snake_draft import DraftState, DRAFT_ORDER

logger = logging.getLogger(__name__)

# Banco de dados estático de campeões por posição e seus respectivos counters
CHAMPIONS_BY_ROLE: Dict[PlayerRole, List[str]] = {
    PlayerRole.TOP: ["Aatrox", "Jax", "Gnar", "Sion", "Irelia", "Ornn", "Fiora", "Jayce", "Renekton", "Camille"],
    PlayerRole.JUNGLE: ["Lee Sin", "Graves", "Kindred", "Sejuani", "Viego", "Jarvan IV", "Nocturne", "Elise", "Maokai", "Wukong"],
    PlayerRole.MID: ["Azir", "Viktor", "Sylas", "Ryze", "Orianna", "Syndra", "Ahri", "Yone", "LeBlanc", "Taliyah"],
    PlayerRole.BOT: ["Jinx", "Ezreal", "Kai'Sa", "Aphelios", "Zeri", "Varus", "Lucian", "Caitlyn", "Ashe", "Xayah"],
    PlayerRole.SUPPORT: ["Thresh", "Morgana", "Lulu", "Nautilus", "Rakan", "Leona", "Alistar", "Karma", "Yuumi", "Braum"],
}

# Tabela de Counter-Picks: champion -> lista de campeões que ele COUNTERA (tem vantagem contra)
# Exemplo: Aatrox counters Sion, mas sofre contra Jax
COUNTER_MAP: Dict[str, List[str]] = {
    # TOP
    "Jax": ["Aatrox", "Camille", "Fiora"],
    "Gnar": ["Jax", "Renekton", "Ornn"],
    "Aatrox": ["Sion", "Ornn", "Gnar"],
    "Sion": ["Irelia", "Jayce"],
    "Irelia": ["Gnar", "Jayce", "Aatrox"],
    "Fiora": ["Sion", "Ornn", "Aatrox"],
    "Jayce": ["Jax", "Renekton"],
    "Renekton": ["Irelia", "Camille"],
    "Camille": ["Gnar", "Sion"],
    "Ornn": ["Sion", "Renekton"],

    # JUNGLE
    "Lee Sin": ["Sejuani", "Jarvan IV", "Maokai"],
    "Graves": ["Lee Sin", "Nocturne", "Viego"],
    "Kindred": ["Graves", "Sejuani", "Maokai"],
    "Sejuani": ["Kindred", "Nocturne", "Jarvan IV"],
    "Viego": ["Lee Sin", "Wukong", "Elise"],
    "Jarvan IV": ["Graves", "Nocturne"],
    "Maokai": ["Jarvan IV", "Viego"],
    "Nocturne": ["Elise", "Wukong"],
    "Elise": ["Lee Sin", "Kindred"],
    "Wukong": ["Sejuani", "Maokai"],

    # MID
    "Azir": ["Ryze", "Orianna", "Viktor"],
    "Viktor": ["Sylas", "Ryze", "Ahri"],
    "Sylas": ["Azir", "Orianna", "Taliyah"],
    "Ryze": ["Sylas", "LeBlanc", "Yone"],
    "Orianna": ["Ryze", "Viktor", "Syndra"],
    "Syndra": ["Azir", "Ahri", "Orianna"],
    "Ahri": ["Viktor", "Taliyah"],
    "Yone": ["Azir", "Syndra"],
    "LeBlanc": ["Viktor", "Syndra", "Ahri"],
    "Taliyah": ["Yone", "LeBlanc"],

    # BOT
    "Jinx": ["Aphelios", "Zeri", "Ashe"],
    "Ezreal": ["Jinx", "Caitlyn", "Varus"],
    "Kai'Sa": ["Ezreal", "Aphelios", "Lucian"],
    "Aphelios": ["Kai'Sa", "Zeri", "Caitlyn"],
    "Zeri": ["Ezreal", "Varus", "Ashe"],
    "Varus": ["Aphelios", "Lucian"],
    "Lucian": ["Jinx", "Ezreal"],
    "Caitlyn": ["Jinx", "Zeri", "Ashe"],
    "Ashe": ["Ezreal", "Lucian"],
    "Xayah": ["Kai'Sa", "Lucian", "Jinx"],

    # SUPPORT
    "Thresh": ["Nautilus", "Leona", "Rakan"],
    "Morgana": ["Thresh", "Nautilus", "Leona"],
    "Lulu": ["Morgana", "Yuumi", "Rakan"],
    "Nautilus": ["Lulu", "Karma", "Braum"],
    "Rakan": ["Nautilus", "Karma"],
    "Leona": ["Rakan", "Lulu", "Yuumi"],
    "Alistar": ["Thresh", "Leona"],
    "Karma": ["Thresh", "Morgana"],
    "Yuumi": ["Alistar", "Braum"],
    "Braum": ["Thresh", "Leona"],
}

class DraftAI:
    """
    Inteligência Artificial encarregada de banir e escolher campeões de forma ótima.
    """

    def __init__(self, patch_bias: Optional[Dict[str, float]] = None) -> None:
        # champion name lower -> score (positivo = buff no patch)
        self.patch_bias: Dict[str, float] = patch_bias or {}

    def _patch_score(self, champion: str) -> float:
        return float(self.patch_bias.get(champion.lower(), 0.0) or 0.0)

    def _weighted_choice(self, champions: List[str]) -> str:
        """Prefere campeões buffados no patch (ainda com aleatoriedade)."""
        if not champions:
            return "Aatrox"
        if len(champions) == 1 or not self.patch_bias:
            return random.choice(champions)
        weights = []
        for c in champions:
            # score 0.1 → ~1.5x; score -0.1 → ~0.67x
            s = self._patch_score(c)
            w = max(0.15, 1.0 + s * 5.0)
            weights.append(w)
        return random.choices(champions, weights=weights, k=1)[0]

    def make_decision(
        self,
        draft_state: DraftState,
        team_side: DraftTeam,
        team_obj,
        opponent_team_obj,
        patch_bias: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, Optional[PlayerRole]]:
        """
        Calcula qual campeão o time deve escolher ou banir no turno atual do draft.

        Returns:
            Tupla (nome_do_campeao, role_hint_ou_None)
        """
        if patch_bias is not None:
            self.patch_bias = patch_bias

        current_action = draft_state.current_action
        if not current_action:
            raise ValueError("Draft já concluído. IA não pode tomar decisões.")

        phase, current_side, action = current_action
        assert current_side == team_side, "Chamada da IA no turno errado do time!"

        unavailable = draft_state.unavailable_champions

        if action == DraftAction.BAN:
            champion = self._decide_ban(draft_state, team_side, opponent_team_obj, unavailable)
            return champion, None
        else:
            champion, role = self._decide_pick(draft_state, team_side, team_obj, opponent_team_obj, unavailable)
            return champion, role

    def _decide_ban(
        self,
        draft_state: DraftState,
        team_side: DraftTeam,
        opponent_team_obj,
        unavailable: Set[str]
    ) -> str:
        """
        Decide o banimento.
        Regra:
            - Tenta identificar os campeões preferidos (MAIN tier) dos melhores jogadores do oponente.
            - Caso não haja informações ou todos já estejam indisponíveis, bane um campeão forte aleatório do meta.
        """
        opp_starters = opponent_team_obj.get_starters()
        
        # Filtra campeões que são MAIN de algum jogador titular oponente
        opp_main_champions = []
        for player in opp_starters:
            pool = player.champion_pool if isinstance(player.champion_pool, list) else []
            for item in pool:
                if isinstance(item, dict) and item.get("tier") == ChampionPoolTier.MAIN.value:
                    champ = item.get("champion")
                    if champ and champ.lower() not in unavailable:
                        opp_main_champions.append(champ)

        if opp_main_champions:
            # Prioriza banir mains do oponente que estão buffados no patch
            chosen_ban = self._weighted_choice(opp_main_champions)
            logger.info(f"[DraftAI] Banindo campeão preferido do oponente: {chosen_ban}")
            return chosen_ban

        # Fallback: Bane um campeão forte aleatório do meta geral (prioriza buffados)
        all_possible = []
        for role_champs in CHAMPIONS_BY_ROLE.values():
            all_possible.extend(role_champs)
        
        valid_bans = [c for c in all_possible if c.lower() not in unavailable]
        if valid_bans:
            return self._weighted_choice(valid_bans)
        
        return "Aatrox"  # Fallback definitivo

    def _decide_pick(
        self,
        draft_state: DraftState,
        team_side: DraftTeam,
        team_obj,
        opponent_team_obj,
        unavailable: Set[str]
    ) -> Tuple[str, PlayerRole]:
        """
        Decide o pick com **flex**: escolhe o melhor par (campeão, role aberta),
        não a próxima role da fila TOP→JG→MID→BOT→SUP.
        """
        starters = team_obj.get_starters()
        my_picks = draft_state.blue_picks if team_side == DraftTeam.BLUE else draft_state.red_picks
        opp_picks = draft_state.red_picks if team_side == DraftTeam.BLUE else draft_state.blue_picks

        my_picked_roles = {p.get("role_hint") for p in my_picks}
        remaining_roles = [
            r
            for r in [
                PlayerRole.TOP,
                PlayerRole.JUNGLE,
                PlayerRole.MID,
                PlayerRole.BOT,
                PlayerRole.SUPPORT,
            ]
            if r.value not in my_picked_roles
        ]
        if not remaining_roles:
            remaining_roles = [PlayerRole.TOP]

        pick_index = len(my_picks)  # 0 = first pick of this team
        options = score_flex_options(
            remaining_roles=remaining_roles,
            starters=starters,
            unavailable=unavailable,
            opp_picks=opp_picks,
            patch_bias=self.patch_bias,
            pick_index=pick_index,
        )

        if not options:
            # Fallback extremo
            role = remaining_roles[0]
            all_possible = []
            for role_champs in CHAMPIONS_BY_ROLE.values():
                all_possible.extend(role_champs)
            fallback = next((c for c in all_possible if c.lower() not in unavailable), "Azir")
            return fallback, role

        # Softmax leve: top opções com noise para variedade, sem ignorar o melhor
        top = options[: min(5, len(options))]
        weights = [max(0.05, o[0] + 0.01) for o in top]
        chosen = random.choices(top, weights=weights, k=1)[0]
        score, champ, role = chosen
        logger.info(
            f"[DraftAI] FLEX pick #{pick_index + 1}: {champ} → {role.value} "
            f"(score={score:.2f}, open={len(remaining_roles)})"
        )
        return champ, role


def score_flex_options(
    *,
    remaining_roles: List[PlayerRole],
    starters,
    unavailable: Set[str],
    opp_picks: List[dict],
    patch_bias: Optional[Dict[str, float]] = None,
    pick_index: int = 0,
) -> List[Tuple[float, str, PlayerRole]]:
    """
    Scoreia todos os pares (champion, role aberta) e retorna lista ordenada
    por score desc: [(score, champion, role), ...].

    Critérios:
      - tier MAIN > SECONDARY > meta fallback > off
      - counter vs lane inimiga já revelada
      - patch bias
      - flex value (champ em mais de um role aberto)
      - blind risk: early picks preferem safe/flex
    """
    patch_bias = patch_bias or {}
    unavailable_l = {u.lower() for u in unavailable}
    open_roles = list(remaining_roles)
    if not open_roles:
        return []

    # Mapa role → player titular
    by_role = {}
    for p in starters or []:
        role = getattr(p, "role", None)
        if role is not None:
            by_role[role] = p

    # Contagem de roles em que cada champ aparece no pool do time (flex)
    champ_role_coverage: Dict[str, Set[str]] = {}
    for role in open_roles:
        player = by_role.get(role)
        if not player:
            continue
        pool = player.champion_pool if isinstance(player.champion_pool, list) else []
        for item in pool:
            if not isinstance(item, dict):
                continue
            c = item.get("champion")
            if not c:
                continue
            champ_role_coverage.setdefault(c.lower(), set()).add(role.value)

    options: List[Tuple[float, str, PlayerRole]] = []

    for role in open_roles:
        player = by_role.get(role)
        main_pool: List[str] = []
        sec_pool: List[str] = []
        if player:
            pool = player.champion_pool if isinstance(player.champion_pool, list) else []
            for item in pool:
                if not isinstance(item, dict):
                    continue
                champ = item.get("champion")
                if not champ:
                    continue
                tier = item.get("tier")
                if tier == ChampionPoolTier.MAIN.value:
                    main_pool.append(champ)
                elif tier == ChampionPoolTier.SECONDARY.value:
                    sec_pool.append(champ)

        # Candidatos: MAIN → SEC → meta da role
        candidates: List[Tuple[str, str]] = []  # (champ, tier_tag)
        seen: Set[str] = set()
        for c in main_pool:
            key = c.lower()
            if key not in unavailable_l and key not in seen:
                candidates.append((c, "MAIN"))
                seen.add(key)
        for c in sec_pool:
            key = c.lower()
            if key not in unavailable_l and key not in seen:
                candidates.append((c, "SEC"))
                seen.add(key)
        for c in CHAMPIONS_BY_ROLE.get(role, []):
            key = c.lower()
            if key not in unavailable_l and key not in seen:
                candidates.append((c, "META"))
                seen.add(key)

        opp_lane = next(
            (p for p in opp_picks if p.get("role_hint") == role.value),
            None,
        )
        opp_champ = opp_lane.get("champion") if opp_lane else None

        # Quem countera o oponente nesta lane?
        counters_for_opp: Set[str] = set()
        if opp_champ:
            for key, val in COUNTER_MAP.items():
                if any(c.lower() == opp_champ.lower() for c in val):
                    counters_for_opp.add(key.lower())

        for champ, tier_tag in candidates:
            score = 0.0

            # Pool tier
            if tier_tag == "MAIN":
                score += 10.0
            elif tier_tag == "SEC":
                score += 6.5
            else:
                score += 3.0  # meta fallback / off

            # Counter
            if opp_champ and champ.lower() in counters_for_opp:
                score += 5.5 if tier_tag in ("MAIN", "SEC") else 3.0
            elif opp_champ:
                # Já revelado sem counter: leve desvantagem
                score -= 0.4

            # Patch bias
            pb = float(patch_bias.get(champ.lower(), 0.0) or 0.0)
            score += pb * 8.0

            # Flex value: jogável em 2+ roles abertos → bônus em picks early
            coverage = len(champ_role_coverage.get(champ.lower(), set()))
            if coverage >= 2:
                score += 1.8 if pick_index <= 1 else 0.8

            # Blind risk: 1ª/2ª pick — prioriza MAIN e flex, evita META off
            if pick_index <= 1:
                if tier_tag == "MAIN":
                    score += 1.5
                elif tier_tag == "META":
                    score -= 1.2
                if coverage >= 2:
                    score += 1.0

            # Bônus se role tem counter opportunity (oponente revelado)
            if opp_champ:
                score += 0.6

            options.append((score, champ, role))

    options.sort(key=lambda x: x[0], reverse=True)
    return options


def calculate_draft_penalties(
    blue_picks: List[dict],
    red_picks: List[dict],
    blue_team,
    red_team
) -> Tuple[float, float]:
    """
    Calcula as penalidades matemáticas de draft de ambos os times.
    
    Regra:
        - Cada jogador fora da pool (OFF_POOL) adiciona 0.12 de penalidade.
        - Cada counter sofrido na lane direta adiciona 0.08 de penalidade.
        - Penalidade máxima limitada a 0.40.
    """
    blue_penalty = 0.0
    red_penalty = 0.0

    blue_starters = blue_team.get_starters()
    red_starters = red_team.get_starters()

    # 1. Verifica Champion Pool
    for pick in blue_picks:
        role = pick["role_hint"]
        champ = pick["champion"]
        player = next((p for p in blue_starters if p.role.value == role), None)
        if player:
            tier = player.get_champion_pool_tier(champ)
            if tier == ChampionPoolTier.OFF_POOL.value:
                blue_penalty += 0.12

    for pick in red_picks:
        role = pick["role_hint"]
        champ = pick["champion"]
        player = next((p for p in red_starters if p.role.value == role), None)
        if player:
            tier = player.get_champion_pool_tier(champ)
            if tier == ChampionPoolTier.OFF_POOL.value:
                red_penalty += 0.12

    # 2. Verifica counters de lane direta
    for role in [PlayerRole.TOP, PlayerRole.JUNGLE, PlayerRole.MID, PlayerRole.BOT, PlayerRole.SUPPORT]:
        b_pick = next((p for p in blue_picks if p["role_hint"] == role.value), None)
        r_pick = next((p for p in red_picks if p["role_hint"] == role.value), None)
        
        if b_pick and r_pick:
            b_champ = b_pick["champion"]
            r_champ = r_pick["champion"]
            
            # Se o campeão do Red countera o do Blue
            if b_champ in COUNTER_MAP.get(r_champ, []):
                blue_penalty += 0.08
                logger.info(f"[DraftAnalysis] Red counterou Blue no {role.value} ({r_champ} countera {b_champ})")
            
            # Se o campeão do Blue countera o do Red
            if r_champ in COUNTER_MAP.get(b_champ, []):
                red_penalty += 0.08
                logger.info(f"[DraftAnalysis] Blue counterou Red no {role.value} ({b_champ} countera {r_champ})")

    return min(blue_penalty, 0.40), min(red_penalty, 0.40)
