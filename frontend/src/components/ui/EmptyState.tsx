import type { ReactNode } from "react";
import { cn } from "./utils";

interface EmptyStateProps {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  compact?: boolean;
}

export function EmptyState({ icon, title, description, action, className, compact }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-surface/40 text-center",
        compact ? "gap-2 px-4 py-6" : "gap-3 px-6 py-10",
        className,
      )}
    >
      {icon && (
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-2 text-muted">
          {icon}
        </div>
      )}
      <div className="space-y-1">
        <div className="text-sm font-semibold text-fg">{title}</div>
        {description && <div className="mx-auto max-w-sm text-xs text-muted">{description}</div>}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
}

interface ErrorBoxProps {
  message: ReactNode;
  className?: string;
}

export function ErrorBox({ message, className }: ErrorBoxProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-xl border border-negative/40 bg-negative/5 p-4 text-sm text-negative",
        className,
      )}
    >
      <svg className="mt-0.5 h-4 w-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
        <path
          fillRule="evenodd"
          d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zM9 5a1 1 0 112 0v4a1 1 0 11-2 0V5zm1 8a1 1 0 100 2 1 1 0 000-2z"
          clipRule="evenodd"
        />
      </svg>
      <span>{message}</span>
    </div>
  );
}
