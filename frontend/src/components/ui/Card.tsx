import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "./utils";

type CardVariant = "default" | "elevated" | "ghost" | "accent";

interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: "section" | "div" | "article" | "form";
  variant?: CardVariant;
  padded?: boolean;
  interactive?: boolean;
}

const VARIANT_STYLES: Record<CardVariant, string> = {
  default: "border border-border bg-surface",
  elevated: "border border-border bg-surface shadow-card",
  ghost: "bg-transparent",
  accent: "border border-accent/20 bg-accent-soft",
};

export function Card({
  as: Tag = "section",
  variant = "default",
  padded = true,
  interactive = false,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <Tag
      className={cn(
        "rounded-2xl transition-all duration-200",
        VARIANT_STYLES[variant],
        padded && "p-5 sm:p-6",
        interactive && "cursor-pointer hover:border-border-strong hover:shadow-card",
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
}

interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  actions?: ReactNode;
  className?: string;
  size?: "default" | "large";
}

export function CardHeader({ 
  title, 
  description, 
  eyebrow, 
  actions, 
  className,
  size = "default"
}: CardHeaderProps) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-4", className)}>
      <div className="space-y-1.5">
        {eyebrow && (
          <div className="text-xs font-medium uppercase tracking-eyebrow text-muted">
            {eyebrow}
          </div>
        )}
        <h2 className={cn(
          "font-semibold text-fg",
          size === "large" ? "text-lg" : "text-base"
        )}>
          {title}
        </h2>
        {description && (
          <p className="text-sm text-muted leading-relaxed max-w-xl">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  );
}

interface CardSectionProps {
  children: ReactNode;
  className?: string;
  divided?: boolean;
}

export function CardSection({ children, className, divided = false }: CardSectionProps) {
  return (
    <div className={cn(
      divided && "border-t border-border pt-5 mt-5",
      className
    )}>
      {children}
    </div>
  );
}
