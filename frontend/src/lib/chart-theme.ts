import type { CSSProperties } from "react";

export const chartTooltipStyle: CSSProperties = {
  background: "rgb(var(--surface-elevated))",
  border: "1px solid rgb(var(--border))",
  borderRadius: 10,
  boxShadow: "0 10px 25px rgb(var(--shadow-rgb) / 0.08)",
  fontSize: 12,
  color: "rgb(var(--fg))",
  padding: "8px 10px",
};

export const chartGridStroke = "rgb(var(--border))";
export const chartAxisTick = { fill: "rgb(var(--muted))", fontSize: 11 } as const;

/** Recharts axis labels read CSS variables verbatim — kept for legacy callers. */
export const cssVarBorder = "rgb(var(--border))";
export const cssVarMuted = "rgb(var(--muted))";
