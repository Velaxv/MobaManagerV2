import type { ComponentType, ReactNode, SVGProps } from 'react';

type IconType = ComponentType<SVGProps<SVGSVGElement> & { className?: string; size?: number | string }>;

interface HubPageHeaderProps {
  icon: IconType;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

/** Cabeçalho padrão das páginas de gestão (FM-like). */
export function HubPageHeader({ icon: Icon, title, subtitle, actions }: HubPageHeaderProps) {
  return (
    <div className="panel-lol p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative overflow-hidden">
      <div className="absolute inset-0 bg-lol-header pointer-events-none" />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-lol-gold/50 to-transparent" />
      <div className="relative flex items-start gap-3 min-w-0">
        <div className="w-10 h-10 rounded-sm border border-lol-gold/30 bg-lol-gold/10 flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-lol-gold" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.22em] text-lol-gold/70 font-semibold mb-0.5">
            Gestão
          </p>
          <h2 className="font-display text-xl sm:text-2xl font-bold text-lol-gold-soft tracking-wide truncate">
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
