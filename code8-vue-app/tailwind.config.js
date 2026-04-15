/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        code8: {
          gold: '#e1c173',
          green: '#00A651',
          red: '#FF4B4B',
          amber: '#FFC107',
          dark: '#222222',
        }
      }
    },
  },
  plugins: [],
}