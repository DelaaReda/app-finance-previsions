import { test, expect } from "@playwright/test";

test("News page renders and shows cards", async ({ page }) => {
  await page.goto("http://localhost:5173/news");
  await expect(page.getByRole("heading", { name: "News" })).toBeVisible();

  // Attend qu'au moins 5 cartes apparaissent (mock ou API)
  await page.waitForSelector('[data-testid="news-card"]', { state: "visible" });
  const cards = await page.locator('[data-testid="news-card"]').all();
  expect(cards.length).toBeGreaterThanOrEqual(2); // 2 en mock, ≥5 si API

  // Screenshot baseline
  await expect(page).toHaveScreenshot("news-page.png", { maxDiffPixelRatio: 0.015 });
});
