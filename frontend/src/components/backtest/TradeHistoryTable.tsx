"use client";

import { Badge } from "@/components/ui/Badge";
import { ChartCard } from "@/components/ui/ChartCard";
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
    <ChartCard
      title="Trades"
      meta={
        <>
          {trades.length} trade{trades.length === 1 ? "" : "s"} · total cost{" "}
          <span className="font-mono text-fg">{formatCurrency(totalCost)}</span>
        </>
      }
    >
      <div className="max-h-96 overflow-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-surface">
            <tr className="border-b border-border text-left text-xs uppercase tracking-eyebrow text-muted">
              <th className="px-3 py-2 font-semibold">Date</th>
              <th className="px-3 py-2 font-semibold">Ticker</th>
              <th className="px-3 py-2 font-semibold">Side</th>
              <th className="px-3 py-2 text-right font-semibold">Quantity</th>
              <th className="px-3 py-2 text-right font-semibold">Price</th>
              <th className="px-3 py-2 text-right font-semibold">Notional</th>
              <th className="px-3 py-2 text-right font-semibold">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {trades.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-sm text-muted">
                  No trades.
                </td>
              </tr>
            ) : (
              trades.map((t, idx) => (
                <tr
                  key={t.id}
                  className={
                    "transition-colors hover:bg-surface-2/60 " +
                    (idx % 2 === 1 ? "bg-surface-2/30" : "")
                  }
                >
                  <td className="px-3 py-2 text-muted">{formatDate(t.date)}</td>
                  <td className="px-3 py-2 font-mono font-medium text-fg">{t.ticker}</td>
                  <td className="px-3 py-2">
                    <Badge tone={t.side === "buy" ? "success" : "danger"} variant="soft">
                      {t.side}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatNumber(t.quantity, 4)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrency(t.price)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrency(t.notional)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-muted">
                    {formatCurrency(t.transaction_cost)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </ChartCard>
  );
}
