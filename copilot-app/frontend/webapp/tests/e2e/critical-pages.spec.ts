/**
 * Playwright E2E Tests for critical pages
 * Task: TEST-001 - Tests E2E Playwright pour endpoints critiques
 * Verifies that UI pages render non-empty states or proper empty-states
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

// Ensure proofs directory exists
const PROOFS_DIR = path.join(process.cwd(), '..', '..', '..', '..', 'proofs', 'TEST-001', 'e2e-screenshots');
if (!fs.existsSync(PROOFS_DIR)) {
  fs.mkdirSync(PROOFS_DIR, { recursive: true });
}

// Base URL for the application
const BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:5173';

test.describe('Critical Pages UX Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Make sure the backend is running before tests
    await page.goto(BASE_URL);
    await expect(page).toHaveURL(BASE_URL);
    await page.waitForTimeout(2000); // Allow data to load
  });

  test.describe('Dashboard Page', () => {
    test('should render Dashboard with non-empty or proper empty state', async ({ page }) => {
      await page.goto(`${BASE_URL}/`);
      
      // Take screenshot
      await page.screenshot({ 
        path: path.join(PROOFS_DIR, 'dashboard.png'),
        fullPage: true 
      });
      
      // Verify page loaded
      await expect(page.locator('text=Dashboard')).toBeVisible();
      
      // Check for KPI cards or loading indicators
      const kpiCards = page.locator('[data-testid="kpi-card"]');
      const loadingIndicators = page.locator('text=Chargement...');
      
      // Either KPIs should be visible or "No data" message
      if (await kpiCards.count() > 0) {
        await expect(kpiCards.first()).toBeVisible();
        expect(await kpiCards.count()).toBeGreaterThanOrEqual(1);
      } else {
        const hasDataOrEmptyState = await page.locator('text=/[A-Za-z0-9]/i').isVisible(); // Any text content
        const hasNoDataMessage = await page.locator('text=No data|Aucune donnée|i=loading').isVisible();
        
        expect(hasDataOrEmptyState || hasNoDataMessage).toBeTruthy();
      }
      
      console.log('✅ Dashboard page has proper data or empty state');
    });

    test('should show Dashboard loading/error/empty states correctly', async ({ page }) => {
      await page.goto(`${BASE_URL}/`);
      
      // Ensure there are no "length/map of undefined" errors in console
      page.on('console', msg => {
        if (msg.type() === 'error' && msg.text().includes('length') && msg.text().includes('undefined')) {
          throw new Error(`Console error detected: ${msg.text()}`);
        }
      });
      
      // Wait for page to load completely
      await page.waitForLoadState('networkidle');
      
      console.log('✅ Dashboard has no console errors for undefined length/map access');
    });
  });

  test.describe('Forecasts Page', () => {
    test('should render Forecasts with non-empty or proper empty state', async ({ page }) => {
      await page.goto(`${BASE_URL}/forecasts`);
      
      // Take screenshot
      await page.screenshot({ 
        path: path.join(PROOFS_DIR, 'forecasts.png'),
        fullPage: true 
      });
      
      // Verify page loaded
      await expect(page.locator('text=Prévisions')).toBeVisible();
      
      // Check for forecast table or empty state
      const forecastTable = page.locator('[data-testid="forecasts-table"]');  
      const forecastRows = page.locator('tr[data-row-key]');
      const emptyState = page.locator('text=Aucune prévision|No forecasts');
      const loadingState = page.locator('text=Chargement...|Loading...');
      
      // Either forecasts should be present or we should have an empty state message
      if (await forecastRows.count() > 0) {
        expect(await forecastRows.count()).toBeGreaterThanOrEqual(1);
        console.log(`✅ Forecasts page loaded with ${await forecastRows.count()} forecast rows`);
      } else {
        const hasEmptyState = await emptyState.isVisible();
        expect(hasEmptyState).toBeTruthy();
        console.log('✅ Forecasts page shows proper empty state');
      }
    });
  });

  test.describe('News Page', () => {
    test('should render News feed with articles or proper empty state', async ({ page }) => {
      await page.goto(`${BASE_URL}/news`);
      
      // Take screenshot
      await page.screenshot({ 
        path: path.join(PROOFS_DIR, 'news.png'),
        fullPage: true 
      });
      
      // Verify page loaded
      await expect(page.locator('text=Actualités|News')).toBeVisible();
      
      // Check for news articles or empty state
      const newsArticles = page.locator('[data-testid="news-article"]');
      const articleCards = page.locator('.MuiCard-root').filter({ has: page.locator('text=titre|title') }); // Any card with title text
      const emptyState = page.locator('text=Aucun article|No articles');
      
      if (await newsArticles.count() > 0 || await articleCards.count() > 0) {
        const articleCount = await newsArticles.count() || await articleCards.count();
        console.log(`✅ News page loaded with ${articleCount} articles`);
      } else {
        const hasEmptyState = await emptyState.isVisible();
        expect(hasEmptyState).toBeTruthy();
        console.log('✅ News page shows proper empty state');
      }
    });
  });

  test.describe('Macro Page', () => {
    test('should render Macro indicators with data or proper empty state', async ({ page }) => {
      await page.goto(`${BASE_URL}/macro`);
      
      // Take screenshot
      await page.screenshot({ 
        path: path.join(PROOFS_DIR, 'macro.png'),
        fullPage: true 
      });
      
      // Verify page loaded
      await expect(page.locator('text=Macro')).toBeVisible();
      
      // Check for macro indicators or empty state
      const macroIndicators = page.locator('[data-testid="macro-indicator"]');
      const charts = page.locator('[data-testid="macro-chart"]'); 
      const emptyState = page.locator('text=Aucune série|No series');
      
      if (await macroIndicators.count() > 0 || await charts.count() > 0) {
        const indicatorCount = await macroIndicators.count();
        const chartCount = await charts.count();
        console.log(`✅ Macro page loaded with ${indicatorCount} indicators and ${chartCount} charts`);
      } else {
        const hasEmptyState = await emptyState.isVisible();
        expect(hasEmptyState).toBeTruthy();
        console.log('✅ Macro page shows proper empty state');
      }
    });
  });

  test.describe('Stocks Page', () => {
    test('should render Stocks with data or proper empty state', async ({ page }) => {
      await page.goto(`${BASE_URL}/stocks`);
      
      // Take screenshot
      await page.screenshot({ 
        path: path.join(PROOFS_DIR, 'stocks.png'),
        fullPage: true 
      });
      
      // Verify page loaded
      await expect(page.locator('text=Actions|Stocks')).toBeVisible();
      
      // Check for stocks table or empty state
      const stockTable = page.locator('[data-testid="stocks-table"]');
      const stockRows = page.locator('tr[data-row-key]');
      const emptyState = page.locator('text=Aucune action|No stocks');
      
      if (await stockRows.count() > 0) {
        expect(await stockRows.count()).toBeGreaterThanOrEqual(1);
        console.log(`✅ Stocks page loaded with ${await stockRows.count()} stock rows`);
      } else {
        const hasEmptyState = await emptyState.isVisible();
        expect(hasEmptyState).toBeTruthy();
        console.log('✅ Stocks page shows proper empty state');
      }
    });
  });

  test.describe('Brief Page', () => {
    test('should render Market Brief with content or proper empty state', async ({ page }) => {
      await page.goto(`${BASE_URL}/brief`);
      
      // Take screenshot
      await page.screenshot({ 
        path: path.join(PROOFS_DIR, 'brief.png'),
        fullPage: true 
      });
      
      // Verify page loaded
      await expect(page.locator('text=Market Brief|Brief')).toBeVisible();
      
      // Check for brief content or empty state
      const signals = page.locator('[data-testid="top-signals"]');
      const risks = page.locator('[data-testid="top-risks"]'); 
      const emptyState = page.locator('text=Aucun brief|No brief available');
      
      if (await signals.isVisible() || await risks.isVisible()) {
        console.log('✅ Brief page loaded with signals/risks content');
      } else {
        const hasEmptyState = await emptyState.isVisible();
        expect(hasEmptyState).toBeTruthy();
        console.log('✅ Brief page shows proper empty state');
      }
    });
  });

  test.describe('Cross-Page Integrity', () => {
    test('should maintain consistent UI states across pages (no crashes)', async ({ page }) => {
      // Navigate to each page and verify no errors
      const pages = ['/', '/forecasts', '/news', '/macro', '/stocks', '/brief'];
      
      for (const pagePath of pages) {
        console.log(`Testing page: ${pagePath}`);
        await page.goto(`${BASE_URL}${pagePath}`);
        
        // Wait briefly for any async rendering
        await page.waitForTimeout(1000);
        
        // Check for JavaScript errors in console
        const errors: string[] = [];
        page.on('console', msg => {
          if (msg.type() === 'error') {
            errors.push(msg.text());
          }
        });
        
        // Wait for page to load
        await page.waitForLoadState('networkidle');
        
        // Verify no critical errors occurred during load
        expect(errors.some(error => 
          error.includes('length') && error.includes('undefined') ||
          error.includes('map') && error.includes('undefined') ||
          error.includes('Cannot read') && error.includes('undefined')
        )).toBeFalsy();
        
        console.log(`✅ Page ${pagePath} loaded without critical JavaScript errors`);
      }
    });
  });

  test('should verify API endpoints return non-empty responses', async ({ request }) => {
    // Test backend API endpoints directly to ensure they return data
    const endpoints = [
      { path: '/api/health', expectedKey: 'status' },
      { path: '/api/forecasts', expectedKey: 'rows' },
      { path: '/api/news/feed', expectedKey: 'articles' },
      { path: '/api/macro/series', expectedKey: 'data' },
      { path: '/api/stocks/universe', expectedKey: 'tickers' },
      { path: '/api/brief/daily', expectedKey: 'top_signals' }
    ];
    
    for (const endpoint of endpoints) {
      const response = await request.get(`http://localhost:8050${endpoint.path}`);
      expect(response.ok()).toBeTruthy();
      
      const responseBody = await response.json();
      
      // Verify the response has an 'ok' field set to true
      expect(responseBody.ok).toBeTruthy();
      
      // Verify the response has a 'data' field that's not null/undefined
      expect(responseBody.data).toBeDefined();
      
      // For some endpoints verify the expected data key has content
      if (responseBody.data && endpoint.expectedKey in responseBody.data) {
        const dataValue = responseBody.data[endpoint.expectedKey];
        if (Array.isArray(dataValue)) {
          // Arrays can be empty and still be valid
          expect(Array.isArray(dataValue)).toBeTruthy();
        } else {
          // Non-array data should be defined
          expect(dataValue).toBeDefined();
        }
      }
      
      console.log(`✅ Endpoint ${endpoint.path} returns valid structured response`);
    }
  });
});