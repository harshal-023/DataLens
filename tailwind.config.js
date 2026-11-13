/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Color 1: Deep Navy (Brand & Navigation)
        navy: {
          DEFAULT: '#102C46',
          main: '#102C46',
          dark: '#0A2036',
          light: '#1D4664',
          subtle: '#0D3550',
          deepest: '#073D50',
        },
        // Color 2: Peacock Teal (Signature Accent)
        teal: {
          DEFAULT: '#009F98',
          main: '#009F98',
          dark: '#007D78',
          active: '#008F89',
          light: '#39C3B8',
          deep: '#086E73',
          soft: '#E0F5F3',
          50: '#EDFAF8',
          100: '#D2F3EF',
          500: '#009F98',
          600: '#007D78',
        },
        // Color 3: Ice Blue (Secondary Accent & Surface)
        ice: {
          DEFAULT: '#DDF0F5',
          soft: '#EDF7FA',
          medium: '#BBDCE8',
          text: '#356B83',
          border: '#CBE5EF',
        },
        // Color 4: White and Cool Off-White (Workplace Surfaces)
        canvas: {
          DEFAULT: '#F5F8FA',
          subtle: '#EEF3F6',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          card: '#FFFFFF',
          muted: '#EEF3F6',
          border: '#DCE5EB',
        },
        // Supporting Semantics
        semantic: {
          successBg: '#E4F3EC',
          successText: '#216548',
          warningBg: '#FFF3DF',
          warningText: '#98620D',
          errorBg: '#FCE9E9',
          errorText: '#A63838',
          infoBg: '#E6F2F8',
          infoText: '#285C78',
          neutralBg: '#EEF2F5',
          neutralText: '#52616C',
        },
        // Legacy-friendly mappings
        charcoal: {
          DEFAULT: '#102C46',
          50: '#8A99A6',
          100: '#52616C',
          200: '#35434F',
          300: '#1D2F3F',
          400: '#102C46',
        },
        warmGrey: '#52616C',
        stone: {
          border: '#DCE5EB',
          subtle: '#EEF3F6',
          muted: '#52616C',
        },
        sage: {
          bg: '#E4F3EC',
          text: '#216548',
          border: '#C3E7D5',
        },
        amber: {
          bg: '#FFF3DF',
          text: '#98620D',
          border: '#F9DFAC',
        },
        dangerRed: {
          bg: '#FCE9E9',
          text: '#A63838',
          border: '#F7C9C5',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['"DM Serif Display"', 'Playfair Display', 'Georgia', 'serif'],
      },
      borderRadius: {
        'card': '16px',
        'glass': '20px',
      },
      boxShadow: {
        'subtle': '0 1px 3px rgba(16, 44, 70, 0.05), 0 1px 2px rgba(16, 44, 70, 0.03)',
        'elevated': '0 10px 25px -5px rgba(16, 44, 70, 0.08), 0 8px 10px -6px rgba(16, 44, 70, 0.04)',
        'teal': '0 4px 14px rgba(0, 159, 152, 0.25)',
      }
    },
  },
  plugins: [],
}
