import type { ReactNode } from "react";

interface PropertyCardProps {
  /** The item's own color (Goal.color / Debt.color) -- becomes the header
   * band, matching a real Monopoly property card's colored top strip. */
  color: string;
  icon: ReactNode;
  name: string;
  /** Bold price/balance line under the header band. */
  amount: ReactNode;
  /** "OWNED"-style badge shown once the property/mortgage is settled
   * (Goal.completed_at set / Debt.paid_off_at set). */
  owned?: boolean;
  ownedLabel?: string;
  children?: ReactNode;
  className?: string;
}

// A Monopoly title-deed card: colored header band (the item's own color),
// cream/white body, bold amount, small ownership badge once settled. Used
// for both Goal "property" tiles and Debt "mortgage/railroad" tiles on the
// board (phase 4) -- generic over which entity it's representing.
export function PropertyCard({
  color,
  icon,
  name,
  amount,
  owned = false,
  ownedLabel,
  children,
  className = "",
}: PropertyCardProps) {
  return (
    <div
      className={`overflow-hidden rounded-lg border border-border/10 bg-cream-50 text-navy-950 shadow-sm dark:bg-surface-card dark:text-text-primary ${className}`}
    >
      <div
        className="flex items-center justify-between gap-2 px-3 py-2"
        style={{ backgroundColor: color }}
      >
        <span className="flex items-center gap-1.5 truncate text-sm font-semibold text-white">
          <span aria-hidden>{icon}</span>
          <span className="truncate">{name}</span>
        </span>
        {owned ? (
          <span className="shrink-0 rounded-full bg-white/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-navy-950">
            {ownedLabel}
          </span>
        ) : null}
      </div>
      <div className="flex flex-col gap-2 p-3">
        <p className="font-display text-lg font-bold tabular-nums">{amount}</p>
        {children}
      </div>
    </div>
  );
}
