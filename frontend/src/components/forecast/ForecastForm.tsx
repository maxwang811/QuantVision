"use client";

import { PortfolioWeightEditor, type PortfolioRow } from "@/components/backtest/PortfolioWeightEditor";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardSection } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { IconChart, IconSparkles, IconCpu } from "@/components/ui/Icons";
import { Input } from "@/components/ui/Input";
import { Tabs } from "@/components/ui/Tabs";
import { cn } from "@/components/ui/utils";
import {
  ApiRequestError,
  api,
  type ForecastCreate,
  type ForecastMethod,
  type ForecastOut,
} from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";

const DEFAULT_ROWS: PortfolioRow[] = [
  { ticker: "SPY", weightPct: 50 },
  { ticker: "AAPL", weightPct: 25 },
  { ticker: "MSFT", weightPct: 25 },
];

const METHODS: { value: ForecastMethod; label: string; detail: string; icon: typeof IconChart }[] = [
  {
    value: "monte_carlo",
    label: "Monte Carlo",
    detail: "Parametric simulation using historical drift, volatility, and covariance.",
    icon: IconSparkles,
  },
  {
    value: "bootstrap",
    label: "Bootstrap",
    detail: "Historical return sampling that preserves same-day cross-asset moves.",
    icon: IconChart,
  },
  {
    value: "ml_drift",
    label: "ML Drift",
    detail: "Ridge-based drift adjustment with Monte Carlo covariance.",
    icon: IconCpu,
  },
];

type ForecastMode = "manual" | "backtest";

interface Props {
  defaultBacktestId?: string | null;
  onSuccess: (forecast: ForecastOut) => void;
}

export function ForecastForm({ defaultBacktestId, onSuccess }: Props) {
  const [mode, setMode] = useState<ForecastMode>(defaultBacktestId ? "backtest" : "manual");
  const [name, setName] = useState<string>("");
  const [rows, setRows] = useState<PortfolioRow[]>(DEFAULT_ROWS);
  const [fromBacktestId, setFromBacktestId] = useState<string>(defaultBacktestId ?? "");
  const [method, setMethod] = useState<ForecastMethod>("monte_carlo");
  const [initialValue, setInitialValue] = useState<number>(10_000);
  const [horizonMonths, setHorizonMonths] = useState<number>(12);
  const [nSimulations, setNSimulations] = useState<number>(10_000);
  const [lookbackDays, setLookbackDays] = useState<number>(1260);
  const [asOfDate, setAsOfDate] = useState<string>("");
  const [benchmarkTicker, setBenchmarkTicker] = useState<string>("SPY");
  const [randomSeed, setRandomSeed] = useState<string>("");

  const { localError, payload } = useMemo(() => {
    const common = buildCommonPayload({
      method,
      horizonMonths,
      nSimulations,
      lookbackDays,
      asOfDate,
      benchmarkTicker,
      randomSeed,
    });
    if ("error" in common) return { localError: common.error, payload: null };

    if (mode === "backtest") {
      const id = fromBacktestId.trim();
      if (!id) return { localError: "Enter a completed backtest id.", payload: null };
      return {
        localError: null,
        payload: {
          ...common.payload,
          name: name.trim() || null,
          from_backtest_id: id,
        } satisfies ForecastCreate,
      };
    }

    const cleanRows = rows.filter((r) => r.ticker.trim().length > 0);
    if (cleanRows.length === 0) {
      return { localError: "Add at least one ticker.", payload: null };
    }
    const total = cleanRows.reduce((s, r) => s + r.weightPct, 0);
    if (Math.abs(total - 100) > 0.01) {
      return { localError: `Weights must sum to 100% (currently ${total.toFixed(2)}%).`, payload: null };
    }
    if (cleanRows.some((r) => r.weightPct < 0)) {
      return { localError: "Weights must be non-negative.", payload: null };
    }
    const seen = new Set<string>();
    for (const row of cleanRows) {
      const ticker = row.ticker.toUpperCase();
      if (seen.has(ticker)) return { localError: `Duplicate ticker: ${ticker}`, payload: null };
      seen.add(ticker);
    }
    if (!(initialValue > 0)) {
      return { localError: "Initial value must be positive.", payload: null };
    }

    return {
      localError: null,
      payload: {
        ...common.payload,
        name: name.trim() || null,
        tickers: cleanRows.map((r) => r.ticker.toUpperCase()),
        weights: cleanRows.map((r) => r.weightPct / 100),
        initial_value: initialValue,
      } satisfies ForecastCreate,
    };
  }, [
    method,
    name,
    horizonMonths,
    nSimulations,
    lookbackDays,
    asOfDate,
    benchmarkTicker,
    randomSeed,
    mode,
    fromBacktestId,
    rows,
    initialValue,
  ]);

  const mutation = useMutation({
    mutationFn: (p: ForecastCreate) => api.runForecast(p),
    onSuccess,
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (payload) mutation.mutate(payload);
  };

  const apiError =
    mutation.error instanceof ApiRequestError
      ? `${mutation.error.code}: ${mutation.error.message}`
      : mutation.error
        ? String(mutation.error)
        : null;

  return (
    <form onSubmit={submit} className="space-y-6">
      <Card variant="elevated">
        <CardHeader
          title="Forecast Configuration"
          description="Choose your portfolio source and simulation method."
          size="large"
        />
        
        <CardSection divided className="space-y-6">
          {/* Run name */}
          <Field label="Run name" hint="Optional - helps identify this forecast later">
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={128}
              placeholder="e.g., 12 month Monte Carlo baseline"
            />
          </Field>

          {/* Source tabs */}
          <div className="space-y-4">
            <Tabs
              value={mode}
              onChange={(v) => setMode(v)}
              tabs={[
                { value: "manual", label: "Manual portfolio" },
                { value: "backtest", label: "From backtest" },
              ]}
            />

            {mode === "manual" ? (
              <PortfolioWeightEditor rows={rows} onChange={setRows} />
            ) : (
              <Field label="Completed backtest ID" hint="Copy from a previous backtest run">
                <Input
                  type="text"
                  value={fromBacktestId}
                  onChange={(e) => setFromBacktestId(e.target.value)}
                  placeholder="00000000-0000-0000-0000-000000000000"
                  className="font-mono"
                />
              </Field>
            )}
          </div>
        </CardSection>

        <CardSection divided className="space-y-6">
          {/* Method selection */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-fg">Simulation Method</h3>
            <div className="grid gap-3 sm:grid-cols-3">
              {METHODS.map((item) => {
                const active = method === item.value;
                const Icon = item.icon;
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setMethod(item.value)}
                    aria-pressed={active}
                    className={cn(
                      "relative flex flex-col items-start gap-3 rounded-xl border p-4 text-left transition-all duration-200 focus-ring",
                      active
                        ? "border-accent bg-accent-soft ring-1 ring-accent/30"
                        : "border-border bg-surface hover:border-border-strong hover:bg-surface-2/50",
                    )}
                  >
                    <div className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                      active ? "bg-accent text-accent-fg" : "bg-surface-2 text-muted"
                    )}>
                      <Icon width={20} height={20} />
                    </div>
                    <div>
                      <div className="font-medium text-fg">{item.label}</div>
                      <div className="mt-1 text-xs text-muted leading-relaxed">{item.detail}</div>
                    </div>
                    {active && (
                      <div className="absolute top-3 right-3">
                        <div className="h-2 w-2 rounded-full bg-accent" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </CardSection>

        <CardSection divided className="space-y-6">
          <h3 className="text-sm font-medium text-fg">Simulation Parameters</h3>
          
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {mode === "manual" && (
              <Field label="Initial value">
                <Input
                  type="number"
                  min={0}
                  step={100}
                  value={initialValue}
                  onChange={(e) => setInitialValue(Number(e.target.value))}
                  adornmentLeft="$"
                />
              </Field>
            )}

            <NumberField
              label="Horizon"
              hint="Months"
              min={1}
              max={120}
              step={1}
              value={horizonMonths}
              onChange={setHorizonMonths}
            />
            <NumberField
              label="Simulations"
              hint="Number of paths"
              min={100}
              max={50_000}
              step={100}
              value={nSimulations}
              onChange={setNSimulations}
            />
            <NumberField
              label="Lookback"
              hint="Trading days"
              min={252}
              max={5040}
              step={21}
              value={lookbackDays}
              onChange={setLookbackDays}
            />
            <Field label="As-of date" hint="Optional">
              <Input
                type="date"
                value={asOfDate}
                onChange={(e) => setAsOfDate(e.target.value)}
              />
            </Field>
            <Field label="Benchmark" hint="Optional">
              <Input
                type="text"
                value={benchmarkTicker}
                onChange={(e) => setBenchmarkTicker(e.target.value)}
                placeholder="SPY"
                className="font-mono"
              />
            </Field>
            <Field label="Random seed" hint="Optional, for reproducibility">
              <Input
                type="number"
                min={0}
                step={1}
                value={randomSeed}
                onChange={(e) => setRandomSeed(e.target.value)}
                placeholder="42"
              />
            </Field>
          </div>
        </CardSection>

        {/* Submit */}
        <CardSection divided>
          <div className="flex flex-wrap items-center gap-4">
            <Button 
              type="submit" 
              disabled={!payload || mutation.isPending} 
              size="lg"
              loading={mutation.isPending}
            >
              {mutation.isPending ? "Running forecast..." : "Run Forecast"}
            </Button>
            {localError && (
              <span className="text-sm text-negative">{localError}</span>
            )}
            {!localError && apiError && (
              <span className="text-sm text-negative">{apiError}</span>
            )}
          </div>
        </CardSection>
      </Card>
    </form>
  );
}

function buildCommonPayload({
  method,
  horizonMonths,
  nSimulations,
  lookbackDays,
  asOfDate,
  benchmarkTicker,
  randomSeed,
}: {
  method: ForecastMethod;
  horizonMonths: number;
  nSimulations: number;
  lookbackDays: number;
  asOfDate: string;
  benchmarkTicker: string;
  randomSeed: string;
}): { payload: ForecastCreate } | { error: string } {
  if (!Number.isInteger(horizonMonths) || horizonMonths < 1 || horizonMonths > 120) {
    return { error: "Horizon must be between 1 and 120 months." };
  }
  if (!Number.isInteger(nSimulations) || nSimulations < 100 || nSimulations > 50_000) {
    return { error: "Simulations must be between 100 and 50,000." };
  }
  if (!Number.isInteger(lookbackDays) || lookbackDays < 252 || lookbackDays > 5040) {
    return { error: "Lookback must be between 252 and 5040 trading days." };
  }

  const payload: ForecastCreate = {
    method,
    horizon_months: horizonMonths,
    n_simulations: nSimulations,
    lookback_days: lookbackDays,
  };
  if (asOfDate) payload.as_of_date = asOfDate;
  if (benchmarkTicker.trim()) payload.benchmark_ticker = benchmarkTicker.trim().toUpperCase();
  if (randomSeed.trim()) {
    const seed = Number(randomSeed);
    if (!Number.isInteger(seed) || seed < 0) {
      return { error: "Random seed must be a non-negative integer." };
    }
    payload.random_seed = seed;
  }
  return { payload };
}

function NumberField({
  label,
  hint,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <Field label={label} hint={hint}>
      <Input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </Field>
  );
}
