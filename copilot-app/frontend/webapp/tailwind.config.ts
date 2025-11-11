import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    // Path to Tremor module
    './node_modules/@tremor/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: '#3b82f6',
          50: '#eef2ff',
          100: '#e6edff',
          200: '#cbd7ff',
        },
        teal: {
          DEFAULT: '#14b8a6'
        },
        primary: 'var(--accent)',
        success: 'var(--accent-2)',
        warning: 'var(--accent-3)',
        danger: 'var(--accent-4)',
        bg: 'var(--bg)',
        text: 'var(--text)',
        'text-secondary': 'var(--text-secondary)',
        muted: 'var(--muted)',
        border: 'var(--border-color)',
        surface: {
          DEFAULT: 'var(--surface)',
          elevated: 'var(--surface-elevated)'
        },
        glass: 'var(--glass-bg)',
        'glass-border': 'var(--glass-border)',
        'glass-shadow': 'var(--glass-shadow)',
        'metric-bg': 'var(--metric-bg)',
        'metric-border': 'var(--metric-border)',
        bullish: 'var(--bullish-color)',
        bearish: 'var(--bearish-color)',
        neutral: 'var(--neutral-color)',
        // Professional financial color palette (from OKComputer)
        'primary-50': 'var(--primary-50)',
        'primary-100': 'var(--primary-100)',
        'primary-200': 'var(--primary-200)',
        'primary-300': 'var(--primary-300)',
        'primary-400': 'var(--primary-400)',
        'primary-500': 'var(--primary-500)',
        'primary-600': 'var(--primary-600)',
        'primary-700': 'var(--primary-700)',
        'primary-800': 'var(--primary-800)',
        'primary-900': 'var(--primary-900)',
        'success-50': 'var(--success-50)',
        'success-100': 'var(--success-100)',
        'success-200': 'var(--success-200)',
        'success-300': 'var(--success-300)',
        'success-400': 'var(--success-400)',
        'success-500': 'var(--success-500)',
        'success-600': 'var(--success-600)',
        'success-700': 'var(--success-700)',
        'success-800': 'var(--success-800)',
        'success-900': 'var(--success-900)',
        'warning-50': 'var(--warning-50)',
        'warning-100': 'var(--warning-100)',
        'warning-200': 'var(--warning-200)',
        'warning-300': 'var(--warning-300)',
        'warning-400': 'var(--warning-400)',
        'warning-500': 'var(--warning-500)',
        'warning-600': 'var(--warning-600)',
        'warning-700': 'var(--warning-700)',
        'warning-800': 'var(--warning-800)',
        'warning-900': 'var(--warning-900)',
        'danger-50': 'var(--danger-50)',
        'danger-100': 'var(--danger-100)',
        'danger-200': 'var(--danger-200)',
        'danger-300': 'var(--danger-300)',
        'danger-400': 'var(--danger-400)',
        'danger-500': 'var(--danger-500)',
        'danger-600': 'var(--danger-600)',
        'danger-700': 'var(--danger-700)',
        'danger-800': 'var(--danger-800)',
        'danger-900': 'var(--danger-900)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      borderRadius: {
        'xl': 'var(--radius)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
      boxShadow: {
        'glass': '0 8px 32px var(--glass-shadow)',
        'card': '0 4px 16px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 8px 24px rgba(0, 0, 0, 0.15)',
        'metric': '0 4px 12px rgba(0, 0, 0, 0.1)',
        'metric-hover': '0 8px 24px rgba(0, 0, 0, 0.2)',
      },
      container: {
        center: true,
        padding: '1rem',
      }
    },
  },
  plugins: [],
}

export default config
