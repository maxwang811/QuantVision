"use client";

import { PortfolioWeightEditor, type PortfolioRow } from "@/components/backtest/PortfolioWeightEditor";
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

const METHODS: { value: ForecastMethod; label: string; detail: string }[] = [
  {
    value: "monte_carlo",
    label: "Monte Carlo",
    detail: "Parametric simulation using historical drift, volatility, and covariance.",
  },
  {
    value: "bootstrap",
    label: "Bootstrap",
    detail: "Historical return sampling that preserves same-day cross-asset moves.",
  },
  {
    value: "ml_drift",
    label: "ML drift",
    detail: "Ridge-based drift adjustment with Monte Carlo covariance.",
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
    <form onSubmit={submit} className="space-y-6 rounded-lg border border-border p-5">
      <Field label="Run name (optional)">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={128}
          placeholder="12 month Monte Carlo baseline"
          className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
        />
      </Field>

      <div className="space-y-2">
        <div className="text-sm font-semibold uppercase tracking-wide text-muted">
          Forecast source
        </div>
        <div className="inline-flex rounded-md border border-border p-1">
          <SourceButton active={mode === "manual"} onClick={() => setMode("manual")}>
            Manual portfolio
          </SourceButton>
          <SourceButton active={mode === "backtest"} onClick={() => setMode("backtest")}>
            From backtest
          </SourceButton>
        </div>
      </div>

      {mode === "manual" ? (
        <PortfolioWeightEditor rows={rows} onChange={setRows} />
      ) : (
        <Field label="Completed backtest id">
          <input
            type="text"
            value={fromBacktestId}
            onChange={(e) => setFromBacktestId(e.target.value)}
            placeholder="00000000-0000-0000-0000-000000000000"
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm font-mono text-fg outline-none focus:border-accent"
          />
        </Field>
      )}

      <div className="space-y-2">
        <div className="text-sm font-semibold uppercase tracking-wide text-muted">
          Forecast method
        </div>
        <div className="grid gap-2 md:grid-cols-3">
          {METHODS.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setMethod(item.value)}
              className={`rounded-md border p-3 text-left transition-colors ${
                method === item.value
                  ? "border-accent bg-accent/10 text-fg"
                  : "border-border text-muted hover:border-accent hover:text-fg"
              }`}
            >
              <div className="text-sm font-semibold">{item.label}</div>
              <div className="mt-1 text-xs leading-5">{item.detail}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {mode === "manual" && (
          <Field label="Initial value">
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">
                $
              </span>
              <input
                type="number"
                min={0}
                step={100}
                value={initialValue}
                onChange={(e) => setInitialValue(Number(e.target.value))}
                className="w-full rounded-md border border-border bg-bg pl-7 pr-3 py-2 text-sm text-fg outline-none focus:border-accent"
              />
            </div>
          </Field>
        )}

        <NumberField
          label="Horizon months"
          min={1}
          max={120}
          step={1}
          value={horizonMonths}
          onChange={setHorizonMonths}
        />
        <NumberField
          label="Simulations"
          min={100}
          max={50_000}
          step={100}
          value={nSimulations}
          onChange={setNSimulations}
        />
        <NumberField
          label="Lookback trading days"
          min={252}
          max={5040}
          step={21}
          value={lookbackDays}
          onChange={setLookbackDays}
        />
        <Field label="As-of date (optional)">
          <input
            type="date"
            value={asOfDate}
            onChange={(e) => setAsOfDate(e.target.value)}
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          />
        </Field>
        <Field label="Benchmark ticker (optional)">
          <input
            type="text"
            value={benchmarkTicker}
            onChange={(e) => setBenchmarkTicker(e.target.value)}
            placeholder="SPY"
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm font-mono text-fg outline-none focus:border-accent"
          />
        </Field>
        <Field label="Random seed (optional)">
          <input
            type="number"
            min={0}
            step={1}
            value={randomSeed}
            onChange={(e) => setRandomSeed(e.target.value)}
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          />
        </Field>
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
        <button
          type="submit"
          disabled={!payload || mutation.isPending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {mutation.isPending ? "Running..." : "Run Forecast"}
        </button>
        {localError && <span className="text-sm text-negative">{localError}</span>}
        {!localError && apiError && <span className="text-sm text-negative">{apiError}</span>}
      </div>
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

function SourceButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
        active ? "bg-accent text-white" : "text-muted hover:text-fg"
      }`}
    >
      {children}
    </button>
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
  onChange: (value: number) => void;
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}
