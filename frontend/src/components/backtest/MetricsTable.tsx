"use client";

import type { BacktestOut } from "@/lib/api";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";

interface Props {
  backtest: BacktestOut;
}

export function MetricsTable({ backtest }: Props) {
  const hasBenchmark = !!backtest.benchmark_ticker;

  return (
    <div className="space-y-5">
      <Section title="Portfolio">
        <Card label="Initial value" value={formatCurrency(backtest.initial_cash)} />
        <Card
          label="Final value"
          value={backtest.final_value != null ? formatCurrency(backtest.final_value) : "—"}
        />
        <Card
          label="Total return"
          value={fmtPct(backtest.total_return)}
          tone={tone(backtest.total_return)}
        />
        <Card
          label="Annualized return"
          value={fmtPct(backtest.annualized_return)}
          tone={tone(backtest.annualized_return)}
        />
        <Card label="Volatility (ann.)" value={fmtPct(backtest.volatility)} />
        <Card
          label="Sharpe ratio"
          value={backtest.sharpe_ratio != null ? formatNumber(backtest.sharpe_ratio, 2) : "—"}
          tone={tone(backtest.sharpe_ratio)}
        />
        <Card
          label="Max drawdown"
          value={fmtPct(backtest.max_drawdown)}
          tone={backtest.max_drawdown != null && backtest.max_drawdown < 0 ? "negative" : "neutral"}
        />
      </Section>

      {hasBenchmark && (
        <Section title={`Benchmark · ${backtest.benchmark_ticker}`}>
          <Card label="Benchmark return" value={fmtPct(backtest.benchmark_total_return)} />
          <Card
            label="Benchmark CAGR"
            value={fmtPct(backtest.benchmark_annualized_return)}
          />
          <Card
            label="Alpha (ann.)"
            value={fmtPct(backtest.alpha)}
            tone={tone(backtest.alpha)}
          />
          <Card
            label="Beta"
            value={backtest.beta != null ? formatNumber(backtest.beta, 2) : "—"}
          />
          <Card
            label="Information ratio"
            value={
              backtest.information_ratio != null
                ? formatNumber(backtest.information_ratio, 2)
                : "—"
            }
            tone={tone(backtest.information_ratio)}
          />
          <Card label="Tracking error" value={fmtPct(backtest.tracking_error)} />
        </Section>
      )}
    </div>
  );
}

function fmtPct(n: number | null): string {
  if (n == null) return "—";
  return formatPercent(n, 2);
}

function tone(n: number | null): CardTone {
  if (n == null) return "neutral";
  if (n > 0) return "positive";
  if (n < 0) return "negative";
  return "neutral";
}

type CardTone = "positive" | "negative" | "neutral";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">{children}</div>
    </div>
  );
}

function Card({ label, value, tone = "neutral" }: { label: string; value: string; tone?: CardTone }) {
  const valueColor =
    tone === "positive" ? "text-positive" : tone === "negative" ? "text-negative" : "text-fg";
  return (
    <div className="rounded-md border border-border bg-bg p-3">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 font-mono text-lg font-semibold tabular-nums ${valueColor}`}>
        {value}
      </div>
    </div>
  );
}
