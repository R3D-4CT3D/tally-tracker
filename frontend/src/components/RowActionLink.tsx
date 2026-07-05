import type { ButtonHTMLAttributes } from "react";

export function RowActionLink({
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      {...props}
      className={`text-sm text-text-primary/70 underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {children}
    </button>
  );
}
