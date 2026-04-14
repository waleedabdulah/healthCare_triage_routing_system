import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        emergency: '#dc2626',    // red-600
        urgent: '#ea580c',       // orange-600
        nonurgent: '#ca8a04',    // yellow-600
        selfcare: '#16a34a',     // green-600
      },
    },
  },
  plugins: [],
}

export default config
