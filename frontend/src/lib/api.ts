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

export const StrategyName = z.enum(["buy_and_hold", "monthly_rebalance"]);
export type StrategyName = z.infer<typeof StrategyName>;

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
  error_message: z.string().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});
export type BacktestOut = z.infer<typeof BacktestOut>;

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
};
