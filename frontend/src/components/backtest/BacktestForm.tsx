"use client";

import { ApiRequestError, api, type BacktestCreate, type BacktestOut, type StrategyName } from "@/lib/api";
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

  const { localError, payload } = useMemo(() => {
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
    const built: BacktestCreate = {
      strategy,
      tickers: cleanRows.map((r) => r.ticker.toUpperCase()),
      weights: cleanRows.map((r) => r.weightPct / 100),
      initial_cash: initialCash,
      start_date: startDate,
      end_date: endDate,
      transaction_cost_bps: transactionCostBps,
      benchmark_ticker: benchmarkTicker.trim() ? benchmarkTicker.trim().toUpperCase() : null,
    };
    return { localError: null, payload: built };
  }, [rows, strategy, initialCash, startDate, endDate, transactionCostBps, benchmarkTicker]);

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

  return (
    <form onSubmit={submit} className="space-y-6 rounded-lg border border-border p-5">
      <PortfolioWeightEditor rows={rows} onChange={setRows} />

      <StrategySelector value={strategy} onChange={setStrategy} />

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Initial cash">
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">
              $
            </span>
            <input
              type="number"
              min={1}
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
