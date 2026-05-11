"use client";

import { chartAxisTick, chartGridStroke, chartTooltipStyle } from "@/lib/chart-theme";
import type { FrontierPointOut } from "@/lib/api";
import {
  CartesianGrid,
  ReferenceDot,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  points: FrontierPointOut[];
  minVariance?: FrontierPointOut | null;
  maxSharpe?: FrontierPointOut | null;
  /** Explicit dimensions (used by tests in jsdom where ResponsiveContainer can't measure). */
  width?: number;
  height?: number;
}

const fmtPct = (v: number) => `${(v * 100).toFixed(2)}%`;

export function EfficientFrontierChart({
  points,
  minVariance,
  maxSharpe,
  width,
  height,
}: Props) {
  if (!points || points.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-lg border border-dashed border-border bg-surface-2/40 text-sm text-muted">
        No frontier to display.
      </div>
    );
  }

  const data = points.map((p) => ({ vol: p.volatility, ret: p.expected_return }));

  const chart = (
    <ScatterChart margin={{ top: 12, right: 12, bottom: 28, left: 28 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
      <XAxis
        type="number"
        dataKey="vol"
        name="Volatility"
        tick={chartAxisTick}
        tickFormatter={fmtPct}
        label={{
          value: "Annualized volatility",
          position: "insideBottom",
          offset: -12,
          fontSize: 11,
          fill: "rgb(var(--muted))",
        }}
      />
      <YAxis
        type="number"
        dataKey="ret"
        name="Expected return"
        tick={chartAxisTick}
        tickFormatter={fmtPct}
        label={{
          value: "Annualized return",
          angle: -90,
          position: "insideLeft",
          fontSize: 11,
          fill: "rgb(var(--muted))",
        }}
      />
      <Tooltip
        formatter={(v: number) => fmtPct(v)}
        labelFormatter={() => ""}
        contentStyle={chartTooltipStyle}
      />
      <Scatter name="frontier" data={data} fill="rgb(var(--accent))" />
      {minVariance && (
        <ReferenceDot
          x={minVariance.volatility}
          y={minVariance.expected_return}
          r={6}
          fill="rgb(var(--positive))"
          stroke="rgb(var(--surface))"
          strokeWidth={2}
          label={{ value: "min-var", fontSize: 10, dy: -10, fill: "rgb(var(--fg))" }}
        />
      )}
      {maxSharpe && (
        <ReferenceDot
          x={maxSharpe.volatility}
          y={maxSharpe.expected_return}
          r={6}
          fill="rgb(var(--accent))"
          stroke="rgb(var(--surface))"
          strokeWidth={2}
          label={{ value: "max-Sharpe", fontSize: 10, dy: -10, fill: "rgb(var(--fg))" }}
        />
      )}
    </ScatterChart>
  );

  if (width && height) {
    return (
      <div style={{ width, height }} data-testid="efficient-frontier-chart">
        <ResponsiveContainer width={width} height={height}>
          {chart}
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="h-72 w-full" data-testid="efficient-frontier-chart">
      <ResponsiveContainer width="100%" height="100%">
        {chart}
      </ResponsiveContainer>
    </div>
  );
}
