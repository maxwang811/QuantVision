"use client";

import type { ForecastDistributionOut } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  distribution: ForecastDistributionOut;
}

export function ForecastDistributionChart({ distribution }: Props) {
  const data = useMemo(
    () =>
      distribution.bins.map((bin) => ({
        midpoint: (bin.lower + bin.upper) / 2,
        count: bin.count,
        range: `${formatCurrency(bin.lower)} to ${formatCurrency(bin.upper)}`,
      })),
    [distribution],
  );

  return (
    <div className="rounded-lg border border-border bg-bg p-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-fg">Terminal distribution</h3>
        <span className="text-xs text-muted">
          P10 {formatCurrency(distribution.percentiles.p10)} / P90{" "}
          {formatCurrency(distribution.percentiles.p90)}
        </span>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="rgb(var(--border))" strokeDasharray="3 3" />
            <XAxis
              dataKey="midpoint"
              type="number"
              tick={{ fill: "rgb(var(--muted))", fontSize: 11 }}
              tickFormatter={(v) => formatCurrency(Number(v))}
              minTickGap={40}
              domain={["dataMin", "dataMax"]}
            />
            <YAxis tick={{ fill: "rgb(var(--muted))", fontSize: 11 }} width={56} />
            <Tooltip
              contentStyle={{
                background: "rgb(var(--bg))",
                border: "1px solid rgb(var(--border))",
                borderRadius: 6,
                fontSize: 12,
              }}
              labelFormatter={(_, rows) => rows?.[0]?.payload?.range ?? ""}
              formatter={(v: number | string) => [Number(v).toLocaleString(), "Simulations"]}
            />
            <ReferenceLine
              x={distribution.initial_value}
              stroke="rgb(var(--negative))"
              strokeDasharray="4 4"
              label={{
                value: "Initial",
                fill: "rgb(var(--muted))",
                fontSize: 11,
                position: "top",
              }}
            />
            <Bar dataKey="count" fill="rgb(var(--accent))" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
