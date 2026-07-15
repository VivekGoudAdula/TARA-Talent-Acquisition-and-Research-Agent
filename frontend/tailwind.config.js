/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E3A8A',
          900: '#1E3A8A',
        },
        success: {
          50: '#ECFDF5',
          400: '#34D399',
          500: '#10B981',
          600: '#059669',
        },
        warning: {
          50: '#FFFBEB',
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706',
        },
        danger: {
          50: '#FEF2F2',
          400: '#F87171',
          500: '#EF4444',
          600: '#DC2626',
        },
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
        surface: {
          app: 'var(--color-app-bg)',
          sidebar: 'var(--color-sidebar)',
          DEFAULT: 'var(--color-surface)',
          elevated: 'var(--color-surface-elevated)',
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
        card: 'var(--shadow-card)',
        panel: 'var(--shadow-panel)',
        dropdown: 'var(--shadow-dropdown)',
      },
    },
  },
  plugins: [],
};
