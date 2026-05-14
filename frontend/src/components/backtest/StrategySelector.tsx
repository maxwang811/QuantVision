"use client";

import { cn } from "@/components/ui/utils";
import { IconChart, IconRefresh, IconTrendingUp, IconCpu, IconActivity } from "@/components/ui/Icons";
import type { StrategyName } from "@/lib/api";

interface StrategyOption {
  value: string;
  label: string;
  description: string;
  enabled: boolean;
  icon: typeof IconChart;
}

const STRATEGIES: StrategyOption[] = [
  {
    value: "buy_and_hold",
    label: "Buy & Hold",
    description: "Allocate to target weights on day 1, never rebalance.",
    enabled: true,
    icon: IconChart,
  },
  {
    value: "monthly_rebalance",
    label: "Monthly Rebalance",
    description: "Rebalance back to target weights at every month end.",
    enabled: true,
    icon: IconRefresh,
  },
  {
    value: "momentum",
    label: "Momentum",
    description: "Rank assets by trailing return, hold the top N.",
    enabled: true,
    icon: IconTrendingUp,
  },
  {
    value: "ma_crossover",
    label: "MA Crossover",
    description: "Hold each asset only when its short MA is above its long MA.",
    enabled: true,
    icon: IconActivity,
  },
  {
    value: "ml_ranking",
    label: "ML Ranking",
    description: "ML model ranks assets by predicted outperformance.",
    enabled: true,
    icon: IconCpu,
  },
];

interface Props {
  value: StrategyName;
  onChange: (s: StrategyName) => void;
}

export function StrategySelector({ value, onChange }: Props) {
  return (
    <fieldset className="space-y-4">
      <legend className="text-sm font-medium text-fg">
        Trading Strategy
      </legend>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {STRATEGIES.map((s) => {
          const checked = value === s.value;
          const Icon = s.icon;
          return (
            <label
              key={s.value}
              className={cn(
                "relative flex cursor-pointer gap-3 rounded-xl border p-4 transition-all duration-200",
                s.enabled
                  ? checked
                    ? "border-accent bg-accent-soft ring-1 ring-accent/30"
                    : "border-border bg-surface hover:border-border-strong hover:bg-surface-2/50"
                  : "cursor-not-allowed border-border bg-surface-2/50 opacity-50",
              )}
            >
              <input
                type="radio"
                name="strategy"
                value={s.value}
                checked={checked}
                disabled={!s.enabled}
                onChange={() => s.enabled && onChange(s.value as StrategyName)}
                className="sr-only"
              />
              <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors",
                checked ? "bg-accent text-accent-fg" : "bg-surface-2 text-muted"
              )}>
                <Icon width={20} height={20} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-fg">{s.label}</div>
                <div className="mt-1 text-xs text-muted leading-relaxed">{s.description}</div>
              </div>
              {checked && (
                <div className="absolute top-3 right-3">
                  <div className="h-2 w-2 rounded-full bg-accent" />
                </div>
              )}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
