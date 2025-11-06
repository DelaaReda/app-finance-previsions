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
          DEFAULT: '#4c6ef5',
          50: '#eef2ff',
          100: '#e6edff',
          200: '#cbd7ff',
        },
        teal: {
          DEFAULT: '#14b8a6'
        },
        surface: {
          DEFAULT: '#0f1724'
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto'],
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
