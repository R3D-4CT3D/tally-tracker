interface ProgressBarProps {
  pct: number;
  className?: string;
}

// Plain percentage bar -- the full "boss HP bar" / quest progress polish is
// M5 (design system)/M6 (gamification) scope; this is the minimal, functional
// version M4 needs for Debts/Goals.
export function ProgressBar({ pct, className = "" }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className={`h-2 w-full rounded-full bg-charcoal/10 dark:bg-linen/10 ${className}`}>
      <div className="h-2 rounded-full bg-ember" style={{ width: `${clamped}%` }} />
    </div>
  );
}
