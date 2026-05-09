# Known Limitations

QuantVision is a research/educational platform. The simulations are bound by several modelling assumptions documented here. Read this before drawing real-money conclusions from any output.

## Data limitations

**Survivorship bias.** yfinance only returns currently-listed tickers. Historical universes don't include companies that were delisted (bankruptcies, mergers, etc.), which biases historical returns upward. A momentum strategy backtested on the current S&P 500 will look better than the same strategy run in real time. We surface this with a tooltip on results pages.

**yfinance flakiness.** Yahoo Finance occasionally returns empty or partial results. We retry with exponential backoff and cache aggressively in Postgres, but recent data may be stale. The UI displays an "as of" timestamp.

**Adjusted close only.** All return calculations use `adj_close`, which already accounts for splits and dividends. We do not model dividends as separate cash flows.

## Backtesting limitations

**Simplistic transaction model.** No bid-ask spread, no market impact, no borrow cost (so no real shorting). Slippage is modeled as a flat basis-point haircut. Real-world execution costs scale with order size, liquidity, and market regime. Stress-test by raising `transaction_cost_bps` and `slippage_bps`.

**T+1 execution assumption.** Signals fire at close[T]; orders execute at close[T+1] with slippage. This is the standard convention but real markets execute at the open or via VWAP/TWAP algorithms.

**No corporate actions besides splits/dividends.** Mergers, tender offers, spin-offs, ticker changes — all ignored.

**Look-ahead bias.** The engine guards against look-ahead by exposing only `date < ctx.date` to the strategy. Feature engineering uses `.shift(1)` and is unit-tested for leakage. But subtle leakage is always possible; flag suspicious results.

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
