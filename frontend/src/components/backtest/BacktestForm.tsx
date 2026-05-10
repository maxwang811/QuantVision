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
import { useEffect, useMemo, useState } from "react";
import { PortfolioWeightEditor, type PortfolioRow } from "./PortfolioWeightEditor";
import { StrategySelector } from "./StrategySelector";
import { validateBacktestPayload } from "./validateBacktest";

const DEFAULT_ROWS: PortfolioRow[] = [
  { ticker: "SPY", weightPct: 50 },
  { ticker: "AAPL", weightPct: 25 },
  { ticker: "MSFT", weightPct: 25 },
];

interface Props {
  onSuccess: (bt: BacktestOut) => void;
  /** When set, the form's portfolio rows are reset to this whenever the prop changes
   *  (used by the optimizer panel to populate weights). */
  defaultRows?: PortfolioRow[];
}

export function BacktestForm({ onSuccess, defaultRows }: Props) {
  const [rows, setRows] = useState<PortfolioRow[]>(defaultRows ?? DEFAULT_ROWS);

  useEffect(() => {
    if (defaultRows && defaultRows.length > 0) {
      setRows(defaultRows);
    }
  }, [defaultRows]);
  const [name, setName] = useState<string>("");
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

  const { localError, payload } = useMemo(
    () =>
      validateBacktestPayload({
        rows,
        name,
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
      }),
    [
      rows,
      name,
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
    ],
  );

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
      <Field label="Run name (optional)">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={128}
          placeholder="Monthly rebalance baseline"
          className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-accent"
        />
      </Field>

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
