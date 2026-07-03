from enum import Enum


class PlayerRole(str, Enum):
    """Posições/funções do jogador no time."""
    TOP = "TOP"
    JUNGLE = "JUNGLE"
    MID = "MID"
    BOT = "BOT"
    SUPPORT = "SUPPORT"
    ADC = "ADC"


class LeagueType(str, Enum):
    """Tipo de liga/competição."""
    LEC = "LEC"          # Liga principal (exige 18+ anos)
    ERL = "ERL"          # Ligas regionais europeias (exige 16+ anos)
    ACADEMY = "ACADEMY"  # Time base/academy


class SplitPhase(str, Enum):
    """Fase atual da temporada/split."""
    OFFSEASON = "OFFSEASON"
    PRESEASON = "PRESEASON"
    REGULAR_SEASON = "REGULAR_SEASON"
    PLAYOFFS = "PLAYOFFS"
    WORLDS = "WORLDS"


class CalendarDayType(str, Enum):
    """Tipo de dia no calendário do time."""
    REST = "REST"              # Descanso obrigatório
    TRAINING = "TRAINING"      # Treino
    SCRIM = "SCRIM"            # Scrim contra outro time
    MATCH_DAY = "MATCH_DAY"    # Dia de partida oficial
    TRAVEL = "TRAVEL"          # Viagem
    MEDIA = "MEDIA"            # Obrigações de mídia


class ContractStatus(str, Enum):
    """Status atual do contrato."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    PENDING_RENEWAL = "PENDING_RENEWAL"
    ROOKIE_EXTENDED = "ROOKIE_EXTENDED"  # Extensão automática por cláusula rookie


class MatchPhase(str, Enum):
    """Fase da partida no motor de simulação."""
    DRAFT = "DRAFT"
    EARLY_GAME = "EARLY_GAME"   # 0-15min: laning phase
    MID_GAME = "MID_GAME"       # 15-25min: objetivos
    LATE_GAME = "LATE_GAME"     # 25+min: teamfights e closes


class DraftAction(str, Enum):
    """Ação possível durante o draft."""
    BAN = "BAN"
    PICK = "PICK"


class DraftTeam(str, Enum):
    """Time no draft (Blue Side / Red Side)."""
    BLUE = "BLUE"
    RED = "RED"


class ChampionPoolTier(str, Enum):
    """Nível de proficiência do campeão no pool do jogador."""
    MAIN = "MAIN"           # Campeão principal — bônus de mecânica
    SECONDARY = "SECONDARY" # Campeão secundário — leve debuff
    OFF_POOL = "OFF_POOL"   # Fora do pool — debuff severo


class BurnoutLevel(str, Enum):
    """Nível de burnout do jogador."""
    FRESH = "FRESH"           # 0-25: em forma
    TIRED = "TIRED"           # 26-50: cansado
    FATIGUED = "FATIGUED"     # 51-75: fatigado
    CRITICAL = "CRITICAL"     # 76-90: crítico
    BURNED_OUT = "BURNED_OUT" # 91-100: burnout total


class MatchResult(str, Enum):
    """Resultado de uma partida."""
    WIN = "WIN"
    LOSS = "LOSS"
    FORFEIT = "FORFEIT"


class Region(str, Enum):
    """Regiões do competitivo de LoL."""
    LEC = "LEC"       # Europa
    LCK = "LCK"       # Coreia
    LPL = "LPL"       # China
    LCS = "LCS"       # América do Norte
    CBLOL = "CBLOL"   # Brasil
    LLA = "LLA"       # América Latina


class DamageType(str, Enum):
    """Tipo de dano primário de um campeão."""
    AD = "AD"
    AP = "AP"
    TRUE = "TRUE"
    MIXED = "MIXED"


class ClassType(str, Enum):
    """Função tática/Arquétipo de um campeão."""
    TANK_ENGAGE = "TANK_ENGAGE"
    TANK_WARDEN = "TANK_WARDEN"
    BRUISER = "BRUISER"
    ASSASSIN = "ASSASSIN"
    MAGE_CONTROL = "MAGE_CONTROL"
    MAGE_BURST = "MAGE_BURST"
    MARKSMAN_HYPERCARRY = "MARKSMAN_HYPERCARRY"
    MARKSMAN_UTILITY = "MARKSMAN_UTILITY"
    ENCHANTER = "ENCHANTER"
