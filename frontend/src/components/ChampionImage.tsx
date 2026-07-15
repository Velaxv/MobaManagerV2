import { useState } from 'react';
import { championPortraitUrl, championSplashUrl, championLoadingUrl } from '../lib/champions';

type Variant = 'portrait' | 'ban' | 'pick' | 'splash-thumb' | 'loading';

interface ChampionImageProps {
  name: string | null | undefined;
  variant?: Variant;
  className?: string;
  showName?: boolean;
  emptyLabel?: string;
  banned?: boolean;
  /** Campeão já travado no draft (borda ouro + brilho) */
  locked?: boolean;
  highlighted?: boolean;
  onClick?: () => void;
  disabled?: boolean;
}

const sizeClass: Record<Variant, string> = {
  portrait: 'w-12 h-12',
  ban: 'w-10 h-10 sm:w-11 sm:h-11',
  pick: 'w-14 h-14 sm:w-16 sm:h-16',
  'splash-thumb': 'w-full h-20 sm:h-24',
  loading: 'w-28 h-48 sm:w-36 sm:h-60',
};

export function ChampionImage({
  name,
  variant = 'portrait',
  className = '',
  showName = false,
  emptyLabel = '—',
  banned = false,
  locked = false,
  highlighted = false,
  onClick,
  disabled = false,
}: ChampionImageProps) {
  const [failed, setFailed] = useState(false);
  const isEmpty = !name;

  const ring = locked
    ? 'ring-2 ring-lol-hq-cyan shadow-hq-cyan'
    : highlighted
      ? 'ring-2 ring-lol-hq-cyan shadow-[0_0_12px_rgba(200,155,60,0.55)]'
      : banned
        ? 'ring-1 ring-red-700/80'
        : 'ring-1 ring-white/10';

  const imgSrc = (() => {
    if (isEmpty || failed) return null;
    if (variant === 'splash-thumb') return championSplashUrl(name!);
    if (variant === 'loading') return championLoadingUrl(name!);
    return championPortraitUrl(name!);
  })();

  const body = (
    <div
      className={`relative overflow-hidden bg-lol-void-deep ${sizeClass[variant]} ${ring} ${
        banned ? 'grayscale brightness-50' : ''
      } ${locked ? 'animate-lock-shine' : ''} ${className}`}
    >
      {imgSrc ? (
        <img
          src={imgSrc}
          alt={name || ''}
          className={`w-full h-full object-cover ${variant === 'loading' ? 'object-top' : ''}`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-[10px] font-mono text-white/30 bg-gradient-to-br from-lol-hextech/40 to-lol-void">
          {isEmpty ? emptyLabel : name?.slice(0, 3)}
        </div>
      )}
      {banned && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/45">
          <div className="w-[130%] h-0.5 bg-red-500 rotate-[-28deg] shadow-[0_0_6px_rgba(255,70,85,0.8)]" />
        </div>
      )}
      {locked && !banned && (
        <div className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-lol-hq-cyan shadow-hq-cyan" />
      )}
      {showName && name && (
        <div className="absolute bottom-0 inset-x-0 bg-black/80 text-[9px] font-semibold text-center truncate px-0.5 py-0.5 text-white">
          {name}
        </div>
      )}
    </div>
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled || banned}
        className={`text-left transition-transform hover:scale-105 disabled:hover:scale-100 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none ${
          highlighted || locked ? 'scale-105' : ''
        }`}
      >
        {body}
      </button>
    );
  }

  return body;
}
