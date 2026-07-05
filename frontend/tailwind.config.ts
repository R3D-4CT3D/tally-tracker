import type { Config } from "tailwindcss";

import { color, fontFamily, radius, spacing } from "./src/design-system/tokens";

function withOpacity(cssVar: string) {
  return `rgb(var(${cssVar}) / <alpha-value>)`;
}

// Each ramp keeps its pre-M5 anchor shade as `DEFAULT` too (charcoal-950,
// linen-50, ember-500) so every not-yet-migrated `bg-ember`/`text-charcoal`/
// `border-linen` call site across the app keeps resolving exactly as
// before, while new code can reach for the full `-50`..`-950` scale.
function withDefault<T extends Record<string, string>>(
  ramp: T,
  defaultKey: keyof T,
): T & { DEFAULT: string } {
  return { ...ramp, DEFAULT: ramp[defaultKey] };
}

export default {
  // "class" (not "media"): M5 adds a manual toggle (ThemeProvider) that
  // defaults to OS preference but lets a user pin their choice regardless
  // of it. See src/design-system/ThemeProvider.tsx.
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        charcoal: withDefault(color.charcoal, 950),
        linen: withDefault(color.linen, 50),
        ember: withDefault(color.ember, 500),
        danger: withDefault(color.danger, 500),
        success: withDefault(color.success, 500),
        // Semantic aliases, backed by CSS custom properties in index.css so
        // one class (e.g. `bg-surface`, `border-border/10`) works in both
        // themes without a `dark:` twin at every call site.
        surface: withOpacity("--color-surface"),
        "surface-card": withOpacity("--color-surface-card"),
        "surface-subtle": withOpacity("--color-surface-subtle"),
        border: withOpacity("--color-border"),
        "text-primary": withOpacity("--color-text-primary"),
      },
      spacing,
      borderRadius: radius,
      fontFamily: {
        display: fontFamily.display,
        body: fontFamily.body,
      },
      transitionDuration: {
        fast: "150ms",
        standard: "250ms",
        emphasis: "400ms",
      },
    },
  },
  plugins: [],
} satisfies Config;
