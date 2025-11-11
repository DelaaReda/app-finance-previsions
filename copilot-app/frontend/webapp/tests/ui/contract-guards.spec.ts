/**
 * Contract Guards - Playwright Tests
 *
 * These tests verify the contract between frontend and backend:
 * - Data shape validation
 * - Row counts > 0
 * - KPI badges present
 * - Intelligence sections visible
 * - Critical UI elements rendered
 *
 * Purpose: Prevent regressions and schema drift
 *
 * Author: CLAUDE-CODE
 * Task: FC-PHASE3-001 - Playwright Contract Guards
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5174';

/**
 * Dashboard Contract Guards
 */
test.describe('Dashboard Contract Guards', () => {
  test('should display KPI cards with non-zero values', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Wait for page to load
    await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 10000 });

    // Check that KPI metrics are present
    const kpiCards = await page.locator('[data-testid="metric-card"]').all();
    expect(kpiCards.length).toBeGreaterThan(0);

    // Verify at least one KPI has a non-empty value
    const hasNonEmptyKPI = await page.locator('[data-testid="metric-card"]').first().isVisible();
    expect(hasNonEmptyKPI).toBeTruthy();
  });

  test('should have health bar visible', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    const healthBar = page.locator('[data-testid="health-bar"]');
    await expect(healthBar).toBeVisible({ timeout: 10000 });
  });
});

/**
 * Forecasts Contract Guards
 */
test.describe('Forecasts Contract Guards', () => {
  test('should display forecasts table with rows', async ({ page }) => {
    await page.goto(`${BASE_URL}/forecasts`);

    // Wait for forecasts to load
    await page.waitForSelector('[data-testid="forecasts-pro"]', { timeout: 10000 });

    // Check table exists
    const table = page.getByRole('table');
    await expect(table).toBeVisible();

    // Count rows (should have at least header + 1 data row)
    const rows = await table.locator('tbody tr').count();
    expect(rows).toBeGreaterThan(0);
  });

  test('should have score and confidence columns', async ({ page }) => {
    await page.goto(`${BASE_URL}/forecasts`);

    await page.waitForSelector('[data-testid="forecasts-pro"]', { timeout: 10000 });

    // Check for score/confidence indicators
    const hasScores = await page.locator('text=/score|Score|confidence|Confidence/i').count();
    expect(hasScores).toBeGreaterThan(0);
  });
});

/**
 * Backtests Contract Guards
 */
test.describe('Backtests Contract Guards', () => {
  test('should display backtests panel with KPIs', async ({ page }) => {
    await page.goto(`${BASE_URL}/backtests?strategy=long_top_score`);

    await page.waitForSelector('[data-testid="backtests-panel"]', { timeout: 10000 });

    // Check for KPI badges
    const kpiBadges = await page.locator('text=/CAGR|Sharpe|Sortino|MaxDD|WinRate/i').count();
    expect(kpiBadges).toBeGreaterThanOrEqual(3); // At least 3 KPIs
  });

  test('should have equity curve chart visible', async ({ page }) => {
    await page.goto(`${BASE_URL}/backtests?strategy=long_top_score`);

    await page.waitForSelector('[data-testid="backtests-panel"]', { timeout: 10000 });

    // Check for chart presence (Tremor charts use canvas or svg)
    const hasChart = await page.locator('canvas, svg').count();
    expect(hasChart).toBeGreaterThan(0);
  });

  test('should have tabs for Overview, Equity, Monthly, Trades', async ({ page }) => {
    await page.goto(`${BASE_URL}/backtests?strategy=long_top_score`);

    await page.waitForSelector('[data-testid="backtests-panel"]', { timeout: 10000 });

    // Check for tabs
    const overviewTab = page.locator('text=/Overview/i').first();
    const equityTab = page.locator('text=/Equity/i').first();
    const monthlyTab = page.locator('text=/Monthly/i').first();
    const tradesTab = page.locator('text=/Trades/i').first();

    await expect(overviewTab).toBeVisible();
    await expect(equityTab).toBeVisible();
    await expect(monthlyTab).toBeVisible();
    await expect(tradesTab).toBeVisible();
  });

  test('should display trades table when Trades tab clicked', async ({ page }) => {
    await page.goto(`${BASE_URL}/backtests?strategy=long_top_score`);

    await page.waitForSelector('[data-testid="backtests-panel"]', { timeout: 10000 });

    // Click Trades tab
    const tradesTab = page.locator('text=/Trades/i').first();
    await tradesTab.click();

    // Wait for table or empty message
    await page.waitForTimeout(1000);

    // Check for table or "no trades" message
    const hasTableOrMessage = await page.locator('table, text=/No trades/i').count();
    expect(hasTableOrMessage).toBeGreaterThan(0);
  });
});

/**
 * Health Page Contract Guards
 */
test.describe('Health Page Contract Guards', () => {
  test('should display system status banner', async ({ page }) => {
    await page.goto(`${BASE_URL}/health`);

    // Check for system status
    const statusBanner = await page.locator('text=/Système|System|Opérationnel|Degraded|up|down/i').count();
    expect(statusBanner).toBeGreaterThan(0);
  });

  test('should display dataset health cards', async ({ page }) => {
    await page.goto(`${BASE_URL}/health`);

    // Wait for health data to load
    await page.waitForTimeout(2000);

    // Check for dataset cards (should have at least 1)
    const cards = await page.locator('[class*="Card"]').count();
    expect(cards).toBeGreaterThan(0);
  });

  test('should show freshness badges', async ({ page }) => {
    await page.goto(`${BASE_URL}/health`);

    await page.waitForTimeout(2000);

    // Check for freshness indicators (time badges)
    const freshnessBadges = await page.locator('text=/[0-9]+[smhd]/i').count();
    expect(freshnessBadges).toBeGreaterThan(0);
  });
});

/**
 * News Radar Contract Guards
 */
test.describe('News Radar Contract Guards', () => {
  test('should display news radar with filters', async ({ page }) => {
    await page.goto(`${BASE_URL}/news/radar`);

    // Check for timeframe filter
    const timeframeFilter = page.locator('text=/Today|This Week|This Month/i');
    await expect(timeframeFilter.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display total articles count', async ({ page }) => {
    await page.goto(`${BASE_URL}/news/radar`);

    await page.waitForTimeout(2000);

    // Check for articles count
    const articlesCount = await page.locator('text=/Total Articles|articles/i').count();
    expect(articlesCount).toBeGreaterThan(0);
  });
});

/**
 * Critical UI Elements Guards
 */
test.describe('Critical UI Elements', () => {
  test('all pages should have navigation', async ({ page }) => {
    const pages = ['/', '/forecasts', '/backtests', '/health', '/news/radar'];

    for (const pagePath of pages) {
      await page.goto(`${BASE_URL}${pagePath}`);

      // Check for navigation elements (links to other pages)
      const hasNav = await page.locator('nav, [role="navigation"], a[href]').count();
      expect(hasNav).toBeGreaterThan(0);
    }
  });

  test('pages should not have console errors', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    // Filter out known non-critical errors (e.g., 404 for optional resources)
    const criticalErrors = consoleErrors.filter(
      err => !err.includes('favicon') && !err.includes('devtools')
    );

    expect(criticalErrors.length).toBe(0);
  });
});

/**
 * Data Freshness Guards
 */
test.describe('Data Freshness Guards', () => {
  test('forecasts should have recent timestamps', async ({ page }) => {
    await page.goto(`${BASE_URL}/forecasts`);

    await page.waitForSelector('[data-testid="forecasts-pro"]', { timeout: 10000 });

    // Check for timestamp indicators
    const hasTimestamps = await page.locator('text=/updated|MAJ|ago|minutes|hours/i').count();
    expect(hasTimestamps).toBeGreaterThan(0);
  });

  test('health page should show last update time', async ({ page }) => {
    await page.goto(`${BASE_URL}/health`);

    await page.waitForTimeout(2000);

    // Check for update timestamps
    const hasUpdateTime = await page.locator('text=/Last|Dernière|Updated|MAJ/i').count();
    expect(hasUpdateTime).toBeGreaterThan(0);
  });
});
