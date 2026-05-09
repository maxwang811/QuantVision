"use client";

import type { ForecastPathsOut } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  paths: ForecastPathsOut;
}

type ChartRow = { date: string } & Record<string, number | string>;

export function ForecastPathChart({ paths }: Props) {
  const { data, highlightedKeys } = useMemo(() => {
    const rows: ChartRow[] = paths.step_dates.map((date, stepIndex) => {
      const row: ChartRow = { date };
      for (const path of paths.paths) {
        row[`path_${path.index}`] = path.values[stepIndex];
      }
      return row;
    });
    const highlighted = new Set(
      paths.paths.filter((path) => path.rank_label).map((path) => `path_${path.index}`),
    );
    return { data: rows, highlightedKeys: highlighted };
  }, [paths]);

  return (
    <div className="rounded-lg border border-border bg-bg p-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-fg">Simulated paths</h3>
        <div className="flex gap-3 text-xs text-muted">
          <LegendDot className="bg-negative" label="Worst" />
          <LegendDot className="bg-accent" label="Median" />
          <LegendDot className="bg-positive" label="Best" />
        </div>
      </div>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="rgb(var(--border))" strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fill: "rgb(var(--muted))", fontSize: 11 }}
              tickFormatter={(d) => formatDate(String(d))}
              minTickGap={40}
            />
            <YAxis
              tick={{ fill: "rgb(var(--muted))", fontSize: 11 }}
              tickFormatter={(v) => formatCurrency(Number(v))}
              width={80}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                background: "rgb(var(--bg))",
                border: "1px solid rgb(var(--border))",
                borderRadius: 6,
                fontSize: 12,
              }}
              labelFormatter={(d) => formatDate(String(d))}
              formatter={(v: number | string, name: string) => [
                formatCurrency(Number(v)),
                displayName(paths, name),
              ]}
            />
            {paths.paths.map((path) => {
              const key = `path_${path.index}`;
              const stroke = strokeFor(path.rank_label);
              const highlighted = highlightedKeys.has(key);
              return (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={key}
                  stroke={stroke}
                  strokeOpacity={highlighted ? 1 : 0.18}
                  strokeWidth={highlighted ? 2.25 : 1}
                  dot={false}
                  isAnimationActive={false}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function strokeFor(label: string | null): string {
  if (label === "worst") return "rgb(var(--negative))";
  if (label === "median") return "rgb(var(--accent))";
  if (label === "best") return "rgb(var(--positive))";
  return "rgb(var(--muted))";
}

function displayName(paths: ForecastPathsOut, key: string): string {
  const index = Number(key.replace("path_", ""));
  const path = paths.paths.find((p) => p.index === index);
  if (path?.rank_label) return path.rank_label;
  return `Simulation ${index + 1}`;
}

function LegendDot({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`h-2 w-2 rounded-full ${className}`} />
      {label}
    </span>
  );
}
