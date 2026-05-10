import { expect, test } from "@playwright/test";

const API_URL = process.env.E2E_API_URL || "http://localhost:8000";

test.describe("smoke", () => {
  test.beforeAll(async () => {
    // Graceful skip when no backend is reachable — keeps `npm run test:e2e`
    // safe to run without the dev stack up.
    try {
      const res = await fetch(`${API_URL}/api/health`);
      if (!res.ok) test.skip(true, `backend unhealthy: ${res.status}`);
    } catch (e) {
      test.skip(true, `backend unreachable at ${API_URL}: ${e}`);
    }
  });

  test("home → backtest → results", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /backtest/i }).first().click();
    await expect(page).toHaveURL(/\/backtest/);

    // Form has SPY/AAPL/MSFT defaults; only override the date range to one
    // that the seeded smoke ingest covers (last 2 years, broad enough to fit).
    const start = page.getByLabel(/start date/i);
    const end = page.getByLabel(/end date/i);
    await start.fill("2023-06-05");
    await end.fill("2024-05-31");

    await page.getByRole("button", { name: /run backtest/i }).click();

    // Results section appears once the backtest completes.
    await expect(page.getByText(/total return/i).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/sharpe/i).first()).toBeVisible();
  });
});
