/**
 * Hierarquia de alertas do hub — o que merece atenção antes do resto.
 * Usado no Painel (inbox) e badges da sidebar.
 */

import type { AppScreen } from '../types/screens';

export type HubAlertLevel = 'critical' | 'warning' | 'info';

export interface HubAlert {
  id: string;
  level: HubAlertLevel;
  title: string;
  detail?: string;
  /** Tela para resolver */
  screen: AppScreen;
  /** Contagem opcional (ex.: atletas em burnout) */
  count?: number;
}

export interface HubAlertInput {
  burnoutCount: number;
  matchPending: boolean;
  matchLive: boolean;
  financeHealth?: string | null;
  boardOnTrack?: boolean | null;
  boardFired?: boolean;
  boardMessage?: string | null;
  renewalsNeeded?: number;
  isOffseason?: boolean;
  scoutingActive?: boolean;
  scoutingProgress?: number | null;
}

/** Ordena critical → warning → info. */
export function buildHubAlerts(input: HubAlertInput): HubAlert[] {
  const alerts: HubAlert[] = [];

  if (input.boardFired) {
    alerts.push({
      id: 'fired',
      level: 'critical',
      title: 'Demissão',
      detail: input.boardMessage || 'A diretoria encerrou o projeto com você.',
      screen: 'ORG',
    });
  }

  if (input.matchPending) {
    alerts.push({
      id: 'match-draft',
      level: 'critical',
      title: 'Match day — draft pendente',
      detail: 'Sua partida está aguardando picks e bans.',
      screen: 'DRAFT',
    });
  } else if (input.matchLive) {
    alerts.push({
      id: 'match-live',
      level: 'warning',
      title: 'Partida ao vivo',
      detail: 'Acompanhe o Rift ou acelere a simulação.',
      screen: 'SIMULATION',
    });
  }

  if (input.financeHealth === 'critical') {
    alerts.push({
      id: 'finance-critical',
      level: 'critical',
      title: 'Finanças críticas',
      detail: 'Caixa / folha em risco — veja a Organização.',
      screen: 'ORG',
    });
  } else if (input.financeHealth === 'warning') {
    alerts.push({
      id: 'finance-warn',
      level: 'warning',
      title: 'Finanças apertadas',
      detail: 'Runway ou folha em alerta.',
      screen: 'ORG',
    });
  }

  if (input.boardOnTrack === false && !input.boardFired) {
    alerts.push({
      id: 'board-pressure',
      level: 'warning',
      title: 'Board sob pressão',
      detail: input.boardMessage || 'Meta da diretoria em risco.',
      screen: 'ORG',
    });
  }

  if (input.burnoutCount > 0) {
    alerts.push({
      id: 'burnout',
      level: input.burnoutCount >= 3 ? 'critical' : 'warning',
      title: 'Forma física',
      detail: `${input.burnoutCount} atleta(s) com burnout/fadiga alta.`,
      screen: 'TRAINING',
      count: input.burnoutCount,
    });
  }

  if (input.isOffseason && (input.renewalsNeeded || 0) > 0) {
    alerts.push({
      id: 'renewals',
      level: 'warning',
      title: 'Contratos na offseason',
      detail: `${input.renewalsNeeded} renovação(ões) pendente(s).`,
      screen: 'DASHBOARD',
      count: input.renewalsNeeded,
    });
  }

  if (
    input.scoutingActive &&
    input.scoutingProgress != null &&
    input.scoutingProgress < 100
  ) {
    alerts.push({
      id: 'scouting',
      level: 'info',
      title: 'Scouting em andamento',
      detail: `${Math.round(input.scoutingProgress)}% no alvo atual.`,
      screen: 'TRAINING',
    });
  }

  const rank = { critical: 0, warning: 1, info: 2 };
  return alerts.sort((a, b) => rank[a.level] - rank[b.level]);
}

/** Badge numérico / flag por tela (sidebar). */
export function badgeForScreen(
  screen: AppScreen,
  input: HubAlertInput,
): { show: boolean; count?: number; tone: HubAlertLevel } | null {
  switch (screen) {
    case 'DASHBOARD': {
      const n = buildHubAlerts(input).filter((a) => a.level !== 'info').length;
      return n > 0 ? { show: true, count: n, tone: 'warning' } : null;
    }
    case 'TRAINING':
      return input.burnoutCount > 0
        ? {
            show: true,
            count: input.burnoutCount,
            tone: input.burnoutCount >= 3 ? 'critical' : 'warning',
          }
        : null;
    case 'ORG':
      if (input.boardFired || input.financeHealth === 'critical') {
        return { show: true, tone: 'critical' };
      }
      if (input.boardOnTrack === false || input.financeHealth === 'warning') {
        return { show: true, tone: 'warning' };
      }
      return null;
    case 'MARKET':
      if (input.isOffseason && (input.renewalsNeeded || 0) > 0) {
        return { show: true, count: input.renewalsNeeded, tone: 'warning' };
      }
      return null;
    case 'DRAFT':
      return input.matchPending ? { show: true, tone: 'critical' } : null;
    case 'SIMULATION':
      return input.matchLive ? { show: true, tone: 'warning' } : null;
    default:
      return null;
  }
}
