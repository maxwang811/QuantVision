import type { BacktestCreate, SelectedModel, StrategyName } from "@/lib/api";
import type { PortfolioRow } from "./PortfolioWeightEditor";

export interface ValidateInput {
  rows: PortfolioRow[];
  name: string;
  strategy: StrategyName;
  initialCash: number;
  startDate: string;
  endDate: string;
  transactionCostBps: number;
  benchmarkTicker: string;
  topN: number;
  selectedModel: SelectedModel;
  trainingLookbackDays: number;
  labelHorizonDays: number;
  shortWindow: number;
  longWindow: number;
}

export interface ValidateOutput {
  localError: string | null;
  payload: BacktestCreate | null;
}

/**
 * Pure validator for the backtest form. Extracted from BacktestForm so it can
 * be unit-tested without a React tree or QueryClientProvider.
 */
export function validateBacktestPayload(input: ValidateInput): ValidateOutput {
  const {
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
  } = input;

  const cleanRows = rows.filter((r) => r.ticker.trim().length > 0);
  if (cleanRows.length === 0) {
    return { localError: "Add at least one ticker.", payload: null };
  }
  const rankingStrategy = strategy === "momentum" || strategy === "ml_ranking";
  const total = cleanRows.reduce((s, r) => s + r.weightPct, 0);
  if (!rankingStrategy) {
    if (Math.abs(total - 100) > 0.01) {
      return {
        localError: `Weights must sum to 100% (currently ${total.toFixed(2)}%).`,
        payload: null,
      };
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
    if (
      !Number.isInteger(trainingLookbackDays) ||
      trainingLookbackDays < 126 ||
      trainingLookbackDays > 5040
    ) {
      return {
        localError: "Training lookback must be between 126 and 5040 trading days.",
        payload: null,
      };
    }
    if (
      !Number.isInteger(labelHorizonDays) ||
      labelHorizonDays < 5 ||
      labelHorizonDays > 126
    ) {
      return {
        localError: "Label horizon must be between 5 and 126 trading days.",
        payload: null,
      };
    }
  }
  if (strategy === "ma_crossover") {
    if (!Number.isInteger(shortWindow) || shortWindow < 2 || shortWindow > 252) {
      return {
        localError: "Short window must be an integer between 2 and 252.",
        payload: null,
      };
    }
    if (!Number.isInteger(longWindow) || longWindow < 2 || longWindow > 252) {
      return {
        localError: "Long window must be an integer between 2 and 252.",
        payload: null,
      };
    }
    if (shortWindow >= longWindow) {
      return {
        localError: "Short window must be less than long window.",
        payload: null,
      };
    }
  }
  const weights = rankingStrategy
    ? cleanRows.map(() => 1 / cleanRows.length)
    : cleanRows.map((r) => r.weightPct / 100);
  const effectiveTopN = Math.min(topN, cleanRows.length);
  const built: BacktestCreate = {
    name: name.trim() || null,
    strategy,
    tickers: cleanRows.map((r) => r.ticker.toUpperCase()),
    weights,
    initial_cash: initialCash,
    start_date: startDate,
    end_date: endDate,
    transaction_cost_bps: transactionCostBps,
    benchmark_ticker: benchmarkTicker.trim()
      ? benchmarkTicker.trim().toUpperCase()
      : null,
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
  if (strategy === "ma_crossover") {
    built.strategy_params = {
      short_window: shortWindow,
      long_window: longWindow,
    };
  }
  return { localError: null, payload: built };
}
