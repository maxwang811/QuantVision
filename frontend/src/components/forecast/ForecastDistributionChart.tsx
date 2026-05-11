"use client";

import { ChartCard } from "@/components/ui/ChartCard";
import { chartAxisTick, chartGridStroke, chartTooltipStyle } from "@/lib/chart-theme";
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
    <ChartCard
      title="Terminal distribution"
      meta={
        <>
          P10 <span className="font-mono text-fg">{formatCurrency(distribution.percentiles.p10)}</span>
          {" · "}
          P90 <span className="font-mono text-fg">{formatCurrency(distribution.percentiles.p90)}</span>
        </>
      }
      bodyClassName="h-72"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={chartGridStroke} strokeDasharray="3 3" />
          <XAxis
            dataKey="midpoint"
            type="number"
            tick={chartAxisTick}
            tickFormatter={(v) => formatCurrency(Number(v))}
            minTickGap={40}
            domain={["dataMin", "dataMax"]}
          />
          <YAxis tick={chartAxisTick} width={56} />
          <Tooltip
            contentStyle={chartTooltipStyle}
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
          <Bar dataKey="count" fill="rgb(var(--accent))" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
