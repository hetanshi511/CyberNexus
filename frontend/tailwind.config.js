/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9', // Example brand color
          600: '#0284c7',
          900: '#0c4a6e',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'], // I'll add Inter later or use system fonts for now
      }
    },
  },
  plugins: [],
}
