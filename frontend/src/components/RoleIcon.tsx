/** Ícones de role no estilo do cliente de League of Legends */

import type { ReactNode } from 'react';

export type RoleKey = 'TOP' | 'JUNGLE' | 'MID' | 'BOT' | 'SUPPORT' | 'ADC';

interface RoleIconProps {
  role: string;
  className?: string;
  size?: number;
  active?: boolean;
}

const PATHS: Record<string, ReactNode> = {
  TOP: (
    <>
      {/* Ícone de top: escudo + seta diagonal */}
      <path d="M4 4h8v2H6v6H4V4z" fill="currentColor" />
      <path d="M8 8l8 8M16 10v6h-6" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <path d="M14 6l4-2v4l-4-2z" fill="currentColor" opacity="0.85" />
    </>
  ),
  JUNGLE: (
    <>
      {/* Folha / monstro de selva */}
      <path
        d="M12 3c-2 3-6 4.5-7 8 2-.5 4 .2 5.5 1.5C9 15 8 18 12 21c4-3 3-6 1.5-8.5C15 11.2 17 10.5 19 11c-1-3.5-5-5-7-8z"
        fill="currentColor"
      />
      <path d="M12 10v8" stroke="#0a1428" strokeWidth="1.2" opacity="0.35" />
    </>
  ),
  MID: (
    <>
      {/* Diamante / rota do meio */}
      <path d="M12 3l7 9-7 9-7-9 7-9z" fill="currentColor" opacity="0.25" />
      <path d="M12 5.5L17 12l-5 6.5L7 12l5-6.5z" fill="currentColor" />
      <path d="M5 5l14 14M19 5L5 19" stroke="currentColor" strokeWidth="1.4" opacity="0.9" />
    </>
  ),
  BOT: (
    <>
      {/* Mira / ADC */}
      <circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="2.2" fill="currentColor" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
  ADC: (
    <>
      <circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="2.2" fill="currentColor" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
  SUPPORT: (
    <>
      {/* Escudo / suporte */}
      <path
        d="M12 3c3 2 6 2.5 7 3v6.5c0 4.5-3.2 7.2-7 8.5-3.8-1.3-7-4-7-8.5V6c1-.5 4-1 7-3z"
        fill="currentColor"
        opacity="0.3"
      />
      <path
        d="M12 4.5c2.2 1.4 4.5 1.8 5.5 2.1v5.6c0 3.4-2.4 5.5-5.5 6.6-3.1-1.1-5.5-3.2-5.5-6.6V6.6c1-.3 3.3-.7 5.5-2.1z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M12 9v6M9 12h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
};

export function RoleIcon({ role, className = '', size = 16, active = false }: RoleIconProps) {
  const key = role === 'ADC' ? 'ADC' : role;
  const content = PATHS[key] || PATHS.MID;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={`shrink-0 ${active ? 'text-lol-hq-cyan drop-shadow-[0_0_4px_rgba(200,155,60,0.6)]' : ''} ${className}`}
      aria-hidden
    >
      {content}
    </svg>
  );
}
