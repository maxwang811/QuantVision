import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "./utils";

interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: "section" | "div" | "article" | "form";
  padded?: boolean;
  interactive?: boolean;
}

export function Card({
  as: Tag = "section",
  padded = true,
  interactive = false,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <Tag
      className={cn(
        "rounded-xl border border-border bg-surface shadow-soft",
        padded && "p-5 sm:p-6",
        interactive && "transition-colors hover:border-border-strong",
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
}

export function CardHeader({ title, description, eyebrow, actions, className }: CardHeaderProps) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="space-y-1">
        {eyebrow && (
          <div className="text-[11px] font-semibold uppercase tracking-eyebrow text-muted">
            {eyebrow}
          </div>
        )}
        <h2 className="text-base font-semibold text-fg">{title}</h2>
        {description && <p className="text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
