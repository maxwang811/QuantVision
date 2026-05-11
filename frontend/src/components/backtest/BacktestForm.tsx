"use client";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input, Select } from "@/components/ui/Input";
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
    <form onSubmit={submit} className="space-y-6">
      <Card>
        <CardHeader
          eyebrow="Step 1"
          title="Portfolio"
          description="Pick tickers and assign target weights. They must sum to 100%."
        />
        <div className="mt-5 space-y-5">
          <Field label="Run name (optional)">
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={128}
              placeholder="Monthly rebalance baseline"
            />
          </Field>
          <PortfolioWeightEditor rows={rows} onChange={setRows} />
        </div>
      </Card>

      <Card>
        <CardHeader
          eyebrow="Step 2"
          title="Strategy"
          description="Choose how the portfolio is traded over the run."
        />
        <div className="mt-5 space-y-5">
          <StrategySelector value={strategy} onChange={setStrategy} />
          {rankingStrategy && (
            <div className="grid gap-4 rounded-lg border border-border bg-surface-2/40 p-4 sm:grid-cols-2 lg:grid-cols-4">
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
                    <Select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value as SelectedModel)}
                    >
                      <option value="xgboost">XGBoost</option>
                      <option value="logistic_regression">Logistic regression</option>
                    </Select>
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
        </div>
      </Card>

      <Card>
        <CardHeader
          eyebrow="Step 3"
          title="Run parameters"
          description="Capital, date range, transaction cost, and benchmark."
        />
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <Field label="Initial cash">
            <Input
              type="number"
              min={0}
              step={100}
              value={initialCash}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              adornmentLeft="$"
            />
          </Field>

          <Field label="Transaction cost (bps)">
            <Input
              type="number"
              min={0}
              max={1000}
              step={1}
              value={transactionCostBps}
              onChange={(e) => setTransactionCostBps(Number(e.target.value))}
            />
          </Field>

          <Field label="Start date">
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </Field>

          <Field label="End date">
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </Field>

          <Field label="Benchmark ticker (optional)">
            <Input
              type="text"
              value={benchmarkTicker}
              onChange={(e) => setBenchmarkTicker(e.target.value)}
              placeholder="SPY"
              className="font-mono"
            />
          </Field>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-border pt-5">
          <Button type="submit" disabled={!payload || mutation.isPending} size="lg">
            {mutation.isPending ? "Running…" : "Run Backtest"}
          </Button>
          {localError && <span className="text-sm text-negative">{localError}</span>}
          {!localError && apiError && <span className="text-sm text-negative">{apiError}</span>}
        </div>
      </Card>
    </form>
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
