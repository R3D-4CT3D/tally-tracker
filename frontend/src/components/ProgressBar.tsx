interface ProgressBarProps {
  pct: number;
  className?: string;
  /** Tick marks at these percentages along the track, e.g. [25, 50, 75]. */
  milestones?: number[];
  /** "green": quest/savings progress. "boss": debt HP bar (reads as debt
   * remaining -- drains as the debt is paid down, matching "boss HP"
   * literally: damage dealt = payments = HP loss). */
  variant?: "green" | "boss";
  /** Skips the width transition when the caller already knows the user
   * prefers reduced motion (see useReducedMotion) -- snaps instantly
   * instead of animating. */
  reduceMotion?: boolean;
}

const FILL_CLASSNAME = {
  green: "bg-green-500",
  boss: "bg-danger-500",
} as const;

export function ProgressBar({
  pct,
  className = "",
  milestones = [],
  variant = "green",
  reduceMotion = false,
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div
      className={`relative h-2 w-full rounded-full bg-border/10 ${className}`}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={`h-2 rounded-full ${FILL_CLASSNAME[variant]} ${
          reduceMotion ? "" : "transition-[width] duration-standard"
        }`}
        style={{ width: `${clamped}%` }}
      />
      {milestones.map((milestone) => (
        <div
          key={milestone}
          className="absolute top-0 h-2 w-px bg-surface-card/60"
          style={{ left: `${milestone}%` }}
          aria-hidden
        />
      ))}
    </div>
  );
}
