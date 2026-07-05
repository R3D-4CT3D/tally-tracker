import { formatCentsDisplay } from "../lib/money";

interface MoneyDisplayProps {
  cents: number;
  variant?: "hero" | "inline";
  className?: string;
}

const VARIANT_CLASSNAME = {
  hero: "font-display text-3xl font-semibold",
  inline: "font-medium",
} as const;

// The one place `tabular-nums` gets applied -- money.ts stays pure
// string/int arithmetic, this is purely presentational.
export function MoneyDisplay({ cents, variant = "inline", className = "" }: MoneyDisplayProps) {
  return (
    <span className={`tabular-nums ${VARIANT_CLASSNAME[variant]} ${className}`}>
      {formatCentsDisplay(cents)}
    </span>
  );
}
