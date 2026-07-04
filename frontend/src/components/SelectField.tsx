import type { SelectHTMLAttributes } from "react";

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  name: string;
}

export function SelectField({ label, name, children, ...selectProps }: SelectFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={name} className="text-sm font-medium text-charcoal/80 dark:text-linen/80">
        {label}
      </label>
      <select
        id={name}
        name={name}
        {...selectProps}
        className="rounded-lg border border-charcoal/15 bg-white/50 px-3 py-2 text-base text-charcoal outline-none transition-colors focus:border-ember focus:ring-2 focus:ring-ember/30 dark:border-linen/15 dark:bg-black/20 dark:text-linen"
      >
        {children}
      </select>
    </div>
  );
}
