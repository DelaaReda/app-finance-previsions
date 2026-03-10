/**
 * Tests for Strategy Playbooks Widget Integration (BATCH-15-DEV-03)
 *
 * Focused coverage for the real widget markup in Top Movers, News Impact,
 * and Stock Relationships.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const playbookIntegrationPath = path.join(__dirname, '../contracts/playbookIntegration.js');
const topMoversPath = path.join(__dirname, '../components/widgets/top-movers.html');
const stockRelationshipsPath = path.join(__dirname, '../components/widgets/stock-relationships.html');
const newsImpactPath = path.join(__dirname, '../components/widgets/news-impact.html');
const appJsPath = path.join(__dirname, '../pages/app.js');

const playbookIntegrationContent = fs.readFileSync(playbookIntegrationPath, 'utf8');
const topMoversContent = fs.readFileSync(topMoversPath, 'utf8');
const stockRelationshipsContent = fs.readFileSync(stockRelationshipsPath, 'utf8');
const newsImpactContent = fs.readFileSync(newsImpactPath, 'utf8');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

// Test results
let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`✓ ${name}`);
    passed++;
  } catch (error) {
    console.log(`✗ ${name}`);
    console.log(`  Error: ${error.message}`);
    failed++;
  }
}

console.log('\n🧪 BATCH-15-DEV-03: Widget Playbook Integration Tests\n');

// Test 1: PlaybookIntegration helper is available
test('PlaybookIntegration helper provides getPlaybookForTicker', () => {
  assert(
    playbookIntegrationContent.includes('window.PlaybookIntegration'),
    'Should expose PlaybookIntegration on window'
  );
  assert(
    playbookIntegrationContent.includes('getPlaybookForTicker'),
    'Should define getPlaybookForTicker'
  );
});

// Test 2: Get playbook for existing ticker
test('getPlaybookForTicker normalizes ticker lookups', () => {
  assert(
    playbookIntegrationContent.includes('ticker.toUpperCase().trim()'),
    'Should normalize ticker input before lookup'
  );
  assert(
    playbookIntegrationContent.includes('pb.ticker && pb.ticker.toUpperCase() === normalizedTicker'),
    'Should match playbooks by normalized ticker'
  );
});

// Test 3: Get playbook for non-existing ticker
test('fetchPlaybooks uses the shared strategy-playbooks API', () => {
  assert(
    playbookIntegrationContent.includes('window.getStrategyPlaybooks'),
    'Should reuse shared strategy-playbooks API helper'
  );
  assert(
    playbookIntegrationContent.includes('CACHE_TTL_MS'),
    'Should cache playbook payloads'
  );
});

// Test 4: Decision badge for GO decision
test('getDecisionBadge maps go decisions to BUY badges', () => {
  assert(playbookIntegrationContent.includes("badgeClass = 'badge-go'"), 'Should map go to badge-go');
  assert(playbookIntegrationContent.includes("badgeText = 'BUY'"), 'Should label go decisions as BUY');
});

// Test 5: Decision badge for HOLD decision
test('getDecisionBadge keeps hold decisions neutral', () => {
  assert(playbookIntegrationContent.includes("let badgeClass = 'badge-neutral'"), 'Should default to neutral badge');
  assert(playbookIntegrationContent.includes("let badgeText = 'HOLD'"), 'Should default to HOLD label');
});

// Test 6: Top Movers widget structure
test('Top Movers widget has playbook container for each ticker', () => {
  const tickers = ['NVDA', 'META', 'AAPL', 'MSFT', 'GOOGL'];
  tickers.forEach(ticker => {
    assert(
      topMoversContent.includes(`data-ticker="${ticker}"`),
      `Should render mover row data-ticker for ${ticker}`
    );
    assert(
      topMoversContent.includes(`id="playbook-${ticker}"`),
      `Should render playbook container for ${ticker}`
    );
  });
  assert(
    topMoversContent.includes('loadTopMoversPlaybooks'),
    'Should load playbooks in top movers widget'
  );
  assert(
    topMoversContent.includes('window.PlaybookIntegration.getDecisionBadge'),
    'Should reuse the shared PlaybookIntegration helper in top movers'
  );
  assert(
    appJsContent.includes('class="mover-playbook" id="playbook-${symbolId}"'),
    'Live app renderer should keep playbook containers when rows rerender'
  );
  assert(
    appJsContent.includes('hydrateTopMoversPlaybooks(rows);'),
    'Live app renderer should hydrate top mover playbooks after rerender'
  );
  assert(
    appJsContent.includes('playbookIntegration.getDecisionBadge(symbol)'),
    'Live app renderer should reuse the shared playbook helper'
  );
});

// Test 7: News Impact widget structure
test('News Impact widget has playbook container for each news item', () => {
  const tickers = ['NVDA', 'META', 'AAPL', 'TSLA'];
  tickers.forEach(ticker => {
    assert(
      newsImpactContent.includes(`id="playbook-news-${ticker}"`),
      `Should render news playbook container for ${ticker}`
    );
  });
  assert(newsImpactContent.includes('loadNewsImpactPlaybooks'), 'Should load playbooks in news widget');
});

// Test 8: Stock Relationships widget structure
test('Stock Relationships widget has playbook container for each pair', () => {
  const pairs = ['AAPL-MSFT', 'MSFT-GOOGL', 'AAPL-GOOGL'];
  pairs.forEach(pair => {
    assert(
      stockRelationshipsContent.includes(`id="playbooks-${pair}"`),
      `Should have pair container for ${pair}`
    );
    assert(
      stockRelationshipsContent.includes(`id="playbook-summary-${pair}"`),
      `Should have summary container for ${pair}`
    );
  });
});

// Test 9: Correlation playbook alignment detection
test('Correlation playbook insights detect aligned decisions', () => {
  assert(
    stockRelationshipsContent.includes('getCorrelationPlaybookSummary'),
    'Should define correlation playbook summary helper'
  );
  assert(
    stockRelationshipsContent.includes('Aligned ') &&
    stockRelationshipsContent.includes('setup across both names'),
    'Should render aligned decision copy'
  );
});

// Test 10: Correlation playbook conflict detection
test('Correlation playbook insights detect conflicting decisions', () => {
  assert(
    stockRelationshipsContent.includes('is-mixed'),
    'Should style mixed decisions'
  );
  assert(
    stockRelationshipsContent.includes('while ') &&
    stockRelationshipsContent.includes(' is '),
    'Should describe conflicting pair decisions'
  );
});

// Test 11: Badge CSS classes exist
test('Widget styles include playbook badge CSS classes', () => {
  const requiredClasses = [
    '.playbook-badge',
    '.playbook-badge.badge-go',
    '.playbook-badge.badge-no-go',
    '.playbook-badge.badge-neutral'
  ];
  requiredClasses.forEach(cls => {
    assert(
      topMoversContent.includes(cls) ||
      newsImpactContent.includes(cls) ||
      stockRelationshipsContent.includes(cls),
      `Should have CSS class ${cls}`
    );
  });
});

// Test 12: Risk indicator styling
test('Widget styles include risk indicator classes', () => {
  const riskClasses = [
    '.playbook-risk.risk-low',
    '.playbook-risk.risk-medium',
    '.playbook-risk.risk-high',
    '.playbook-risk.risk-critical'
  ];
  riskClasses.forEach(cls => {
    assert(
      topMoversContent.includes(cls),
      `Should have risk CSS class ${cls} in top movers`
    );
  });
});

test('Stock Relationships widget uses pair-scoped rendering instead of duplicate ticker ids', () => {
  assert(
    !stockRelationshipsContent.includes('id="playbook-corr-AAPL"'),
    'Should not reuse duplicate AAPL correlation ids'
  );
  assert(
    stockRelationshipsContent.includes("container.querySelector('[data-role=\"ticker-a\"]')"),
    'Should render ticker-a badge within the pair container'
  );
  assert(
    stockRelationshipsContent.includes("container.querySelector('[data-role=\"ticker-b\"]')"),
    'Should render ticker-b badge within the pair container'
  );
});

// Summary
console.log('\n' + '='.repeat(50));
console.log(`Tests: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log('='.repeat(50) + '\n');

if (failed > 0) {
  process.exit(1);
}

console.log('✅ All widget playbook integration tests passed!\n');
