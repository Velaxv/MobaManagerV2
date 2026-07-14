import asyncio
import logging
import random
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel
from sqlalchemy import select

from src.core.database import AsyncSessionLocal
from src.core.redis_client import redis_client
from src.models import Team, Player, Match, LeagueTeam, Champion, Staff
from src.shared.enums import MatchPhase, MatchResult, PlayerRole, ClassType, DamageType, SplitPhase, ContractStatus
from src.shared.math_utils import clamp, normalize_attribute, stochastic_roll, gold_advantage_to_probability, sigmoid
from src.modules.draft.draft_analyzer import DraftAnalyzer
from src.models.contract import Contract


def _state_to_dict(state: "LiveMatchState") -> Dict[str, Any]:
    """Serializa LiveMatchState de forma compatível com Pydantic v1/v2."""
    return state.model_dump()


def _normalize_event_log(log: Dict[str, Any]) -> Dict[str, Any]:
    """Garante campos message/severity esperados pelo frontend."""
    normalized = dict(log)
    if "message" not in normalized:
        normalized["message"] = normalized.get("description", "")
    if "severity" not in normalized:
        event_type = str(normalized.get("event_type", "")).upper()
        if event_type in {"SOLO_KILL", "TEAMFIGHT", "BARON_SECURED", "SNOWBALL", "VICTORY"}:
            normalized["severity"] = "high"
        elif event_type in {"DRAGON_SECURED", "TURRET_DESTROYED", "COACH_COMM", "SCOUT_REPORT"}:
            normalized["severity"] = "medium"
        else:
            normalized["severity"] = "low"
    return normalized

logger = logging.getLogger(__name__)

class LiveMatchState(BaseModel):
    """Representa o estado mutável de uma partida ao vivo persistido no Redis Simulado."""
    match_id: str
    league_id: str
    split_week: int
    is_playoff: bool
    blue_team_id: str
    red_team_id: str
    blue_team_name: str
    red_team_name: str
    
    current_minute: int = 0
    phase: str = "SETUP"  # SETUP, EARLY_GAME, MID_GAME, LATE_GAME, FINISHED
    is_complete: bool = False
    winner_side: Optional[str] = None
    
    # Placar e Recursos
    blue_kills: int = 0
    red_kills: int = 0
    blue_gold: int = 15000  # Ouro inicial da equipe
    red_gold: int = 15000
    gold_difference: int = 0
    
    # Objetivos Neutros
    blue_dragons: int = 0
    red_dragons: int = 0
    blue_barons: int = 0
    red_barons: int = 0
    
    # Drafts (Lista de dicionários contendo champion e role)
    blue_draft: List[Dict[str, str]] = []
    red_draft: List[Dict[str, str]] = []
    
    # Logs narrativos
    event_logs: List[Dict[str, Any]] = []
    
    # Coach Comms
    blue_coach_comms_used: int = 0
    red_coach_comms_used: int = 0
    blue_focus_debuffs: Dict[str, float] = {}  # player_id -> debuff
    red_focus_debuffs: Dict[str, float] = {}

    # Velocidade: ms reais por minuto de jogo (0 = instantâneo)
    tick_ms: int = 2000
    speed_label: str = "1x"

    # Táticas pré-partida
    blue_game_style: str = "BALANCED"
    red_game_style: str = "BALANCED"
    blue_coach_comms_max: int = 3
    red_coach_comms_max: int = 2

    # Draft scout session (avaliação pós-partida)
    scout_session_id: Optional[str] = None
    managed_team_id: Optional[str] = None
    blue_bans: List[str] = []
    red_bans: List[str] = []
    scout_evaluation: Optional[Dict[str, Any]] = None
    # Playoff série multi-map
    series_id: Optional[str] = None
    fearless_used: List[str] = []
    series_score: Optional[Dict[str, int]] = None
    map_index: Optional[int] = None
    momentum_team_id: Optional[str] = None
    series_map_result: Optional[Dict[str, Any]] = None


# Speeds permitidas (label → tick_ms)
LIVE_SPEED_PRESETS: Dict[str, int] = {
    "1x": 2000,
    "2x": 1000,
    "4x": 500,
    "instant": 0,
}


class MatchEngineService:
    """
    Motor de simulação de partidas em tempo real (Match Engine) orientado a ticks.
    Gerencia a simulação assíncrona, salvando o estado no Redis virtual e a persistência final no SQLite.
    """
    
    def __init__(self):
        import numpy as np
        self.draft_analyzer = DraftAnalyzer()
        self.rng = random.SystemRandom()
        self.np_rng = np.random.default_rng()

    async def get_live_state(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Lê o estado da partida ao vivo do Redis Simulado."""
        key = f"live_match:{match_id}"
        state = await redis_client.get_generic(key)
        if not state:
            return None
        # Normaliza logs e fase para o frontend (message/severity + COMPLETE)
        logs = state.get("event_logs") or []
        state["event_logs"] = [_normalize_event_log(log) for log in logs]
        if state.get("phase") in ("FINISHED", "COMPLETE") or state.get("is_complete"):
            state["phase"] = "COMPLETE"
            state["is_complete"] = True
        return state

    async def start_live_simulation(
        self,
        match_id: str,
        league_id: str,
        split_week: int,
        is_playoff: bool,
        blue_team: Team,
        red_team: Team,
        blue_draft: List[Dict[str, str]],
        red_draft: List[Dict[str, str]],
        speed: str = "1x",
        tick_ms: Optional[int] = None,
        blue_game_style: str = "BALANCED",
        red_game_style: str = "BALANCED",
        blue_coach_comms_max: int = 3,
        red_coach_comms_max: int = 2,
        scout_session_id: Optional[str] = None,
        managed_team_id: Optional[str] = None,
        blue_bans: Optional[List[str]] = None,
        red_bans: Optional[List[str]] = None,
        series_id: Optional[str] = None,
        fearless_used: Optional[List[str]] = None,
        series_score: Optional[Dict[str, int]] = None,
        map_index: Optional[int] = None,
        momentum_team_id: Optional[str] = None,
    ) -> LiveMatchState:
        """Inicializa o estado da partida ao vivo no Redis e dispara a background task do loop de ticks."""
        from src.modules.simulation.tactics import clamp_coach_comms, normalize_style

        label = speed if speed in LIVE_SPEED_PRESETS else "1x"
        resolved_tick = LIVE_SPEED_PRESETS[label] if tick_ms is None else max(0, int(tick_ms))
        # Se tick_ms custom, deriva label aproximado
        if tick_ms is not None:
            label = next(
                (k for k, v in LIVE_SPEED_PRESETS.items() if v == resolved_tick),
                f"{resolved_tick}ms",
            )

        state = LiveMatchState(
            match_id=match_id,
            league_id=league_id,
            split_week=split_week,
            is_playoff=is_playoff,
            blue_team_id=str(blue_team.id),
            red_team_id=str(red_team.id),
            blue_team_name=blue_team.name,
            red_team_name=red_team.name,
            blue_draft=blue_draft,
            red_draft=red_draft,
            tick_ms=resolved_tick,
            speed_label=label,
            blue_game_style=normalize_style(blue_game_style),
            red_game_style=normalize_style(red_game_style),
            blue_coach_comms_max=clamp_coach_comms(blue_coach_comms_max),
            red_coach_comms_max=clamp_coach_comms(red_coach_comms_max),
            scout_session_id=scout_session_id,
            managed_team_id=str(managed_team_id) if managed_team_id else None,
            blue_bans=list(blue_bans or []),
            red_bans=list(red_bans or []),
            series_id=series_id,
            fearless_used=list(fearless_used or []),
            series_score=series_score,
            map_index=map_index,
            momentum_team_id=str(momentum_team_id) if momentum_team_id else None,
        )

        # Momentum: ouro inicial extra no lado do vencedor do map anterior
        if momentum_team_id:
            mid = str(momentum_team_id)
            if mid == str(blue_team.id):
                state.blue_gold += 400
            elif mid == str(red_team.id):
                state.red_gold += 400
        
        # Grava estado inicial
        key = f"live_match:{match_id}"
        await redis_client.set_generic(key, _state_to_dict(state))

        if scout_session_id:
            try:
                from src.modules.draft.scout_session import ScoutSessionService

                await ScoutSessionService().bind_match(scout_session_id, match_id)
            except Exception as se:
                logger.warning(f"[MatchEngineService] bind scout session: {se}")
        
        # Dispara background task para simulação em tempo real
        asyncio.create_task(self._run_simulation_loop(match_id))
        
        return state

    async def set_live_speed(self, match_id: str, speed: str) -> Dict[str, Any]:
        """
        Altera a velocidade da partida ao vivo (lida a cada tick).
        speed: 1x | 2x | 4x | instant
        """
        if speed not in LIVE_SPEED_PRESETS:
            return {
                "error": f"Velocidade inválida. Use: {', '.join(LIVE_SPEED_PRESETS.keys())}"
            }
        key = f"live_match:{match_id}"
        state_data = await redis_client.get_generic(key)
        if not state_data:
            return {"error": "Partida não encontrada."}
        state = LiveMatchState(**state_data)
        if state.is_complete:
            return {"error": "Partida já encerrada."}
        state.tick_ms = LIVE_SPEED_PRESETS[speed]
        state.speed_label = speed
        await redis_client.set_generic(key, _state_to_dict(state))
        return {
            "success": True,
            "match_id": match_id,
            "speed": speed,
            "tick_ms": state.tick_ms,
        }

    async def apply_coach_comm(self, match_id: str, team_side: str) -> Dict[str, Any]:
        """
        Aplica instrução tática do Head Coach em tempo real durante o Early Game.
        Verifica atributos de comunicação do Coach e Coachability do jogador Mid.
        """
        key = f"live_match:{match_id}"
        state_data = await redis_client.get_generic(key)
        if not state_data:
            return {"error": "Partida não encontrada."}
            
        state = LiveMatchState(**state_data)
        if state.phase != "EARLY_GAME":
            return {"error": "Comandos táticos de coach só podem ser enviados no Early Game."}
            
        async with AsyncSessionLocal() as db:
            team_id = state.blue_team_id if team_side == "BLUE" else state.red_team_id
            team = await db.get(Team, uuid.UUID(team_id))
            
            # Obtém Head Coach e Mid Laner
            head_coach = next((s for s in team.staffs if s.role == "HEAD_COACH"), None)
            starters = team.get_starters()
            mid_player = next((p for p in starters if p.role == PlayerRole.MID), None)
            
            if not head_coach or not mid_player:
                return {"error": "Estrutura do time inválida para comunicação."}
                
            comms_used = state.blue_coach_comms_used if team_side == "BLUE" else state.red_coach_comms_used
            comms_max = (
                state.blue_coach_comms_max if team_side == "BLUE" else state.red_coach_comms_max
            )
            if comms_used >= comms_max:
                return {
                    "error": f"Limite de coach comms atingido ({comms_max}). Ajuste nas táticas pré-partida.",
                }
            
            # RNG de sucesso baseado em Communication e Coachability
            base_success_chance = (head_coach.communication / 20.0) * 0.70 + (mid_player.coachability / 20.0) * 0.30
            success = self.rng.random() < base_success_chance
            
            # Excesso de comandos (> 3) gera risco de Confusão Mental
            confusion_debuff = 0.0
            confusion_message = ""
            if comms_used >= 3:
                confusion_chance = 0.15 + (comms_used - 3) * 0.10
                # Jogadores com baixo foco têm mais chance de se confundirem
                focus_multiplier = (20.0 - mid_player.focus) / 20.0
                if self.rng.random() < (confusion_chance * focus_multiplier):
                    confusion_debuff = self.rng.uniform(1.0, 5.0)
                    confusion_message = f" No entanto, {mid_player.name} ficou confuso com excesso de chamadas e perdeu {confusion_debuff:.1f} de foco!"
            
            log_desc = f"[Coach] Treinador {head_coach.name} enviou comandos táticos para {mid_player.name}. "
            impact = {}
            
            if success:
                log_desc += f"Sucesso! {mid_player.name} ajustou seu posicionamento na rota." + confusion_message
                impact["team_gold"] = "+150"
                if team_side == "BLUE":
                    state.blue_gold += 150
                else:
                    state.red_gold += 150
            else:
                log_desc += f"Falha! {mid_player.name} não entendeu a instrução técnica." + confusion_message
                
            # Atualiza estado no Redis
            if team_side == "BLUE":
                state.blue_coach_comms_used += 1
                if confusion_debuff > 0:
                    state.blue_focus_debuffs[str(mid_player.id)] = state.blue_focus_debuffs.get(str(mid_player.id), 0.0) + confusion_debuff
            else:
                state.red_coach_comms_used += 1
                if confusion_debuff > 0:
                    state.red_focus_debuffs[str(mid_player.id)] = state.red_focus_debuffs.get(str(mid_player.id), 0.0) + confusion_debuff
                    
            state.event_logs.append(_normalize_event_log({
                "timestamp": f"{state.current_minute:02d}:00",
                "phase": "EARLY_GAME",
                "event_type": "COACH_COMM",
                "description": log_desc,
                "impact": impact
            }))
            
            await redis_client.set_generic(key, _state_to_dict(state))
            return {
                "success": True,
                "message": log_desc,
                "log": log_desc,
                "comms_used": comms_used + 1,
            }

    async def _run_simulation_loop(self, match_id: str):
        """Loop de simulação em tempo real orientado a ticks (intervalo de 2.0 segundos reais por minuto do jogo)."""
        key = f"live_match:{match_id}"
        
        # Carrega dados do banco SQLite
        async with AsyncSessionLocal() as db:
            state_data = await redis_client.get_generic(key)
            if not state_data:
                return
                
            state = LiveMatchState(**state_data)
            
            blue_team = await db.get(Team, uuid.UUID(state.blue_team_id))
            red_team = await db.get(Team, uuid.UUID(state.red_team_id))
            
            # Carrega campeões reais do banco para cálculo de sinergias/conforto
            blue_champions = []
            for pick in state.blue_draft:
                champ_res = await db.execute(select(Champion).where(Champion.name == pick["champion"]))
                blue_champions.append(champ_res.scalar_one())
                
            red_champions = []
            for pick in state.red_draft:
                champ_res = await db.execute(select(Champion).where(Champion.name == pick["champion"]))
                red_champions.append(champ_res.scalar_one())
                
            # 1. SETUP PHASE: Calcula Sinergias e Penalidades de Draft
            blue_draft_report = self.draft_analyzer.analyze_composition(blue_champions)
            red_draft_report = self.draft_analyzer.analyze_composition(red_champions)
            
            state.phase = "EARLY_GAME"
            state.event_logs.append(_normalize_event_log({
                "timestamp": "00:00",
                "phase": "SETUP",
                "event_type": "SETUP",
                "description": "Partida iniciada! Composições analisadas pelas comissões técnicas.",
                "impact": {
                    "blue_comp": blue_draft_report["power_curve"]["archetype"],
                    "red_comp": red_draft_report["power_curve"]["archetype"]
                }
            }))
            await redis_client.set_generic(key, _state_to_dict(state))
            
            # Loop de Minutos (0 a 40 minutos)
            for minute in range(1, 41):
                # Relê tick_ms (permite mudar velocidade mid-match)
                peek = await redis_client.get_generic(key)
                if peek:
                    tick_ms = int(peek.get("tick_ms", 2000) or 0)
                else:
                    tick_ms = 2000
                if tick_ms > 0:
                    await asyncio.sleep(tick_ms / 1000.0)
                
                # Relê estado para pegar possíveis coach comms / speed concorrentes
                state_data = await redis_client.get_generic(key)
                if not state_data:
                    return
                state = LiveMatchState(**state_data)
                if state.is_complete:
                    break
                state.current_minute = minute
                
                # Define Fase e pesos matemáticos
                if minute <= 14:
                    state.phase = "EARLY_GAME"
                    self._simulate_early_tick(state, blue_team, red_team, blue_champions, red_champions)
                elif minute <= 28:
                    state.phase = "MID_GAME"
                    self._simulate_mid_tick(state, blue_team, red_team, blue_champions, red_champions, blue_draft_report, red_draft_report)
                else:
                    state.phase = "LATE_GAME"
                    self._simulate_late_tick(state, blue_team, red_team, blue_champions, red_champions, blue_draft_report, red_draft_report)

                # Viés de estilo tático (Early/Mid/Late)
                self._apply_style_tick_bias(state)
                    
                # Checa Snowball crítico (Diferença de ouro > 12.000g)
                state.gold_difference = state.blue_gold - state.red_gold
                if abs(state.gold_difference) >= 12000 and minute >= 20:
                    winning_side = "BLUE" if state.gold_difference > 0 else "RED"
                    winning_name = state.blue_team_name if winning_side == "BLUE" else state.red_team_name
                    
                    state.event_logs.append(_normalize_event_log({
                        "timestamp": f"{minute:02d}:00",
                        "phase": state.phase,
                        "event_type": "SNOWBALL",
                        "description": f"Inibidor do time inimigo destruido! {winning_name} abre vantagem avassaladora.",
                        "impact": {"gold_diff": f"{state.gold_difference:+d}"}
                    }))
                    state.is_complete = True
                    state.winner_side = winning_side
                    # COMPLETE = alias consumido pelo frontend; FINISHED mantido no payload bruto
                    state.phase = "COMPLETE"
                    await redis_client.set_generic(key, _state_to_dict(state))
                    break
                    
                await redis_client.set_generic(key, _state_to_dict(state))
                
            # Fim do jogo por tempo limite se não terminou em snowball
            if not state.is_complete:
                winning_side = "BLUE" if state.blue_gold > state.red_gold else "RED"
                state.is_complete = True
                state.winner_side = winning_side
                state.phase = "COMPLETE"
                
                state.event_logs.append(_normalize_event_log({
                    "timestamp": "40:00",
                    "phase": "COMPLETE",
                    "event_type": "VICTORY",
                    "description": "Fim de jogo! Vitória decidida por vantagem estratégica de recursos.",
                    "impact": {"winner": winning_side}
                }))
                await redis_client.set_generic(key, _state_to_dict(state))
                
            # 5. Persiste resultado + standings + rookie + burnout de MATCH_DAY
            await self._persist_match_result(db, state)

    def _apply_style_tick_bias(self, state: LiveMatchState) -> None:
        """Pequeno viés de ouro por estilo tático em cada minuto."""
        from src.modules.simulation.tactics import style_phase_multiplier

        phase = state.phase or "EARLY_GAME"
        b = style_phase_multiplier(state.blue_game_style, phase)
        r = style_phase_multiplier(state.red_game_style, phase)
        # Converte mult ~1.1 em +~8 gold/tick (sutil)
        if b > 1.0:
            state.blue_gold += int(round((b - 1.0) * 80))
        elif b < 1.0:
            state.red_gold += int(round((1.0 - b) * 40))
        if r > 1.0:
            state.red_gold += int(round((r - 1.0) * 80))
        elif r < 1.0:
            state.blue_gold += int(round((1.0 - r) * 40))

    def _simulate_early_tick(self, state: LiveMatchState, blue_team: Team, red_team: Team, blue_champs: List[Champion], red_champs: List[Champion]):
        """Simulação da Laning Phase (min 1-14). Foco: 70% Atributos Técnicos, 30% Mentais."""
        # Seleciona uma role aleatória para o duelo de laning
        roles = [PlayerRole.TOP, PlayerRole.JUNGLE, PlayerRole.MID, PlayerRole.BOT, PlayerRole.SUPPORT]
        active_role = self.rng.choice(roles)
        
        blue_starters = blue_team.get_starters()
        red_starters = red_team.get_starters()
        
        p_blue = next((p for p in blue_starters if p.role == active_role), None)
        p_red = next((p for p in red_starters if p.role == active_role), None)
        
        c_blue = next((c for c in blue_champs if c.primary_role == active_role or c.secondary_role == active_role), blue_champs[0])
        c_red = next((c for c in red_champs if c.primary_role == active_role or c.secondary_role == active_role), red_champs[0])
        
        if p_blue and p_red:
            # Aplica debuffs de Coach Comms na mecânica de foco
            focus_blue = p_blue.focus - state.blue_focus_debuffs.get(str(p_blue.id), 0.0)
            focus_red = p_red.focus - state.red_focus_debuffs.get(str(p_red.id), 0.0)
            
            # Resolução de Duelo (Early: 70% Técnicos/Mecânica, 30% Mentais/Foco)
            val_blue = self._resolve_duel(p_blue, c_blue, focus_blue, 0.70, 0.30)
            val_red = self._resolve_duel(p_red, c_red, focus_red, 0.70, 0.30)
            
            gold_swing = int(self.rng.uniform(150, 350))
            if val_blue > val_red + 15.0:
                state.blue_kills += 1
                state.blue_gold += (gold_swing + 300)
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "EARLY_GAME",
                    "event_type": "SOLO_KILL",
                    "description": f"[{active_role.value}] {p_blue.name} executou um solo kill em {p_red.name} devido a superioridade mecanica!",
                    "impact": {"blue_gold": f"+{gold_swing+300}", "red_kills": "+0"}
                }))
            elif val_red > val_blue + 15.0:
                state.red_kills += 1
                state.red_gold += (gold_swing + 300)
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "EARLY_GAME",
                    "event_type": "SOLO_KILL",
                    "description": f"[{active_role.value}] {p_red.name} abateu {p_blue.name} em duelo mecanico de rota!",
                    "impact": {"red_gold": f"+{gold_swing+300}", "blue_kills": "+0"}
                }))
            else:
                # Farm de rotina
                state.blue_gold += gold_swing
                state.red_gold += gold_swing
                if self.rng.random() < 0.20:
                    state.event_logs.append(_normalize_event_log({
                        "timestamp": f"{state.current_minute:02d}:00",
                        "phase": "EARLY_GAME",
                        "event_type": "FARM",
                        "description": f"[{active_role.value}] Luta equilibrada. {p_blue.name} e {p_red.name} disputam controle de barricadas.",
                        "impact": {}
                    }))

    def _simulate_mid_tick(self, state: LiveMatchState, blue_team: Team, red_team: Team, blue_champs: List[Champion], red_champs: List[Champion], blue_draft: dict, red_draft: dict):
        """Simulação de Objetivos no Mid Game (min 15-28). Foco: 60% Mentais (Teamwork, Decision), 40% Técnicos."""
        # Chance de disputa de objetivo neutro (Dragão/Arauto)
        is_dragon_tick = self.rng.random() < 0.40
        
        blue_starters = blue_team.get_starters()
        red_starters = red_team.get_starters()
        
        # Média de CA com modificadores de frontline do draft
        frontline_bonus_blue = 1.05 if blue_draft["frontline"]["has_frontline"] else 0.90
        frontline_bonus_red = 1.05 if red_draft["frontline"]["has_frontline"] else 0.90
        
        score_blue = sum(self._resolve_duel(p, c, p.focus, 0.40, 0.60) for p, c in zip(blue_starters, blue_champs)) * frontline_bonus_blue
        score_red = sum(self._resolve_duel(p, c, p.focus, 0.40, 0.60) for p, c in zip(red_starters, red_champs)) * frontline_bonus_red
        
        gold_swing = int(self.rng.uniform(400, 800))
        
        if is_dragon_tick:
            if score_blue > score_red:
                state.blue_dragons += 1
                state.blue_gold += gold_swing
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "MID_GAME",
                    "event_type": "DRAGON_SECURED",
                    "description": f"Dragão conquistado pela {state.blue_team_name}! Ótima rotação coletiva.",
                    "impact": {"blue_gold": f"+{gold_swing}", "dragons": "BLUE +1"}
                }))
            else:
                state.red_dragons += 1
                state.red_gold += gold_swing
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "MID_GAME",
                    "event_type": "DRAGON_SECURED",
                    "description": f"Dragão abatido pela {state.red_team_name} após controle de mapa.",
                    "impact": {"red_gold": f"+{gold_swing}", "dragons": "RED +1"}
                }))
        else:
            # Luta por torres / rotas
            if score_blue > score_red + 30.0:
                state.blue_gold += (gold_swing + 500)
                state.blue_kills += 1
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "MID_GAME",
                    "event_type": "TURRET_DESTROYED",
                    "description": f"Torre destruida no Mid pela {state.blue_team_name} após pickoff no caçador inimigo.",
                    "impact": {"blue_gold": f"+{gold_swing+500}"}
                }))
            elif score_red > score_blue + 30.0:
                state.red_gold += (gold_swing + 500)
                state.red_kills += 1
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "MID_GAME",
                    "event_type": "TURRET_DESTROYED",
                    "description": f"Defesa falha! {state.red_team_name} derruba a torre tier 1 da rota lateral.",
                    "impact": {"red_gold": f"+{gold_swing+500}"}
                }))
            else:
                # Controle de visão equilibrado
                state.blue_gold += 200
                state.red_gold += 200

    def _simulate_late_tick(self, state: LiveMatchState, blue_team: Team, red_team: Team, blue_champs: List[Champion], red_champs: List[Champion], blue_draft: dict, red_draft: dict):
        """Simulação de Teamfights e Baron no Late Game (min 29+). Foco: Atributos Ocultos e Burnout."""
        blue_starters = blue_team.get_starters()
        red_starters = red_team.get_starters()
        
        # Debuff por Burnout/Fadiga em lutas longas
        def calculate_late_score(players, champs, draft_report):
            score = 0.0
            for p, c in zip(players, champs):
                # Burnout acumulado reduz linearmente atributos mecânicos no Late Game
                burnout_penalty = 1.0 - (p.burnout_meter / 100.0) * 0.25
                # Atributos ocultos pesam muito na pressão do Late Game (Consistency / Big Match Aptitude)
                pressure_resistance = (p.consistency + p.big_match_aptitude) / 40.0 # normaliza
                
                base_val = (p.current_ability * burnout_penalty) + (pressure_resistance * 20.0)
                score += base_val
            return score * (1.05 if draft_report["frontline"]["has_frontline"] else 0.90)
            
        score_blue = calculate_late_score(blue_starters, blue_champs, blue_draft)
        score_red = calculate_late_score(red_starters, red_champs, red_draft)
        
        # Chance de Baron Nashor ou Elder Dragon
        is_baron_fight = self.rng.random() < 0.35
        gold_swing = int(self.rng.uniform(1000, 1500))
        
        if is_baron_fight:
            if score_blue > score_red:
                state.blue_barons += 1
                state.blue_gold += gold_swing
                state.blue_kills += 2
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "LATE_GAME",
                    "event_type": "BARON_SECURED",
                    "description": f"BARON NASHOR abatido pela {state.blue_team_name}! Ace parcial na teamfight final.",
                    "impact": {"blue_gold": f"+{gold_swing}", "blue_kills": "+2"}
                }))
            else:
                state.red_barons += 1
                state.red_gold += gold_swing
                state.red_kills += 2
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "LATE_GAME",
                    "event_type": "BARON_SECURED",
                    "description": f"BARON roubado pela {state.red_team_name}! Roubo espetacular de objetivo.",
                    "impact": {"red_gold": f"+{gold_swing}", "red_kills": "+2"}
                }))
        else:
            # Teamfight Geral
            if score_blue > score_red + 50.0:
                state.blue_gold += gold_swing
                state.blue_kills += 3
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "LATE_GAME",
                    "event_type": "TEAMFIGHT",
                    "description": f"Ace para a {state.blue_team_name}! Luta perfeita de posicionamento e dano massivo.",
                    "impact": {"blue_gold": f"+{gold_swing}", "blue_kills": "+3"}
                }))
            elif score_red > score_blue + 50.0:
                state.red_gold += gold_swing
                state.red_kills += 3
                state.event_logs.append(_normalize_event_log({
                    "timestamp": f"{state.current_minute:02d}:00",
                    "phase": "LATE_GAME",
                    "event_type": "TEAMFIGHT",
                    "description": f"Ace para a {state.red_team_name}! Erro de posicionamento custa caro no late game.",
                    "impact": {"red_gold": f"+{gold_swing}", "red_kills": "+3"}
                }))

    def _resolve_duel(self, player: Player, champion: Champion, focus_val: float, tech_weight: float, mental_weight: float) -> float:
        """Fórmula estocástica básica para duelos individuais cruzando atributos e conforto."""
        # 1. Atributo Técnico (Mecânica) vs Atributo Mental (Foco e Trabalho em Equipe)
        tech_score = normalize_attribute(player.mechanics)
        mental_score = normalize_attribute(focus_val)
        
        weighted_attr = (tech_score * tech_weight) + (mental_score * mental_weight)
        
        # 2. Conforto do Campeão e Multiplicador de Patch (meta)
        # Verifica se o campeão está na pool do jogador
        pool_tier = player.get_champion_pool_tier(champion.name)
        conforto_multiplier = 1.10 if pool_tier == "MAIN" else (0.85 if pool_tier == "SECONDARY" else 0.60)
        
        base_ability = (player.current_ability / 200.0) * weighted_attr * conforto_multiplier
        
        # 3. Rolagem estocástica baseada na consistência do jogador
        rolled_value = stochastic_roll(base_ability * 100.0, player.consistency, self.np_rng)
        
        return rolled_value

    async def _persist_match_result(self, db, state: LiveMatchState):
        """Salva o resultado consolidado e os logs da partida na base SQLite local."""
        try:
            # 1. Registra a partida no banco
            winner_id = uuid.UUID(state.blue_team_id) if state.winner_side == "BLUE" else uuid.UUID(state.red_team_id)
            
            blue_res = MatchResult.WIN if state.winner_side == "BLUE" else MatchResult.LOSS
            red_res = MatchResult.WIN if state.winner_side == "RED" else MatchResult.LOSS
            
            # Filtra logs por fase
            early_logs = [l for l in state.event_logs if l.get("phase") == "EARLY_GAME"]
            mid_logs = [l for l in state.event_logs if l.get("phase") == "MID_GAME"]
            late_logs = [l for l in state.event_logs if l.get("phase") in ("LATE_GAME", "COMPLETE", "FINISHED")]
            
            total_gold = max(1, state.blue_gold + state.red_gold)
            match = Match(
                id=uuid.UUID(state.match_id),
                league_id=uuid.UUID(state.league_id),
                split_week=state.split_week,
                split_phase=SplitPhase.PLAYOFFS if state.is_playoff else SplitPhase.REGULAR_SEASON,
                is_playoff=state.is_playoff,
                scheduled_at=datetime.utcnow(),
                blue_team_id=uuid.UUID(state.blue_team_id),
                red_team_id=uuid.UUID(state.red_team_id),
                winner_team_id=winner_id,
                blue_result=blue_res,
                red_result=red_res,
                match_duration_minutes=float(state.current_minute),
                blue_win_probability=float(state.blue_gold / total_gold),
                draft_log={"blue": state.blue_draft, "red": state.red_draft},
                early_game_log=early_logs,
                mid_game_log=mid_logs,
                late_game_log=late_logs
            )
            db.add(match)
            
            # 2. Atualiza a tabela de pontuação (LeagueTeam standings)
            blue_lt_query = await db.execute(
                select(LeagueTeam).where(
                    LeagueTeam.league_id == uuid.UUID(state.league_id),
                    LeagueTeam.team_id == uuid.UUID(state.blue_team_id)
                )
            )
            blue_lt = blue_lt_query.scalar_one_or_none()
            
            red_lt_query = await db.execute(
                select(LeagueTeam).where(
                    LeagueTeam.league_id == uuid.UUID(state.league_id),
                    LeagueTeam.team_id == uuid.UUID(state.red_team_id)
                )
            )
            red_lt = red_lt_query.scalar_one_or_none()
            
            # Standings de pontos: só na fase regular
            if blue_lt and red_lt and not state.is_playoff:
                if state.winner_side == "BLUE":
                    blue_lt.wins += 1
                    blue_lt.points += 3
                    red_lt.losses += 1
                else:
                    red_lt.wins += 1
                    red_lt.points += 3
                    blue_lt.losses += 1

            # Playoffs: resolve série no bracket (Redis)
            if state.is_playoff:
                try:
                    from src.modules.calendar.playoff_service import PlayoffService

                    ps = PlayoffService(db)
                    bracket = await ps.resolve_match_result(
                        league_id=state.league_id,
                        blue_team_id=state.blue_team_id,
                        red_team_id=state.red_team_id,
                        winner_team_id=str(winner_id),
                        series_id=getattr(state, "series_id", None),
                        blue_draft=list(state.blue_draft or []),
                        red_draft=list(state.red_draft or []),
                    )
                    if bracket and isinstance(bracket, dict):
                        last = bracket.get("last_map_result") or {}
                        state.series_map_result = last
                        if last.get("score"):
                            state.series_score = last["score"]
                        state.event_logs.append(
                            _normalize_event_log(
                                {
                                    "timestamp": f"{int(state.current_minute):02d}:00",
                                    "phase": "COMPLETE",
                                    "event_type": "SERIES_UPDATE",
                                    "description": (
                                        f"Map {last.get('map_index', '?')} encerrado. "
                                        f"Placar da série: {last.get('score_display', '—')}"
                                        + (
                                            " · Série fechada!"
                                            if last.get("series_complete")
                                            else " · Próximo map em breve."
                                        )
                                    ),
                                    "impact": last,
                                }
                            )
                        )
                        await redis_client.set_generic(
                            f"live_match:{state.match_id}", _state_to_dict(state)
                        )
                except Exception as pe:
                    logger.error(
                        f"[MatchEngineService] Falha ao resolver série de playoff: {pe}",
                        exc_info=True,
                    )

            # 2b. Avalia sessão do draft scout (acertos/erros)
            if getattr(state, "scout_session_id", None):
                try:
                    from src.modules.draft.scout_session import ScoutSessionService

                    managed = str(state.managed_team_id or "")
                    managed_side = "BLUE" if managed == str(state.blue_team_id) else "RED"
                    if managed_side == "BLUE":
                        my_bans, opp_bans = list(state.blue_bans or []), list(state.red_bans or [])
                        my_picks, opp_picks = list(state.blue_draft or []), list(state.red_draft or [])
                        opp_id = state.red_team_id
                    else:
                        my_bans, opp_bans = list(state.red_bans or []), list(state.blue_bans or [])
                        my_picks, opp_picks = list(state.red_draft or []), list(state.blue_draft or [])
                        opp_id = state.blue_team_id

                    opp_pools = []
                    ot = await db.get(Team, uuid.UUID(str(opp_id)))
                    if ot:
                        for p in ot.get_starters():
                            opp_pools.append(
                                {
                                    "name": p.name,
                                    "champion_pool": p.champion_pool
                                    if isinstance(p.champion_pool, list)
                                    else [],
                                }
                            )

                    evaluation = await ScoutSessionService().evaluate_and_store(
                        state.scout_session_id,
                        my_bans=my_bans,
                        opp_bans=opp_bans,
                        my_picks=my_picks,
                        opp_picks=opp_picks,
                        opp_starters_pools=opp_pools,
                        winner_side=state.winner_side,
                    )
                    if evaluation:
                        state.scout_evaluation = evaluation
                        # Regrava estado live com avaliação para o FE
                        await redis_client.set_generic(
                            f"live_match:{state.match_id}", _state_to_dict(state)
                        )
                        state.event_logs.append(
                            _normalize_event_log(
                                {
                                    "timestamp": f"{int(state.current_minute):02d}:00",
                                    "phase": "COMPLETE",
                                    "event_type": "SCOUT_REPORT",
                                    "description": evaluation.get("summary")
                                    or "Relatório do scout disponível.",
                                    "impact": {
                                        "grade": evaluation.get("grade"),
                                        "accuracy": evaluation.get("accuracy"),
                                        "hits": evaluation.get("hits"),
                                        "misses": evaluation.get("misses"),
                                    },
                                }
                            )
                        )
                        await redis_client.set_generic(
                            f"live_match:{state.match_id}", _state_to_dict(state)
                        )
                except Exception as scout_exc:
                    logger.error(
                        f"[MatchEngineService] Falha ao avaliar scout session: {scout_exc}",
                        exc_info=True,
                    )

            # 3. Incrementa games_played e contratos rookie dos titulares
            # 4. Aplica burnout de MATCH_DAY nos titulares (consequência da partida)
            from src.shared.math_utils import clamp as _clamp
            from src.core.config import get_settings
            _settings = get_settings()

            from src.modules.career.training_service import TrainingService
            from sqlalchemy.orm import selectinload

            training_svc = TrainingService(db)

            for team_id in (state.blue_team_id, state.red_team_id):
                # Reload com players (get_starters precisa do roster)
                tq = await db.execute(
                    select(Team)
                    .where(Team.id == uuid.UUID(team_id))
                    .options(selectinload(Team.players))
                )
                team = tq.scalar_one_or_none()
                if not team:
                    continue
                for player in team.get_starters():
                    player.games_played_this_split = (player.games_played_this_split or 0) + 1
                    # Burnout de partida oficial (alinha com BurnoutService MATCH_DAY)
                    player.burnout_meter = _clamp(
                        float(player.burnout_meter) + float(_settings.burnout_daily_penalty),
                        0.0,
                        100.0,
                    )
                    player.visual_fatigue = _clamp(float(player.visual_fatigue) + 12.0, 0.0, 100.0)
                    player.mental_fatigue = _clamp(float(player.mental_fatigue) + 8.0, 0.0, 100.0)

                    contract_query = await db.execute(
                        select(Contract).where(
                            Contract.player_id == player.id,
                            Contract.status == ContractStatus.ACTIVE,
                        )
                    )
                    contract = contract_query.scalar_one_or_none()
                    if contract:
                        contract.rookie_games_played += 1
                        contract.check_and_trigger_rookie_extension()

                # XP de partida: chance de CA/attrs nos titulares
                try:
                    await training_svc.apply_match_xp_for_starters(team)
                except Exception as te:
                    logger.warning(
                        f"[MatchEngineService] Match XP falhou ({team.name}): {te}"
                    )

            await db.commit()
            logger.info(
                f"[MatchEngineService] Partida {state.match_id} persistida; "
                f"standings e burnout de titulares atualizados."
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"[MatchEngineService] Erro ao persistir resultado da partida: {e}", exc_info=True)


# Instância global do helper numpy_rng para o stochastic_roll de match_engine
def numpy_rng():
    import numpy as np
    return np.random.default_generator()
