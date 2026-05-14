import type { ReactNode } from "react";
import { cn } from "./utils";

type Tone = "neutral" | "success" | "danger" | "info" | "warn";
type Variant = "soft" | "outline" | "dot";
type Size = "sm" | "md";

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  variant?: Variant;
  size?: Size;
  className?: string;
}

const SOFT: Record<Tone, string> = {
  neutral: "bg-surface-2 text-muted border-border",
  success: "bg-positive-soft text-positive border-positive/20",
  danger: "bg-negative-soft text-negative border-negative/20",
  info: "bg-accent-soft text-accent border-accent/20",
  warn: "bg-warn-soft text-warn border-warn/20",
};

const DOT: Record<Tone, string> = {
  neutral: "bg-muted",
  success: "bg-positive",
  danger: "bg-negative",
  info: "bg-accent",
  warn: "bg-warn",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "px-2 py-0.5 text-2xs",
  md: "px-2.5 py-1 text-xs",
};

export function Badge({ 
  children, 
  tone = "neutral", 
  variant = "soft", 
  size = "md",
  className 
}: BadgeProps) {
  if (variant === "dot") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border bg-surface font-medium text-fg",
          SIZE_CLASSES[size],
          className,
        )}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full animate-pulse-soft", DOT[tone])} aria-hidden />
        {children}
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border font-medium transition-colors",
        SIZE_CLASSES[size],
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
