import type { ReactNode } from "react";
import { cn } from "./utils";

type Tone = "neutral" | "success" | "danger" | "info" | "warn";
type Variant = "soft" | "outline" | "dot";

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  variant?: Variant;
  className?: string;
}

const SOFT: Record<Tone, string> = {
  neutral: "bg-surface-2 text-muted border-border",
  success: "bg-positive/10 text-positive border-positive/30",
  danger: "bg-negative/10 text-negative border-negative/30",
  info: "bg-accent/10 text-accent border-accent/30",
  warn: "bg-warn/10 text-warn border-warn/40",
};

const DOT: Record<Tone, string> = {
  neutral: "bg-muted",
  success: "bg-positive",
  danger: "bg-negative",
  info: "bg-accent",
  warn: "bg-warn",
};

export function Badge({ children, tone = "neutral", variant = "soft", className }: BadgeProps) {
  if (variant === "dot") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2 py-0.5 text-xs font-medium text-fg",
          className,
        )}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", DOT[tone])} aria-hidden />
        {children}
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        variant === "outline" ? "border-border bg-transparent text-fg" : SOFT[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Maps experiment/sweep status strings to a Badge tone. */
export function statusTone(status: string): Tone {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "danger";
    case "partial":
      return "info";
    case "running":
    case "queued":
      return "warn";
    default:
      return "neutral";
  }
}
