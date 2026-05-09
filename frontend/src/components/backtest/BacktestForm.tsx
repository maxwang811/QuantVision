"use client";

import {
  ApiRequestError,
  api,
  type BacktestCreate,
  type BacktestOut,
  type SelectedModel,
  type StrategyName,
} from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PortfolioWeightEditor, type PortfolioRow } from "./PortfolioWeightEditor";
import { StrategySelector } from "./StrategySelector";

const DEFAULT_ROWS: PortfolioRow[] = [
  { ticker: "SPY", weightPct: 50 },
  { ticker: "AAPL", weightPct: 25 },
  { ticker: "MSFT", weightPct: 25 },
];

interface Props {
  onSuccess: (bt: BacktestOut) => void;
}

export function BacktestForm({ onSuccess }: Props) {
  const [rows, setRows] = useState<PortfolioRow[]>(DEFAULT_ROWS);
  const [strategy, setStrategy] = useState<StrategyName>("monthly_rebalance");
  const [initialCash, setInitialCash] = useState<number>(10_000);
  const [startDate, setStartDate] = useState<string>("2020-01-01");
  const [endDate, setEndDate] = useState<string>("2024-01-01");
  const [transactionCostBps, setTransactionCostBps] = useState<number>(10);
  const [benchmarkTicker, setBenchmarkTicker] = useState<string>("SPY");
  const [topN, setTopN] = useState<number>(3);
  const [selectedModel, setSelectedModel] = useState<SelectedModel>("xgboost");
  const [trainingLookbackDays, setTrainingLookbackDays] = useState<number>(756);
  const [labelHorizonDays, setLabelHorizonDays] = useState<number>(20);

  const { localError, payload } = useMemo(() => {
    const cleanRows = rows.filter((r) => r.ticker.trim().length > 0);
    if (cleanRows.length === 0) {
      return { localError: "Add at least one ticker.", payload: null };
    }
    const rankingStrategy = strategy === "momentum" || strategy === "ml_ranking";
    const total = cleanRows.reduce((s, r) => s + r.weightPct, 0);
    if (!rankingStrategy) {
      if (Math.abs(total - 100) > 0.01) {
        return { localError: `Weights must sum to 100% (currently ${total.toFixed(2)}%).`, payload: null };
      }
      if (cleanRows.some((r) => r.weightPct < 0)) {
        return { localError: "Weights must be non-negative.", payload: null };
      }
    }
    if (!(initialCash > 0)) {
      return { localError: "Initial cash must be positive.", payload: null };
    }
    if (!startDate || !endDate) {
      return { localError: "Pick start and end dates.", payload: null };
    }
    if (startDate >= endDate) {
      return { localError: "End date must be after start date.", payload: null };
    }
    const seen = new Set<string>();
    for (const r of cleanRows) {
      const t = r.ticker.toUpperCase();
      if (seen.has(t)) return { localError: `Duplicate ticker: ${t}`, payload: null };
      seen.add(t);
    }
    if (rankingStrategy) {
      if (!Number.isInteger(topN) || topN < 1) {
        return { localError: "Top N must be at least 1.", payload: null };
      }
    }
    if (strategy === "ml_ranking") {
      if (!Number.isInteger(trainingLookbackDays) || trainingLookbackDays < 126 || trainingLookbackDays > 5040) {
        return { localError: "Training lookback must be between 126 and 5040 trading days.", payload: null };
      }
      if (!Number.isInteger(labelHorizonDays) || labelHorizonDays < 5 || labelHorizonDays > 126) {
        return { localError: "Label horizon must be between 5 and 126 trading days.", payload: null };
      }
    }
    const weights = rankingStrategy
      ? cleanRows.map(() => 1 / cleanRows.length)
      : cleanRows.map((r) => r.weightPct / 100);
    const effectiveTopN = Math.min(topN, cleanRows.length);
    const built: BacktestCreate = {
      strategy,
      tickers: cleanRows.map((r) => r.ticker.toUpperCase()),
      weights,
      initial_cash: initialCash,
      start_date: startDate,
      end_date: endDate,
      transaction_cost_bps: transactionCostBps,
      benchmark_ticker: benchmarkTicker.trim() ? benchmarkTicker.trim().toUpperCase() : null,
    };
    if (strategy === "momentum") {
      built.strategy_params = {
        top_n: effectiveTopN,
        rebalance_frequency: "monthly",
        lookback_days: 63,
      };
    }
    if (strategy === "ml_ranking") {
      built.strategy_params = {
        top_n: effectiveTopN,
        rebalance_frequency: "monthly",
        selected_model: selectedModel,
        training_lookback_days: trainingLookbackDays,
        label_horizon_days: labelHorizonDays,
      };
    }
    return { localError: null, payload: built };
  }, [
    rows,
    strategy,
    initialCash,
    startDate,
    endDate,
    transactionCostBps,
    benchmarkTicker,
    topN,
    selectedModel,
    trainingLookbackDays,
    labelHorizonDays,
  ]);

  const mutation = useMutation({
    mutationFn: (p: BacktestCreate) => api.runBacktest(p),
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
  const rankingStrategy = strategy === "momentum" || strategy === "ml_ranking";

  return (
    <form onSubmit={submit} className="space-y-6 rounded-lg border border-border p-5">
      <PortfolioWeightEditor rows={rows} onChange={setRows} />

      <StrategySelector value={strategy} onChange={setStrategy} />

      {rankingStrategy && (
        <div className="grid gap-4 rounded-md border border-border/70 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <NumberField
            label="Top N"
            min={1}
            max={Math.max(1, rows.filter((r) => r.ticker.trim()).length)}
            step={1}
            value={topN}
            onChange={setTopN}
          />
          {strategy === "ml_ranking" && (
            <>
              <Field label="Model">
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value as SelectedModel)}
                  className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
                >
                  <option value="xgboost">XGBoost</option>
                  <option value="logistic_regression">Logistic regression</option>
                </select>
              </Field>
              <NumberField
                label="Training lookback"
                min={126}
                max={5040}
                step={21}
                value={trainingLookbackDays}
                onChange={setTrainingLookbackDays}
              />
              <NumberField
                label="Label horizon"
                min={5}
                max={126}
                step={1}
                value={labelHorizonDays}
                onChange={setLabelHorizonDays}
              />
            </>
          )}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Initial cash">
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">
              $
            </span>
            <input
              type="number"
              min={0}
              step={100}
              value={initialCash}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              className="w-full rounded-md border border-border bg-bg pl-7 pr-3 py-2 text-sm text-fg outline-none focus:border-accent"
            />
          </div>
        </Field>

        <Field label="Transaction cost (bps)">
          <input
            type="number"
            min={0}
            max={1000}
            step={1}
            value={transactionCostBps}
            onChange={(e) => setTransactionCostBps(Number(e.target.value))}
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          />
        </Field>

        <Field label="Start date">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          />
        </Field>

        <Field label="End date">
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
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
      </div>

      <div className="flex items-center gap-3 border-t border-border pt-4">
        <button
          type="submit"
          disabled={!payload || mutation.isPending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {mutation.isPending ? "Running…" : "Run Backtest"}
        </button>
        {localError && <span className="text-sm text-negative">{localError}</span>}
        {!localError && apiError && <span className="text-sm text-negative">{apiError}</span>}
      </div>
    </form>
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
