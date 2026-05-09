# Known Limitations

QuantVision is a research/educational platform. The simulations are bound by several modelling assumptions documented here. Read this before drawing real-money conclusions from any output.

## Data limitations

**Survivorship bias.** yfinance only returns currently-listed tickers. Historical universes don't include companies that were delisted (bankruptcies, mergers, etc.), which biases historical returns upward. A momentum strategy backtested on the current S&P 500 will look better than the same strategy run in real time. We surface this with a tooltip on results pages.

**yfinance flakiness.** Yahoo Finance occasionally returns empty or partial results. We retry with exponential backoff and cache aggressively in Postgres, but recent data may be stale. The UI displays an "as of" timestamp.

**Adjusted close only.** All return calculations use `adj_close`, which already accounts for splits and dividends. We do not model dividends as separate cash flows.

## Backtesting limitations

**Simplistic transaction model.** No bid-ask spread, no market impact, no borrow cost (so no real shorting). Costs are modeled as a flat basis-point haircut on notional (`transaction_cost_bps`); no separate slippage model in Stage 2. Real-world execution costs scale with order size, liquidity, and market regime.

**T+1 execution.** Signals fire at close[T]; orders execute at close[T+1]. This is the standard convention but real markets execute at the open or via VWAP/TWAP algorithms. Orders queued on the final trading day cannot fill (no T+1 within the window) and are dropped with a warning.

**Forward-fill on missing prices.** When a ticker has no bar on a given trading day (holiday, halt, partial yfinance coverage), the engine forward-fills from the most recent prior `adj_close`. If a ticker has no price *anywhere* before `start_date`, the runner rejects the request with `insufficient_coverage`. Prices are loaded with a 14 calendar-day pre-buffer so day-0 fills always have a source.

**Fractional shares.** The engine allows fractional shares so target-weight allocations are exact. Real markets often don't; this is a known simplification.

**Adjusted close only.** All signals, fills, and equity calculations use `adj_close`, which already accounts for splits and dividends. Dividends are not modeled as separate cash flows.

**No corporate actions besides splits/dividends.** Mergers, tender offers, spin-offs, ticker changes — all ignored.

**Synchronous engine (Stage 2).** `POST /api/backtests` runs the engine inline and blocks the request thread. A 5y × 5-ticker run is sub-second; longer runs will block proportionally. A job queue is deferred to Stage 7.

**Look-ahead bias.** The engine guards against look-ahead by slicing `BacktestContext.prices_so_far[ticker]` to dates ≤ `ctx.date` on every iteration; combined with the T+1 fill rule, a strategy cannot trade on data it hasn't yet seen. A `PeekingStrategy` canary test asserts the slice invariant. But subtle leakage in future feature engineering is always possible; flag suspicious results.

## Forecasting limitations

**Monte Carlo normality assumption.** The parametric MVN method assumes returns are jointly normal. Real returns have fat tails (kurtosis), skew, and volatility clustering. The MVN method understates tail risk. Prefer the **bootstrap** method, which preserves empirical distributions including fat tails and joint dependence.

**Static expected returns.** All methods estimate μ and Σ from a fixed lookback window. Real markets exhibit regime shifts. Long horizons (>3 years) are particularly sensitive to this.

**No rebalancing in the forecast.** Forecasts hold initial weights. A real investor rebalancing introduces a different return path. Future work.

## ML limitations

**Walk-forward, but not bulletproof.** We split train/test by time and require `t + 20 <= train_cutoff` for label availability. But feature engineering is the largest leakage surface; we test for it but cannot guarantee zero leakage.

**Static label horizon.** 20 trading days only. Multi-horizon prediction is future work.

**Model staleness.** Walk-forward training is manual. If you don't retrain, predictions stop covering recent dates.

## System limitations

**No authentication.** The MVP runs with rate-limiting only. All experiments are global. Auth is V2.

**Single worker.** The job runner is in-process; auto-scaling beyond 1 machine breaks the worker pool. Set `min_machines_running=1, auto_scale=off` in production until migrating to Celery.

**Free-tier Postgres.** Neon free tier is 0.5 GB. A TTL job prunes experiments older than 90 days.

## Disclaimer

This is research/educational software. Past performance does not guarantee future results. Nothing here is investment advice. Don't trade real money based on its outputs.
