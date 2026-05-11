"use client";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { IconBeaker, IconChevronDown } from "@/components/ui/Icons";
import { Input } from "@/components/ui/Input";
import { cn } from "@/components/ui/utils";
import {
  ApiRequestError,
  api,
  type FrontierPointOut,
  type OptimizationResultOut,
} from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { EfficientFrontierChart } from "./EfficientFrontierChart";
import type { PortfolioRow } from "./PortfolioWeightEditor";

interface Props {
  onApply: (rows: PortfolioRow[]) => void;
  defaultTickers?: string[];
}

const DEFAULT_TICKERS = ["SPY", "AAPL", "MSFT"];

export function OptimizerPanel({ onApply, defaultTickers = DEFAULT_TICKERS }: Props) {
  const [open, setOpen] = useState(false);
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
    <Card padded={false}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-surface-2/40 sm:px-6 focus-ring"
      >
        <div className="flex items-start gap-3">
          <span className="mt-0.5 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent">
            <IconBeaker width={18} height={18} />
          </span>
          <div className="space-y-1">
            <div className="text-[11px] font-semibold uppercase tracking-eyebrow text-muted">
              Optional
            </div>
            <div className="text-base font-semibold text-fg">
              Portfolio optimizer (mean-variance)
            </div>
            <p className="text-sm text-muted">
              Compute long-only min-variance and max-Sharpe portfolios, then apply the weights to
              the backtest form below.
            </p>
          </div>
        </div>
        <IconChevronDown
          width={18}
          height={18}
          className={cn(
            "h-5 w-5 flex-shrink-0 text-muted transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div className="border-t border-border px-5 py-5 sm:px-6">
          <form onSubmit={submit} className="space-y-5">
            <Field label="Tickers (comma or space separated)">
              <Input
                type="text"
                value={tickersText}
                onChange={(e) => setTickersText(e.target.value)}
                placeholder="SPY, AAPL, MSFT, NVDA"
                className="font-mono"
              />
            </Field>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field label="Lookback days">
                <Input
                  type="number"
                  min={252}
                  max={5040}
                  step={21}
                  value={lookbackDays}
                  onChange={(e) => setLookbackDays(Number(e.target.value))}
                />
              </Field>
              <Field label="Risk-free rate">
                <Input
                  type="number"
                  min={0}
                  max={0.25}
                  step={0.005}
                  value={riskFreeRate}
                  onChange={(e) => setRiskFreeRate(Number(e.target.value))}
                />
              </Field>
              <Field label="Target return">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={useTargetReturn}
                    onChange={(e) => setUseTargetReturn(e.target.checked)}
                    className="h-4 w-4 accent-accent"
                    aria-label="Use target return"
                  />
                  <Input
                    type="number"
                    min={-0.5}
                    max={1.0}
                    step={0.01}
                    value={targetReturn}
                    disabled={!useTargetReturn}
                    onChange={(e) => setTargetReturn(Number(e.target.value))}
                  />
                </div>
              </Field>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <Button type="submit" disabled={!!localError || mutation.isPending}>
                {mutation.isPending ? "Optimizing…" : "Optimize"}
              </Button>
              {localError && <span className="text-sm text-negative">{localError}</span>}
              {!localError && apiError && <span className="text-sm text-negative">{apiError}</span>}
            </div>
          </form>

          {result && <ResultBlock result={result} onApply={applyWeights} />}
        </div>
      )}
    </Card>
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
    <div className="mt-6 space-y-5">
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

      <Card className="bg-surface">
        <CardHeader
          eyebrow={`${result.n_observations} obs · ${result.lookback_start} → ${result.lookback_end}`}
          title="Efficient frontier"
        />
        <div className="mt-4">
          <EfficientFrontierChart
            points={result.frontier}
            minVariance={result.min_variance}
            maxSharpe={result.max_sharpe}
          />
        </div>
      </Card>
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
    <Card className="bg-surface" padded>
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-fg">{title}</h3>
        <Button type="button" variant="secondary" size="sm" onClick={onApply}>
          Use these weights
        </Button>
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-3 text-xs">
        <Stat label="Expected return" value={`${(point.expected_return * 100).toFixed(2)}%`} />
        <Stat label="Volatility" value={`${(point.volatility * 100).toFixed(2)}%`} />
        <Stat label="Sharpe" value={point.sharpe_ratio.toFixed(2)} />
      </dl>
      <div className="mt-4 overflow-hidden rounded-md border border-border">
        <table className="w-full text-xs">
          <tbody className="divide-y divide-border">
            {tickers.map((t, i) => (
              <tr key={t}>
                <td className="px-3 py-1.5 font-mono font-medium text-fg">{t}</td>
                <td className="px-3 py-1.5 text-right font-mono tabular-nums text-muted">
                  {(point.weights[i] * 100).toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface-2/60 p-2.5">
      <div className="text-[10px] font-medium uppercase tracking-eyebrow text-muted">{label}</div>
      <div className="mt-1 font-mono text-sm font-semibold text-fg">{value}</div>
    </div>
  );
}

function roundPct(x: number): number {
  return Math.round(x * 100) / 100;
}
