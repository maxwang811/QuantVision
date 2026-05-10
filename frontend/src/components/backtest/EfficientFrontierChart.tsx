"use client";

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
      <div className="flex h-40 items-center justify-center rounded-md border border-border/60 text-sm text-muted">
        No frontier to display.
      </div>
    );
  }

  const data = points.map((p) => ({ vol: p.volatility, ret: p.expected_return }));

  const chart = (
    <ScatterChart margin={{ top: 12, right: 12, bottom: 24, left: 24 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
      <XAxis
        type="number"
        dataKey="vol"
        name="Volatility"
        tickFormatter={fmtPct}
        label={{ value: "Annualized volatility", position: "insideBottom", offset: -10, fontSize: 11 }}
      />
      <YAxis
        type="number"
        dataKey="ret"
        name="Expected return"
        tickFormatter={fmtPct}
        label={{ value: "Annualized return", angle: -90, position: "insideLeft", fontSize: 11 }}
      />
      <Tooltip
        formatter={(v: number) => fmtPct(v)}
        labelFormatter={() => ""}
        contentStyle={{ background: "var(--bg)", border: "1px solid var(--border)" }}
      />
      <Scatter name="frontier" data={data} fill="var(--accent)" />
      {minVariance && (
        <ReferenceDot
          x={minVariance.volatility}
          y={minVariance.expected_return}
          r={6}
          fill="var(--positive)"
          stroke="var(--bg)"
          strokeWidth={2}
          label={{ value: "min-var", fontSize: 10, dy: -10 }}
        />
      )}
      {maxSharpe && (
        <ReferenceDot
          x={maxSharpe.volatility}
          y={maxSharpe.expected_return}
          r={6}
          fill="var(--accent)"
          stroke="var(--bg)"
          strokeWidth={2}
          label={{ value: "max-Sharpe", fontSize: 10, dy: -10 }}
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
