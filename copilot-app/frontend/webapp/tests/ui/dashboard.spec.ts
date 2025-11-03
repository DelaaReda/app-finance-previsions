import { test, expect } from "@playwright/test";

test.describe("Dashboard page", () => {
  test("renders overview and captures screenshot", async ({ page }) => {
    await page.goto("http://localhost:5173/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(500);

    await expect(
      page.getByRole("heading", { name: "Dashboard - Vue d'ensemble" })
    ).toBeVisible();

    await expect(page.getByRole("heading", { name: "Filtres (Secteur, Horizon, Thème)" })).toBeVisible();

    await expect(page.getByPlaceholder("ex: AAPL,MSFT,GOOGL")).toBeVisible();

    await expect(page).toHaveScreenshot("dashboard-page.png", {
      maxDiffPixelRatio: 0.02,
      fullPage: true,
    });
  });
});
