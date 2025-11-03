import { test, expect } from "@playwright/test";

test.describe("Dashboard page", () => {
  test("renders overview and captures screenshot", async ({ page }) => {
    // Mock the Date constructor to make timestamps deterministic
    await page.addInitScript(() => {
      // Mock Date to always return a fixed date for visual consistency
      const mockDate = new Date('2025-01-01T10:00:00Z');
      const OriginalDate = Date;
      
      // Create a mock Date constructor
      const MockDate = class extends OriginalDate {
        constructor(...args: any[]) {
          if (args.length === 0) {
            // When no arguments are passed, return our fixed date
            super(mockDate.getTime());
          } else {
            // Otherwise, behave normally (for creating specific dates)
            super(...args);
          }
        }
      };

      // Also mock the static methods to return the same fixed date
      (MockDate as any).now = () => mockDate.getTime();
      (MockDate as any).parse = OriginalDate.parse;
      (MockDate as any).UTC = OriginalDate.UTC;

      // Replace the global Date object
      window.Date = MockDate as any;
    });

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
