import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { IconArrowRight, IconChart } from "@/components/ui/Icons";
import { PageHeader } from "@/components/ui/PageHeader";

export default function PortfolioPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Portfolio"
        title="Portfolio builder"
        description="The portfolio builder lives inside the backtest flow — pick tickers, set target weights, choose a strategy, and run."
      />

      <Card className="flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
            <IconChart width={20} height={20} />
          </span>
          <div className="space-y-1">
            <div className="text-base font-semibold text-fg">Head to Backtest to build a portfolio</div>
            <p className="max-w-md text-sm text-muted">
              Assemble tickers, set weights, choose a strategy, and replay it on historical data —
              all in one flow.
            </p>
          </div>
        </div>
        <Link
          href="/backtest"
          className="inline-flex h-10 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-accent-fg shadow-soft transition-colors hover:bg-accent/90 focus-ring"
        >
          Open backtest
          <IconArrowRight width={16} height={16} />
        </Link>
      </Card>
    </div>
  );
}
