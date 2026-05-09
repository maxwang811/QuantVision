import { z } from "zod";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ApiError = z.object({
  error: z.object({ code: z.string(), message: z.string() }),
});

export class ApiRequestError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let code = "http_error";
    let message = res.statusText;
    try {
      const body = ApiError.parse(await res.json());
      code = body.error.code;
      message = body.error.message;
    } catch {
      // body wasn't a structured error; use status text
    }
    throw new ApiRequestError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const Asset = z.object({
  id: z.string().uuid(),
  ticker: z.string(),
  name: z.string().nullable(),
  asset_class: z.string(),
  exchange: z.string().nullable(),
  currency: z.string(),
  created_at: z.string(),
});
export type Asset = z.infer<typeof Asset>;

export const PricePoint = z.object({
  date: z.string(),
  open: z.number().nullable().optional(),
  high: z.number().nullable().optional(),
  low: z.number().nullable().optional(),
  close: z.number().nullable().optional(),
  adj_close: z.number(),
  volume: z.number().nullable().optional(),
});
export type PricePoint = z.infer<typeof PricePoint>;

export const PriceSeries = z.object({
  ticker: z.string(),
  points: z.array(PricePoint),
});
export type PriceSeries = z.infer<typeof PriceSeries>;

export const Health = z.object({ status: z.string(), db: z.boolean() });
export type Health = z.infer<typeof Health>;

export const StrategyName = z.enum(["buy_and_hold", "monthly_rebalance", "momentum", "ml_ranking"]);
export type StrategyName = z.infer<typeof StrategyName>;

export const SelectedModel = z.enum(["logistic_regression", "xgboost"]);
export type SelectedModel = z.infer<typeof SelectedModel>;

export const BacktestCreate = z.object({
  name: z.string().max(128).nullable().optional(),
  strategy: StrategyName,
  tickers: z.array(z.string()).min(1).max(50),
  weights: z.array(z.number()).min(1).max(50),
  initial_cash: z.number().positive(),
  start_date: z.string(),
  end_date: z.string(),
  transaction_cost_bps: z.number().int().min(0).max(1000),
  benchmark_ticker: z.string().max(16).nullable().optional(),
  strategy_params: z.record(z.unknown()).optional(),
});
export type BacktestCreate = z.infer<typeof BacktestCreate>;

export const BacktestOut = z.object({
  id: z.string().uuid(),
  name: z.string().nullable(),
  strategy: z.string(),
  status: z.string(),
  initial_cash: z.number(),
  final_value: z.number().nullable(),
  total_return: z.number().nullable(),
  annualized_return: z.number().nullable(),
  volatility: z.number().nullable(),
  sharpe_ratio: z.number().nullable(),
  max_drawdown: z.number().nullable(),
  benchmark_total_return: z.number().nullable(),
  benchmark_annualized_return: z.number().nullable(),
  alpha: z.number().nullable(),
  beta: z.number().nullable(),
  information_ratio: z.number().nullable(),
  tracking_error: z.number().nullable(),
  start_date: z.string(),
  end_date: z.string(),
  transaction_cost_bps: z.number(),
  benchmark_ticker: z.string().nullable(),
  model_run_id: z.string().uuid().nullable().optional(),
  error_message: z.string().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});
export type BacktestOut = z.infer<typeof BacktestOut>;

export const ModelRunCreate = z.object({
  name: z.string().max(128).nullable().optional(),
  tickers: z.array(z.string()).min(1).max(50),
  benchmark_ticker: z.string().max(16).optional(),
  start_date: z.string(),
  end_date: z.string(),
  label_horizon_days: z.number().int().min(5).max(126).optional(),
  training_lookback_days: z.number().int().min(126).max(5040).optional(),
  selected_model: SelectedModel.optional(),
  random_seed: z.number().int().min(0).optional(),
});
export type ModelRunCreate = z.infer<typeof ModelRunCreate>;

export const ModelRunOut = z.object({
  id: z.string().uuid(),
  name: z.string().nullable(),
  tickers: z.array(z.string()),
  benchmark_ticker: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  label_horizon_days: z.number(),
  training_lookback_days: z.number(),
  selected_model: z.string(),
  params: z.record(z.unknown()),
  metrics: z.record(z.unknown()).nullable(),
  status: z.string(),
  error_message: z.string().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});
export type ModelRunOut = z.infer<typeof ModelRunOut>;

export const ModelPredictionOut = z.object({
  id: z.string().uuid(),
  date: z.string(),
  ticker: z.string(),
  model_name: z.string(),
  score: z.number(),
  rank: z.number(),
  label: z.number().nullable(),
  forward_return: z.number().nullable(),
  benchmark_forward_return: z.number().nullable(),
});
export type ModelPredictionOut = z.infer<typeof ModelPredictionOut>;

export const ModelPredictionsOut = z.object({
  model_run_id: z.string().uuid(),
  predictions: z.array(ModelPredictionOut),
});
export type ModelPredictionsOut = z.infer<typeof ModelPredictionsOut>;

export const TradeOut = z.object({
  id: z.string().uuid(),
  date: z.string(),
  ticker: z.string(),
  side: z.string(),
  quantity: z.number(),
  price: z.number(),
  transaction_cost: z.number(),
  notional: z.number(),
});
export type TradeOut = z.infer<typeof TradeOut>;

export const BacktestTradesOut = z.object({
  backtest_id: z.string().uuid(),
  trades: z.array(TradeOut),
});
export type BacktestTradesOut = z.infer<typeof BacktestTradesOut>;

export const PortfolioValuePoint = z.object({
  date: z.string(),
  cash: z.number(),
  holdings_value: z.number(),
  total_value: z.number(),
});
export type PortfolioValuePoint = z.infer<typeof PortfolioValuePoint>;

export const BenchmarkPoint = z.object({
  date: z.string(),
  value: z.number(),
});
export type BenchmarkPoint = z.infer<typeof BenchmarkPoint>;

export const BacktestEquityCurveOut = z.object({
  backtest_id: z.string().uuid(),
  points: z.array(PortfolioValuePoint),
  benchmark: z.array(BenchmarkPoint).nullable().optional(),
  benchmark_ticker: z.string().nullable().optional(),
});
export type BacktestEquityCurveOut = z.infer<typeof BacktestEquityCurveOut>;

export const ForecastMethod = z.enum(["monte_carlo", "bootstrap", "ml_drift"]);
export type ForecastMethod = z.infer<typeof ForecastMethod>;

export const ForecastCreate = z.object({
  name: z.string().max(128).nullable().optional(),
  method: ForecastMethod,
  tickers: z.array(z.string()).min(1).max(50).optional(),
  weights: z.array(z.number()).min(1).max(50).optional(),
  initial_value: z.number().positive().optional(),
  from_backtest_id: z.string().uuid().optional(),
  horizon_months: z.number().int().min(1).max(120),
  n_simulations: z.number().int().min(100).max(50_000),
  lookback_days: z.number().int().min(252).max(5040),
  as_of_date: z.string().nullable().optional(),
  benchmark_ticker: z.string().max(16).nullable().optional(),
  random_seed: z.number().int().min(0).optional(),
});
export type ForecastCreate = z.infer<typeof ForecastCreate>;

export const ForecastOut = z.object({
  id: z.string().uuid(),
  name: z.string().nullable(),
  method: z.string(),
  status: z.string(),
  initial_value: z.number(),
  horizon_months: z.number(),
  horizon_trading_days: z.number(),
  n_simulations: z.number(),
  as_of_date: z.string(),
  lookback_start: z.string(),
  lookback_end: z.string(),
  benchmark_ticker: z.string().nullable(),
  from_backtest_id: z.string().uuid().nullable(),
  random_seed: z.number(),
  tickers: z.array(z.string()).nullable(),
  weights: z.array(z.number()).nullable(),
  expected_value: z.number().nullable(),
  median_value: z.number().nullable(),
  p5_value: z.number().nullable(),
  p10_value: z.number().nullable(),
  p25_value: z.number().nullable(),
  p75_value: z.number().nullable(),
  p90_value: z.number().nullable(),
  p95_value: z.number().nullable(),
  probability_of_loss: z.number().nullable(),
  probability_beat_benchmark: z.number().nullable(),
  annualized_volatility: z.number().nullable(),
  expected_return: z.number().nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});
export type ForecastOut = z.infer<typeof ForecastOut>;

export const ForecastPathPoint = z.object({
  index: z.number(),
  rank_label: z.string().nullable(),
  values: z.array(z.number()),
});
export type ForecastPathPoint = z.infer<typeof ForecastPathPoint>;

export const ForecastPathsOut = z.object({
  forecast_id: z.string().uuid(),
  as_of_date: z.string(),
  horizon_trading_days: z.number(),
  initial_value: z.number(),
  step_dates: z.array(z.string()),
  paths: z.array(ForecastPathPoint),
});
export type ForecastPathsOut = z.infer<typeof ForecastPathsOut>;

export const ForecastDistributionBin = z.object({
  index: z.number(),
  lower: z.number(),
  upper: z.number(),
  count: z.number(),
});
export type ForecastDistributionBin = z.infer<typeof ForecastDistributionBin>;

export const ForecastPercentiles = z.object({
  p5: z.number(),
  p10: z.number(),
  p25: z.number(),
  p50: z.number(),
  p75: z.number(),
  p90: z.number(),
  p95: z.number(),
});
export type ForecastPercentiles = z.infer<typeof ForecastPercentiles>;

export const ForecastDistributionOut = z.object({
  forecast_id: z.string().uuid(),
  initial_value: z.number(),
  bin_count: z.number(),
  bins: z.array(ForecastDistributionBin),
  percentiles: ForecastPercentiles,
});
export type ForecastDistributionOut = z.infer<typeof ForecastDistributionOut>;

export const api = {
  health: () => apiFetch<Health>("/api/health").then((d) => Health.parse(d)),
  searchAssets: (q: string, limit = 20) =>
    apiFetch<unknown>(`/api/assets?q=${encodeURIComponent(q)}&limit=${limit}`).then((d) =>
      z.array(Asset).parse(d),
    ),
  prices: (ticker: string, opts: { start?: string; end?: string } = {}) => {
    const qs = new URLSearchParams();
    if (opts.start) qs.set("start", opts.start);
    if (opts.end) qs.set("end", opts.end);
    const path = `/api/prices/${encodeURIComponent(ticker)}${qs.toString() ? `?${qs}` : ""}`;
    return apiFetch<unknown>(path).then((d) => PriceSeries.parse(d));
  },
  runBacktest: (payload: BacktestCreate) =>
    apiFetch<unknown>("/api/backtests", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((d) => BacktestOut.parse(d)),
  getBacktest: (id: string) =>
    apiFetch<unknown>(`/api/backtests/${encodeURIComponent(id)}`).then((d) => BacktestOut.parse(d)),
  getBacktestTrades: (id: string) =>
    apiFetch<unknown>(`/api/backtests/${encodeURIComponent(id)}/trades`).then((d) =>
      BacktestTradesOut.parse(d),
    ),
  getBacktestEquityCurve: (id: string) =>
    apiFetch<unknown>(`/api/backtests/${encodeURIComponent(id)}/portfolio_values`).then((d) =>
      BacktestEquityCurveOut.parse(d),
    ),
  createModelRun: (payload: ModelRunCreate) =>
    apiFetch<unknown>("/api/model-runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((d) => ModelRunOut.parse(d)),
  getModelRun: (id: string) =>
    apiFetch<unknown>(`/api/model-runs/${encodeURIComponent(id)}`).then((d) =>
      ModelRunOut.parse(d),
    ),
  getModelPredictions: (id: string, modelName?: SelectedModel) => {
    const qs = modelName ? `?model_name=${encodeURIComponent(modelName)}` : "";
    return apiFetch<unknown>(`/api/model-runs/${encodeURIComponent(id)}/predictions${qs}`).then(
      (d) => ModelPredictionsOut.parse(d),
    );
  },
  runForecast: (payload: ForecastCreate) =>
    apiFetch<unknown>("/api/forecasts", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((d) => ForecastOut.parse(d)),
  getForecast: (id: string) =>
    apiFetch<unknown>(`/api/forecasts/${encodeURIComponent(id)}`).then((d) =>
      ForecastOut.parse(d),
    ),
  getForecastPaths: (id: string) =>
    apiFetch<unknown>(`/api/forecasts/${encodeURIComponent(id)}/paths`).then((d) =>
      ForecastPathsOut.parse(d),
    ),
  getForecastDistribution: (id: string) =>
    apiFetch<unknown>(`/api/forecasts/${encodeURIComponent(id)}/distribution`).then((d) =>
      ForecastDistributionOut.parse(d),
    ),
};
