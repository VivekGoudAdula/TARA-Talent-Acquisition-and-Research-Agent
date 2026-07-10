/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#0078D4',
          600: '#106EBE',
          700: '#0F5A9E',
          800: '#0C4A8A',
          900: '#083A70',
        },
        success: { 50: '#F0FDF4', 500: '#107C10', 600: '#0D6B0D' },
        warning: { 50: '#FFF7ED', 500: '#F7630C', 600: '#D14F00' },
        danger:  { 50: '#FFF1F2', 500: '#D13438', 600: '#A4262C' },
        neutral: {
          50:  '#FAF9F8',
          100: '#F3F2F1',
          200: '#E1DFDD',
          300: '#C8C6C4',
          400: '#A19F9D',
          500: '#605E5C',
          600: '#484644',
          700: '#323130',
          800: '#201F1E',
          900: '#11100F',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
        panel: '0 2px 8px rgba(0,0,0,0.10)',
        dropdown: '0 4px 16px rgba(0,0,0,0.14)',
      },
    },
  },
  plugins: [],
};
