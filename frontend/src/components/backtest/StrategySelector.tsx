"use client";

import { cn } from "@/components/ui/utils";
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
    <fieldset className="space-y-3">
      <legend className="text-[11px] font-semibold uppercase tracking-eyebrow text-muted">
        Strategy
      </legend>
      <div className="grid gap-2.5 sm:grid-cols-2">
        {STRATEGIES.map((s) => {
          const checked = value === s.value;
          return (
            <label
              key={s.value}
              className={cn(
                "relative flex cursor-pointer gap-3 rounded-lg border p-3.5 text-sm transition-all",
                s.enabled
                  ? checked
                    ? "border-accent bg-accent/[0.06] ring-1 ring-accent/30"
                    : "border-border hover:border-accent/40 hover:bg-surface-2"
                  : "cursor-not-allowed border-border bg-surface-2/40 opacity-60",
              )}
            >
              <input
                type="radio"
                name="strategy"
                value={s.value}
                checked={checked}
                disabled={!s.enabled}
                onChange={() => s.enabled && onChange(s.value as StrategyName)}
                className="mt-0.5 accent-accent"
              />
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-fg">{s.label}</span>
                  {s.hint && (
                    <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                      {s.hint}
                    </span>
                  )}
                </div>
                <div className="mt-1 text-xs leading-5 text-muted">{s.description}</div>
              </div>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
