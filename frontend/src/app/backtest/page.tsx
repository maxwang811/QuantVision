"use client";

import { BacktestForm } from "@/components/backtest/BacktestForm";
import { BacktestResults } from "@/components/backtest/BacktestResults";
import { OptimizerPanel } from "@/components/backtest/OptimizerPanel";
import type { PortfolioRow } from "@/components/backtest/PortfolioWeightEditor";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
import type { BacktestOut } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

export default function BacktestPage() {
  return (
    <Suspense fallback={<Header />}>
      <BacktestPageInner />
    </Suspense>
  );
}

function Header() {
  return (
    <PageHeader
      eyebrow="Run"
      title="Backtest"
      description="Build a portfolio, pick a strategy, and replay it on historical prices. Metrics, equity curve, drawdown, and trades render below after the run completes."
    />
  );
}

function BacktestPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const urlId = params.get("id");
  const [latest, setLatest] = useState<BacktestOut | null>(null);
  const [presetRows, setPresetRows] = useState<PortfolioRow[] | undefined>(undefined);

  const activeId = latest?.id ?? urlId ?? null;

  const onSuccess = (bt: BacktestOut) => {
    setLatest(bt);
    const next = new URLSearchParams(params.toString());
    next.set("id", bt.id);
    router.replace(`/backtest?${next.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-10">
      <Header />

      <OptimizerPanel onApply={(rows) => setPresetRows(rows)} />

      <BacktestForm onSuccess={onSuccess} defaultRows={presetRows} />

      {activeId && (
        <section className="space-y-4">
          <SectionEyebrow as="h2">Results</SectionEyebrow>
          <BacktestResults backtestId={activeId} initial={latest ?? undefined} />
        </section>
      )}
    </div>
  );
}
