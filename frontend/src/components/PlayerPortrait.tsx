import { useState } from 'react';
import { getPlayerPhotoUrl } from '../lib/playerPhotoMap';

type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

const SIZE_CLASS: Record<Size, string> = {
  xs: 'w-8 h-8',
  sm: 'w-10 h-10',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
  xl: 'w-20 h-20',
};

interface PlayerPortraitProps {
  name: string;
  size?: Size;
  className?: string;
  /** Anel/borda ativa (ex.: seu time) */
  highlighted?: boolean;
}

/** Silhueta genérica — sem foto de campeão. */
function Silhouette({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      className={`w-full h-full ${className}`}
      aria-hidden
    >
      <defs>
        <linearGradient id="silBody" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1a2332" />
          <stop offset="100%" stopColor="#0a1018" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" fill="url(#silBody)" />
      {/* cabeça */}
      <circle cx="32" cy="22" r="11" fill="#2a3548" />
      {/* ombros / torso */}
      <ellipse cx="32" cy="52" rx="20" ry="16" fill="#2a3548" />
      {/* brilho sutil */}
      <ellipse cx="28" cy="18" rx="4" ry="3" fill="#3d4d66" opacity="0.35" />
    </svg>
  );
}

/**
 * Retrato do jogador: foto real se existir no mapa local; senão silhueta.
 * Nunca usa splash/portrait de campeão do Data Dragon.
 */
export function PlayerPortrait({
  name,
  size = 'md',
  className = '',
  highlighted = false,
}: PlayerPortraitProps) {
  const url = getPlayerPhotoUrl(name);
  const [failed, setFailed] = useState(false);
  const showPhoto = Boolean(url) && !failed;

  return (
    <div
      className={`
        relative shrink-0 overflow-hidden rounded-sm bg-lol-void
        border ${highlighted ? 'border-lol-hq-cyan/60 shadow-hq-cyan' : 'border-white/10'}
        ${SIZE_CLASS[size]} ${className}
      `}
      title={name}
    >
      {showPhoto ? (
        <img
          src={url!}
          alt={name}
          className="w-full h-full object-cover object-top"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <Silhouette />
      )}
      {/* vinheta inferior */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-black/50 to-transparent" />
    </div>
  );
}
