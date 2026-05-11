"use client";

import { MetricCard, type MetricTone } from "@/components/ui/MetricCard";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
import type { ForecastOut } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber, formatPercent } from "@/lib/format";

interface Props {
  forecast: ForecastOut;
}

export function ForecastMetrics({ forecast }: Props) {
  return (
    <div className="space-y-6">
      <Section title="Outcome range">
        <MetricCard label="Initial value" value={formatCurrency(forecast.initial_value)} />
        <MetricCard
          label="Expected value"
          value={forecast.expected_value != null ? formatCurrency(forecast.expected_value) : "-"}
          tone={toneDelta(forecast.expected_value, forecast.initial_value)}
        />
        <MetricCard
          label="Median value"
          value={forecast.median_value != null ? formatCurrency(forecast.median_value) : "-"}
          tone={toneDelta(forecast.median_value, forecast.initial_value)}
        />
        <MetricCard
          label="10th percentile"
          value={forecast.p10_value != null ? formatCurrency(forecast.p10_value) : "-"}
          tone={toneDelta(forecast.p10_value, forecast.initial_value)}
        />
        <MetricCard
          label="90th percentile"
          value={forecast.p90_value != null ? formatCurrency(forecast.p90_value) : "-"}
          tone={toneDelta(forecast.p90_value, forecast.initial_value)}
        />
      </Section>

      <Section title="Risk">
        <MetricCard
          label="Probability of loss"
          value={fmtPct(forecast.probability_of_loss)}
          tone={
            forecast.probability_of_loss != null && forecast.probability_of_loss > 0.5
              ? "negative"
              : "neutral"
          }
        />
        <MetricCard
          label="Beat benchmark"
          value={fmtPct(forecast.probability_beat_benchmark)}
          tone={tone(forecast.probability_beat_benchmark != null ? forecast.probability_beat_benchmark - 0.5 : null)}
        />
        <MetricCard label="Volatility (ann.)" value={fmtPct(forecast.annualized_volatility)} />
        <MetricCard
          label="Expected return (ann.)"
          value={fmtPct(forecast.expected_return)}
          tone={tone(forecast.expected_return)}
        />
        <MetricCard label="Simulations" value={formatNumber(forecast.n_simulations, 0)} />
        <MetricCard label="As of" value={formatDate(forecast.as_of_date)} />
      </Section>
    </div>
  );
}

function fmtPct(n: number | null): string {
  if (n == null) return "-";
  return formatPercent(n, 2);
}

function tone(n: number | null): MetricTone {
  if (n == null) return "neutral";
  if (n > 0) return "positive";
  if (n < 0) return "negative";
  return "neutral";
}

function toneDelta(n: number | null, initialValue: number): MetricTone {
  if (n == null) return "neutral";
  return tone(n - initialValue);
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <SectionEyebrow>{title}</SectionEyebrow>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">{children}</div>
    </div>
  );
}
