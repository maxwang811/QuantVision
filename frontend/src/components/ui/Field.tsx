import type { ReactNode } from "react";
import { cn } from "./utils";

interface FieldProps {
  label: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  error?: ReactNode;
  children: ReactNode;
  className?: string;
  required?: boolean;
}

export function Field({ label, htmlFor, hint, error, children, className, required }: FieldProps) {
  return (
    <label htmlFor={htmlFor} className={cn("block space-y-2", className)}>
      <span className="flex items-center gap-1 text-sm font-medium text-fg">
        {label}
        {required && <span className="text-negative">*</span>}
      </span>
      {children}
      {error ? (
        <span className="block text-xs text-negative">{error}</span>
      ) : hint ? (
        <span className="block text-xs text-muted">{hint}</span>
      ) : null}
    </label>
  );
}
