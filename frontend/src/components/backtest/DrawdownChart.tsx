"use client";

import { ChartCard } from "@/components/ui/ChartCard";
import { chartAxisTick, chartGridStroke, chartTooltipStyle } from "@/lib/chart-theme";
import type { BacktestEquityCurveOut } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  curve: BacktestEquityCurveOut;
}

export function DrawdownChart({ curve }: Props) {
  const { data, maxDD } = useMemo(() => {
    let runningMax = 0;
    let worst = 0;
    const rows = curve.points.map((p) => {
      runningMax = Math.max(runningMax, p.total_value);
      const dd = runningMax > 0 ? (p.total_value - runningMax) / runningMax : 0;
      if (dd < worst) worst = dd;
      return { date: p.date, drawdown: dd };
    });
    return { data: rows, maxDD: worst };
  }, [curve]);

  return (
    <ChartCard
      title="Drawdown"
      meta={
        <>
          Max: <span className="font-mono text-negative">{formatPercent(maxDD, 2)}</span>
        </>
      }
      bodyClassName="h-48"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="dd-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgb(var(--negative))" stopOpacity={0.0} />
              <stop offset="100%" stopColor="rgb(var(--negative))" stopOpacity={0.4} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={chartGridStroke} strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={chartAxisTick}
            tickFormatter={(d) => formatDate(d)}
            minTickGap={40}
          />
          <YAxis
            tick={chartAxisTick}
            tickFormatter={(v) => formatPercent(v, 0)}
            width={60}
            domain={[(dataMin: number) => Math.min(dataMin, 0), 0]}
          />
          <Tooltip
            contentStyle={chartTooltipStyle}
            labelFormatter={(d) => formatDate(String(d))}
            formatter={(v: number) => formatPercent(v, 2)}
          />
          <Area
            type="monotone"
            dataKey="drawdown"
            name="Drawdown"
            stroke="rgb(var(--negative))"
            strokeWidth={1.75}
            fill="url(#dd-gradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
