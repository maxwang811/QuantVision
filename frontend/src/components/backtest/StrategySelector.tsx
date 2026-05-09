"use client";

import type { StrategyName } from "@/lib/api";

interface StrategyOption {
  value: string;
  label: string;
  description: string;
  enabled: boolean;
  hint?: string;
}

const STRATEGIES: StrategyOption[] = [
  {
    value: "buy_and_hold",
    label: "Buy & Hold",
    description: "Allocate to target weights on day 1, never rebalance.",
    enabled: true,
  },
  {
    value: "monthly_rebalance",
    label: "Monthly Rebalance",
    description: "Rebalance back to target weights at every month end.",
    enabled: true,
  },
  {
    value: "momentum",
    label: "Momentum",
    description: "Rank assets by trailing return, hold the top N.",
    enabled: true,
  },
  {
    value: "ma_crossover",
    label: "MA Crossover",
    description: "Buy when short MA crosses above long MA.",
    enabled: false,
    hint: "Coming Stage 5",
  },
  {
    value: "ml_ranking",
    label: "ML Ranking",
    description: "ML model ranks assets by predicted outperformance.",
    enabled: true,
  },
];

interface Props {
  value: StrategyName;
  onChange: (s: StrategyName) => void;
}

export function StrategySelector({ value, onChange }: Props) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-semibold uppercase tracking-wide text-muted">
        Strategy
      </legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {STRATEGIES.map((s) => {
          const checked = value === s.value;
          return (
            <label
              key={s.value}
              className={`relative flex cursor-pointer gap-3 rounded-md border p-3 text-sm transition-colors ${
                s.enabled
                  ? checked
                    ? "border-accent bg-accent/5"
                    : "border-border hover:border-accent/60"
                  : "cursor-not-allowed border-border/60 bg-border/10 opacity-60"
              }`}
            >
              <input
                type="radio"
                name="strategy"
                value={s.value}
                checked={checked}
                disabled={!s.enabled}
                onChange={() => s.enabled && onChange(s.value as StrategyName)}
                className="mt-1 accent-accent"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-fg">{s.label}</span>
                  {s.hint && (
                    <span className="rounded bg-border/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                      {s.hint}
                    </span>
                  )}
                </div>
                <div className="mt-0.5 text-xs text-muted">{s.description}</div>
              </div>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
