"use client";

import { TickerInput } from "@/components/portfolio/TickerInput";
import { Button } from "@/components/ui/Button";
import { IconCheck, IconPlus, IconX } from "@/components/ui/Icons";
import { Input } from "@/components/ui/Input";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
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
      <div className="flex items-baseline justify-between gap-3">
        <SectionEyebrow as="div">Portfolio</SectionEyebrow>
        <div
          className={cn(
            "inline-flex items-center gap-1.5 font-mono text-xs font-medium tabular-nums",
            balanced ? "text-positive" : "text-negative",
          )}
        >
          {balanced && <IconCheck width={12} height={12} />}
          Total: {totalPct.toFixed(2)}%
        </div>
      </div>

      <div className="space-y-2">
        {rows.map((row, i) => (
          <div
            key={i}
            className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-2 sm:flex-row sm:items-center"
          >
            <div className="flex-1">
              <TickerInput
                key={`ti-${i}-${row.ticker}`}
                placeholder="Search ticker…"
                onSelect={(a) => update(i, { ticker: a.ticker })}
              />
            </div>
            <div className="flex items-center gap-2">
              <div className="hidden w-20 truncate text-right font-mono text-sm text-fg sm:block">
                {row.ticker ? row.ticker : <span className="text-muted">—</span>}
              </div>
              <div className="w-24">
                <Input
                  type="number"
                  inputMode="decimal"
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
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeRow(i)}
                aria-label="Remove row"
                disabled={rows.length <= 1}
                className="h-9 w-9 p-0 text-muted hover:text-negative"
              >
                <IconX width={14} height={14} />
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={addRow} leadingIcon={<IconPlus width={12} height={12} />}>
          Add ticker
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={normalize}>
          Normalize to 100%
        </Button>
      </div>
    </div>
  );
}
