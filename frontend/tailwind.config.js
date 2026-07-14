/** @type {import('tailwindcss').Config} */
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
          'void-deep': '#0a1428',
          hextech: '#0a323c',
          'hextech-bright': '#1e9c9c',
          gold: '#c89b3c',
          'gold-soft': '#f0e6d2',
          'gold-dim': '#785a28',
          blue: '#0ac8b9',
          'blue-side': '#0096ff',
          'red-side': '#ff4655',
          mana: '#0a96aa',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Cinzel', 'Georgia', 'serif'],
      },
      boxShadow: {
        'lol-gold': '0 0 16px rgba(200, 155, 60, 0.35)',
        'lol-blue': '0 0 12px rgba(10, 200, 185, 0.3)',
        'panel': '0 4px 24px rgba(0, 0, 0, 0.45)',
      },
      backgroundImage: {
        'lol-panel': 'linear-gradient(180deg, rgba(10,50,60,0.55) 0%, rgba(1,10,19,0.92) 100%)',
        'lol-header': 'linear-gradient(90deg, rgba(200,155,60,0.12) 0%, transparent 50%, rgba(10,150,170,0.1) 100%)',
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
          '0%, 100%': { boxShadow: '0 0 8px rgba(200,155,60,0.35)' },
          '50%': { boxShadow: '0 0 18px rgba(200,155,60,0.75)' },
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
      },
      animation: {
        'fade-in': 'fade-in 0.25s ease-out',
        'lock-in': 'lock-in 0.55s cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'lock-shine': 'lock-shine 1.8s ease-in-out infinite',
        'ban-stamp': 'ban-stamp 0.45s cubic-bezier(0.2, 0.9, 0.3, 1) forwards',
        'splash-pulse': 'splash-pulse 6s ease-in-out infinite',
        'draft-bar': 'draft-bar 1.1s linear forwards',
        'kill-pop': 'kill-pop 0.45s cubic-bezier(0.2, 0.9, 0.3, 1)',
      },
    },
  },
  plugins: [],
}
