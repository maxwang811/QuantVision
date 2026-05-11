"use client";

import { ChartCard } from "@/components/ui/ChartCard";
import { chartAxisTick, chartGridStroke, chartTooltipStyle } from "@/lib/chart-theme";
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
    <ChartCard
      title="Equity curve"
      meta={hasBenchmark && curve.benchmark_ticker ? <>vs. {curve.benchmark_ticker}</> : null}
      bodyClassName="h-72"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={chartGridStroke} strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={chartAxisTick}
            tickFormatter={(d) => formatDate(d)}
            minTickGap={40}
          />
          <YAxis
            tick={chartAxisTick}
            tickFormatter={(v) => formatCurrency(v)}
            width={80}
            domain={["auto", "auto"]}
          />
          <Tooltip
            contentStyle={chartTooltipStyle}
            labelFormatter={(d) => formatDate(String(d))}
            formatter={(v: number) => formatCurrency(v)}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Line
            type="monotone"
            dataKey="portfolio"
            name="Portfolio"
            stroke="rgb(var(--accent))"
            strokeWidth={2.25}
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
    </ChartCard>
  );
}
