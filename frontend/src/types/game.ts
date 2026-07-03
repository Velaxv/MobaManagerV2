// Objetos de tempo de execução (as const) e tipos equivalentes para compatibilidade com erasableSyntaxOnly no Vite v6

export const PlayerRole = {
  TOP: "TOP",
  JUNGLE: "JUNGLE",
  MID: "MID",
  BOT: "BOT",
  SUPPORT: "SUPPORT",
} as const;
export type PlayerRole = typeof PlayerRole[keyof typeof PlayerRole];

export const Region = {
  LEC: "LEC",
  ERL: "ERL",
  LCK: "LCK",
  LPL: "LPL",
  LCS: "LCS",
  CBLOL: "CBLOL",
  LLA: "LLA",
} as const;
export type Region = typeof Region[keyof typeof Region];

export const ChampionPoolTier = {
  MAIN: "MAIN",
  SECONDARY: "SECONDARY",
  OFF_POOL: "OFF_POOL",
} as const;
export type ChampionPoolTier = typeof ChampionPoolTier[keyof typeof ChampionPoolTier];

export const CalendarDayType = {
  REST: "REST",
  TRAINING: "TRAINING",
  SCRIM: "SCRIM",
  MATCH_DAY: "MATCH_DAY",
  TRAVEL: "TRAVEL",
  MEDIA: "MEDIA",
} as const;
export type CalendarDayType = typeof CalendarDayType[keyof typeof CalendarDayType];

export const ContractStatus = {
  ACTIVE: "ACTIVE",
  EXPIRED: "EXPIRED",
  TERMINATED: "TERMINATED",
  PENDING_RENEWAL: "PENDING_RENEWAL",
  ROOKIE_EXTENDED: "ROOKIE_EXTENDED",
} as const;
export type ContractStatus = typeof ContractStatus[keyof typeof ContractStatus];

export const SplitPhase = {
  OFFSEASON: "OFFSEASON",
  PRESEASON: "PRESEASON",
  REGULAR_SEASON: "REGULAR_SEASON",
  PLAYOFFS: "PLAYOFFS",
} as const;
export type SplitPhase = typeof SplitPhase[keyof typeof SplitPhase];

export const DraftAction = {
  BAN: "BAN",
  PICK: "PICK",
} as const;
export type DraftAction = typeof DraftAction[keyof typeof DraftAction];

export const DraftTeam = {
  BLUE: "BLUE",
  RED: "RED",
} as const;
export type DraftTeam = typeof DraftTeam[keyof typeof DraftTeam];

export const MatchResult = {
  WIN: "WIN",
  LOSS: "LOSS",
} as const;
export type MatchResult = typeof MatchResult[keyof typeof MatchResult];

// Ordem oficial de 20 ações do Snake Draft competitivo
export const DRAFT_ORDER: [string, DraftTeam, DraftAction][] = [
  // Bans 1 (ABABAB)
  ["BAN 1", DraftTeam.BLUE, DraftAction.BAN],
  ["BAN 1", DraftTeam.RED, DraftAction.BAN],
  ["BAN 1", DraftTeam.BLUE, DraftAction.BAN],
  ["BAN 1", DraftTeam.RED, DraftAction.BAN],
  ["BAN 1", DraftTeam.BLUE, DraftAction.BAN],
  ["BAN 1", DraftTeam.RED, DraftAction.BAN],
  
  // Picks 1 (ABBAAB)
  ["PICK 1", DraftTeam.BLUE, DraftAction.PICK],
  ["PICK 1", DraftTeam.RED, DraftAction.PICK],
  ["PICK 1", DraftTeam.RED, DraftAction.PICK],
  ["PICK 1", DraftTeam.BLUE, DraftAction.PICK],
  ["PICK 1", DraftTeam.BLUE, DraftAction.PICK],
  ["PICK 1", DraftTeam.RED, DraftAction.PICK],
  
  // Bans 2 (BABA)
  ["BAN 2", DraftTeam.RED, DraftAction.BAN],
  ["BAN 2", DraftTeam.BLUE, DraftAction.BAN],
  ["BAN 2", DraftTeam.RED, DraftAction.BAN],
  ["BAN 2", DraftTeam.BLUE, DraftAction.BAN],
  
  // Picks 2 (BAAB)
  ["PICK 2", DraftTeam.RED, DraftAction.PICK],
  ["PICK 2", DraftTeam.BLUE, DraftAction.PICK],
  ["PICK 2", DraftTeam.BLUE, DraftAction.PICK],
  ["PICK 2", DraftTeam.RED, DraftAction.PICK],
];

export const CHAMPIONS_BY_ROLE: Record<string, string[]> = {
  "TOP": ["Aatrox", "Jax", "Gnar", "Sion", "Irelia", "Ornn", "Fiora", "Jayce", "Renekton", "Camille"],
  "JUNGLE": ["Lee Sin", "Graves", "Kindred", "Sejuani", "Viego", "Jarvan IV", "Nocturne", "Elise", "Maokai", "Wukong"],
  "MID": ["Azir", "Viktor", "Sylas", "Ryze", "Orianna", "Syndra", "Ahri", "Yone", "LeBlanc", "Taliyah"],
  "BOT": ["Jinx", "Ezreal", "Kai'Sa", "Aphelios", "Zeri", "Varus", "Lucian", "Caitlyn", "Ashe", "Xayah"],
  "SUPPORT": ["Thresh", "Morgana", "Lulu", "Nautilus", "Rakan", "Leona", "Alistar", "Karma", "Yuumi", "Braum"],
};

export const COUNTER_MAP: Record<string, string[]> = {
  // TOP
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

  // JUNGLE
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

  // MID
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

  // BOT
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

  // SUPPORT
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
};
