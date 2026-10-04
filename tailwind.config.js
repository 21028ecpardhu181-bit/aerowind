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
          glass: 'rgba(255, 255, 255, 0.78)',
          muted: '#F1F5F9',
        },
        energy: {
          DEFAULT: '#FFD21F',
          50: '#FFFDEB',
          100: '#FFF9C2',
          200: '#FFF38A',
          300: '#FFEC52',
          400: '#FFE229',
          500: '#FFD21F',
          600: '#E6BA0A',
          700: '#B89200',
        },
        primary: {
          DEFAULT: '#FFD21F', // Exact #FFD21F energy yellow
          hover: '#F2C50F',
          active: '#DCAE00',
          foreground: '#0F172A',
        },
        charcoal: {
          DEFAULT: '#0F172A',
          muted: '#334155',
          subtle: '#64748B',
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
        'glass': '0 20px 40px -15px rgba(15, 23, 42, 0.07), 0 1px 3px 0 rgba(15, 23, 42, 0.04), inset 0 1px 1px 0 rgba(255, 255, 255, 0.95), inset 0 -1px 1px 0 rgba(15, 23, 42, 0.03)',
        'glass-elevated': '0 25px 50px -12px rgba(15, 23, 42, 0.10), 0 4px 12px 0 rgba(15, 23, 42, 0.03), inset 0 1px 1.5px 0 rgba(255, 255, 255, 1.0), inset 0 -1px 1px 0 rgba(15, 23, 42, 0.02)',
        'glass-subtle': '0 8px 24px -6px rgba(15, 23, 42, 0.05), inset 0 1px 1px 0 rgba(255, 255, 255, 0.85)',
        'glass-hover': '0 25px 50px -10px rgba(15, 23, 42, 0.12), 0 2px 6px 0 rgba(15, 23, 42, 0.06), inset 0 1px 1.5px 0 rgba(255, 255, 255, 1.0)',
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
