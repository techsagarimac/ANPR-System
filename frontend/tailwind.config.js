/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        ink: {
          950: "#070b14",
          900: "#0b1220",
          800: "#121a2b",
          700: "#18233a",
          600: "#243047",
        },
        line: "#24324d",
        accent: {
          DEFAULT: "#22d3ee",
          dim: "#0891b2",
        },
      },
      boxShadow: {
        panel: "0 18px 40px rgba(0, 0, 0, 0.28)",
      },
    },
  },
  plugins: [],
};
