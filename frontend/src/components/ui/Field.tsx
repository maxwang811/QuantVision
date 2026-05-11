import type { ReactNode } from "react";
import { cn } from "./utils";

interface FieldProps {
  label: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  error?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, hint, error, children, className }: FieldProps) {
  return (
    <label htmlFor={htmlFor} className={cn("block space-y-1.5", className)}>
      <span className="text-[11px] font-semibold uppercase tracking-eyebrow text-muted">
        {label}
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
