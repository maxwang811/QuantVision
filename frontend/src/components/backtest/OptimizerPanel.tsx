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
    <Card variant="default" padded={false} className="overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-surface-2/50 sm:px-6 focus-ring"
      >
        <div className="flex items-start gap-4">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accent-fg shrink-0">
            <IconBeaker width={20} height={20} />
          </span>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-base font-semibold text-fg">
                Portfolio Optimizer
              </span>
              <span className="text-xs text-muted bg-surface-2 px-2 py-0.5 rounded-full">
                Optional
              </span>
            </div>
            <p className="text-sm text-muted leading-relaxed">
              Compute optimal min-variance and max-Sharpe portfolios using mean-variance optimization, then apply the weights below.
            </p>
          </div>
        </div>
        <IconChevronDown
          width={20}
          height={20}
          className={cn(
            "shrink-0 text-muted transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div className="border-t border-border px-5 py-6 sm:px-6 animate-fade-in">
          <form onSubmit={submit} className="space-y-6">
            <Field label="Tickers" hint="Comma or space separated">
              <Input
                type="text"
                value={tickersText}
                onChange={(e) => setTickersText(e.target.value)}
                placeholder="SPY, AAPL, MSFT, NVDA"
                className="font-mono"
              />
            </Field>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
              <Field label="Target return" hint="Optional constraint">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={useTargetReturn}
                    onChange={(e) => setUseTargetReturn(e.target.checked)}
                    className="h-4 w-4 rounded border-border accent-accent"
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

            <div className="flex flex-wrap items-center gap-3">
              <Button 
                type="submit" 
                disabled={!!localError || mutation.isPending}
                loading={mutation.isPending}
              >
                {mutation.isPending ? "Optimizing..." : "Run Optimization"}
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
    <div className="mt-8 space-y-6">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-medium text-fg">Optimization Results</h3>
        <div className="h-px flex-1 bg-border" />
      </div>
      
      <div className="grid gap-4 lg:grid-cols-2">
        <PointCard
          title="Min-variance Portfolio"
          tickers={result.tickers}
          point={result.min_variance}
          onApply={() => onApply(result.min_variance)}
        />
        <PointCard
          title="Max-Sharpe Portfolio"
          tickers={result.tickers}
          point={result.max_sharpe}
          onApply={() => onApply(result.max_sharpe)}
        />
      </div>

      {result.target_return && (
        <PointCard
          title="Target-return Portfolio"
          tickers={result.tickers}
          point={result.target_return}
          onApply={() => onApply(result.target_return!)}
        />
      )}

      <Card variant="default">
        <CardHeader
          eyebrow={`${result.n_observations} observations`}
          title="Efficient Frontier"
          description={`${result.lookback_start} to ${result.lookback_end}`}
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
    <div className="rounded-xl border border-border bg-surface p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="font-medium text-fg">{title}</h4>
        <Button type="button" variant="outline" size="sm" onClick={onApply}>
          Apply weights
        </Button>
      </div>
      
      {/* Metrics */}
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Expected Return" value={`${(point.expected_return * 100).toFixed(2)}%`} />
        <Stat label="Volatility" value={`${(point.volatility * 100).toFixed(2)}%`} />
        <Stat label="Sharpe Ratio" value={point.sharpe_ratio.toFixed(2)} />
      </div>
      
      {/* Weights table */}
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <tbody className="divide-y divide-border">
            {tickers.map((t, i) => (
              <tr key={t} className="hover:bg-surface-2/50">
                <td className="px-3 py-2 font-mono font-medium text-fg">{t}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-muted">
                  {(point.weights[i] * 100).toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface-2/60 p-3 text-center">
      <div className="text-2xs font-medium text-muted uppercase tracking-eyebrow">{label}</div>
      <div className="mt-1 font-mono text-sm font-semibold text-fg">{value}</div>
    </div>
  );
}

function roundPct(x: number): number {
  return Math.round(x * 100) / 100;
}
