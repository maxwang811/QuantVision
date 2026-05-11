"use client";

import { Button } from "@/components/ui/Button";
import { ErrorBox } from "@/components/ui/EmptyState";
import { IconSparkles } from "@/components/ui/Icons";
import { Skeleton } from "@/components/ui/Skeleton";
import { ApiRequestError, api, type BacktestOut } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { DrawdownChart } from "./DrawdownChart";
import { EquityCurveChart } from "./EquityCurveChart";
import { MetricsTable } from "./MetricsTable";
import { TradeHistoryTable } from "./TradeHistoryTable";

interface Props {
  backtestId: string;
  initial?: BacktestOut;
}

export function BacktestResults({ backtestId, initial }: Props) {
  const summary = useQuery({
    queryKey: ["backtest", backtestId],
    queryFn: () => api.getBacktest(backtestId),
    initialData: initial && initial.id === backtestId ? initial : undefined,
  });

  const trades = useQuery({
    queryKey: ["backtest", backtestId, "trades"],
    queryFn: () => api.getBacktestTrades(backtestId),
  });

  const curve = useQuery({
    queryKey: ["backtest", backtestId, "curve"],
    queryFn: () => api.getBacktestEquityCurve(backtestId),
  });

  if (summary.isError) {
    const e = summary.error;
    const msg = e instanceof ApiRequestError ? `${e.code}: ${e.message}` : String(e);
    return <ErrorBox message={msg} />;
  }

  if (!summary.data) return <ResultsSkeleton />;

  if (summary.data.status === "failed") {
    return (
      <ErrorBox message={`Backtest failed: ${summary.data.error_message ?? "(no message)"}`} />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Link
          href={`/forecast?from_backtest_id=${encodeURIComponent(backtestId)}`}
          className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border bg-surface px-3 text-sm font-medium text-fg transition-colors hover:border-accent hover:text-accent focus-ring"
        >
          <IconSparkles width={14} height={14} />
          Forecast from this backtest
        </Link>
      </div>

      <MetricsTable backtest={summary.data} />

      {curve.data ? (
        <>
          <EquityCurveChart curve={curve.data} />
          <DrawdownChart curve={curve.data} />
        </>
      ) : (
        <ChartSkeleton />
      )}

      {trades.data ? (
        <TradeHistoryTable trades={trades.data.trades} />
      ) : (
        <Skeleton className="h-32" />
      )}
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <ChartSkeleton />
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-72" />
      <Skeleton className="h-48" />
    </div>
  );
}
