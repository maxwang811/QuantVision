import { describe, expect, test } from "vitest";
import { validateBacktestPayload } from "../backtest/validateBacktest";

const baseInput = {
  rows: [
    { ticker: "SPY", weightPct: 50 },
    { ticker: "AAPL", weightPct: 50 },
  ],
  name: "",
  strategy: "monthly_rebalance" as const,
  initialCash: 10_000,
  startDate: "2023-01-01",
  endDate: "2024-01-01",
  transactionCostBps: 10,
  benchmarkTicker: "SPY",
  topN: 3,
  selectedModel: "xgboost" as const,
  trainingLookbackDays: 756,
  labelHorizonDays: 20,
  shortWindow: 50,
  longWindow: 200,
};

describe("validateBacktestPayload", () => {
  test("balanced weights produce a payload", () => {
    const out = validateBacktestPayload(baseInput);
    expect(out.localError).toBeNull();
    expect(out.payload).not.toBeNull();
    expect(out.payload!.tickers).toEqual(["SPY", "AAPL"]);
    expect(out.payload!.weights).toEqual([0.5, 0.5]);
  });

  test("weights summing to 99.5 reject with sum error", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      rows: [
        { ticker: "SPY", weightPct: 49.5 },
        { ticker: "AAPL", weightPct: 50 },
      ],
    });
    expect(out.localError).toMatch(/sum to 100/i);
    expect(out.payload).toBeNull();
  });

  test("negative weight rejected", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      rows: [
        { ticker: "SPY", weightPct: -10 },
        { ticker: "AAPL", weightPct: 110 },
      ],
    });
    expect(out.localError).toMatch(/non-negative/i);
  });

  test("empty ticker list rejected", () => {
    const out = validateBacktestPayload({ ...baseInput, rows: [] });
    expect(out.localError).toMatch(/Add at least one/i);
  });

  test("end date before start date rejected", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      startDate: "2024-01-01",
      endDate: "2023-01-01",
    });
    expect(out.localError).toMatch(/End date must be after/i);
  });

  test("duplicate tickers rejected", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      rows: [
        { ticker: "spy", weightPct: 50 },
        { ticker: "SPY", weightPct: 50 },
      ],
    });
    expect(out.localError).toMatch(/Duplicate ticker: SPY/);
  });

  test("ranking strategy skips weight-sum check", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      strategy: "momentum",
      rows: [
        { ticker: "AAA", weightPct: 0 },
        { ticker: "BBB", weightPct: 0 },
        { ticker: "CCC", weightPct: 0 },
      ],
      topN: 2,
    });
    expect(out.localError).toBeNull();
    expect(out.payload!.strategy_params).toMatchObject({
      top_n: 2,
      rebalance_frequency: "monthly",
    });
  });

  test("ml_ranking with bad top_n rejected", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      strategy: "ml_ranking",
      topN: 0,
      rows: [{ ticker: "AAA", weightPct: 100 }],
    });
    expect(out.localError).toMatch(/Top N must be at least 1/i);
  });

  test("ml_ranking with too-short training lookback rejected", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      strategy: "ml_ranking",
      trainingLookbackDays: 50,
      rows: [{ ticker: "AAA", weightPct: 100 }],
    });
    expect(out.localError).toMatch(/Training lookback/i);
  });

  test("initial cash <= 0 rejected", () => {
    const out = validateBacktestPayload({ ...baseInput, initialCash: 0 });
    expect(out.localError).toMatch(/Initial cash/i);
  });

  test("ma_crossover passes window params through", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      strategy: "ma_crossover",
      shortWindow: 20,
      longWindow: 100,
    });
    expect(out.localError).toBeNull();
    expect(out.payload!.strategy_params).toEqual({
      short_window: 20,
      long_window: 100,
    });
  });

  test("ma_crossover rejects short >= long", () => {
    const out = validateBacktestPayload({
      ...baseInput,
      strategy: "ma_crossover",
      shortWindow: 200,
      longWindow: 50,
    });
    expect(out.localError).toMatch(/Short window must be less than long window/i);
  });

  test("benchmark ticker is upper-cased and trimmed", () => {
    const out = validateBacktestPayload({ ...baseInput, benchmarkTicker: "  spy  " });
    expect(out.payload!.benchmark_ticker).toBe("SPY");
  });
});
