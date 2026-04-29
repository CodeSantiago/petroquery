import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(40 20% 98%)",
        foreground: "hsl(220 10% 35%)",
        card: {
          DEFAULT: "hsla(0 0% 100% / 0.7)",
          foreground: "hsl(220 10% 35%)",
        },
        primary: {
          DEFAULT: "hsl(270 70% 65%)",
          foreground: "hsl(0 0% 100%)",
          light: "hsl(270 70% 75%)",
          dark: "hsl(270 70% 55%)",
        },
        secondary: {
          DEFAULT: "hsl(160 60% 70%)",
          foreground: "hsl(0 0% 100%)",
          light: "hsl(160 60% 80%)",
          dark: "hsl(160 60% 60%)",
        },
        accent: {
          DEFAULT: "hsl(340 70% 75%)",
          foreground: "hsl(0 0% 100%)",
          light: "hsl(340 70% 85%)",
          dark: "hsl(340 70% 65%)",
        },
        muted: {
          DEFAULT: "hsl(220 10% 95%)",
          foreground: "hsl(220 10% 55%)",
        },
        border: "hsl(220 10% 90%)",
        'petro-blue': '#1A237E',
        'petro-orange': '#FF6F00',
        'petro-gray': '#F5F5F5',
        'petro-lime': '#C0CA33',
        'petro-dark': '#0D47A1',
        'petro-light': '#E8EAF6',
      },
      backgroundImage: {
        "mesh-gradient": `radial-gradient(at 40% 20%, hsla(270,70%,75%,0.3) 0px, transparent 50%),
                          radial-gradient(at 80% 0%, hsla(160,60%,70%,0.3) 0px, transparent 50%),
                          radial-gradient(at 0% 50%, hsla(340,70%,75%,0.3) 0px, transparent 50%),
                          radial-gradient(at 80% 50%, hsla(270,70%,75%,0.2) 0px, transparent 50%),
                          radial-gradient(at 0% 100%, hsla(160,60%,70%,0.3) 0px, transparent 50%)`,
      },
      fontFamily: {
        sans: ["Quicksand", "Outfit", "system-ui", "sans-serif"],
      },
      animation: {
        "mesh-move": "mesh-move 20s ease infinite",
        "confetti": "confetti 1s ease-out forwards",
        "shine": "shine 2s ease-in-out infinite",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        "float": "float 3s ease-in-out infinite",
      },
      keyframes: {
        "mesh-move": {
          "0%, 100%": { backgroundPosition: "0% 0%", backgroundSize: "200% 200%" },
          "50%": { backgroundPosition: "100% 100%", backgroundSize: "150% 150%" },
        },
        "confetti": {
          "0%": { transform: "scale(0) rotate(0deg)", opacity: "1" },
          "50%": { transform: "scale(1.2) rotate(180deg)", opacity: "0.8" },
          "100%": { transform: "scale(0.5) rotate(360deg)", opacity: "0" },
        },
        "shine": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
export default config;