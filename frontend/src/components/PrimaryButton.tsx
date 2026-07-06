import type { ButtonHTMLAttributes } from "react";

export function PrimaryButton({
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`min-h-11 w-auto rounded-lg bg-green-500 px-4 py-2.5 font-medium text-navy-950 transition-colors hover:bg-green-600 disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {children}
    </button>
  );
}
