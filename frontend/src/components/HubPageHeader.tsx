import type { ComponentType, ReactNode, SVGProps } from 'react';

type IconType = ComponentType<SVGProps<SVGSVGElement> & { className?: string; size?: number | string }>;

interface HubPageHeaderProps {
  icon: IconType;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** Small technical eyebrow label (default: War Room module) */
  eyebrow?: string;
}

/** Cabeçalho padrão das páginas — linguagem War Room / tech-noir. */
export function HubPageHeader({
  icon: Icon,
  title,
  subtitle,
  actions,
  eyebrow = 'Operations',
}: HubPageHeaderProps) {
  return (
    <div className="hq-page-header hq-frame panel-enter relative overflow-hidden">
      <div className="absolute inset-0 bg-hq-header pointer-events-none opacity-80" />
      <div className="hq-scan-bar" aria-hidden />
      <div className="relative flex items-start gap-3 min-w-0">
        <div className="hq-page-header-icon">
          <Icon className="w-5 h-5 text-lol-hq-cyan" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-hud text-lol-hq-cyan/70 font-semibold mb-0.5 font-mono">
            {eyebrow}
          </p>
          <h2 className="font-display text-xl sm:text-2xl font-bold text-white tracking-wide truncate">
            {title}
          </h2>
          {subtitle && (
            <p className="text-xs text-white/45 mt-1 leading-relaxed max-w-xl">{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="relative flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}
