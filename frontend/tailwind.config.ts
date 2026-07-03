import type { Config } from "tailwindcss";

// Placeholder token slots — the real "tally" palette (charcoal/ember dark mode,
// linen light mode) and full type scale land in M5's design-system milestone.
// This file is deliberately the *one place* those tokens will live, per spec §3.
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        charcoal: {
          DEFAULT: "#1c1917",
        },
        ember: {
          DEFAULT: "#f59e0b",
        },
        linen: {
          DEFAULT: "#faf6f1",
        },
      },
      fontFamily: {
        // TODO(M5): swap in the real display/body typefaces once chosen.
        display: ["system-ui", "sans-serif"],
        body: ["system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
