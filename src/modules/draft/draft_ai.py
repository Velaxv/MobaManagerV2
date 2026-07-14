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
        Decide a escolha do pick.
        Lógica sofisticada:
            1. Determina quais roles ainda precisam de pick no time.
            2. Identifica se o oponente já revelou o pick dele para a mesma role.
            3. Se sim, tenta aplicar um COUNTER-PICK se o campeão de counter estiver no pool (MAIN/SECONDARY) do jogador daquela lane.
            4. Se não, escolhe o campeão de maior proficiência (preferencialmente MAIN) disponível do jogador.
        """
        starters = team_obj.get_starters()
        
        # Identifica quais roles já foram escolhidas pelo time
        my_picks = draft_state.blue_picks if team_side == DraftTeam.BLUE else draft_state.red_picks
        opp_picks = draft_state.red_picks if team_side == DraftTeam.BLUE else draft_state.blue_picks
        
        my_picked_roles = {p["role_hint"] for p in my_picks}
        
        # Determina quais posições titulares ainda estão abertas
        remaining_roles = [r for r in [PlayerRole.TOP, PlayerRole.JUNGLE, PlayerRole.MID, PlayerRole.BOT, PlayerRole.SUPPORT] 
                           if r.value not in my_picked_roles]

        if not remaining_roles:
            # Caso raro de erro
            remaining_roles = [PlayerRole.TOP]

        # Prioriza escolher para a role que já tem pick adversário revelado (para maximizar chance de counter) ou simplesmente pega a primeira role
        chosen_role = remaining_roles[0]
        opp_champ_for_lane = None

        for role in remaining_roles:
            # Verifica se o oponente já escolheu campeão para essa role
            opp_lane_pick = next((p for p in opp_picks if p["role_hint"] == role.value), None)
            if opp_lane_pick:
                chosen_role = role
                opp_champ_for_lane = opp_lane_pick["champion"]
                break

        # Encontra o jogador titular correspondente à role escolhida
        player = next((p for p in starters if p.role == chosen_role), None)
        if not player:
            # Se não achar o jogador da role, pega qualquer titular que sobrou
            player = starters[0]
            chosen_role = player.role

        # Coleta a champion_pool do jogador
        player_pool = player.champion_pool if isinstance(player.champion_pool, list) else []
        main_pool = [item.get("champion") for item in player_pool if isinstance(item, dict) and item.get("tier") == ChampionPoolTier.MAIN.value]
        sec_pool = [item.get("champion") for item in player_pool if isinstance(item, dict) and item.get("tier") == ChampionPoolTier.SECONDARY.value]

        # Tenta Counter-Pick se o oponente já escolheu para a mesma lane
        if opp_champ_for_lane:
            # Quais campeões counteram opp_champ_for_lane?
            counters = []
            for key, val in COUNTER_MAP.items():
                if any(c.lower() == opp_champ_for_lane.lower() for c in val):
                    counters.append(key)

            # Verifica se algum desses counters está na pool do jogador e disponível
            available_counters = [c for c in counters if c.lower() not in unavailable]
            
            # Prioridade de counter: se estiver no MAIN pool, depois no SECONDARY pool
            main_counters = [c for c in available_counters if any(c.lower() == mp.lower() for mp in main_pool)]
            if main_counters:
                chosen_champ = main_counters[0]
                logger.info(f"[DraftAI] COUNTER-PICK PERFEITO! {player.name} picka {chosen_champ} contra {opp_champ_for_lane} (MAIN pool)")
                return chosen_champ, chosen_role
            
            sec_counters = [c for c in available_counters if any(c.lower() == sp.lower() for sp in sec_pool)]
            if sec_counters:
                chosen_champ = sec_counters[0]
                logger.info(f"[DraftAI] COUNTER-PICK SECUNDÁRIO! {player.name} picka {chosen_champ} contra {opp_champ_for_lane} (SECONDARY pool)")
                return chosen_champ, chosen_role

        # Sem counter-pick viável. Escolhe o melhor campeão da pool do jogador disponível.
        # Preferência leve por buffs do patch atual.
        available_main = [c for c in main_pool if c and c.lower() not in unavailable]
        if available_main:
            chosen_champ = self._weighted_choice(available_main)
            logger.info(f"[DraftAI] Escolhendo MAIN champion da pool de {player.name}: {chosen_champ}")
            return chosen_champ, chosen_role

        available_sec = [c for c in sec_pool if c and c.lower() not in unavailable]
        if available_sec:
            chosen_champ = self._weighted_choice(available_sec)
            logger.info(f"[DraftAI] Escolhendo SECONDARY champion da pool de {player.name}: {chosen_champ}")
            return chosen_champ, chosen_role

        # Fallback definitivo: escolhe qualquer campeão válido da posição
        pos_champs = CHAMPIONS_BY_ROLE.get(chosen_role, [])
        valid_pos_champs = [c for c in pos_champs if c.lower() not in unavailable]
        
        if valid_pos_champs:
            chosen_champ = self._weighted_choice(valid_pos_champs)
            logger.warning(f"[DraftAI] Jogador {player.name} FORÇADO a jogar fora da pool com {chosen_champ}")
            return chosen_champ, chosen_role

        # Fallback extremo caso tudo esteja indisponível
        all_possible = []
        for role_champs in CHAMPIONS_BY_ROLE.values():
            all_possible.extend(role_champs)
        fallback_champ = next((c for c in all_possible if c.lower() not in unavailable), "Azir")
        return fallback_champ, chosen_role


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
