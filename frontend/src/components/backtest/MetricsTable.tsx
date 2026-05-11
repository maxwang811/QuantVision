"use client";

import { MetricCard, type MetricTone } from "@/components/ui/MetricCard";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
import type { BacktestOut } from "@/lib/api";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";

interface Props {
  backtest: BacktestOut;
}

export function MetricsTable({ backtest }: Props) {
  const hasBenchmark = !!backtest.benchmark_ticker;

  return (
    <div className="space-y-6">
      <Section title="Portfolio">
        <MetricCard label="Initial value" value={formatCurrency(backtest.initial_cash)} />
        <MetricCard
          label="Final value"
          value={backtest.final_value != null ? formatCurrency(backtest.final_value) : "—"}
        />
        <MetricCard
          label="Total return"
          value={fmtPct(backtest.total_return)}
          tone={tone(backtest.total_return)}
        />
        <MetricCard
          label="Annualized return"
          value={fmtPct(backtest.annualized_return)}
          tone={tone(backtest.annualized_return)}
        />
        <MetricCard label="Volatility (ann.)" value={fmtPct(backtest.volatility)} />
        <MetricCard
          label="Sharpe ratio"
          value={backtest.sharpe_ratio != null ? formatNumber(backtest.sharpe_ratio, 2) : "—"}
          tone={tone(backtest.sharpe_ratio)}
        />
        <MetricCard
          label="Max drawdown"
          value={fmtPct(backtest.max_drawdown)}
          tone={backtest.max_drawdown != null && backtest.max_drawdown < 0 ? "negative" : "neutral"}
        />
      </Section>

      {hasBenchmark && (
        <Section title={`Benchmark · ${backtest.benchmark_ticker}`}>
          <MetricCard label="Benchmark return" value={fmtPct(backtest.benchmark_total_return)} />
          <MetricCard label="Benchmark CAGR" value={fmtPct(backtest.benchmark_annualized_return)} />
          <MetricCard
            label="Alpha (ann.)"
            value={fmtPct(backtest.alpha)}
            tone={tone(backtest.alpha)}
          />
          <MetricCard
            label="Beta"
            value={backtest.beta != null ? formatNumber(backtest.beta, 2) : "—"}
          />
          <MetricCard
            label="Information ratio"
            value={
              backtest.information_ratio != null
                ? formatNumber(backtest.information_ratio, 2)
                : "—"
            }
            tone={tone(backtest.information_ratio)}
          />
          <MetricCard label="Tracking error" value={fmtPct(backtest.tracking_error)} />
        </Section>
      )}
    </div>
  );
}

function fmtPct(n: number | null): string {
  if (n == null) return "—";
  return formatPercent(n, 2);
}

function tone(n: number | null): MetricTone {
  if (n == null) return "neutral";
  if (n > 0) return "positive";
  if (n < 0) return "negative";
  return "neutral";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <SectionEyebrow>{title}</SectionEyebrow>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{children}</div>
    </div>
  );
}
