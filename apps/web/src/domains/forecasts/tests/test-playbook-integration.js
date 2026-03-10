/**
 * Playbook Integration Tests
 * 
 * Tests for the strategy playbooks integration helper (playbookIntegration.js)
 * and widget integration (top-movers.html with playbook badges)
 * 
 * BATCH-15-DEV-03: Strategy Playbooks Engine - Widget Integration
 */

const fs = require('fs');
const path = require('path');

let passCount = 0;
let failCount = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✅ ${message}`);
    passCount++;
  } else {
    console.log(`  ❌ ${message}`);
    failCount++;
  }
}

console.log('🧪 Running Playbook Integration Tests (BATCH-15-DEV-03)\n');

// Test 1: Playbook Integration Helper exists
console.log('📦 Test Suite: Playbook Integration Helper');
const integrationPath = path.join(__dirname, '../contracts/playbookIntegration.js');
assert(fs.existsSync(integrationPath), 'playbookIntegration.js exists');

if (fs.existsSync(integrationPath)) {
  const content = fs.readFileSync(integrationPath, 'utf8');
  assert(content.includes('window.PlaybookIntegration'), 'Exports PlaybookIntegration to window');
  assert(content.includes('fetchPlaybooks'), 'Has fetchPlaybooks function');
  assert(content.includes('getPlaybookForTicker'), 'Has getPlaybookForTicker function');
  assert(content.includes('getDecisionBadge'), 'Has getDecisionBadge function');
  assert(content.includes('getRiskIndicator'), 'Has getRiskIndicator function');
  assert(content.includes('getExpectedReturn'), 'Has getExpectedReturn function');
  assert(content.includes('window.getStrategyPlaybooks'), 'Uses window.getStrategyPlaybooks API');
  assert(content.includes('CACHE_TTL_MS'), 'Implements caching mechanism');
}

// Test 2: Top Movers widget integration
console.log('\n📈 Test Suite: Top Movers Widget Integration');
const topMoversPath = path.join(__dirname, '../components/widgets/top-movers.html');
assert(fs.existsSync(topMoversPath), 'top-movers.html exists');

if (fs.existsSync(topMoversPath)) {
  const content = fs.readFileSync(topMoversPath, 'utf8');
  assert(content.includes('mover-playbook'), 'Has playbook container in mover rows');
  assert(content.includes('playbook-NVDA'), 'Has playbook container for NVDA');
  assert(content.includes('playbook-META'), 'Has playbook container for META');
  assert(content.includes('playbook-AAPL'), 'Has playbook container for AAPL');
  assert(content.includes('playbook-MSFT'), 'Has playbook container for MSFT');
  assert(content.includes('playbook-GOOGL'), 'Has playbook container for GOOGL');
  assert(content.includes('loadTopMoversPlaybooks'), 'Has loadTopMoversPlaybooks function');
  assert(content.includes('PlaybookIntegration.getDecisionBadge'), 'Uses PlaybookIntegration helper');
  assert(content.includes('.playbook-badge'), 'Has playbook badge styles');
  assert(content.includes('.badge-go'), 'Has GO decision badge style');
  assert(content.includes('.badge-no-go'), 'Has NO-GO decision badge style');
  assert(content.includes('data-ticker='), 'Has data-ticker attributes for dynamic loading');
}

// Test 3: API Connector integration
console.log('\n🔌 Test Suite: API Connector Integration');
const apiConnectorPath = path.join(__dirname, '../contracts/apiConnector.js');
assert(fs.existsSync(apiConnectorPath), 'apiConnector.js exists');

if (fs.existsSync(apiConnectorPath)) {
  const content = fs.readFileSync(apiConnectorPath, 'utf8');
  assert(content.includes('getStrategyPlaybooks'), 'Exports getStrategyPlaybooks function');
  assert(content.includes('/judge/strategy-playbooks'), 'Has strategy-playbooks endpoint');
  assert(content.includes('window.getStrategyPlaybooks = getStrategyPlaybooks'), 'Exports to window');
}

// Test 4: Verify no duplicate helpers (INTEGRATION-APP-EENGINEER-RECOMMENDATIONS)
console.log('\n🔍 Test Suite: No Duplicate Helpers');
const contractsDir = path.join(__dirname, '../contracts');
const jsFiles = fs.readdirSync(contractsDir).filter(f => f.endsWith('.js'));
const playbookHelpers = jsFiles.filter(f => f.toLowerCase().includes('playbook'));
assert(playbookHelpers.length === 1, `Only one playbook helper file (${playbookHelpers.join(', ')})`);

// Test 5: Integration script loading
console.log('\n📜 Test Suite: Script Loading Order');
const indexHtmlPath = path.join(__dirname, '../pages/index.html');
if (fs.existsSync(indexHtmlPath)) {
  const indexContent = fs.readFileSync(indexHtmlPath, 'utf8');
  // Check if playbookIntegration would be loaded after apiConnector
  const apiConnectorPos = indexContent.indexOf('apiConnector.js');
  const playbookPos = indexContent.indexOf('playbookIntegration.js');
  
  if (apiConnectorPos > -1 && playbookPos > -1) {
    assert(playbookPos > apiConnectorPos, 'playbookIntegration.js loads after apiConnector.js');
  } else if (playbookPos > -1) {
    assert(true, 'playbookIntegration.js is referenced in index.html');
  } else {
    assert(false, 'playbookIntegration.js should be added to index.html');
  }
} else {
  assert(false, 'pages/index.html should exist for script order verification');
}

// Summary
console.log('\n' + '='.repeat(60));
console.log(`Test Summary: ${passCount} passed, ${failCount} failed`);
console.log('='.repeat(60));

if (failCount > 0) {
  console.log('\n❌ Some tests failed. Review the output above.');
  process.exit(1);
} else {
  console.log('\n✅ All tests passed! Playbook integration is ready.');
  process.exit(0);
}
