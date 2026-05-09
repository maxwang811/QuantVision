import Link from "next/link";

export default function PortfolioPage() {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Portfolio Builder</h1>
      <p className="text-muted">
        The portfolio builder lives inside the backtest flow. Head to{" "}
        <Link href="/backtest" className="text-accent hover:underline">
          Backtest
        </Link>{" "}
        to assemble tickers, set weights, and run a strategy.
      </p>
    </div>
  );
}
