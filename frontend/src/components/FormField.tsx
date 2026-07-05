import type { InputHTMLAttributes } from "react";

import { FIELD_CHROME_CLASSNAME } from "./fieldChrome";

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  name: string;
}

export function FormField({ label, name, ...inputProps }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={name} className="text-sm font-medium text-text-primary/80">
        {label}
      </label>
      <input id={name} name={name} {...inputProps} className={FIELD_CHROME_CLASSNAME} />
    </div>
  );
}
