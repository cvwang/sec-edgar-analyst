/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gcpBg: "#F8F9FA",
        gcpSurface: "#FFFFFF",
        gcpBlue: "#1A73E8",
        gcpBlueHover: "#1557B0",
        gcpRed: "#EA4335",
        gcpYellow: "#FBBC04",
        gcpGreen: "#34A853",
        gcpBorder: "#DADCE0",
        gcpText: "#202124",
        gcpTextSecondary: "#5F6368",
        darkBg: "#F8F9FA",
        darkSurface: "#FFFFFF",
        cardBg: "#FFFFFF",
        accentBlue: "#1A73E8",
        accentBlueHover: "#1557B0",
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['Outfit', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
