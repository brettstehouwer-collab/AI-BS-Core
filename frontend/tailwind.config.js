/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    'src/**/*.{js,ts,jsx,tsx}',
    'layouts/**/*.{js,ts,jsx,tsx}',
    'components/**/*.{js,ts,jsx,tsx}',
    '!**/node_modules/**',
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#090A0F',
          secondary: '#0D0F17',
        },
        surface: {
          DEFAULT: '#11141E',
          elevated: '#181C2A',
          subtle: '#141824',
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.07)',
          active: 'rgba(255, 255, 255, 0.15)',
        },
        accent: {
          primary: '#3B82F6',   // Controlled blue
          success: '#10B981',   // Status online / telemetry
          warning: '#F59E0B',   // Advisory / warnings
          danger: '#EF4444',    // Operational errors
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
