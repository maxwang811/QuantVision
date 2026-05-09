"""Forecasting engine: pure simulation kernels + DB-aware runner.

Mirrors the structure of `app.services.backtest`: a pure engine module
(no I/O) and a runner module that handles DB persistence and orchestration.
"""
