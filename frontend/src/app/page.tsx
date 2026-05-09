"use client";

import { TickerInput } from "@/components/portfolio/TickerInput";
import { api, type Asset, type Health } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

export default function HomePage() {
  const [picked, setPicked] = useState<Asset | null>(null);
  const { data: health } = useQuery<Health>({ queryKey: ["health"], queryFn: api.health });

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">QuantVision</h1>
        <p className="text-muted max-w-2xl">
          Build portfolios, backtest strategies on historical market data, and forecast future
          outcomes using Monte Carlo simulation, historical bootstrap, and ML-driven methods.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          Search the asset universe
        </h2>
        <TickerInput onSelect={setPicked} autoFocus />
        {picked && (
          <div className="text-sm text-fg pt-2">
            Selected:{" "}
            <span className="font-mono font-semibold">{picked.ticker}</span>{" "}
            <span className="text-muted">— {picked.name}</span>
          </div>
        )}
      </section>

      <section className="text-xs text-muted border-t border-border pt-4">
        API status:{" "}
        <span className={health?.db ? "text-positive" : "text-negative"}>
          {health ? (health.db ? "connected" : "degraded") : "checking…"}
        </span>
      </section>
    </div>
  );
}
