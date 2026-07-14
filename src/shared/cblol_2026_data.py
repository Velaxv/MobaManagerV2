# -*- coding: utf-8 -*-
"""
Dados oficiais do CBLOL 2026 Split 1 (seed do jogo).

Fonte de referência (Leaguepedia / CBLOL 2026 Split 1):
  8 times — sem KaBuM, INTZ, Liberty, Isurus.
  Elencos dos titulares + head coach.

Formato de cada time:
  name, abbreviation, has_academy, budget_millions, monthly_rev_k,
  head_coach, strategic_coach|None,
  starters: list of (nick, role, ca, pa, mechanics, focus, nationality)

Mercado interno = jogadores de outros times CBLOL (sem G2/T1/LEC/LPL).
"""

from src.shared.enums import PlayerRole

# Pools por role (campeões presentes em champions_data / meta BR)
POOLS_BY_ROLE = {
    PlayerRole.TOP: [
        {"champion": "Aatrox", "tier": "MAIN"},
        {"champion": "Jax", "tier": "MAIN"},
        {"champion": "Renekton", "tier": "SECONDARY"},
        {"champion": "Gnar", "tier": "SECONDARY"},
        {"champion": "K'Sante", "tier": "SECONDARY"},
    ],
    PlayerRole.JUNGLE: [
        {"champion": "Lee Sin", "tier": "MAIN"},
        {"champion": "Viego", "tier": "MAIN"},
        {"champion": "Sejuani", "tier": "SECONDARY"},
        {"champion": "Maokai", "tier": "SECONDARY"},
        {"champion": "Xin Zhao", "tier": "SECONDARY"},
    ],
    PlayerRole.MID: [
        {"champion": "Azir", "tier": "MAIN"},
        {"champion": "Viktor", "tier": "MAIN"},
        {"champion": "Ahri", "tier": "SECONDARY"},
        {"champion": "Orianna", "tier": "SECONDARY"},
        {"champion": "Sylas", "tier": "SECONDARY"},
    ],
    PlayerRole.BOT: [
        {"champion": "Kai'Sa", "tier": "MAIN"},
        {"champion": "Jinx", "tier": "MAIN"},
        {"champion": "Varus", "tier": "SECONDARY"},
        {"champion": "Ezreal", "tier": "SECONDARY"},
        {"champion": "Zeri", "tier": "SECONDARY"},
    ],
    PlayerRole.SUPPORT: [
        {"champion": "Rell", "tier": "MAIN"},
        {"champion": "Nautilus", "tier": "MAIN"},
        {"champion": "Lulu", "tier": "SECONDARY"},
        {"champion": "Rakan", "tier": "SECONDARY"},
        {"champion": "Alistar", "tier": "SECONDARY"},
    ],
}

# (name, tag, has_academy, budget_M, monthly_rev_k, head_coach, strat_coach, starters)
# starters: (nick, role, CA, PA, mechanics, focus, nationality)
CBLOL_2026_TEAMS = [
    (
        "RED Canids Kalunga",
        "RED",
        True,
        4.2,
        115,
        "tockers",
        "BeellzY",
        [
            ("zynts", PlayerRole.TOP, 142, 168, 14.5, 14.0, "Brazil"),
            ("STEPZ", PlayerRole.JUNGLE, 144, 170, 15.0, 14.5, "Venezuela"),
            ("Kaze", PlayerRole.MID, 152, 178, 16.5, 15.5, "Argentina"),  # All-Pro
            ("Rabelo", PlayerRole.BOT, 145, 172, 15.0, 14.5, "Brazil"),
            ("frosty", PlayerRole.SUPPORT, 140, 165, 14.0, 15.0, "Brazil"),
        ],
    ),
    (
        "FURIA Esports",
        "FUR",
        True,
        4.8,
        125,
        "furyz",
        "lanterninho",
        [
            ("Guigo", PlayerRole.TOP, 146, 172, 15.0, 15.0, "Brazil"),
            ("Tatu", PlayerRole.JUNGLE, 155, 185, 17.0, 16.0, "Brazil"),  # Finals MVP / All-Pro
            ("Tutsz", PlayerRole.MID, 148, 175, 15.5, 15.0, "Brazil"),
            ("Ayu", PlayerRole.BOT, 154, 182, 16.5, 15.0, "Brazil"),  # All-Pro
            ("JoJo", PlayerRole.SUPPORT, 151, 178, 15.5, 16.0, "Brazil"),  # All-Pro
        ],
    ),
    (
        "Vivo Keyd Stars",
        "VKS",
        True,
        4.5,
        120,
        "SeeEl",
        "Smiley",
        [
            ("Wizer", PlayerRole.TOP, 150, 175, 16.0, 15.5, "South Korea"),
            ("Disamis", PlayerRole.JUNGLE, 146, 174, 15.0, 14.5, "Brazil"),
            ("Mireu", PlayerRole.MID, 149, 176, 16.0, 15.0, "South Korea"),
            ("ceo", PlayerRole.BOT, 144, 170, 15.0, 14.0, "Argentina"),
            ("Kaiwing", PlayerRole.SUPPORT, 147, 172, 15.0, 15.5, "Hong Kong"),
        ],
    ),
    (
        "LØS",
        "LOS",
        False,  # Guest team no CBLOL 2026
        3.2,
        85,
        "Enatron",
        "Brandão",
        [
            ("Zest", PlayerRole.TOP, 153, 180, 16.5, 15.5, "South Korea"),  # All-Pro / Fearless
            ("Curse", PlayerRole.JUNGLE, 141, 168, 14.5, 14.0, "Brazil"),
            ("Feisty", PlayerRole.MID, 148, 176, 16.0, 15.0, "South Korea"),
            ("Duduhh", PlayerRole.BOT, 143, 170, 15.0, 14.0, "Brazil"),
            ("Ackerman", PlayerRole.SUPPORT, 145, 172, 14.5, 15.5, "Argentina"),
        ],
    ),
    (
        "Fluxo W7M",
        "FX7",
        True,
        3.5,
        95,
        "Samyy",
        "Guchi",
        [
            ("curty", PlayerRole.TOP, 138, 165, 14.0, 14.0, "Brazil"),
            ("Peach", PlayerRole.JUNGLE, 143, 170, 15.0, 14.0, "South Korea"),
            ("cody", PlayerRole.MID, 140, 168, 14.5, 14.0, "Chile"),
            ("BAO", PlayerRole.BOT, 146, 174, 15.5, 14.5, "South Korea"),
            ("Momochi", PlayerRole.SUPPORT, 137, 162, 13.5, 14.5, "Brazil"),
        ],
    ),
    (
        "LOUD",
        "LLL",
        True,
        5.0,
        130,
        "Raise",
        "Sephis",
        [
            ("Xyno", PlayerRole.TOP, 142, 170, 14.5, 14.5, "Brazil"),
            ("YoungJae", PlayerRole.JUNGLE, 147, 175, 15.5, 15.0, "South Korea"),
            ("Envy", PlayerRole.MID, 149, 176, 15.5, 15.5, "Brazil"),
            ("Bull", PlayerRole.BOT, 150, 180, 16.5, 14.5, "South Korea"),  # Cup Finals MVP hist.
            ("RedBert", PlayerRole.SUPPORT, 144, 170, 14.5, 15.5, "Brazil"),
        ],
    ),
    (
        "paiN Gaming",
        "PNG",
        True,
        4.6,
        122,
        "Sarkis",
        "Xero",
        [
            ("Robo", PlayerRole.TOP, 151, 178, 16.0, 16.0, "Brazil"),
            ("CarioK", PlayerRole.JUNGLE, 145, 172, 15.0, 15.5, "Brazil"),
            ("Keine", PlayerRole.MID, 148, 176, 16.0, 15.0, "South Korea"),
            ("Trigger", PlayerRole.BOT, 147, 175, 15.5, 14.5, "South Korea"),
            ("Kuri", PlayerRole.SUPPORT, 146, 172, 15.0, 15.5, "South Korea"),
        ],
    ),
    (
        "Leviatán",
        "LEV",
        True,
        3.8,
        100,
        "Kouke",
        "SrVenancio",
        [
            ("Devost", PlayerRole.TOP, 136, 162, 13.5, 13.5, "Colombia"),
            ("Booki", PlayerRole.JUNGLE, 138, 164, 14.0, 13.5, "Peru"),
            ("Enga", PlayerRole.MID, 141, 168, 14.5, 14.0, "Argentina"),
            ("Snaker", PlayerRole.BOT, 143, 170, 15.0, 14.0, "Argentina"),
            ("Toplop", PlayerRole.SUPPORT, 135, 160, 13.5, 14.0, "Argentina"),
        ],
    ),
]

# Subs / sixth man conhecidos (opcional) — gerados no seed como reserva se has_academy
KNOWN_SUBS = {
    "PNG": [("Samkz", PlayerRole.JUNGLE, 128, 155, 13.0, 13.0, "Brazil")],
    "LLL": [("uZent", PlayerRole.SUPPORT, 130, 158, 13.5, 14.0, "Brazil")],
    "VKS": [("sarolu", PlayerRole.JUNGLE, 125, 152, 12.5, 13.0, "Brazil")],
    "RED": [("Morttheus", PlayerRole.BOT, 132, 160, 14.0, 13.5, "Brazil")],
    "LOS": [("Drakehero", PlayerRole.JUNGLE, 134, 162, 14.0, 13.5, "Brazil")],
}

LEAGUE_META = {
    "name": "Campeonato Brasileiro de League of Legends 2026",
    "abbreviation": "CBLOL",
    "regular_season_weeks": 7,  # Single round-robin 8 times → 7 weeks
    "matches_per_week": 4,  # 4 BO3 por rodada (8 times)
    "playoff_teams": 6,
    "prize_pool": {"1st": 100000.0, "2nd": 60000.0, "3rd": 40000.0},
    "total_prize_pool": "200000.00",
}
