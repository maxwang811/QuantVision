import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EfficientFrontierChart } from "../backtest/EfficientFrontierChart";

describe("EfficientFrontierChart", () => {
  test("renders empty-state when no points", () => {
    render(<EfficientFrontierChart points={[]} />);
    expect(screen.getByText(/no frontier/i)).toBeInTheDocument();
  });

  test("renders an svg when given points and explicit dimensions", () => {
    const points = [
      { expected_return: 0.05, volatility: 0.10, sharpe_ratio: 0.5, weights: [0.5, 0.5] },
      { expected_return: 0.08, volatility: 0.15, sharpe_ratio: 0.6, weights: [0.7, 0.3] },
      { expected_return: 0.10, volatility: 0.20, sharpe_ratio: 0.55, weights: [0.9, 0.1] },
    ];
    const { container } = render(
      <EfficientFrontierChart
        points={points}
        minVariance={points[0]}
        maxSharpe={points[1]}
        width={400}
        height={300}
      />,
    );
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
