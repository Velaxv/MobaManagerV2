/**
 * Integração com Data Dragon (CDN oficial Riot) para retratos e splashes.
 * Nomes do jogo → IDs do client (sem acentos / casos especiais).
 */

const DDRAGON_VERSION = '15.8.1';
const DDRAGON_BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}`;

/** Mapa de nomes do seed/API → id Data Dragon */
const CHAMPION_ID_OVERRIDES: Record<string, string> = {
  "Cho'Gath": 'Chogath',
  "Kai'Sa": 'Kaisa',
  "Kha'Zix": 'Khazix',
  "Kog'Maw": 'KogMaw',
  "LeBlanc": 'Leblanc',
  "Lee Sin": 'LeeSin',
  "Master Yi": 'MasterYi',
  "Miss Fortune": 'MissFortune',
  "Nunu & Willump": 'Nunu',
  "Rek'Sai": "RekSai",
  "Tahm Kench": 'TahmKench',
  "Twisted Fate": 'TwistedFate',
  "Vel'Koz": 'Velkoz',
  "Xin Zhao": 'XinZhao',
  "Dr. Mundo": 'DrMundo',
  "Jarvan IV": 'JarvanIV',
  "Aurelion Sol": 'AurelionSol',
  "Bel'Veth": 'Belveth',
  "K'Sante": 'KSante',
  "Wukong": 'MonkeyKing',
  "Renata Glasc": 'Renata',
};

export function championDdragonId(name: string): string {
  if (!name) return 'Aatrox';
  if (CHAMPION_ID_OVERRIDES[name]) return CHAMPION_ID_OVERRIDES[name];
  // Remove espaços e apóstrofos como fallback genérico
  return name.replace(/['.\s]/g, '').replace(/&/g, '');
}

export function championPortraitUrl(name: string): string {
  return `${DDRAGON_BASE}/img/champion/${championDdragonId(name)}.png`;
}

export function championSplashUrl(name: string, skin = 0): string {
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${championDdragonId(name)}_${skin}.jpg`;
}

export function championLoadingUrl(name: string, skin = 0): string {
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/${championDdragonId(name)}_${skin}.jpg`;
}

export const ROLE_LABELS: Record<string, string> = {
  TOP: 'Topo',
  JUNGLE: 'Selva',
  MID: 'Meio',
  BOT: 'Atirador',
  SUPPORT: 'Suporte',
  ADC: 'Atirador',
};
