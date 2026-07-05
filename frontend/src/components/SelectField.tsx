import type { SelectHTMLAttributes } from "react";

import { FIELD_CHROME_CLASSNAME } from "./fieldChrome";

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  name: string;
}

export function SelectField({ label, name, children, ...selectProps }: SelectFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={name} className="text-sm font-medium text-text-primary/80">
        {label}
      </label>
      <select id={name} name={name} {...selectProps} className={FIELD_CHROME_CLASSNAME}>
        {children}
      </select>
    </div>
  );
}
