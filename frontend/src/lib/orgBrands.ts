/**
 * Brand kit estilizado CBLOL 2026 (não assets oficiais Riot).
 * Cores derivadas da identidade pública de cada org.
 */

import type { CSSProperties } from 'react';

export type OrgBrand = {
  tag: string;
  name: string;
  /** Cor primária (hex) */
  primary: string;
  /** Cor de destaque */
  accent: string;
  /** Fundo do crest */
  crestBg: string;
  /** Texto no crest */
  crestFg: string;
  /** Classe Tailwind-friendly ring */
  ring: string;
};

const BRANDS: Record<string, OrgBrand> = {
  RED: {
    tag: 'RED',
    name: 'RED Canids',
    primary: '#E10600',
    accent: '#FF4D4D',
    crestBg: 'linear-gradient(145deg, #7a0000 0%, #e10600 55%, #1a0505 100%)',
    crestFg: '#fff',
    ring: 'ring-red-500/50',
  },
  FUR: {
    tag: 'FUR',
    name: 'FURIA',
    primary: '#000000',
    accent: '#FFFFFF',
    crestBg: 'linear-gradient(145deg, #111 0%, #2a2a2a 50%, #000 100%)',
    crestFg: '#fff',
    ring: 'ring-white/40',
  },
  VKS: {
    tag: 'VKS',
    name: 'Vivo Keyd Stars',
    primary: '#660099',
    accent: '#FF9900',
    crestBg: 'linear-gradient(145deg, #3d0060 0%, #660099 50%, #ff9900 140%)',
    crestFg: '#fff',
    ring: 'ring-purple-500/50',
  },
  LOS: {
    tag: 'LOS',
    name: 'LØS',
    primary: '#00D4AA',
    accent: '#E8FFF8',
    crestBg: 'linear-gradient(145deg, #064e3b 0%, #00d4aa 70%, #0f172a 100%)',
    crestFg: '#04120e',
    ring: 'ring-emerald-400/50',
  },
  FX7: {
    tag: 'FX7',
    name: 'Fluxo W7M',
    primary: '#00A3FF',
    accent: '#7DF9FF',
    crestBg: 'linear-gradient(145deg, #0c4a6e 0%, #00a3ff 55%, #082f49 100%)',
    crestFg: '#fff',
    ring: 'ring-sky-400/50',
  },
  LLL: {
    tag: 'LLL',
    name: 'LOUD',
    primary: '#39FF14',
    accent: '#B8FF9F',
    crestBg: 'linear-gradient(145deg, #14532d 0%, #39ff14 45%, #052e16 100%)',
    crestFg: '#052e16',
    ring: 'ring-lime-400/50',
  },
  PNG: {
    tag: 'PNG',
    name: 'paiN Gaming',
    primary: '#000000',
    accent: '#E10600',
    crestBg: 'linear-gradient(145deg, #0a0a0a 0%, #1f1f1f 40%, #e10600 120%)',
    crestFg: '#fff',
    ring: 'ring-red-600/40',
  },
  LEV: {
    tag: 'LEV',
    name: 'Leviatán',
    primary: '#00B4D8',
    accent: '#90E0EF',
    crestBg: 'linear-gradient(145deg, #023e8a 0%, #00b4d8 55%, #03045e 100%)',
    crestFg: '#fff',
    ring: 'ring-cyan-400/50',
  },
};

const FALLBACK: OrgBrand = {
  tag: '???',
  name: 'Org',
  primary: '#C8AA6E',
  accent: '#F0E6D2',
  crestBg: 'linear-gradient(145deg, #3d3420 0%, #c8aa6e 55%, #1a1610 100%)',
  crestFg: '#1a1610',
  ring: 'ring-amber-400/40',
};

/** Resolve brand por abbreviation / tag. */
export function getOrgBrand(tagOrName?: string | null): OrgBrand {
  if (!tagOrName) return FALLBACK;
  const raw = tagOrName.trim().toUpperCase();
  if (BRANDS[raw]) return BRANDS[raw];
  // match por nome parcial
  for (const b of Object.values(BRANDS)) {
    if (raw.includes(b.tag) || b.name.toUpperCase().includes(raw) || raw.includes(b.name.toUpperCase())) {
      return b;
    }
  }
  // heurísticas de nome
  if (raw.includes('PAIN') || raw.includes('PAIN')) return BRANDS.PNG;
  if (raw.includes('FURIA')) return BRANDS.FUR;
  if (raw.includes('LOUD')) return BRANDS.LLL;
  if (raw.includes('KEYD') || raw.includes('VIVO')) return BRANDS.VKS;
  if (raw.includes('FLUXO') || raw.includes('W7M')) return BRANDS.FX7;
  if (raw.includes('CANID') || raw.includes('RED')) return BRANDS.RED;
  if (raw.includes('LEVI')) return BRANDS.LEV;
  if (raw.includes('LØS') || raw.includes('LOS')) return BRANDS.LOS;
  return { ...FALLBACK, tag: raw.slice(0, 3), name: tagOrName };
}

export function orgCrestStyle(tagOrName?: string | null): CSSProperties {
  const b = getOrgBrand(tagOrName);
  return {
    background: b.crestBg,
    color: b.crestFg,
    boxShadow: `0 0 0 1px ${b.primary}55, 0 4px 14px ${b.primary}33`,
  };
}

export function orgPrimary(tagOrName?: string | null): string {
  return getOrgBrand(tagOrName).primary;
}

export const ALL_ORG_BRANDS = Object.values(BRANDS);
