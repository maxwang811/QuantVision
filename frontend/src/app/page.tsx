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
import { api, type Asset, type Health } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

const FEATURES: {
  href: string;
  label: string;
  description: string;
  icon: typeof IconChart;
  gradient: string;
}[] = [
  {
    href: "/backtest",
    label: "Backtest",
    description: "Replay strategies on historical prices with full risk metrics and trade logs.",
    icon: IconChart,
    gradient: "from-accent/20 to-accent/5",
  },
  {
    href: "/forecast",
    label: "Forecast",
    description: "Monte Carlo, bootstrap, and ML-adjusted simulations of future portfolio paths.",
    icon: IconSparkles,
    gradient: "from-positive/20 to-positive/5",
  },
  {
    href: "/backtest",
    label: "Optimizer",
    description: "Mean-variance optimization with efficient frontier and target allocation.",
    icon: IconBeaker,
    gradient: "from-warn/20 to-warn/5",
  },
  {
    href: "/experiments",
    label: "History",
    description: "Track every run, compare side-by-side, export to CSV or JSON.",
    icon: IconClock,
    gradient: "from-muted/20 to-muted/5",
  },
];

const STATS = [
  { label: "Assets", value: "510+" },
  { label: "Strategies", value: "5" },
  { label: "Methods", value: "3" },
];

export default function HomePage() {
  const [picked, setPicked] = useState<Asset | null>(null);
  const { data: health } = useQuery<Health>({ queryKey: ["health"], queryFn: api.health });

  const healthTone = health ? (health.db ? "success" : "danger") : "neutral";
  const healthLabel = health ? (health.db ? "Online" : "Degraded") : "Checking...";

  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="relative">
        {/* Background gradient effect */}
        <div className="pointer-events-none absolute -top-20 left-1/2 h-[500px] w-[800px] -translate-x-1/2 bg-gradient-to-b from-accent/5 via-transparent to-transparent blur-3xl" />
        
        <div className="relative space-y-8">
          {/* Status indicator */}
          <div className="flex items-center gap-3">
            <Badge tone={healthTone} variant="dot" size="sm">
              {healthLabel}
            </Badge>
          </div>

          {/* Main headline */}
          <div className="space-y-4">
            <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-fg sm:text-5xl lg:text-6xl text-balance">
              Reason about returns{" "}
              <span className="text-gradient">under uncertainty</span>
            </h1>
            <p className="max-w-xl text-base text-muted leading-relaxed sm:text-lg">
              Build portfolios, replay strategies on historical data, and simulate 
              thousands of possible futures — then compare and export every run.
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-wrap items-center gap-4">
            <Link
              href="/backtest"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-accent px-6 text-sm font-semibold text-accent-fg shadow-soft transition-all duration-200 hover:bg-accent-hover hover:shadow-glow focus-ring"
            >
              Start a backtest
              <IconArrowRight width={16} height={16} />
            </Link>
            <Link
              href="/forecast"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-border bg-surface px-6 text-sm font-semibold text-fg transition-all duration-200 hover:border-border-strong hover:bg-surface-2 focus-ring"
            >
              Run a forecast
            </Link>
          </div>

          {/* Quick Stats */}
          <div className="flex items-center gap-8 pt-4">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl font-semibold text-fg font-mono">{stat.value}</div>
                <div className="text-xs text-muted uppercase tracking-eyebrow">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="space-y-6">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-fg">What you can do</h2>
          <p className="text-sm text-muted">Comprehensive tools for portfolio analysis and simulation.</p>
        </div>
        
        <div className="grid gap-4 sm:grid-cols-2">
          {FEATURES.map(({ href, label, description, icon: Icon, gradient }) => (
            <Link
              key={label}
              href={href}
              className="group relative flex items-start gap-4 rounded-2xl border border-border bg-surface p-5 transition-all duration-200 hover:border-border-strong hover:shadow-card focus-ring overflow-hidden"
            >
              {/* Subtle gradient background */}
              <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 transition-opacity duration-200 group-hover:opacity-100`} />
              
              <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-fg transition-colors group-hover:bg-surface border border-border">
                <Icon width={20} height={20} />
              </div>
              
              <div className="relative space-y-1.5 flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-fg">{label}</h3>
                  <IconArrowRight 
                    width={16} 
                    height={16} 
                    className="text-muted opacity-0 -translate-x-2 transition-all duration-200 group-hover:opacity-100 group-hover:translate-x-0" 
                  />
                </div>
                <p className="text-sm text-muted leading-relaxed">{description}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Asset Search */}
      <Card variant="elevated" className="overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="space-y-4 lg:max-w-md">
            <CardHeader
              title="Search the asset universe"
              description="Look up any of the 510+ seeded S&P 500 and ETF tickers to start building your portfolio."
              size="large"
            />
            
            {/* Search input */}
            <div className="max-w-sm">
              <TickerInput onSelect={setPicked} autoFocus />
            </div>
            
            {picked && (
              <div className="animate-fade-in inline-flex items-center gap-3 rounded-xl border border-accent/20 bg-accent-soft px-4 py-3">
                <span className="font-mono text-base font-semibold text-accent">{picked.ticker}</span>
                <span className="text-sm text-muted">{picked.name}</span>
              </div>
            )}
          </div>

          {/* Visual element */}
          <div className="hidden lg:flex items-center justify-center w-64 h-40">
            <div className="relative w-full h-full">
              {/* Decorative chart-like lines */}
              <svg viewBox="0 0 200 100" className="w-full h-full text-accent/20">
                <path
                  d="M 0 80 Q 40 70 60 50 T 100 40 T 140 55 T 200 30"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="animate-pulse-soft"
                />
                <path
                  d="M 0 90 Q 50 85 80 70 T 120 60 T 160 65 T 200 50"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  opacity="0.5"
                />
              </svg>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
