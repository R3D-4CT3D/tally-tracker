/**
 * Single source of truth for Tally's design tokens (the Monopoly-board
 * redesign milestone). tailwind.config.ts imports this file and spreads it
 * into theme.extend -- components should only ever reach for the resulting
 * Tailwind utility classes (bg-surface, text-green-600, duration-standard,
 * ...), never a raw hex value or inline style.
 *
 * Ramp anchors (hue/lightness held exact, other steps interpolated around
 * them -- see the migration commit for the generation script):
 *   navy.950  === "#1a1f3c" (dark background, replaces charcoal)
 *   cream.50  === "#f5f0e8" (light background, replaces linen)
 *   green.500 === "#1b7a3e" (classic Monopoly green, replaces ember as the
 *                            primary/brand accent)
 *   danger.500 === "#cc2200" (brick red)
 * success is intentionally the *same* ramp as green, not a separate hue --
 * Monopoly green already is this app's positive-money color.
 */

export const color = {
  navy: {
    50: "#f2f3f7",
    100: "#e2e4ee",
    200: "#c3c7df",
    300: "#9aa1cb",
    400: "#6e79b9",
    500: "#4a57a1",
    600: "#39437f",
    700: "#2c3463",
    800: "#22284e",
    900: "#1d2344",
    950: "#1a1f3c",
  },
  cream: {
    50: "#f5f0e8",
    100: "#ece3d5",
    200: "#ddceb6",
    300: "#c7b18e",
    400: "#b19568",
    500: "#92784f",
    600: "#745f3e",
    700: "#5d4c32",
    800: "#463925",
    900: "#31291c",
    950: "#201b13",
  },
  green: {
    50: "#edf8f1",
    100: "#d1f0dc",
    200: "#a0e3b9",
    300: "#64d88f",
    400: "#2cba60",
    500: "#1b7a3e",
    600: "#176333",
    700: "#144d29",
    800: "#123b21",
    900: "#0f2e1b",
    950: "#0b1e12",
  },
  // Brick red -- Monopoly board accent/danger, replaces the earlier
  // terracotta-leaning red.
  danger: {
    50: "#fdefec",
    100: "#fcd7cf",
    200: "#faad9e",
    300: "#f87b62",
    400: "#fa3f19",
    500: "#cc2200",
    600: "#a21c02",
    700: "#7f1a05",
    800: "#5e1608",
    900: "#451208",
    950: "#2d0d06",
  },
  // Deliberately identical to `green` -- see file header. Kept as its own
  // export so `text-success-600`-style call sites (MoneyDisplay's
  // positive-amount color, etc.) don't need touching.
  success: {
    50: "#edf8f1",
    100: "#d1f0dc",
    200: "#a0e3b9",
    300: "#64d88f",
    400: "#2cba60",
    500: "#1b7a3e",
    600: "#176333",
    700: "#144d29",
    800: "#123b21",
    900: "#0f2e1b",
    950: "#0b1e12",
  },
} as const;

/**
 * Semantic aliases layered on the ramps above, resolved per-theme via CSS
 * custom properties (see index.css's :root / .dark blocks) rather than
 * requiring a `dark:` twin at every call site -- e.g. `border-border/10`
 * alone replaces `border-navy/10 dark:border-cream/10`.
 * Accent/status colors (green/danger/success) intentionally do NOT flip
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
  // Bold slab-serif for board-game-confident headings/hero numbers.
  display: ["Roboto Slab", "Georgia", "serif"],
  body: ["Inter", "system-ui", "sans-serif"],
} as const;
