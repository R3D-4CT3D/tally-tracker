import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** "form": rounded-2xl/p-6, the form-container recipe.
   *  "row": rounded-xl/px-4 py-3, the list-item recipe. */
  size?: "form" | "row";
}

const SIZE_CLASSNAME = {
  form: "rounded-2xl p-6",
  row: "rounded-xl px-4 py-3",
} as const;

export function Card({ size = "form", className = "", children, ...props }: CardProps) {
  return (
    <div
      {...props}
      className={`border border-border/10 bg-surface-card ${SIZE_CLASSNAME[size]} ${className}`}
    >
      {children}
    </div>
  );
}
