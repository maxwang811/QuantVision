import type { ReactNode } from "react";
import { cn } from "./utils";

export type MetricTone = "neutral" | "positive" | "negative";
export type MetricSize = "sm" | "md" | "lg";

interface MetricCardProps {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  tone?: MetricTone;
  size?: MetricSize;
  icon?: ReactNode;
  className?: string;
}

const VALUE_TONE: Record<MetricTone, string> = {
  neutral: "text-fg",
  positive: "text-positive",
  negative: "text-negative",
};

const SURFACE_TONE: Record<MetricTone, string> = {
  neutral: "bg-surface border-border",
  positive: "bg-positive-soft border-positive/20",
  negative: "bg-negative-soft border-negative/20",
};

const SIZE_STYLES: Record<MetricSize, { container: string; label: string; value: string }> = {
  sm: {
    container: "p-3",
    label: "text-2xs",
    value: "text-base mt-1",
  },
  md: {
    container: "p-4",
    label: "text-xs",
    value: "text-xl mt-2",
  },
  lg: {
    container: "p-5",
    label: "text-xs",
    value: "text-2xl mt-2",
  },
};

export function MetricCard({ 
  label, 
  value, 
  hint, 
  tone = "neutral", 
  size = "md",
  icon,
  className 
}: MetricCardProps) {
  const sizeStyles = SIZE_STYLES[size];
  
  return (
    <div
      className={cn(
        "rounded-xl border transition-all duration-200 hover:shadow-soft",
        SURFACE_TONE[tone],
        sizeStyles.container,
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className={cn(
          "font-medium uppercase tracking-eyebrow text-muted",
          sizeStyles.label
        )}>
          {label}
        </div>
        {icon && (
          <span className="text-muted">
            {icon}
          </span>
        )}
      </div>
      <div className={cn(
        "font-mono font-semibold tabular-nums",
        sizeStyles.value,
        VALUE_TONE[tone]
      )}>
        {value}
      </div>
      {hint && (
        <div className="mt-1.5 text-xs text-muted">
          {hint}
        </div>
      )}
    </div>
  );
}

interface MetricRowProps {
  label: ReactNode;
  value: ReactNode;
  tone?: MetricTone;
  className?: string;
}

export function MetricRow({ label, value, tone = "neutral", className }: MetricRowProps) {
  return (
    <div className={cn("flex items-center justify-between py-2", className)}>
      <span className="text-sm text-muted">{label}</span>
      <span className={cn("font-mono text-sm font-medium tabular-nums", VALUE_TONE[tone])}>
        {value}
      </span>
    </div>
  );
}
