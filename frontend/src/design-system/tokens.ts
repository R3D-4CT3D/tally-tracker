/**
 * Single source of truth for Tally's design tokens (spec §3's design-system
 * milestone). tailwind.config.ts imports this file and spreads it into
 * theme.extend — components should only ever reach for the resulting
 * Tailwind utility classes (bg-surface, text-ember-600, duration-standard,
 * ...), never a raw hex value or inline style.
 *
 * Anchor values from the pre-M5 placeholder are kept exact within their
 * ramps (charcoal.950, linen.50, ember.500) so nothing visually shifts by
 * accident: charcoal.950 === "#1c1917", linen.50 === "#faf6f1",
 * ember.500 === "#f59e0b".
 */

export const color = {
  charcoal: {
    50: "#faf9f8",
    100: "#f2f0ee",
    200: "#e4e0dc",
    300: "#cbc4bd",
    400: "#a89e93",
    500: "#83766a",
    600: "#665a4f",
    700: "#4d423a",
    800: "#362e28",
    900: "#241f1a",
    950: "#1c1917",
  },
  linen: {
    50: "#faf6f1",
    100: "#f3ece3",
    200: "#e8dccc",
    300: "#d8c4a8",
    400: "#c2a67d",
    500: "#a8875a",
    600: "#8a6c44",
    700: "#6d5535",
    800: "#4f3d27",
    900: "#362a1b",
    950: "#241a11",
  },
  ember: {
    50: "#fffbeb",
    100: "#fef3c7",
    200: "#fde68a",
    300: "#fcd34d",
    400: "#fbbf24",
    500: "#f59e0b",
    600: "#d97706",
    700: "#b45309",
    800: "#92400e",
    900: "#78350f",
    950: "#451a03",
  },
  // Warm terracotta-leaning red, on-brand rather than a raw Tailwind red --
  // replaces ErrorBanner.tsx's hardcoded red-500/red-700.
  danger: {
    50: "#fef2f2",
    100: "#fde2e1",
    200: "#fbc9c7",
    300: "#f5a19d",
    400: "#ec7268",
    500: "#dc4c3e",
    600: "#c0342a",
    700: "#9f2a22",
    800: "#82241f",
    900: "#6b211d",
    950: "#390e0c",
  },
  // Small ramp, not much used until M6's payoff-celebration/goal-complete
  // states -- cheap to define alongside the other ramps now.
  success: {
    50: "#f0fdf4",
    100: "#dcfce7",
    200: "#bbf7d0",
    300: "#86efac",
    400: "#4ade80",
    500: "#22c55e",
    600: "#16a34a",
    700: "#15803d",
    800: "#166534",
    900: "#14532d",
    950: "#052e16",
  },
} as const;

/**
 * Semantic aliases layered on the ramps above, resolved per-theme via CSS
 * custom properties (see index.css's :root / .dark blocks) rather than
 * requiring a `dark:` twin at every call site -- e.g. `border-border/10`
 * alone replaces today's `border-charcoal/10 dark:border-linen/10`.
 * Accent/status colors (ember/danger/success) intentionally do NOT flip
 * between themes, so they stay flat ramp references, not CSS vars.
 */
export const semanticColorVar = {
  surface: "--color-surface", // page background
  surfaceCard: "--color-surface-card", // Card component background
  surfaceSubtle: "--color-surface-subtle", // input/field chrome background
  border: "--color-border", // base border color (before opacity modifiers)
  textPrimary: "--color-text-primary", // base text color (before opacity modifiers)
} as const;

export const spacing = {
  // Extends Tailwind's default scale rather than replacing it -- only add
  // values the app actually needs that the default scale lacks.
  18: "4.5rem", // nav header height
} as const;

export const radius = {
  sm: "6px",
  md: "10px",
  lg: "14px",
  xl: "20px",
  full: "9999px",
} as const;

export const typeScale = {
  xs: { fontSize: "0.75rem", lineHeight: "1rem" },
  sm: { fontSize: "0.875rem", lineHeight: "1.25rem" },
  base: { fontSize: "1rem", lineHeight: "1.5rem" },
  lg: { fontSize: "1.125rem", lineHeight: "1.75rem" },
  xl: { fontSize: "1.25rem", lineHeight: "1.75rem" },
  "2xl": { fontSize: "1.5rem", lineHeight: "2rem" },
  "3xl": { fontSize: "1.875rem", lineHeight: "2.25rem" },
  "4xl": { fontSize: "2.25rem", lineHeight: "2.5rem" },
} as const;

export const motion = {
  duration: {
    fast: 150,
    standard: 250,
    emphasis: 400,
  },
  easing: {
    standard: "cubic-bezier(0.4, 0, 0.2, 1)",
    emphasis: "cubic-bezier(0.16, 1, 0.3, 1)",
  },
} as const;

export const fontFamily = {
  display: ["Fraunces Variable", "Georgia", "serif"],
  body: ["Inter", "system-ui", "sans-serif"],
} as const;
