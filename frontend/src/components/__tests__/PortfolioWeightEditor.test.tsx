import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";
import {
  PortfolioWeightEditor,
  type PortfolioRow,
} from "../backtest/PortfolioWeightEditor";

function withQuery(node: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("PortfolioWeightEditor", () => {
  test("clicking + Add ticker appends an empty row", () => {
    const onChange = vi.fn();
    const rows: PortfolioRow[] = [
      { ticker: "SPY", weightPct: 50 },
      { ticker: "AAPL", weightPct: 50 },
    ];
    render(withQuery(<PortfolioWeightEditor rows={rows} onChange={onChange} />));
    fireEvent.click(screen.getByRole("button", { name: /add ticker/i }));
    expect(onChange).toHaveBeenCalledTimes(1);
    const next = onChange.mock.calls[0][0] as PortfolioRow[];
    expect(next).toHaveLength(3);
    expect(next[2]).toEqual({ ticker: "", weightPct: 0 });
  });

  test("removing the middle row keeps the outer rows", () => {
    const onChange = vi.fn();
    const rows: PortfolioRow[] = [
      { ticker: "A", weightPct: 33 },
      { ticker: "B", weightPct: 33 },
      { ticker: "C", weightPct: 34 },
    ];
    render(withQuery(<PortfolioWeightEditor rows={rows} onChange={onChange} />));
    const removes = screen.getAllByRole("button", { name: /remove row/i });
    fireEvent.click(removes[1]);
    const next = onChange.mock.calls[0][0] as PortfolioRow[];
    expect(next.map((r) => r.ticker)).toEqual(["A", "C"]);
  });

  test("remove disabled when only one row remains", () => {
    const onChange = vi.fn();
    render(
      withQuery(
        <PortfolioWeightEditor
          rows={[{ ticker: "SPY", weightPct: 100 }]}
          onChange={onChange}
        />,
      ),
    );
    const remove = screen.getByRole("button", { name: /remove row/i });
    expect(remove).toBeDisabled();
  });

  test("Normalize to 100% scales weights proportionally", () => {
    const onChange = vi.fn();
    const rows: PortfolioRow[] = [
      { ticker: "A", weightPct: 20 },
      { ticker: "B", weightPct: 30 },
      { ticker: "C", weightPct: 50 },
    ];
    render(withQuery(<PortfolioWeightEditor rows={rows} onChange={onChange} />));
    fireEvent.click(screen.getByRole("button", { name: /normalize/i }));
    const next = onChange.mock.calls[0][0] as PortfolioRow[];
    const total = next.reduce((s, r) => s + r.weightPct, 0);
    expect(Math.abs(total - 100)).toBeLessThan(0.01);
  });

  test("Normalize on all-zero rows distributes evenly", () => {
    const onChange = vi.fn();
    const rows: PortfolioRow[] = [
      { ticker: "A", weightPct: 0 },
      { ticker: "B", weightPct: 0 },
      { ticker: "C", weightPct: 0 },
    ];
    render(withQuery(<PortfolioWeightEditor rows={rows} onChange={onChange} />));
    fireEvent.click(screen.getByRole("button", { name: /normalize/i }));
    const next = onChange.mock.calls[0][0] as PortfolioRow[];
    next.forEach((r) => expect(r.weightPct).toBeCloseTo(100 / 3, 3));
  });

  test("total bar uses positive style when balanced", () => {
    const onChange = vi.fn();
    const rows: PortfolioRow[] = [
      { ticker: "A", weightPct: 60 },
      { ticker: "B", weightPct: 40 },
    ];
    const { container } = render(
      withQuery(<PortfolioWeightEditor rows={rows} onChange={onChange} />),
    );
    expect(container.querySelector(".text-positive")).not.toBeNull();
    expect(container.querySelector(".text-negative")).toBeNull();
  });
});
