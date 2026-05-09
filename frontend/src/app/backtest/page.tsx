"use client";

import { BacktestForm } from "@/components/backtest/BacktestForm";
import { BacktestResults } from "@/components/backtest/BacktestResults";
import type { BacktestOut } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

export default function BacktestPage() {
  return (
    <Suspense fallback={<PageHeader />}>
      <BacktestPageInner />
    </Suspense>
  );
}

function PageHeader() {
  return (
    <header className="space-y-2">
      <h1 className="text-2xl font-semibold tracking-tight">Backtest</h1>
      <p className="text-sm text-muted">
        Build a portfolio, pick a strategy, and replay it on historical prices. Metrics, equity
        curve, drawdown, and trades all render below after the run completes.
      </p>
    </header>
  );
}

function BacktestPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const urlId = params.get("id");
  const [latest, setLatest] = useState<BacktestOut | null>(null);

  const activeId = latest?.id ?? urlId ?? null;

  const onSuccess = (bt: BacktestOut) => {
    setLatest(bt);
    const next = new URLSearchParams(params.toString());
    next.set("id", bt.id);
    router.replace(`/backtest?${next.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-8">
      <PageHeader />

      <BacktestForm onSuccess={onSuccess} />

      {activeId && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Results</h2>
          <BacktestResults backtestId={activeId} initial={latest ?? undefined} />
        </section>
      )}
    </div>
  );
}
