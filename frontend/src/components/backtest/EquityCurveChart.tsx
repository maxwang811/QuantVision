"use client";

import type { BacktestEquityCurveOut } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  curve: BacktestEquityCurveOut;
}

interface Row {
  date: string;
  portfolio: number;
  benchmark?: number;
}

export function EquityCurveChart({ curve }: Props) {
  const data: Row[] = useMemo(() => {
    const benchByDate = new Map<string, number>();
    if (curve.benchmark) {
      for (const b of curve.benchmark) benchByDate.set(b.date, b.value);
    }
    return curve.points.map((p) => ({
      date: p.date,
      portfolio: p.total_value,
      benchmark: benchByDate.get(p.date),
    }));
  }, [curve]);

  const hasBenchmark = !!curve.benchmark && curve.benchmark.length > 0;

  return (
    <div className="rounded-lg border border-border bg-bg p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-fg">Equity curve</h3>
        {hasBenchmark && curve.benchmark_ticker && (
          <span className="text-xs text-muted">vs. {curve.benchmark_ticker}</span>
        )}
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="rgb(var(--border))" strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fill: "rgb(var(--muted))", fontSize: 11 }}
              tickFormatter={(d) => formatDate(d)}
              minTickGap={40}
            />
            <YAxis
              tick={{ fill: "rgb(var(--muted))", fontSize: 11 }}
              tickFormatter={(v) => formatCurrency(v)}
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
              formatter={(v: number) => formatCurrency(v)}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line
              type="monotone"
              dataKey="portfolio"
              name="Portfolio"
              stroke="rgb(var(--accent))"
              strokeWidth={2}
              dot={false}
            />
            {hasBenchmark && (
              <Line
                type="monotone"
                dataKey="benchmark"
                name={curve.benchmark_ticker ?? "Benchmark"}
                stroke="rgb(var(--muted))"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
