/** @type {import('tailwindcss').Config} */
/**
 * Design system — War Room / Tech-Noir HQ
 * Paleta: void black · electric cyan · neon orange · clean white
 * Superfícies: frosted glass · cantos nítidos · contornos finos · neon glow
 */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        lol: {
          void: '#010a13',
          'void-deep': '#050d18',
          'void-panel': '#0a1628',
          hextech: '#0a323c',
          'hextech-bright': '#1e9c9c',
          // Legacy brand gold (LoL crest / secondary)
          gold: '#c89b3c',
          'gold-soft': '#f0e6d2',
          'gold-dim': '#785a28',
          blue: '#0ac8b9',
          'blue-side': '#0096ff',
          'red-side': '#ff4655',
          mana: '#0a96aa',
          // HQ / War Room language (primary UI accents)
          hq: '#071422',
          'hq-void': '#030810',
          'hq-cyan': '#22d3ee',
          'hq-cyan-dim': '#0891b2',
          'hq-cyan-bright': '#67e8f9',
          'hq-orange': '#f97316',
          'hq-orange-bright': '#fb923c',
          'hq-glass': 'rgba(6, 18, 32, 0.62)',
          'hq-glass-strong': 'rgba(4, 12, 22, 0.82)',
          'hq-line': 'rgba(34, 211, 238, 0.18)',
          'hq-muted': 'rgba(226, 232, 240, 0.45)',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'], // tech UI — not fantasy serif
      },
      letterSpacing: {
        'hud': '0.18em',
        'hud-wide': '0.28em',
      },
      boxShadow: {
        'lol-gold': '0 0 16px rgba(200, 155, 60, 0.35)',
        'lol-blue': '0 0 12px rgba(10, 200, 185, 0.3)',
        'panel': '0 4px 24px rgba(0, 0, 0, 0.45)',
        'hq-cyan': '0 0 20px rgba(34, 211, 238, 0.28), 0 0 4px rgba(34, 211, 238, 0.4)',
        'hq-cyan-sm': '0 0 10px rgba(34, 211, 238, 0.2)',
        'hq-orange': '0 0 18px rgba(249, 115, 22, 0.3), 0 0 4px rgba(249, 115, 22, 0.35)',
        'hq-orange-sm': '0 0 10px rgba(249, 115, 22, 0.22)',
        'hq-glass':
          '0 8px 32px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255,255,255,0.07), 0 0 0 1px rgba(34,211,238,0.06)',
        'hq-inset': 'inset 0 0 40px rgba(34, 211, 238, 0.04)',
        'hq-focus': '0 0 0 1px rgba(34, 211, 238, 0.45), 0 0 16px rgba(34, 211, 238, 0.2)',
      },
      backgroundImage: {
        'lol-panel':
          'linear-gradient(180deg, rgba(10,50,60,0.55) 0%, rgba(1,10,19,0.92) 100%)',
        'lol-header':
          'linear-gradient(90deg, rgba(200,155,60,0.12) 0%, transparent 50%, rgba(10,150,170,0.1) 100%)',
        'hq-panel':
          'linear-gradient(160deg, rgba(10, 36, 56, 0.72) 0%, rgba(5, 14, 26, 0.88) 55%, rgba(2, 8, 16, 0.94) 100%)',
        'hq-header':
          'linear-gradient(90deg, rgba(34, 211, 238, 0.14) 0%, transparent 42%, rgba(249, 115, 22, 0.1) 100%)',
        'hq-grid':
          'linear-gradient(rgba(34,211,238,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.04) 1px, transparent 1px)',
        'hq-ambient':
          'radial-gradient(ellipse 70% 55% at 8% 12%, rgba(34, 211, 238, 0.12), transparent 55%), radial-gradient(ellipse 55% 45% at 92% 88%, rgba(249, 115, 22, 0.09), transparent 50%), radial-gradient(ellipse 50% 35% at 50% 0%, rgba(14, 165, 233, 0.06), transparent 60%)',
        'hq-scan':
          'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)',
      },
      backgroundSize: {
        'hq-grid': '28px 28px',
      },
      backdropBlur: {
        glass: '12px',
        'glass-strong': '20px',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'lock-in': {
          '0%': { opacity: '0', transform: 'scale(1.15)' },
          '40%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'lock-shine': {
          '0%, 100%': { boxShadow: '0 0 8px rgba(34,211,238,0.35)' },
          '50%': { boxShadow: '0 0 20px rgba(34,211,238,0.75)' },
        },
        'ban-stamp': {
          '0%': { opacity: '0', transform: 'scale(1.4) rotate(-12deg)' },
          '60%': { opacity: '1', transform: 'scale(0.95) rotate(0deg)' },
          '100%': { opacity: '1', transform: 'scale(1) rotate(0deg)' },
        },
        'splash-pulse': {
          '0%, 100%': { opacity: '0.35' },
          '50%': { opacity: '0.5' },
        },
        'draft-bar': {
          '0%': { width: '100%' },
          '100%': { width: '0%' },
        },
        'kill-pop': {
          '0%': { transform: 'scale(1)' },
          '40%': { transform: 'scale(1.22)' },
          '100%': { transform: 'scale(1)' },
        },
        'neon-breathe': {
          '0%, 100%': { opacity: '0.55' },
          '50%': { opacity: '1' },
        },
        'hud-line': {
          '0%': { transform: 'scaleX(0)', opacity: '0' },
          '100%': { transform: 'scaleX(1)', opacity: '1' },
        },
        'panel-enter': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.25s ease-out',
        'lock-in': 'lock-in 0.55s cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'lock-shine': 'lock-shine 1.8s ease-in-out infinite',
        'ban-stamp': 'ban-stamp 0.45s cubic-bezier(0.2, 0.9, 0.3, 1) forwards',
        'splash-pulse': 'splash-pulse 6s ease-in-out infinite',
        'draft-bar': 'draft-bar 1.1s linear forwards',
        'kill-pop': 'kill-pop 0.45s cubic-bezier(0.2, 0.9, 0.3, 1)',
        'neon-breathe': 'neon-breathe 2.8s ease-in-out infinite',
        'hud-line': 'hud-line 0.4s ease-out forwards',
        'panel-enter': 'panel-enter 0.38s cubic-bezier(0.2, 0.85, 0.25, 1) both',
      },
    },
  },
  plugins: [],
}
