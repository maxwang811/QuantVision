import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { cn } from "./utils";

const baseField =
  "w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-fg placeholder:text-muted/60 transition-all duration-200 hover:border-border-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-surface-2";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  adornmentLeft?: ReactNode;
  adornmentRight?: ReactNode;
  invalid?: boolean;
  inputSize?: "sm" | "md" | "lg";
}

const INPUT_SIZE = {
  sm: "h-8 px-3 py-1.5 text-xs",
  md: "h-10 px-3.5 py-2.5 text-sm",
  lg: "h-12 px-4 py-3 text-base",
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { adornmentLeft, adornmentRight, invalid, inputSize = "md", className, ...rest },
  ref,
) {
  const sizeClasses = INPUT_SIZE[inputSize];
  
  if (adornmentLeft || adornmentRight) {
    return (
      <div className="relative">
        {adornmentLeft && (
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted">
            {adornmentLeft}
          </span>
        )}
        <input
          ref={ref}
          className={cn(
            baseField,
            sizeClasses,
            adornmentLeft && "pl-10",
            adornmentRight && "pr-10",
            invalid && "border-negative focus:border-negative focus:ring-negative/20",
            className,
          )}
          {...rest}
        />
        {adornmentRight && (
          <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-muted">
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
        sizeClasses,
        invalid && "border-negative focus:border-negative focus:ring-negative/20",
        className,
      )}
      {...rest}
    />
  );
});

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
  selectSize?: "sm" | "md" | "lg";
}

const SELECT_SIZE = {
  sm: "h-8 px-3 py-1.5 text-xs pr-8",
  md: "h-10 px-3.5 py-2.5 text-sm pr-10",
  lg: "h-12 px-4 py-3 text-base pr-12",
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid, selectSize = "md", className, children, ...rest },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        baseField,
        SELECT_SIZE[selectSize],
        "appearance-none cursor-pointer bg-[length:16px_16px] bg-[right_0.75rem_center] bg-no-repeat",
        invalid && "border-negative focus:border-negative focus:ring-negative/20",
        className,
      )}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none' stroke='%23888' stroke-width='1.5'><path d='M6 8l4 4 4-4' stroke-linecap='round' stroke-linejoin='round'/></svg>\")",
      }}
      {...rest}
    >
      {children}
    </select>
  );
});

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, className, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(
        baseField,
        "min-h-[100px] resize-y py-3",
        invalid && "border-negative focus:border-negative focus:ring-negative/20",
        className,
      )}
      {...rest}
    />
  );
});
