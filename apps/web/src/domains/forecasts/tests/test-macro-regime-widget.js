/**
 * Tests for Macro Regime Cards Widget (BATCH-46-DEV-02)
 *
 * Country/Continent/World Macro Regime Forecasts
 * Validates widget structure, hierarchical display, and consistency checks.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const macroRegimeCardsPath = path.join(__dirname, '../components/widgets/macro-regime-cards.html');
const indexHtmlPath = path.join(__dirname, '../pages/index.html');

const macroRegimeCardsContent = fs.readFileSync(macroRegimeCardsPath, 'utf8');
const indexHtmlContent = fs.readFileSync(indexHtmlPath, 'utf8');

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

console.log('\n🧪 BATCH-46-DEV-02: Macro Regime Cards Widget Tests\n');

// Test 1: Widget file exists and is readable
test('Macro regime cards widget file exists', () => {
  assert(
    fs.existsSync(macroRegimeCardsPath),
    'macro-regime-cards.html should exist in components/widgets'
  );
});

// Test 2: Widget has proper semantic structure
test('Widget has semantic HTML structure', () => {
  assert(
    macroRegimeCardsContent.includes('<section class="widget-card macro-regime-cards"'),
    'Should have widget-card class with macro-regime-cards modifier'
  );
  assert(
    macroRegimeCardsContent.includes('aria-label="Macro Regime Forecasts"'),
    'Should have accessible aria-label'
  );
});

// Test 3: Widget has hierarchical levels (World, Continent, Country)
test('Widget displays all three hierarchical levels', () => {
  assert(
    macroRegimeCardsContent.includes('world-level'),
    'Should have world-level card (L5)'
  );
  assert(
    macroRegimeCardsContent.includes('continent-level'),
    'Should have continent-level card (L4)'
  );
  assert(
    macroRegimeCardsContent.includes('country-level'),
    'Should have country-level card (L3)'
  );
});

// Test 4: Widget shows confidence indicators
test('Widget displays confidence levels', () => {
  assert(
    macroRegimeCardsContent.includes('macro-confidence'),
    'Should have confidence indicator class'
  );
  assert(
    macroRegimeCardsContent.includes('macro-confidence high') ||
    macroRegimeCardsContent.includes('macro-confidence.medium') ||
    macroRegimeCardsContent.includes('macro-confidence.low'),
    'Should have at least one confidence level class'
  );
});

// Test 5: Widget shows regime badges
test('Widget displays regime indicators', () => {
  assert(
    macroRegimeCardsContent.includes('regime-badge'),
    'Should have regime-badge class'
  );
  assert(
    macroRegimeCardsContent.includes('regime-badge expansion') ||
    macroRegimeCardsContent.includes('regime-badge recovery') ||
    macroRegimeCardsContent.includes('regime-badge slowdown') ||
    macroRegimeCardsContent.includes('regime-badge recession'),
    'Should have at least one regime type'
  );
});

// Test 6: Widget shows macro metrics
test('Widget displays macro economic metrics', () => {
  assert(
    macroRegimeCardsContent.includes('GDP Growth'),
    'Should display GDP Growth metric'
  );
  assert(
    macroRegimeCardsContent.includes('Inflation'),
    'Should display Inflation metric'
  );
  assert(
    macroRegimeCardsContent.includes('Risk Level'),
    'Should display Risk Level metric'
  );
});

// Test 7: Widget has consistency check
test('Widget includes cross-level consistency check', () => {
  assert(
    macroRegimeCardsContent.includes('consistency-check'),
    'Should have consistency-check section'
  );
  assert(
    macroRegimeCardsContent.includes('Cross-level consistency'),
    'Should display consistency status message'
  );
});

// Test 8: Widget has AI insight bar
test('Widget includes AI insight bar', () => {
  assert(
    macroRegimeCardsContent.includes('ai-insight-bar'),
    'Should have ai-insight-bar class'
  );
  assert(
    macroRegimeCardsContent.includes('Hierarchical model confidence'),
    'Should mention hierarchical model confidence in insight'
  );
});

// Test 9: Widget is registered in index.html
test('Widget container is registered in index.html', () => {
  assert(
    indexHtmlContent.includes('macro-regime-cards-widget-container'),
    'Should have widget container div in index.html'
  );
});

// Test 10: Widget is in loadComponents list
test('Widget is in loadComponents configuration', () => {
  assert(
    indexHtmlContent.includes("path: '../components/widgets/macro-regime-cards.html'"),
    'Should be in loadComponents array'
  );
  assert(
    indexHtmlContent.includes("target: '#macro-regime-cards-widget-container'"),
    'Should have correct target selector'
  );
});

// Test 11: Widget has responsive design
test('Widget includes responsive CSS', () => {
  assert(
    macroRegimeCardsContent.includes('@media'),
    'Should have media query for responsive design'
  );
  assert(
    macroRegimeCardsContent.includes('grid-template-columns: 1fr'),
    'Should have single-column layout for mobile'
  );
});

// Test 12: Widget has proper styling
test('Widget has professional styling', () => {
  assert(
    macroRegimeCardsContent.includes('linear-gradient'),
    'Should use gradient backgrounds'
  );
  assert(
    macroRegimeCardsContent.includes('border-radius'),
    'Should have rounded corners'
  );
  assert(
    macroRegimeCardsContent.includes('transition'),
    'Should have hover transitions'
  );
});

// Test 13: Widget follows design system
test('Widget uses design tokens', () => {
  assert(
    macroRegimeCardsContent.includes('var(--color-text-primary)') ||
    macroRegimeCardsContent.includes('var(--color-text-secondary)'),
    'Should reference design token CSS variables'
  );
});

// Test 14: Widget has help and menu actions
test('Widget has header actions', () => {
  assert(
    macroRegimeCardsContent.includes('help-icon'),
    'Should have help button'
  );
  assert(
    macroRegimeCardsContent.includes('menu-icon'),
    'Should have menu button'
  );
});

// Test 15: Widget has footer with timestamp
test('Widget has footer with timestamp', () => {
  assert(
    macroRegimeCardsContent.includes('widget-timestamp'),
    'Should have timestamp in footer'
  );
  assert(
    macroRegimeCardsContent.includes('widget-action-btn'),
    'Should have action button in footer'
  );
});

// Summary
console.log('\n' + '='.repeat(60));
console.log(`\nTest Results: ${passed} passed, ${failed} failed\n`);

if (failed > 0) {
  console.log('❌ Some tests failed. Review the widget implementation.\n');
  process.exit(1);
} else {
  console.log('✅ All tests passed! Macro Regime Cards widget is ready.\n');
  process.exit(0);
}
