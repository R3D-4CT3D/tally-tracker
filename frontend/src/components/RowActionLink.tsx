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
      className={`inline-flex min-h-11 items-center px-2 text-sm text-text-primary/70 underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {children}
    </button>
  );
}
