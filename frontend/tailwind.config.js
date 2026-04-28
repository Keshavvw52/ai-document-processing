/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'bg-deep':      '#020203',
        'bg-base':      '#050506',
        'bg-elevated':  '#0a0a0c',
        accent:         '#5E6AD2',
        'accent-bright':'#6872D9',
        fg:             '#EDEDEF',
        'fg-muted':     '#8A8F98',
      },
      fontFamily: {
        sans: ['"Inter"', '"Geist Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'float-slow':   'float 10s ease-in-out infinite',
        'float-medium': 'floatB 8s ease-in-out 2s infinite',
        'float-fast':   'floatC 6s ease-in-out 4s infinite',
        'shimmer':      'shimmer 3s linear infinite',
        'pulse-glow':   'pulseGlow 4s ease-in-out infinite',
        'fade-up':      'fadeUp 0.6s cubic-bezier(0.16,1,0.3,1) forwards',
        'fade-in':      'fadeInAnim 0.3s ease-out forwards',
        'slide-in':     'slideIn 0.3s cubic-bezier(0.16,1,0.3,1) forwards',
      },
      keyframes: {
        float:    { '0%,100%': { transform: 'translateY(0) rotate(0deg)' },   '50%': { transform: 'translateY(-20px) rotate(1deg)' } },
        floatB:   { '0%,100%': { transform: 'translateY(0) rotate(0deg)' },   '50%': { transform: 'translateY(-14px) rotate(-0.5deg)' } },
        floatC:   { '0%,100%': { transform: 'translateY(0) rotate(0deg)' },   '50%': { transform: 'translateY(-10px) rotate(0.8deg)' } },
        shimmer:  { '0%': { backgroundPosition: '200% center' }, '100%': { backgroundPosition: '-200% center' } },
        pulseGlow:{ '0%,100%': { opacity: '0.5' }, '50%': { opacity: '1' } },
        fadeUp:   { '0%': { opacity: '0', transform: 'translateY(24px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        fadeInAnim:{ '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideIn:  { '0%': { opacity: '0', transform: 'translateY(8px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
      },
      boxShadow: {
        'card':       '0 0 0 1px rgba(255,255,255,0.06),0 2px 20px rgba(0,0,0,0.4),0 0 40px rgba(0,0,0,0.2)',
        'card-hover': '0 0 0 1px rgba(255,255,255,0.10),0 8px 40px rgba(0,0,0,0.5),0 0 80px rgba(94,106,210,0.1)',
        'accent-glow':'0 0 0 1px rgba(94,106,210,0.5),0 4px 12px rgba(94,106,210,0.3),inset 0 1px 0 0 rgba(255,255,255,0.2)',
        'inner-top':  'inset 0 1px 0 0 rgba(255,255,255,0.1)',
        'inner-card': 'inset 0 1px 0 0 rgba(255,255,255,0.08)',
      },
    },
  },
  plugins: [],
}