import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "./utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
}

const VARIANT: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-fg shadow-soft hover:bg-accent/90 active:bg-accent/80 disabled:hover:bg-accent",
  secondary:
    "border border-border bg-surface text-fg hover:border-border-strong hover:bg-surface-2",
  ghost: "text-muted hover:text-fg hover:bg-surface-2",
  danger:
    "border border-negative/40 bg-negative/10 text-negative hover:bg-negative/15 hover:border-negative/60",
};

const SIZE: Record<Size, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-9 px-4 text-sm",
  lg: "h-10 px-5 text-sm",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", leadingIcon, trailingIcon, className, children, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={cn(
        "inline-flex select-none items-center justify-center gap-1.5 rounded-md font-medium transition-colors focus-ring disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT[variant],
        SIZE[size],
        className,
      )}
      {...rest}
    >
      {leadingIcon && <span className="inline-flex h-4 w-4 items-center justify-center">{leadingIcon}</span>}
      {children}
      {trailingIcon && <span className="inline-flex h-4 w-4 items-center justify-center">{trailingIcon}</span>}
    </button>
  );
});
