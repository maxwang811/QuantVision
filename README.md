# QuantVision

Full-stack portfolio forecasting and strategy simulation platform.

QuantVision lets users build portfolios, backtest investment strategies on historical market data, and forecast future portfolio outcomes using Monte Carlo simulation, historical bootstrap, and machine-learning-driven methods. The system outputs distributions and risk metrics — not point predictions — so users can reason about returns under uncertainty.

## What it does

**Backtesting** — Replay historical price data with one of five strategies (buy-and-hold, monthly rebalance, moving-average crossover, momentum ranking, ML ranking). Computes Sharpe ratio, max drawdown, CAGR, alpha, beta, and a benchmark comparison.

**Forecasting** — Simulate thousands of possible 1-month to 5-year futures using parametric Monte Carlo, block bootstrap, or an ML-adjusted drift model. Reports P10/P50/P90 outcomes, probability of loss, and probability of beating SPY.

**ML pipeline** — Walk-forward XGBoost classifier predicting next-20-day asset outperformance vs SPY. Trained with strict no-look-ahead discipline; predictions persist to Postgres and feed the ML ranking strategy.

**Experiment tracking** — Every backtest and forecast is persisted; a comparison view overlays multiple equity curves and metric grids side by side.

## Stack

- **Backend:** FastAPI · SQLAlchemy 2.0 · Alembic · Pandas · NumPy · scikit-learn · XGBoost
- **Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind · Recharts · TanStack Query
- **Data:** yfinance (free, daily OHLCV)
- **Infra:** docker-compose (dev) · Fly.io + Vercel + Neon (prod)

## Quickstart

```bash
cp .env.example .env
make dev          # starts Postgres + backend + frontend
make migrate      # apply database schema
make seed         # populate ~510 tickers
make ingest       # pull 5y of historical prices
```

Then open <http://localhost:3000>.

## Documentation

- [LIMITATIONS.md](LIMITATIONS.md) — known modelling limitations (survivorship bias, transaction model, etc.)
- Implementation plan: see `~/.claude/plans/here-is-a-project-humble-puddle.md`

## Status

Stage 6 — ML ranking strategies. Stages 1–5 deliver data ingestion, event-driven backtesting, risk metrics, the Next.js dashboard, and Monte Carlo/bootstrap forecasting. Stage 6 adds walk-forward Logistic Regression/XGBoost ranking, persisted model runs and predictions, momentum and ML ranking backtests, and frontend controls for ranking strategy parameters. Experiment tracking (Stage 7) is next.
