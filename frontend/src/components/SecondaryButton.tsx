import type { ButtonHTMLAttributes } from "react";

export function SecondaryButton({
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      {...props}
      className={`min-h-11 rounded-lg border border-border/20 px-4 py-2.5 text-sm font-medium transition-colors hover:bg-border/5 disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {children}
    </button>
  );
}
