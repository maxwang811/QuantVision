"use client";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardSection } from "@/components/ui/Card";
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
  const [shortWindow, setShortWindow] = useState<number>(50);
  const [longWindow, setLongWindow] = useState<number>(200);

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
        shortWindow,
        longWindow,
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
      shortWindow,
      longWindow,
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
      <Card variant="elevated">
        <CardHeader
          title="Portfolio & Strategy"
          description="Select assets, assign weights, and choose how the portfolio is traded."
          size="large"
        />
        
        <CardSection divided className="space-y-6">
          {/* Run name */}
          <Field label="Run name" hint="Optional - helps identify this backtest later">
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={128}
              placeholder="e.g., Monthly rebalance baseline"
            />
          </Field>

          {/* Portfolio weights */}
          <PortfolioWeightEditor rows={rows} onChange={setRows} />
        </CardSection>

        <CardSection divided className="space-y-6">
          {/* Strategy selection */}
          <StrategySelector value={strategy} onChange={setStrategy} />
          
          {/* Strategy-specific parameters */}
          {strategy === "ma_crossover" && (
            <div className="grid gap-4 rounded-xl border border-border bg-surface-2/50 p-4 sm:grid-cols-2">
              <NumberField
                label="Short MA window"
                hint="Trading days"
                min={2}
                max={252}
                step={1}
                value={shortWindow}
                onChange={setShortWindow}
              />
              <NumberField
                label="Long MA window"
                hint="Trading days"
                min={2}
                max={252}
                step={1}
                value={longWindow}
                onChange={setLongWindow}
              />
            </div>
          )}
          
          {rankingStrategy && (
            <div className="grid gap-4 rounded-xl border border-border bg-surface-2/50 p-4 sm:grid-cols-2 lg:grid-cols-4">
              <NumberField
                label="Top N"
                hint="Assets to hold"
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
                    hint="Days"
                    min={126}
                    max={5040}
                    step={21}
                    value={trainingLookbackDays}
                    onChange={setTrainingLookbackDays}
                  />
                  <NumberField
                    label="Label horizon"
                    hint="Days"
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
        </CardSection>

        <CardSection divided className="space-y-6">
          <h3 className="text-sm font-medium text-fg">Run Parameters</h3>
          
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Initial capital">
              <Input
                type="number"
                min={0}
                step={100}
                value={initialCash}
                onChange={(e) => setInitialCash(Number(e.target.value))}
                adornmentLeft="$"
              />
            </Field>

            <Field label="Transaction cost" hint="Basis points">
              <Input
                type="number"
                min={0}
                max={1000}
                step={1}
                value={transactionCostBps}
                onChange={(e) => setTransactionCostBps(Number(e.target.value))}
                adornmentRight="bps"
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
              {mutation.isPending ? "Running backtest..." : "Run Backtest"}
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
