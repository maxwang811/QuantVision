"use client";

import { ForecastForm } from "@/components/forecast/ForecastForm";
import { ForecastResults } from "@/components/forecast/ForecastResults";
import { PageHeader } from "@/components/ui/PageHeader";
import type { ForecastOut } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

export default function ForecastPage() {
  return (
    <Suspense fallback={<Header />}>
      <ForecastPageInner />
    </Suspense>
  );
}

function Header() {
  return (
    <PageHeader
      title="Forecast"
      description="Project future portfolio outcomes using simulation methods. Returns are distributions, not point predictions."
    />
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
      <Header />

      <ForecastForm defaultBacktestId={fromBacktestId} onSuccess={onSuccess} />

      {activeId && (
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-fg">Results</h2>
            <div className="h-px flex-1 bg-border" />
          </div>
          <ForecastResults forecastId={activeId} initial={latest ?? undefined} />
        </section>
      )}
    </div>
  );
}
