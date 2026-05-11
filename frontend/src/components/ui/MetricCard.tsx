import type { ReactNode } from "react";
import { cn } from "./utils";

export type MetricTone = "neutral" | "positive" | "negative";

interface MetricCardProps {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  tone?: MetricTone;
  className?: string;
}

const VALUE_TONE: Record<MetricTone, string> = {
  neutral: "text-fg",
  positive: "text-positive",
  negative: "text-negative",
};

const SURFACE_TONE: Record<MetricTone, string> = {
  neutral: "bg-surface",
  positive: "bg-positive/[0.06]",
  negative: "bg-negative/[0.06]",
};

export function MetricCard({ label, value, hint, tone = "neutral", className }: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border p-4 shadow-soft transition-colors",
        SURFACE_TONE[tone],
        className,
      )}
    >
      <div className="text-[11px] font-semibold uppercase tracking-eyebrow text-muted">{label}</div>
      <div className={cn("mt-2 font-mono text-xl font-semibold tabular-nums", VALUE_TONE[tone])}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}
