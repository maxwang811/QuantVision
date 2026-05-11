"use client";

import { ForecastForm } from "@/components/forecast/ForecastForm";
import { ForecastResults } from "@/components/forecast/ForecastResults";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
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
      eyebrow="Simulate"
      title="Forecast"
      description="Project future portfolio outcomes using Monte Carlo simulation, historical bootstrap, or ML-adjusted drift. Returns are distributions, not point predictions."
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
    <div className="space-y-10">
      <Header />

      <ForecastForm defaultBacktestId={fromBacktestId} onSuccess={onSuccess} />

      {activeId && (
        <section className="space-y-4">
          <SectionEyebrow as="h2">Results</SectionEyebrow>
          <ForecastResults forecastId={activeId} initial={latest ?? undefined} />
        </section>
      )}
    </div>
  );
}
