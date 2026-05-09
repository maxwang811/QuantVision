"use client";

import type { TradeOut } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";
import { useMemo } from "react";

interface Props {
  trades: TradeOut[];
}

export function TradeHistoryTable({ trades }: Props) {
  const { totalCost } = useMemo(() => {
    return { totalCost: trades.reduce((s, t) => s + t.transaction_cost, 0) };
  }, [trades]);

  return (
    <div className="rounded-lg border border-border bg-bg p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-fg">Trades</h3>
        <span className="text-xs text-muted">
          {trades.length} trade{trades.length === 1 ? "" : "s"} · total cost{" "}
          <span className="font-mono text-fg">{formatCurrency(totalCost)}</span>
        </span>
      </div>

      <div className="max-h-96 overflow-auto rounded-md border border-border">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-bg">
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
              <th className="px-3 py-2 font-medium">Date</th>
              <th className="px-3 py-2 font-medium">Ticker</th>
              <th className="px-3 py-2 font-medium">Side</th>
              <th className="px-3 py-2 text-right font-medium">Quantity</th>
              <th className="px-3 py-2 text-right font-medium">Price</th>
              <th className="px-3 py-2 text-right font-medium">Notional</th>
              <th className="px-3 py-2 text-right font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-muted">
                  No trades.
                </td>
              </tr>
            ) : (
              trades.map((t) => (
                <tr key={t.id} className="border-b border-border/50 last:border-0">
                  <td className="px-3 py-1.5 text-muted">{formatDate(t.date)}</td>
                  <td className="px-3 py-1.5 font-mono text-fg">{t.ticker}</td>
                  <td className="px-3 py-1.5">
                    <span
                      className={`inline-flex rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${
                        t.side === "buy"
                          ? "bg-positive/15 text-positive"
                          : "bg-negative/15 text-negative"
                      }`}
                    >
                      {t.side}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                    {formatNumber(t.quantity, 4)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                    {formatCurrency(t.price)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                    {formatCurrency(t.notional)}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono tabular-nums text-muted">
                    {formatCurrency(t.transaction_cost)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
