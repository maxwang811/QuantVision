"use client";

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

  if (!summary.data) return <Skeleton />;

  if (summary.data.status === "failed") {
    return (
      <div className="rounded-lg border border-negative/40 bg-negative/5 p-4 text-sm text-negative">
        Backtest failed: {summary.data.error_message ?? "(no message)"}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Link
          href={`/forecast?from_backtest_id=${encodeURIComponent(backtestId)}`}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-fg hover:border-accent hover:text-accent"
        >
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
        <div className="h-32 animate-pulse rounded-lg border border-border bg-border/20" />
      )}
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-negative/40 bg-negative/5 p-4 text-sm text-negative">
      {message}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3">
      <div className="h-24 animate-pulse rounded-lg border border-border bg-border/20" />
      <ChartSkeleton />
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="space-y-3">
      <div className="h-72 animate-pulse rounded-lg border border-border bg-border/20" />
      <div className="h-48 animate-pulse rounded-lg border border-border bg-border/20" />
    </div>
  );
}
