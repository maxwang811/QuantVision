"use client";

import {
  ApiRequestError,
  api,
  type FrontierPointOut,
  type OptimizationResultOut,
} from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import type { PortfolioRow } from "./PortfolioWeightEditor";
import { EfficientFrontierChart } from "./EfficientFrontierChart";

interface Props {
  /** Called when the user clicks "Use these weights"; parent should seed BacktestForm with these rows. */
  onApply: (rows: PortfolioRow[]) => void;
  defaultTickers?: string[];
}

const DEFAULT_TICKERS = ["SPY", "AAPL", "MSFT"];

export function OptimizerPanel({ onApply, defaultTickers = DEFAULT_TICKERS }: Props) {
  const [tickersText, setTickersText] = useState<string>(defaultTickers.join(", "));
  const [lookbackDays, setLookbackDays] = useState<number>(1260);
  const [riskFreeRate, setRiskFreeRate] = useState<number>(0.04);
  const [useTargetReturn, setUseTargetReturn] = useState<boolean>(false);
  const [targetReturn, setTargetReturn] = useState<number>(0.10);

  const tickers = tickersText
    .split(/[\s,]+/)
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean);

  const localError =
    tickers.length < 2
      ? "Enter at least two tickers."
      : new Set(tickers).size !== tickers.length
        ? "Duplicate tickers."
        : null;

  const mutation = useMutation({
    mutationFn: () =>
      api.optimize({
        tickers,
        lookback_days: lookbackDays,
        risk_free_rate: riskFreeRate,
        target_return: useTargetReturn ? targetReturn : null,
      }),
  });

  const apiError =
    mutation.error instanceof ApiRequestError
      ? `${mutation.error.code}: ${mutation.error.message}`
      : mutation.error
        ? String(mutation.error)
        : null;

  const result = mutation.data ?? null;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!localError) mutation.mutate();
  };

  const applyWeights = (point: FrontierPointOut) => {
    if (!result) return;
    const rows: PortfolioRow[] = result.tickers.map((t, i) => ({
      ticker: t,
      weightPct: roundPct(point.weights[i] * 100),
    }));
    // Repair tiny rounding drift on the last row so weights sum to exactly 100.
    const drift = 100 - rows.reduce((s, r) => s + r.weightPct, 0);
    if (rows.length > 0) {
      rows[rows.length - 1] = {
        ...rows[rows.length - 1],
        weightPct: roundPct(rows[rows.length - 1].weightPct + drift),
      };
    }
    onApply(rows);
  };

  return (
    <details className="rounded-lg border border-border p-5">
      <summary className="cursor-pointer text-sm font-semibold uppercase tracking-wide text-muted">
        Portfolio optimizer (mean-variance)
      </summary>
      <p className="mt-3 text-sm text-muted">
        Compute the long-only minimum-variance and max-Sharpe portfolios from
        historical log-returns. Click <em>Use these weights</em> to populate the
        backtest form.
      </p>

      <form onSubmit={submit} className="mt-4 space-y-4">
        <Field label="Tickers (comma or space separated)">
          <input
            type="text"
            value={tickersText}
            onChange={(e) => setTickersText(e.target.value)}
            placeholder="SPY, AAPL, MSFT, NVDA"
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm font-mono text-fg outline-none focus:border-accent"
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <NumberField
            label="Lookback days"
            min={252}
            max={5040}
            step={21}
            value={lookbackDays}
            onChange={setLookbackDays}
          />
          <NumberField
            label="Risk-free rate"
            min={0}
            max={0.25}
            step={0.005}
            value={riskFreeRate}
            onChange={setRiskFreeRate}
          />
          <Field label="Target return">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={useTargetReturn}
                onChange={(e) => setUseTargetReturn(e.target.checked)}
              />
              <input
                type="number"
                min={-0.5}
                max={1.0}
                step={0.01}
                value={targetReturn}
                disabled={!useTargetReturn}
                onChange={(e) => setTargetReturn(Number(e.target.value))}
                className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent disabled:opacity-50"
              />
            </div>
          </Field>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={!!localError || mutation.isPending}
            className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? "Optimizing…" : "Optimize"}
          </button>
          {localError && <span className="text-sm text-negative">{localError}</span>}
          {!localError && apiError && <span className="text-sm text-negative">{apiError}</span>}
        </div>
      </form>

      {result && <ResultBlock result={result} onApply={applyWeights} />}
    </details>
  );
}

function ResultBlock({
  result,
  onApply,
}: {
  result: OptimizationResultOut;
  onApply: (point: FrontierPointOut) => void;
}) {
  return (
    <div className="mt-6 space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <PointCard
          title="Min-variance"
          tickers={result.tickers}
          point={result.min_variance}
          onApply={() => onApply(result.min_variance)}
        />
        <PointCard
          title="Max-Sharpe"
          tickers={result.tickers}
          point={result.max_sharpe}
          onApply={() => onApply(result.max_sharpe)}
        />
      </div>

      {result.target_return && (
        <PointCard
          title="Target-return"
          tickers={result.tickers}
          point={result.target_return}
          onApply={() => onApply(result.target_return!)}
        />
      )}

      <div className="rounded-md border border-border/60 p-4">
        <div className="mb-3 text-xs font-medium uppercase tracking-wide text-muted">
          Efficient frontier ({result.n_observations} observations,{" "}
          {result.lookback_start} → {result.lookback_end})
        </div>
        <EfficientFrontierChart
          points={result.frontier}
          minVariance={result.min_variance}
          maxSharpe={result.max_sharpe}
        />
      </div>
    </div>
  );
}

function PointCard({
  title,
  tickers,
  point,
  onApply,
}: {
  title: string;
  tickers: string[];
  point: FrontierPointOut;
  onApply: () => void;
}) {
  return (
    <div className="rounded-md border border-border/60 p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <button
          type="button"
          onClick={onApply}
          className="rounded-md border border-border px-3 py-1 text-xs hover:bg-border/40"
        >
          Use these weights
        </button>
      </div>
      <dl className="grid grid-cols-3 gap-3 text-xs">
        <Stat label="Expected return" value={`${(point.expected_return * 100).toFixed(2)}%`} />
        <Stat label="Volatility" value={`${(point.volatility * 100).toFixed(2)}%`} />
        <Stat label="Sharpe" value={point.sharpe_ratio.toFixed(2)} />
      </dl>
      <table className="mt-3 w-full text-xs">
        <tbody>
          {tickers.map((t, i) => (
            <tr key={t} className="border-t border-border/40">
              <td className="py-1 font-mono">{t}</td>
              <td className="py-1 text-right">{(point.weights[i] * 100).toFixed(2)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-muted">{label}</div>
      <div className="font-mono text-sm">{value}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <Field label={label}>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
      />
    </Field>
  );
}

function roundPct(x: number): number {
  return Math.round(x * 100) / 100;
}
