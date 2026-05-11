"use client";

import Link from "next/link";
import { TickerInput } from "@/components/portfolio/TickerInput";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import {
  IconArrowRight,
  IconBeaker,
  IconChart,
  IconClock,
  IconSparkles,
} from "@/components/ui/Icons";
import { SectionEyebrow } from "@/components/ui/SectionEyebrow";
import { api, type Asset, type Health } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

const FEATURES: {
  href: string;
  label: string;
  description: string;
  icon: typeof IconChart;
}[] = [
  {
    href: "/backtest",
    label: "Backtest",
    description: "Replay 5 strategies on historical prices with full risk metrics.",
    icon: IconChart,
  },
  {
    href: "/forecast",
    label: "Forecast",
    description: "Monte Carlo, bootstrap, and ML-adjusted simulations of future paths.",
    icon: IconSparkles,
  },
  {
    href: "/backtest",
    label: "Optimizer",
    description: "Mean-variance min-variance and max-Sharpe portfolios with frontier sweep.",
    icon: IconBeaker,
  },
  {
    href: "/experiments",
    label: "Experiments",
    description: "Track every run, compare side-by-side, export to CSV/JSON, run sweeps.",
    icon: IconClock,
  },
];

export default function HomePage() {
  const [picked, setPicked] = useState<Asset | null>(null);
  const { data: health } = useQuery<Health>({ queryKey: ["health"], queryFn: api.health });

  const healthTone = health ? (health.db ? "success" : "danger") : "neutral";
  const healthLabel = health ? (health.db ? "API connected" : "API degraded") : "Checking API…";

  return (
    <div className="space-y-12">
      <section className="space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <Badge tone="info" variant="soft">
            Portfolio analytics
          </Badge>
          <Badge tone={healthTone} variant="dot">
            {healthLabel}
          </Badge>
        </div>
        <div className="space-y-4">
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-fg sm:text-5xl">
            Reason about returns under uncertainty.
          </h1>
          <p className="max-w-2xl text-base text-muted sm:text-lg">
            Build portfolios, replay strategies on historical market data, and simulate thousands
            of possible futures using Monte Carlo, historical bootstrap, and ML-driven methods —
            then compare and export every run.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/backtest"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-accent px-5 text-sm font-semibold text-accent-fg shadow-soft transition-colors hover:bg-accent/90 focus-ring"
          >
            Start a backtest
            <IconArrowRight width={16} height={16} />
          </Link>
          <Link
            href="/forecast"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border bg-surface px-5 text-sm font-semibold text-fg transition-colors hover:border-border-strong hover:bg-surface-2 focus-ring"
          >
            Run a forecast
          </Link>
        </div>
      </section>

      <section className="space-y-4">
        <SectionEyebrow as="h2">What you can do</SectionEyebrow>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ href, label, description, icon: Icon }) => (
            <Link
              key={label}
              href={href}
              className="group relative flex h-full flex-col gap-3 rounded-xl border border-border bg-surface p-5 shadow-soft transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-card focus-ring"
            >
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent transition-colors group-hover:bg-accent/15">
                <Icon width={18} height={18} />
              </span>
              <div className="space-y-1">
                <div className="text-sm font-semibold text-fg">{label}</div>
                <p className="text-xs leading-5 text-muted">{description}</p>
              </div>
              <span className="mt-auto inline-flex items-center gap-1 text-xs font-medium text-accent opacity-0 transition-opacity group-hover:opacity-100">
                Open <IconArrowRight width={12} height={12} />
              </span>
            </Link>
          ))}
        </div>
      </section>

      <Card>
        <CardHeader
          eyebrow="Search"
          title="Asset universe"
          description="Lookup any of the ~510 seeded S&P 500 and ETF tickers."
        />
        <div className="mt-5 max-w-xl">
          <TickerInput onSelect={setPicked} autoFocus />
          {picked && (
            <div className="mt-3 inline-flex items-center gap-2 rounded-md border border-border bg-surface-2 px-3 py-2 text-sm">
              <span className="font-mono font-semibold text-fg">{picked.ticker}</span>
              <span className="text-muted">— {picked.name}</span>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
