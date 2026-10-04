/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./frontend/**/*.{html,js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: '#F8FAFC',
        surface: {
          DEFAULT: '#FFFFFF',
          elevated: 'rgba(255, 255, 255, 0.88)',
          glass: 'rgba(255, 255, 255, 0.75)',
          muted: '#F1F5F9',
        },
        energy: {
          50: '#FFFBEB',
          100: '#FEF3C7',
          200: '#FDE68A',
          300: '#FCD34D',
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706',
          700: '#B45309',
        },
        primary: {
          DEFAULT: '#F59E0B', // Yellow energy accent from mockup
          hover: '#D97706',
          active: '#B45309',
          foreground: '#0F172A',
        },
        secondary: {
          DEFAULT: '#0F172A',
          foreground: '#FFFFFF',
        },
        slate: {
          850: '#141E33',
        },
        success: {
          DEFAULT: '#10B981',
          subtle: '#ECFDF5',
        },
        info: {
          DEFAULT: '#3B82F6',
          subtle: '#EFF6FF',
        },
        border: {
          DEFAULT: '#E2E8F0',
          subtle: 'rgba(226, 232, 240, 0.7)',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(15, 23, 42, 0.08), 0 1px 2px 0 rgba(15, 23, 42, 0.04)',
        'glass-hover': '0 12px 40px 0 rgba(15, 23, 42, 0.12), 0 2px 4px 0 rgba(15, 23, 42, 0.06)',
        'subtle': '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)',
        'elevated': '0 10px 25px -5px rgba(0, 0, 0, 0.06), 0 8px 10px -6px rgba(0, 0, 0, 0.04)',
      },
      backdropBlur: {
        'xs': '2px',
        'glass': '16px',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      }
    },
  },
  plugins: [],
}
