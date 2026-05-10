import "@testing-library/jest-dom/vitest";

// Recharts' ResponsiveContainer uses ResizeObserver — jsdom doesn't ship one.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
const g = globalThis as unknown as { ResizeObserver?: typeof ResizeObserverStub };
if (typeof g.ResizeObserver === "undefined") {
  g.ResizeObserver = ResizeObserverStub;
}
