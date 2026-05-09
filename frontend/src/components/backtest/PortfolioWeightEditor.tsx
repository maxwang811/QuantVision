"use client";

import { TickerInput } from "@/components/portfolio/TickerInput";

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
      // Distribute evenly when there's nothing to scale.
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
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <legend className="text-sm font-semibold uppercase tracking-wide text-muted">
          Portfolio
        </legend>
        <div className={`text-sm font-mono ${balanced ? "text-positive" : "text-negative"}`}>
          Total: {totalPct.toFixed(2)}%
        </div>
      </div>

      <div className="space-y-2">
        {rows.map((row, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="flex-1">
              <TickerInput
                key={`ti-${i}-${row.ticker}`}
                placeholder="Search ticker…"
                onSelect={(a) => update(i, { ticker: a.ticker })}
              />
            </div>
            <div className="font-mono text-sm text-fg w-20 text-right truncate">
              {row.ticker || <span className="text-muted">—</span>}
            </div>
            <div className="relative">
              <input
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
                className="w-24 rounded-md border border-border bg-bg pl-3 pr-7 py-2 text-sm text-fg outline-none focus:border-accent"
                aria-label="Weight percent"
              />
              <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted">
                %
              </span>
            </div>
            <button
              type="button"
              onClick={() => removeRow(i)}
              className="rounded-md border border-border px-2 py-2 text-sm text-muted hover:text-negative hover:border-negative/60"
              aria-label="Remove row"
              disabled={rows.length <= 1}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={addRow}
          className="rounded-md border border-border px-3 py-1.5 text-sm text-fg hover:border-accent hover:text-accent"
        >
          + Add ticker
        </button>
        <button
          type="button"
          onClick={normalize}
          className="rounded-md border border-border px-3 py-1.5 text-sm text-fg hover:border-accent hover:text-accent"
        >
          Normalize to 100%
        </button>
      </div>
    </div>
  );
}
