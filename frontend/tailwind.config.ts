import type { Config } from "tailwindcss";

const config: Config = {
  // v3: content paths are required — Tailwind scans these for class names
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
    "./src/context/**/*.{js,ts,jsx,tsx}",
    "./src/hooks/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    extend: {
      // Custom fonts (optional — remove if not loading Inter/JetBrains Mono)
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },

      // gray-950 does not exist in Tailwind v3 by default.
      // We define it here so bg-gray-950 / text-gray-950 work.
      colors: {
        gray: {
          950: "#0a0f1a",
        },
      },
    },
  },

  plugins: [],
};

export default config;