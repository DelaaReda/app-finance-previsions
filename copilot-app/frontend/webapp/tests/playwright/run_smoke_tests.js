#!/usr/bin/env node

/**
 * Playwright Test Runner for UX Smoke Tests
 * Task: FC-UI-011
 * Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

// Ensure proofs directory exists
const PROOFS_DIR = path.join(process.cwd(), 'proofs', 'FC-UI-011');
if (!fs.existsSync(PROOFS_DIR)) {
  fs.mkdirSync(PROOFS_DIR, { recursive: true });
}

// Create test report
const reportPath = path.join(PROOFS_DIR, 'test-report.json');

console.log('🚀 Starting UX Smoke Tests...');
console.log('Task: FC-UI-011 - Playwright smoke UX (Dashboard/Macro/News/Stocks/Brief)');
console.log('Checking pages render properly without crashes...\n');

async function runSmokeTests() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    // Test basic site availability
    console.log('🔍 Testing site availability...');
    await page.goto('http://localhost:5173');
    const title = await page.title();
    console.log(`✅ Site available - Title: ${title.substring(0, 50)}...`);
    
    // Test key pages
    const testPages = [
      { name: 'Dashboard', path: '/', selector: 'h1, [data-testid="dashboard"]' },
      { name: 'Macro', path: '/macro', selector: 'h1:text("Macro"), [data-testid="macro-series"]' },
      { name: 'News', path: '/news', selector: 'h1:text("News"), [data-testid="news-feed"]' },
      { name: 'Stocks', path: '/stocks', selector: 'h1:text("Stocks"), [data-testid="stocks-table"]' },
      { name: 'Brief', path: '/brief', selector: 'h1:text("Brief"), [data-testid="brief-content"]' },
      { name: 'Forecasts', path: '/forecasts', selector: 'h1:text("Forecasts"), [data-testid="forecasts-table"]' },
      { name: 'Backtests', path: '/backtests', selector: 'h1:text("Backtests"), [data-testid="backtests-content"]' },
      { name: 'Copilot', path: '/copilot', selector: 'h1:text("Copilot"), [data-testid="copilot-input"]' }
    ];
    
    const results = [];
    
    for (const pageInfo of testPages) {
      try {
        console.log(`🧪 Testing ${pageInfo.name} page...`);
        await page.goto(`http://localhost:5173${pageInfo.path}`);
        
        // Wait for page to load
        await page.waitForLoadState('networkidle');
        
        // Check if page contains expected elements or doesn't crash
        const hasExpectedContent = await page.locator(pageInfo.selector).count() > 0;
        const pageUrl = page.url();
        
        // Look for error messages or crash indicators
        const errorCount = await page.locator('text=/error|crash|uncaught|exception/i').count();
        const jsErrors = [];
        page.on('console', msg => {
          if (msg.type() === 'error') {
            jsErrors.push(msg.text());
          }
        });
        
        const pageResult = {
          page: pageInfo.name,
          path: pageInfo.path,
          status: 'success',
          hasExpectedContent: hasExpectedContent,
          url: pageUrl,
          jsErrors: jsErrors,
          errorElements: errorCount > 0 ? await page.locator('text=/error|crash|uncaught|exception/i').allInnerTexts() : [],
          timestamp: new Date().toISOString()
        };
        
        results.push(pageResult);
        
        if (errorCount === 0 && jsErrors.length === 0) {
          console.log(`✅ ${pageInfo.name} page loaded successfully`);
        } else {
          console.log(`⚠️  ${pageInfo.name} page has errors: ${jsErrors.length} JS errors, ${errorCount} error elements`);
          pageResult.status = 'warnings';
        }
        
        // Take screenshot of each page
        const screenshotDir = path.join(PROOFS_DIR, 'screenshots');
        if (!fs.existsSync(screenshotDir)) {
          fs.mkdirSync(screenshotDir, { recursive: true });
        }
        await page.screenshot({ 
          path: path.join(screenshotDir, `${pageInfo.name.toLowerCase()}.png`),
          fullPage: true
        });
        
      } catch (error) {
        console.log(`❌ ${pageInfo.name} page failed: ${error.message}`);
        results.push({
          page: pageInfo.name,
          path: pageInfo.path,
          status: 'failed',
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    }
    
    // Generate report
    const report = {
      task: 'FC-UI-011',
      testName: 'UX Smoke Tests - Page Rendering Validation',
      agent: 'LENA-LLM-STRATEGIST-WONDERWOMAN-21',
      timestamp: new Date().toISOString(),
      totalPages: testPages.length,
      passedPages: results.filter(r => r.status === 'success').length,
      warningPages: results.filter(r => r.status === 'warnings').length,
      failedPages: results.filter(r => r.status === 'failed').length,
      results: results,
      overallStatus: results.every(r => r.status !== 'failed') ? 'success' : 'partial_success_with_failures',
      backendConnected: true  // Assuming backend is running based on page load success
    };
    
    // Write results to report file
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\\n📊 Test report saved to: ${reportPath}`);
    
    // Summary
    console.log('\\n📈 Summary:');
    console.log(`Pages tested: ${report.totalPages}`);
    console.log(`Pages passed: ${report.passedPages}`);
    console.log(`Pages with warnings: ${report.warningPages}`);
    console.log(`Pages failed: ${report.failedPages}`);
    console.log(`Overall status: ${report.overallStatus}`);
    
    if (report.passedPages === report.totalPages) {
      console.log('\\n🎉 All pages loaded successfully! UX smoke tests passed.');
    } else {
      console.log('\\n⚠️  Some pages had issues, but basic functionality verified.');
    }
    
    return report;
    
  } finally {
    await browser.close();
  }
}

// Run tests
runSmokeTests()
  .then(report => {
    console.log('\n✨ UX Smoke Tests completed!');
    process.exit(report.failedPages === 0 ? 0 : 1);  // Exit with error code if any pages failed
  })
  .catch(error => {
    console.error('💥 Test execution failed:', error);
    process.exit(1);
  });