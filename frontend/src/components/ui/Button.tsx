import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "./utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  loading?: boolean;
  fullWidth?: boolean;
}

const VARIANT: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-fg shadow-soft hover:bg-accent-hover active:scale-[0.98] disabled:hover:bg-accent",
  secondary:
    "border border-border bg-surface text-fg hover:border-border-strong hover:bg-surface-2 active:scale-[0.98]",
  outline:
    "border border-accent/30 bg-transparent text-accent hover:bg-accent-soft hover:border-accent/50 active:scale-[0.98]",
  ghost: 
    "text-muted hover:text-fg hover:bg-surface-2 active:scale-[0.98]",
  danger:
    "border border-negative/30 bg-negative-soft text-negative hover:bg-negative/15 hover:border-negative/50 active:scale-[0.98]",
};

const SIZE: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-9 px-4 text-sm gap-2",
  lg: "h-11 px-6 text-sm gap-2",
};

function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn("animate-spin", className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { 
    variant = "primary", 
    size = "md", 
    leadingIcon, 
    trailingIcon, 
    loading = false,
    fullWidth = false,
    className, 
    children, 
    type,
    disabled,
    ...rest 
  },
  ref,
) {
  const isDisabled = disabled || loading;
  
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      disabled={isDisabled}
      className={cn(
        "inline-flex select-none items-center justify-center rounded-lg font-medium transition-all duration-200 focus-ring disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT[variant],
        SIZE[size],
        fullWidth && "w-full",
        className,
      )}
      {...rest}
    >
      {loading ? (
        <LoadingSpinner className="h-4 w-4" />
      ) : leadingIcon ? (
        <span className="inline-flex h-4 w-4 items-center justify-center shrink-0">
          {leadingIcon}
        </span>
      ) : null}
      {children}
      {!loading && trailingIcon && (
        <span className="inline-flex h-4 w-4 items-center justify-center shrink-0">
          {trailingIcon}
        </span>
      )}
    </button>
  );
});
