"use client";

import type { ForecastOut } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber, formatPercent } from "@/lib/format";

interface Props {
  forecast: ForecastOut;
}

export function ForecastMetrics({ forecast }: Props) {
  return (
    <div className="space-y-5">
      <Section title="Outcome range">
        <Card label="Initial value" value={formatCurrency(forecast.initial_value)} />
        <Card
          label="Expected value"
          value={forecast.expected_value != null ? formatCurrency(forecast.expected_value) : "-"}
          tone={toneDelta(forecast.expected_value, forecast.initial_value)}
        />
        <Card
          label="Median value"
          value={forecast.median_value != null ? formatCurrency(forecast.median_value) : "-"}
          tone={toneDelta(forecast.median_value, forecast.initial_value)}
        />
        <Card
          label="10th percentile"
          value={forecast.p10_value != null ? formatCurrency(forecast.p10_value) : "-"}
          tone={toneDelta(forecast.p10_value, forecast.initial_value)}
        />
        <Card
          label="90th percentile"
          value={forecast.p90_value != null ? formatCurrency(forecast.p90_value) : "-"}
          tone={toneDelta(forecast.p90_value, forecast.initial_value)}
        />
      </Section>

      <Section title="Risk">
        <Card
          label="Probability of loss"
          value={fmtPct(forecast.probability_of_loss)}
          tone={
            forecast.probability_of_loss != null && forecast.probability_of_loss > 0.5
              ? "negative"
              : "neutral"
          }
        />
        <Card
          label="Beat benchmark"
          value={fmtPct(forecast.probability_beat_benchmark)}
          tone={tone(forecast.probability_beat_benchmark != null ? forecast.probability_beat_benchmark - 0.5 : null)}
        />
        <Card label="Volatility (ann.)" value={fmtPct(forecast.annualized_volatility)} />
        <Card
          label="Expected return (ann.)"
          value={fmtPct(forecast.expected_return)}
          tone={tone(forecast.expected_return)}
        />
        <Card label="Simulations" value={formatNumber(forecast.n_simulations, 0)} />
        <Card label="As of" value={formatDate(forecast.as_of_date)} />
      </Section>
    </div>
  );
}

function fmtPct(n: number | null): string {
  if (n == null) return "-";
  return formatPercent(n, 2);
}

function tone(n: number | null): CardTone {
  if (n == null) return "neutral";
  if (n > 0) return "positive";
  if (n < 0) return "negative";
  return "neutral";
}

function toneDelta(n: number | null, initialValue: number): CardTone {
  if (n == null) return "neutral";
  return tone(n - initialValue);
}

type CardTone = "positive" | "negative" | "neutral";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6">{children}</div>
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
