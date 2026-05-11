import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { cn } from "./utils";

const baseField =
  "w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-fg placeholder:text-muted/70 transition-colors hover:border-border-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:cursor-not-allowed disabled:opacity-60";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  adornmentLeft?: ReactNode;
  adornmentRight?: ReactNode;
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { adornmentLeft, adornmentRight, invalid, className, ...rest },
  ref,
) {
  if (adornmentLeft || adornmentRight) {
    return (
      <div className="relative">
        {adornmentLeft && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">
            {adornmentLeft}
          </span>
        )}
        <input
          ref={ref}
          className={cn(
            baseField,
            adornmentLeft ? "pl-7" : null,
            adornmentRight ? "pr-7" : null,
            invalid ? "border-negative focus:border-negative focus:ring-negative/30" : null,
            className,
          )}
          {...rest}
        />
        {adornmentRight && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted">
            {adornmentRight}
          </span>
        )}
      </div>
    );
  }

  return (
    <input
      ref={ref}
      className={cn(
        baseField,
        invalid && "border-negative focus:border-negative focus:ring-negative/30",
        className,
      )}
      {...rest}
    />
  );
});

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid, className, children, ...rest },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        baseField,
        "appearance-none bg-[length:14px_14px] bg-[right_0.75rem_center] bg-no-repeat pr-9",
        invalid && "border-negative focus:border-negative focus:ring-negative/30",
        className,
      )}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none' stroke='currentColor' stroke-width='1.6'><path d='M6 8l4 4 4-4' stroke-linecap='round' stroke-linejoin='round'/></svg>\")",
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 0.75rem center",
        backgroundSize: "14px 14px",
      }}
      {...rest}
    >
      {children}
    </select>
  );
});
