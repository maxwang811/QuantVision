import type { ReactNode } from "react";
import { cn } from "./utils";

interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  actions?: ReactNode;
  className?: string;
  size?: "default" | "large";
}

export function PageHeader({ 
  title, 
  description, 
  eyebrow, 
  actions, 
  className,
  size = "default"
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 pb-8 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="space-y-2">
        {eyebrow && (
          <div className="text-xs font-medium text-accent">
            {eyebrow}
          </div>
        )}
        <h1 className={cn(
          "font-semibold tracking-tight text-fg text-balance",
          size === "large" 
            ? "text-3xl sm:text-4xl" 
            : "text-2xl sm:text-3xl"
        )}>
          {title}
        </h1>
        {description && (
          <p className="max-w-2xl text-sm text-muted leading-relaxed sm:text-base">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-3">
          {actions}
        </div>
      )}
    </header>
  );
}
