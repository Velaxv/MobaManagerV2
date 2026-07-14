# -*- coding: utf-8 -*-
"""
Meta global competitivo (proxy estilo op.gg / u.gg) por campeão.

Usado pelo Draft Scout para win rate, pick rate e volume de partidas.
Valores calibrados para o patch de referência do seed (CBLOL / pro-play BR).
Campeões fora da lista usam fallback determinístico em draft_scout.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# patch de referência dos números abaixo
META_PATCH_VERSION = "16.1"

# champion lower -> stats
# games_played: volume global no patch (soloq+pro proxy)
# pick_rate: % de jogos
# win_rate: %
# pro_presence: 0–1 peso no competitivo
GLOBAL_CHAMPION_META: Dict[str, Dict[str, Any]] = {
    # TOP
    "aatrox": {"games_played": 1_850_000, "pick_rate": 12.4, "win_rate": 50.8, "pro_presence": 0.92, "role": "TOP"},
    "jax": {"games_played": 1_420_000, "pick_rate": 9.1, "win_rate": 50.2, "pro_presence": 0.78, "role": "TOP"},
    "gnar": {"games_played": 980_000, "pick_rate": 6.2, "win_rate": 49.6, "pro_presence": 0.88, "role": "TOP"},
    "ornn": {"games_played": 720_000, "pick_rate": 4.8, "win_rate": 51.4, "pro_presence": 0.90, "role": "TOP"},
    "renekton": {"games_played": 1_100_000, "pick_rate": 7.5, "win_rate": 49.1, "pro_presence": 0.80, "role": "TOP"},
    "ksante": {"games_played": 640_000, "pick_rate": 4.1, "win_rate": 48.2, "pro_presence": 0.85, "role": "TOP"},
    "k'sante": {"games_played": 640_000, "pick_rate": 4.1, "win_rate": 48.2, "pro_presence": 0.85, "role": "TOP"},
    "camille": {"games_played": 890_000, "pick_rate": 5.9, "win_rate": 50.5, "pro_presence": 0.82, "role": "TOP"},
    "jayce": {"games_played": 760_000, "pick_rate": 5.0, "win_rate": 49.0, "pro_presence": 0.84, "role": "TOP"},
    "sion": {"games_played": 540_000, "pick_rate": 3.6, "win_rate": 51.9, "pro_presence": 0.70, "role": "TOP"},
    "fiora": {"games_played": 1_050_000, "pick_rate": 7.0, "win_rate": 50.9, "pro_presence": 0.55, "role": "TOP"},
    "irelia": {"games_played": 1_200_000, "pick_rate": 8.0, "win_rate": 49.4, "pro_presence": 0.62, "role": "TOP"},
    "rumble": {"games_played": 410_000, "pick_rate": 2.7, "win_rate": 50.1, "pro_presence": 0.75, "role": "TOP"},
    "gwen": {"games_played": 680_000, "pick_rate": 4.5, "win_rate": 50.6, "pro_presence": 0.58, "role": "TOP"},
    "ambessa": {"games_played": 920_000, "pick_rate": 6.0, "win_rate": 50.3, "pro_presence": 0.72, "role": "TOP"},
    # JUNGLE
    "lee sin": {"games_played": 2_100_000, "pick_rate": 14.2, "win_rate": 48.8, "pro_presence": 0.70, "role": "JUNGLE"},
    "sejuani": {"games_played": 680_000, "pick_rate": 4.4, "win_rate": 51.2, "pro_presence": 0.93, "role": "JUNGLE"},
    "maokai": {"games_played": 520_000, "pick_rate": 3.4, "win_rate": 51.8, "pro_presence": 0.88, "role": "JUNGLE"},
    "vi": {"games_played": 1_150_000, "pick_rate": 7.6, "win_rate": 51.0, "pro_presence": 0.65, "role": "JUNGLE"},
    "viego": {"games_played": 1_380_000, "pick_rate": 9.0, "win_rate": 50.4, "pro_presence": 0.72, "role": "JUNGLE"},
    "graves": {"games_played": 890_000, "pick_rate": 5.8, "win_rate": 49.7, "pro_presence": 0.68, "role": "JUNGLE"},
    "kindred": {"games_played": 540_000, "pick_rate": 3.5, "win_rate": 50.0, "pro_presence": 0.60, "role": "JUNGLE"},
    "xinzhao": {"games_played": 720_000, "pick_rate": 4.7, "win_rate": 51.5, "pro_presence": 0.55, "role": "JUNGLE"},
    "xin zhao": {"games_played": 720_000, "pick_rate": 4.7, "win_rate": 51.5, "pro_presence": 0.55, "role": "JUNGLE"},
    "wukong": {"games_played": 610_000, "pick_rate": 4.0, "win_rate": 50.8, "pro_presence": 0.74, "role": "JUNGLE"},
    "jarvan iv": {"games_played": 780_000, "pick_rate": 5.1, "win_rate": 50.6, "pro_presence": 0.80, "role": "JUNGLE"},
    "nocturne": {"games_played": 650_000, "pick_rate": 4.2, "win_rate": 51.1, "pro_presence": 0.58, "role": "JUNGLE"},
    "elise": {"games_played": 430_000, "pick_rate": 2.8, "win_rate": 49.5, "pro_presence": 0.66, "role": "JUNGLE"},
    "lillia": {"games_played": 700_000, "pick_rate": 4.6, "win_rate": 51.3, "pro_presence": 0.62, "role": "JUNGLE"},
    "skarner": {"games_played": 390_000, "pick_rate": 2.5, "win_rate": 50.9, "pro_presence": 0.77, "role": "JUNGLE"},
    # MID
    "azir": {"games_played": 820_000, "pick_rate": 5.3, "win_rate": 48.9, "pro_presence": 0.95, "role": "MID"},
    "orianna": {"games_played": 740_000, "pick_rate": 4.8, "win_rate": 50.7, "pro_presence": 0.94, "role": "MID"},
    "ahri": {"games_played": 1_650_000, "pick_rate": 10.8, "win_rate": 50.5, "pro_presence": 0.78, "role": "MID"},
    "syndra": {"games_played": 910_000, "pick_rate": 5.9, "win_rate": 50.1, "pro_presence": 0.82, "role": "MID"},
    "viktor": {"games_played": 780_000, "pick_rate": 5.0, "win_rate": 50.4, "pro_presence": 0.86, "role": "MID"},
    "sylas": {"games_played": 1_280_000, "pick_rate": 8.4, "win_rate": 49.6, "pro_presence": 0.84, "role": "MID"},
    "ryze": {"games_played": 420_000, "pick_rate": 2.7, "win_rate": 48.5, "pro_presence": 0.80, "role": "MID"},
    "yone": {"games_played": 1_900_000, "pick_rate": 12.5, "win_rate": 49.9, "pro_presence": 0.55, "role": "MID"},
    "leblanc": {"games_played": 690_000, "pick_rate": 4.5, "win_rate": 49.2, "pro_presence": 0.70, "role": "MID"},
    "le blanc": {"games_played": 690_000, "pick_rate": 4.5, "win_rate": 49.2, "pro_presence": 0.70, "role": "MID"},
    "taliyah": {"games_played": 380_000, "pick_rate": 2.4, "win_rate": 50.8, "pro_presence": 0.76, "role": "MID"},
    "akali": {"games_played": 1_450_000, "pick_rate": 9.5, "win_rate": 49.0, "pro_presence": 0.58, "role": "MID"},
    "aurora": {"games_played": 860_000, "pick_rate": 5.6, "win_rate": 50.2, "pro_presence": 0.72, "role": "MID"},
    "hwei": {"games_played": 710_000, "pick_rate": 4.6, "win_rate": 49.8, "pro_presence": 0.68, "role": "MID"},
    # BOT
    "jinx": {"games_played": 1_780_000, "pick_rate": 11.6, "win_rate": 51.2, "pro_presence": 0.70, "role": "BOT"},
    "ezreal": {"games_played": 2_050_000, "pick_rate": 13.4, "win_rate": 49.3, "pro_presence": 0.75, "role": "BOT"},
    "kai'sa": {"games_played": 1_620_000, "pick_rate": 10.6, "win_rate": 50.0, "pro_presence": 0.88, "role": "BOT"},
    "kaisa": {"games_played": 1_620_000, "pick_rate": 10.6, "win_rate": 50.0, "pro_presence": 0.88, "role": "BOT"},
    "varus": {"games_played": 980_000, "pick_rate": 6.4, "win_rate": 49.7, "pro_presence": 0.86, "role": "BOT"},
    "aphelios": {"games_played": 720_000, "pick_rate": 4.7, "win_rate": 49.1, "pro_presence": 0.80, "role": "BOT"},
    "zeri": {"games_played": 540_000, "pick_rate": 3.5, "win_rate": 48.8, "pro_presence": 0.72, "role": "BOT"},
    "xayah": {"games_played": 810_000, "pick_rate": 5.3, "win_rate": 50.9, "pro_presence": 0.74, "role": "BOT"},
    "caitlyn": {"games_played": 1_300_000, "pick_rate": 8.5, "win_rate": 50.4, "pro_presence": 0.60, "role": "BOT"},
    "ashe": {"games_played": 1_100_000, "pick_rate": 7.2, "win_rate": 50.7, "pro_presence": 0.65, "role": "BOT"},
    "lucian": {"games_played": 890_000, "pick_rate": 5.8, "win_rate": 49.5, "pro_presence": 0.70, "role": "BOT"},
    "smolder": {"games_played": 760_000, "pick_rate": 5.0, "win_rate": 50.1, "pro_presence": 0.58, "role": "BOT"},
    "miss fortune": {"games_played": 1_250_000, "pick_rate": 8.1, "win_rate": 51.0, "pro_presence": 0.45, "role": "BOT"},
    # SUPPORT
    "thresh": {"games_played": 1_400_000, "pick_rate": 9.1, "win_rate": 49.4, "pro_presence": 0.82, "role": "SUPPORT"},
    "nautilus": {"games_played": 1_280_000, "pick_rate": 8.3, "win_rate": 50.6, "pro_presence": 0.90, "role": "SUPPORT"},
    "rakan": {"games_played": 860_000, "pick_rate": 5.6, "win_rate": 50.8, "pro_presence": 0.88, "role": "SUPPORT"},
    "lulu": {"games_played": 1_050_000, "pick_rate": 6.8, "win_rate": 50.9, "pro_presence": 0.80, "role": "SUPPORT"},
    "leona": {"games_played": 1_100_000, "pick_rate": 7.1, "win_rate": 50.5, "pro_presence": 0.72, "role": "SUPPORT"},
    "alistar": {"games_played": 720_000, "pick_rate": 4.7, "win_rate": 50.3, "pro_presence": 0.78, "role": "SUPPORT"},
    "braum": {"games_played": 540_000, "pick_rate": 3.5, "win_rate": 50.1, "pro_presence": 0.76, "role": "SUPPORT"},
    "morgana": {"games_played": 980_000, "pick_rate": 6.4, "win_rate": 50.0, "pro_presence": 0.55, "role": "SUPPORT"},
    "karma": {"games_played": 690_000, "pick_rate": 4.5, "win_rate": 49.8, "pro_presence": 0.68, "role": "SUPPORT"},
    "yuumi": {"games_played": 820_000, "pick_rate": 5.3, "win_rate": 48.6, "pro_presence": 0.40, "role": "SUPPORT"},
    "rell": {"games_played": 610_000, "pick_rate": 4.0, "win_rate": 51.0, "pro_presence": 0.85, "role": "SUPPORT"},
    "bard": {"games_played": 480_000, "pick_rate": 3.1, "win_rate": 51.4, "pro_presence": 0.70, "role": "SUPPORT"},
    "poppy": {"games_played": 550_000, "pick_rate": 3.6, "win_rate": 51.2, "pro_presence": 0.74, "role": "SUPPORT"},
    "neeko": {"games_played": 430_000, "pick_rate": 2.8, "win_rate": 50.4, "pro_presence": 0.66, "role": "SUPPORT"},
}


def _normalize_key(name: str) -> str:
    return (name or "").strip().lower().replace(".", "")


def get_champion_meta(champion_name: str) -> Optional[Dict[str, Any]]:
    """Retorna stats de meta global ou None se não houver seed."""
    key = _normalize_key(champion_name)
    if key in GLOBAL_CHAMPION_META:
        return dict(GLOBAL_CHAMPION_META[key])
    # tenta sem apóstrofo / espaços extras
    key2 = key.replace("'", "").replace("  ", " ")
    if key2 in GLOBAL_CHAMPION_META:
        return dict(GLOBAL_CHAMPION_META[key2])
    # leblanc / kaisa variants
    compact = key.replace(" ", "").replace("'", "")
    for k, v in GLOBAL_CHAMPION_META.items():
        if k.replace(" ", "").replace("'", "") == compact:
            return dict(v)
    return None


def list_meta_champions() -> Dict[str, Dict[str, Any]]:
    return {k: dict(v) for k, v in GLOBAL_CHAMPION_META.items()}
