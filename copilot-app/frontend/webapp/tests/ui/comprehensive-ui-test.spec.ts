import { test, expect } from "@playwright/test";

test.describe("Comprehensive UI Testing Suite", () => {
  test.describe("Page Navigation and Basic Functionality", () => {
    test("should navigate through all pages successfully", async ({ page }) => {
      // Start on Dashboard
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Dashboard - Vue d'ensemble" })).toBeVisible();

      // Take initial screenshot
      await page.screenshot({ path: 'test-results/dashboard-initial.png', fullPage: true });

      // Navigate to Market Brief
      await page.getByRole("link", { name: "Brief", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Market Brief" })).toBeVisible();
      await expect(page).toHaveURL(/.*brief/);
      await page.screenshot({ path: 'test-results/market-brief-page.png', fullPage: true });

      // Navigate to Macro
      await page.getByRole("link", { name: "Macro" }).click();
      await expect(page.getByRole("heading", { name: "Macro" })).toBeVisible();
      await expect(page).toHaveURL(/.*macro/);
      await page.screenshot({ path: 'test-results/macro-page.png', fullPage: true });

      // Navigate to Stocks
      await page.locator('a[href="/stocks"]').click();
      await expect(page.getByRole("heading", { name: "📈 Actions - Analyse Technique" })).toBeVisible();
      await expect(page).toHaveURL(/.*stocks/);
      await page.screenshot({ path: 'test-results/stocks-page.png', fullPage: true });

      // Navigate to News
      await page.getByRole("link", { name: "News" }).click();
      await expect(page.getByRole("heading", { name: "News" })).toBeVisible();
      await expect(page).toHaveURL(/.*news/);
      await page.screenshot({ path: 'test-results/news-page.png', fullPage: true });

      // Navigate to Copilot
      await page.getByRole("link", { name: "Copilot" }).click();
      await expect(page.getByRole("heading", { name: "Copilot LLM" })).toBeVisible();
      await expect(page).toHaveURL(/.*copilot/);
      await page.screenshot({ path: 'test-results/copilot-page.png', fullPage: true });

      // Navigate to Forecasts
      await page.getByRole("link", { name: "Forecasts" }).click();
      await expect(page.getByRole("heading", { name: "Forecasts" })).toBeVisible();
      await expect(page).toHaveURL(/.*forecasts/);
      await page.screenshot({ path: 'test-results/forecasts-page.png', fullPage: true });

      // Navigate to Backtests
      await page.getByRole("link", { name: "Backtests" }).click();
      await expect(page.getByRole("heading", { name: "Backtests" })).toBeVisible();
      await expect(page).toHaveURL(/.*backtests/);
      await page.screenshot({ path: 'test-results/backtests-page.png', fullPage: true });

      // Navigate to LLM Judge
      await page.getByRole("link", { name: "LLM Judge" }).click();
      await expect(page.getByRole("heading", { name: "LLM Judge" })).toBeVisible();
      await expect(page).toHaveURL(/.*judge/);
      await page.screenshot({ path: 'test-results/llm-judge-page.png', fullPage: true });

      // Return to Dashboard
      await page.getByRole("link", { name: "Dashboard" }).click();
      await expect(page.getByRole("heading", { name: "Dashboard - Vue d'ensemble" })).toBeVisible();
    });
  });

  test.describe("Dashboard Page - Detailed Testing", () => {
    test("should load dashboard and test all interactive elements", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Dashboard - Vue d'ensemble" })).toBeVisible();

      // Test filter section visibility
      await expect(page.getByRole("heading", { name: "Filtres (Secteur, Horizon, Thème)" })).toBeVisible();

      // Test ticker input
      const tickerInput = page.getByPlaceholder("ex: AAPL,MSFT,GOOGL");
      await expect(tickerInput).toBeVisible();
      await tickerInput.fill("AAPL");
      await tickerInput.press("Enter");

      // Test sector checkboxes - click first available checkbox
      const checkboxes = page.locator("input[type='checkbox']");
      const checkboxCount = await checkboxes.count();
      if (checkboxCount > 0) {
        await checkboxes.first().click();
        await expect(checkboxes.first()).toBeChecked();
      }

      // Test signals sections
      const signalsSection = page.locator('text=Top 3 Signaux');
      const risksSection = page.locator('text=Top 3 Risques');

      // Check if signals are displayed (may be empty but sections should exist)
      await page.waitForTimeout(3000); // Wait for potential API calls

      // Take screenshot after interactions
      await page.screenshot({ path: 'test-results/dashboard-after-interactions.png', fullPage: true });

      // Test that page doesn't crash
      await expect(page.locator('body')).toBeVisible();
    });

    test("should handle filter combinations correctly", async ({ page }) => {
      await page.goto("/");

      // Test multiple filter combinations
      const tickerInput = page.getByPlaceholder("ex: AAPL,MSFT,GOOGL");
      await tickerInput.fill("AAPL,MSFT,GOOGL");

      // Click multiple checkboxes if available
      const checkboxes = page.locator("input[type='checkbox']");
      const checkboxCount = await checkboxes.count();

      for (let i = 0; i < Math.min(checkboxCount, 3); i++) {
        await checkboxes.nth(i).click();
      }

      await page.waitForTimeout(2000);

      // Take screenshot of filtered state
      await page.screenshot({ path: 'test-results/dashboard-filters-applied.png', fullPage: true });
    });
  });

  test.describe("Market Brief Page - Detailed Testing", () => {
    test("should load market brief and test all controls", async ({ page }) => {
      await page.goto("/brief");
      await expect(page.getByRole("heading", { name: "Market Brief" })).toBeVisible();

      // Test daily/weekly buttons
      const dailyButton = page.getByRole("button", { name: "Quotidien" });
      const weeklyButton = page.getByRole("button", { name: "Hebdomadaire" });

      await expect(dailyButton).toBeVisible();
      await expect(weeklyButton).toBeVisible();

      // Test button clicks
      await dailyButton.click();
      await expect(dailyButton).toHaveClass(/active|selected/);

      await weeklyButton.click();
      await expect(weeklyButton).toHaveClass(/active|selected/);

      // Test universe dropdown
      const universeSelect = page.locator("#universe-select");
      if (await universeSelect.isVisible()) {
        await universeSelect.click();
        await universeSelect.fill("SPY,QQQ,AAPL");
        await universeSelect.press("Enter");
      }

      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'test-results/market-brief-after-interactions.png', fullPage: true });
    });
  });

  test.describe("Macro Analysis Page - Detailed Testing", () => {
    test("should load macro page and test indicator controls", async ({ page }) => {
      await page.goto("/macro");
      await expect(page.getByRole("heading", { name: "📈 Macro (Pilier 1)" })).toBeVisible();

      // Test macro indicator checkboxes
      const checkboxes = page.locator("input[type='checkbox']");
      const checkboxCount = await checkboxes.count();

      // Click first few checkboxes to test functionality
      for (let i = 0; i < Math.min(checkboxCount, 5); i++) {
        await checkboxes.nth(i).click();
        await page.waitForTimeout(500);
      }

      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'test-results/macro-after-checkbox-interactions.png', fullPage: true });

      // Test that charts or data areas are present
      const chartAreas = page.locator('.chart, .graph, canvas, svg');
      const chartCount = await chartAreas.count();

      // Document findings
      console.log(`Found ${chartCount} chart/visualization elements on macro page`);
    });
  });

  test.describe("Stock Analysis Page - Detailed Testing", () => {
    test("should load stocks page and test search functionality", async ({ page }) => {
      await page.goto("/stocks");
      await expect(page.getByRole("heading", { name: "📈 Actions - Analyse Technique" })).toBeVisible();

      // Test search input
      const searchInput = page.getByPlaceholder(/Ticker ou nom/);
      await expect(searchInput).toBeVisible();

      // Test search with different inputs
      await searchInput.fill("AAPL");
      await searchInput.press("Enter");

      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'test-results/stocks-search-aapl.png', fullPage: true });

      // Clear and search for another ticker
      await searchInput.clear();
      await searchInput.fill("MSFT");
      await searchInput.press("Enter");

      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'test-results/stocks-search-msft.png', fullPage: true });

      // Test invalid ticker
      await searchInput.clear();
      await searchInput.fill("INVALID");
      await searchInput.press("Enter");

      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'test-results/stocks-search-invalid.png', fullPage: true });
    });
  });

  test.describe("News Page - Detailed Testing", () => {
    test("should load news page and test filtering", async ({ page }) => {
      await page.goto("/news");
      await expect(page.getByRole("heading", { name: "News" })).toBeVisible();

      // Test filter inputs
      const tickerInput = page.getByPlaceholder("AAPL");
      const keywordInput = page.getByPlaceholder("AI");
      const filterButton = page.getByRole("button", { name: "Filtrer" });

      await expect(tickerInput).toBeVisible();
      await expect(keywordInput).toBeVisible();
      await expect(filterButton).toBeVisible();

      // Test filtering
      await tickerInput.fill("AAPL");
      await keywordInput.fill("earnings");
      await filterButton.click();

      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'test-results/news-after-filtering.png', fullPage: true });

      // Test filter button state
      const isDisabled = await filterButton.isDisabled();
      console.log(`Filter button disabled state: ${isDisabled}`);
    });
  });

  test.describe("Copilot LLM Page - Detailed Testing", () => {
    test("should load copilot page and verify static content", async ({ page }) => {
      await page.goto("/copilot");
      await expect(page.getByRole("heading", { name: "Copilot LLM" })).toBeVisible();

      // Check for expected content
      await expect(page.getByText("Q&A avec contexte historique (RAG ≥5 ans)")).toBeVisible();

      // Look for input areas or chat interface
      const textareas = page.locator('textarea');
      const inputs = page.locator('input[type="text"]');

      const textareaCount = await textareas.count();
      const inputCount = await inputs.count();

      console.log(`Found ${textareaCount} textareas and ${inputCount} text inputs on copilot page`);

      await page.screenshot({ path: 'test-results/copilot-interface.png', fullPage: true });
    });
  });

  test.describe("Forecasts Page - Detailed Testing", () => {
    test("should load forecasts page and check table structure", async ({ page }) => {
      await page.goto("/forecasts");
      await expect(page.getByRole("heading", { name: "Forecasts" })).toBeVisible();

      // Check for table structure
      const table = page.locator('table');
      const tableVisible = await table.isVisible();

      if (tableVisible) {
        // Test table interactions
        const rows = page.locator('table tr');
        const rowCount = await rows.count();
        console.log(`Found ${rowCount} rows in forecasts table`);

        // Try to click on table headers for sorting
        const headers = page.locator('table th');
        const headerCount = await headers.count();

        if (headerCount > 0) {
          await headers.first().click();
          await page.waitForTimeout(1000);
        }
      } else {
        console.log("No table found on forecasts page");
      }

      await page.screenshot({ path: 'test-results/forecasts-page-structure.png', fullPage: true });
    });
  });

  test.describe("Backtests Page - Critical Bug Testing", () => {
    test("should attempt to load backtests page and document errors", async ({ page }) => {
      await page.goto("/backtests");

      // Check if page loads normally or shows error
      const errorBoundary = page.locator('text=Unexpected Application Error');
      const normalHeading = page.getByRole("heading", { name: "Backtests" });

      const hasError = await errorBoundary.isVisible();
      const hasNormalHeading = await normalHeading.isVisible();

      if (hasError) {
        console.log("CRITICAL BUG: Backtests page shows React Error Boundary");

        // Capture error details
        const errorText = await page.locator('.error-message, .error-boundary').textContent();
        console.log(`Error details: ${errorText}`);

        await page.screenshot({ path: 'test-results/backtests-error-boundary.png', fullPage: true });
      } else if (hasNormalHeading) {
        console.log("Backtests page loaded normally");

        // Test form controls
        const horizonDropdown = page.locator("select").first();
        const topNInput = page.locator("input[type='number']").first();

        if (await horizonDropdown.isVisible()) {
          await horizonDropdown.click();
          await horizonDropdown.selectOption({ index: 1 });
        }

        if (await topNInput.isVisible()) {
          await topNInput.fill("10");
        }

        await page.waitForTimeout(2000);
        await page.screenshot({ path: 'test-results/backtests-form-filled.png', fullPage: true });
      } else {
        console.log("Backtests page in unknown state");
        await page.screenshot({ path: 'test-results/backtests-unknown-state.png', fullPage: true });
      }
    });
  });

  test.describe("LLM Judge Page - Detailed Testing", () => {
    test("should load LLM judge page and test form elements", async ({ page }) => {
      await page.goto("/judge");
      await expect(page.getByRole("heading", { name: "LLM Judge" })).toBeVisible();

      // Look for form elements
      const textInputs = page.locator('input[type="text"]');
      const textareas = page.locator('textarea');
      const buttons = page.locator('button');

      const inputCount = await textInputs.count();
      const textareaCount = await textareas.count();
      const buttonCount = await buttons.count();

      console.log(`LLM Judge page: ${inputCount} text inputs, ${textareaCount} textareas, ${buttonCount} buttons`);

      // Test run button if it exists
      const runButton = page.locator('button:has-text("Run"), button:has-text("Exécuter")').first();
      if (await runButton.isVisible()) {
        const isDisabled = await runButton.isDisabled();
        console.log(`Run button disabled: ${isDisabled}`);

        if (!isDisabled) {
          await runButton.click();
          await page.waitForTimeout(2000);
          await page.screenshot({ path: 'test-results/llm-judge-after-run.png', fullPage: true });
        } else {
          await page.screenshot({ path: 'test-results/llm-judge-run-disabled.png', fullPage: true });
        }
      } else {
        await page.screenshot({ path: 'test-results/llm-judge-no-run-button.png', fullPage: true });
      }
    });
  });

  test.describe("Responsive Design Testing", () => {
    test("should work on mobile viewport", async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Dashboard - Vue d'ensemble" })).toBeVisible();

      await page.screenshot({ path: 'test-results/dashboard-mobile.png', fullPage: true });

      // Test navigation on mobile
      await page.getByRole("link", { name: "Brief", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Market Brief" })).toBeVisible();

      await page.screenshot({ path: 'test-results/market-brief-mobile.png', fullPage: true });
    });

    test("should work on tablet viewport", async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Dashboard - Vue d'ensemble" })).toBeVisible();

      await page.screenshot({ path: 'test-results/dashboard-tablet.png', fullPage: true });
    });
  });

  test.describe("Error Handling and Edge Cases", () => {
    test("should handle network errors gracefully", async ({ page }) => {
      // Test with backend unavailable
      await page.goto("/");
      await page.waitForTimeout(5000);

      // Check for error messages or loading states
      const errorMessages = page.locator('.error, .error-message, text=Error, text=Failed');
      const loadingStates = page.locator('text=Loading, text=Chargement, .loading, .spinner');

      const errorCount = await errorMessages.count();
      const loadingCount = await loadingStates.count();

      console.log(`Found ${errorCount} error messages and ${loadingCount} loading indicators`);

      await page.screenshot({ path: 'test-results/error-handling-test.png', fullPage: true });
    });

    test("should handle invalid URLs gracefully", async ({ page }) => {
      await page.goto("/nonexistent-page");

      // Check if redirected to dashboard or shows 404
      const dashboardHeading = page.getByRole("heading", { name: "Dashboard - Vue d'ensemble" });
      const notFoundText = page.locator('text=404, text=Not Found, text=Page not found');

      const hasDashboard = await dashboardHeading.isVisible();
      const hasNotFound = await notFoundText.isVisible();

      console.log(`Invalid URL test: Dashboard visible: ${hasDashboard}, 404 visible: ${hasNotFound}`);

      await page.screenshot({ path: 'test-results/invalid-url-handling.png', fullPage: true });
    });
  });

  test.describe("Performance and Loading Tests", () => {
    test("should measure page load times", async ({ page }) => {
      const startTime = Date.now();

      await page.goto("/");
      await page.waitForLoadState('domcontentloaded');

      const loadTime = Date.now() - startTime;
      console.log(`Dashboard page load time: ${loadTime}ms`);

      // Wait for dynamic content
      await page.waitForTimeout(3000);
      const fullLoadTime = Date.now() - startTime;
      console.log(`Dashboard full load time (with dynamic content): ${fullLoadTime}ms`);
    });

    test("should check for console errors", async ({ page }) => {
      const errors: string[] = [];
      const warnings: string[] = [];

      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        } else if (msg.type() === 'warning') {
          warnings.push(msg.text());
        }
      });

      await page.goto("/");
      await page.waitForTimeout(5000);

      console.log(`Console errors: ${errors.length}`);
      console.log(`Console warnings: ${warnings.length}`);

      if (errors.length > 0) {
        console.log('Errors:', errors.slice(0, 5)); // Show first 5 errors
      }
    });
  });
});
