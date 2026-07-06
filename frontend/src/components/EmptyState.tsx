import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface EmptyStateProps {
  icon?: ReactNode;
  message: string;
  ctaLabel?: string;
  ctaTo?: string;
}

export function EmptyState({ icon, message, ctaLabel, ctaTo }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-8 text-center">
      {icon ? (
        <span className="text-3xl" aria-hidden>
          {icon}
        </span>
      ) : null}
      <p className="text-sm text-text-primary/60">{message}</p>
      {ctaLabel && ctaTo ? (
        <Link
          to={ctaTo}
          className="text-sm font-medium text-green-600 underline-offset-2 hover:underline dark:text-green-400"
        >
          {ctaLabel}
        </Link>
      ) : null}
    </div>
  );
}
