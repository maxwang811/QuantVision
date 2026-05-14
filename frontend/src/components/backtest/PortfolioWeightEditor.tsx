"use client";

import { TickerInput } from "@/components/portfolio/TickerInput";
import { Button } from "@/components/ui/Button";
import { IconCheck, IconPlus, IconX } from "@/components/ui/Icons";
import { Input } from "@/components/ui/Input";
import { cn } from "@/components/ui/utils";

export interface PortfolioRow {
  ticker: string;
  weightPct: number;
}

interface Props {
  rows: PortfolioRow[];
  onChange: (rows: PortfolioRow[]) => void;
}

const WEIGHT_TOLERANCE = 0.0001;

export function PortfolioWeightEditor({ rows, onChange }: Props) {
  const totalPct = rows.reduce((sum, r) => sum + (Number.isFinite(r.weightPct) ? r.weightPct : 0), 0);
  const balanced = Math.abs(totalPct - 100) < WEIGHT_TOLERANCE;

  const update = (i: number, patch: Partial<PortfolioRow>) => {
    onChange(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  };

  const addRow = () => {
    onChange([...rows, { ticker: "", weightPct: 0 }]);
  };

  const removeRow = (i: number) => {
    onChange(rows.filter((_, idx) => idx !== i));
  };

  const normalize = () => {
    const sum = rows.reduce((s, r) => s + (Number.isFinite(r.weightPct) ? r.weightPct : 0), 0);
    if (sum <= 0) {
      const each = rows.length > 0 ? 100 / rows.length : 0;
      onChange(rows.map((r) => ({ ...r, weightPct: Number(each.toFixed(4)) })));
      return;
    }
    onChange(
      rows.map((r) => ({
        ...r,
        weightPct: Number(((r.weightPct / sum) * 100).toFixed(4)),
      })),
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-medium text-fg">Portfolio Allocation</h3>
          <p className="text-xs text-muted mt-0.5">Weights must sum to 100%</p>
        </div>
        <div
          className={cn(
            "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium font-mono tabular-nums",
            balanced 
              ? "bg-positive-soft text-positive" 
              : "bg-negative-soft text-negative",
          )}
        >
          {balanced && <IconCheck width={14} height={14} />}
          {totalPct.toFixed(1)}%
        </div>
      </div>

      {/* Rows */}
      <div className="space-y-2">
        {rows.map((row, i) => (
          <div
            key={i}
            className="flex items-center gap-3 rounded-xl border border-border bg-surface p-3 transition-colors hover:border-border-strong"
          >
            {/* Ticker search */}
            <div className="flex-1 min-w-0">
              <TickerInput
                key={`ti-${i}-${row.ticker}`}
                placeholder="Search ticker..."
                onSelect={(a) => update(i, { ticker: a.ticker })}
              />
            </div>
            
            {/* Selected ticker display */}
            <div className="hidden sm:flex w-20 items-center justify-end">
              {row.ticker ? (
                <span className="font-mono text-sm font-medium text-fg bg-surface-2 px-2 py-1 rounded">
                  {row.ticker}
                </span>
              ) : (
                <span className="text-xs text-muted">No ticker</span>
              )}
            </div>
            
            {/* Weight input */}
            <div className="w-28">
              <Input
                type="number"
                inputMode="decimal"
                inputSize="sm"
                min={0}
                max={100}
                step={0.01}
                value={Number.isFinite(row.weightPct) ? row.weightPct : ""}
                onChange={(e) => {
                  const v = e.target.value;
                  update(i, { weightPct: v === "" ? 0 : Number(v) });
                }}
                adornmentRight="%"
                aria-label="Weight percent"
              />
            </div>
            
            {/* Remove button */}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => removeRow(i)}
              aria-label="Remove row"
              disabled={rows.length <= 1}
              className="h-8 w-8 p-0 text-muted hover:text-negative shrink-0"
            >
              <IconX width={16} height={16} />
            </Button>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <Button 
          type="button" 
          variant="secondary" 
          size="sm" 
          onClick={addRow} 
          leadingIcon={<IconPlus width={14} height={14} />}
        >
          Add ticker
        </Button>
        <Button 
          type="button" 
          variant="ghost" 
          size="sm" 
          onClick={normalize}
          disabled={rows.length === 0}
        >
          Normalize to 100%
        </Button>
      </div>
    </div>
  );
}
