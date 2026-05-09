"use client";

import { ForecastForm } from "@/components/forecast/ForecastForm";
import { ForecastResults } from "@/components/forecast/ForecastResults";
import type { ForecastOut } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

export default function ForecastPage() {
  return (
    <Suspense fallback={<PageHeader />}>
      <ForecastPageInner />
    </Suspense>
  );
}

function PageHeader() {
  return (
    <header className="space-y-2">
      <h1 className="text-2xl font-semibold tracking-tight">Forecast</h1>
      <p className="text-sm text-muted">
        Simulate future portfolio outcomes with Monte Carlo, historical bootstrap, or ML-adjusted
        drift.
      </p>
    </header>
  );
}

function ForecastPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const urlId = params.get("id");
  const fromBacktestId = params.get("from_backtest_id");
  const [latest, setLatest] = useState<ForecastOut | null>(null);

  const activeId = latest?.id ?? urlId ?? null;

  const onSuccess = (forecast: ForecastOut) => {
    setLatest(forecast);
    const next = new URLSearchParams(params.toString());
    next.set("id", forecast.id);
    router.replace(`/forecast?${next.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-8">
      <PageHeader />

      <ForecastForm defaultBacktestId={fromBacktestId} onSuccess={onSuccess} />

      {activeId && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Results</h2>
          <ForecastResults forecastId={activeId} initial={latest ?? undefined} />
        </section>
      )}
    </div>
  );
}
