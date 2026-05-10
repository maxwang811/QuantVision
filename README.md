# QuantVision

Full-stack portfolio forecasting and strategy simulation platform.

QuantVision lets users build portfolios, backtest investment strategies on historical market data, and forecast future portfolio outcomes using Monte Carlo simulation, historical bootstrap, and machine-learning-driven methods. The system outputs distributions and risk metrics — not point predictions — so users can reason about returns under uncertainty.

## What it does

**Backtesting** — Replay historical price data with one of five strategies (buy-and-hold, monthly rebalance, moving-average crossover, momentum ranking, ML ranking). Computes Sharpe ratio, max drawdown, CAGR, alpha, beta, and a benchmark comparison.

**Forecasting** — Simulate thousands of possible 1-month to 5-year futures using parametric Monte Carlo, block bootstrap, or an ML-adjusted drift model. Reports P10/P50/P90 outcomes, probability of loss, and probability of beating SPY.

**ML pipeline** — Walk-forward XGBoost classifier predicting next-20-day asset outperformance vs SPY. Trained with strict no-look-ahead discipline; predictions persist to Postgres and feed the ML ranking strategy. An automated leakage-detection test (`tests/unit/test_no_leakage.py`) verifies the temporal barrier with a poisoned-future probe.

**Portfolio optimization** — Mean-variance / max-Sharpe optimizer (long-only, fully invested) with an efficient-frontier scatter visualization. `POST /api/optimize` returns the min-variance and max-Sharpe portfolios plus a 25-point frontier sweep. The frontend optimizer panel can populate the backtest form with one click.

**Experiment tracking** — Every backtest and forecast is persisted; a comparison view overlays multiple equity curves and metric grids side by side. Bounded parameter sweeps and CSV/JSON exports are wired through the same UI.

## Stack

- **Backend:** FastAPI · SQLAlchemy 2.0 · Alembic · Pandas · NumPy · scikit-learn · XGBoost
- **Frontend:** Next.js 14 (App Router) · TypeScript · Tailwind · Recharts · TanStack Query
- **Data:** yfinance (free, daily OHLCV)
- **Infra:** docker-compose (dev) · Fly.io + Vercel + Neon (prod)

## Quickstart

```bash
cp .env.example .env
make dev          # starts Postgres + backend + frontend (dev images, --reload)
make migrate      # apply database schema
make seed         # populate ~510 tickers
make ingest       # pull 5y of historical prices
```

Then open <http://localhost:3000>.

### End-to-end smoke check

```bash
make smoke        # boots stack, ingests SPY/AAPL/MSFT (~2y), hits every API endpoint
```

The smoke harness exercises the full backtest → forecast → sweep → compare → optimize pipeline and reports `PASS=N FAIL=M`.

### Production images

```bash
cp .env.prod.example .env.prod   # fill in real secrets, real DATABASE_URL, real CORS_ORIGINS
make prod-up                     # multi-stage builds, healthchecks, --workers 4 (no --reload)
make prod-down
```

`NEXT_PUBLIC_API_URL` is baked into the frontend at build time — changing it requires `make prod-up` to rebuild.

## Documentation

- [LIMITATIONS.md](LIMITATIONS.md) — known modelling limitations (survivorship bias, transaction model, etc.)
- Implementation plan: see `~/.claude/plans/here-is-a-project-humble-puddle.md`

## Status

Stage 7 — Experiment tracking, comparison, sweeps, and exports. Stages 1–6 deliver data ingestion, event-driven backtesting, risk metrics, the Next.js dashboard, Monte Carlo/bootstrap forecasting, and walk-forward ML ranking. Stage 7 adds unified history, side-by-side comparison, bounded backtest/forecast parameter sweeps, and CSV/JSON exports.
