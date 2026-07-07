/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: { 50: '#f0f0ff', 100: '#e0e0ff', 200: '#c4b5fd', 300: '#a78bfa', 400: '#8b5cf6', 500: '#7c3aed', 600: '#6d28d9', 700: '#5b21b6', 800: '#4c1d95', 900: '#1a1a2e' },
        accent: { 400: '#667eea', 500: '#764ba2' },
      },
    },
  },
  plugins: [],
}
