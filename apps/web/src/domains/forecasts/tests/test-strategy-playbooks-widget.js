/**
 * Strategy Playbooks Widget - Frontend Tests
 * BATCH-15-DEV-02
 * 
 * Tests for the strategy playbooks widget integration
 */

// Test 1: Widget file exists and is valid HTML
function testWidgetFileExists() {
    const fs = require('fs');
    const path = require('path');

    const widgetPath = path.join(__dirname, '../components/widgets/strategy-playbooks.html');

    try {
        const content = fs.readFileSync(widgetPath, 'utf8');
        console.assert(content.includes('<section class="widget-card strategy-playbooks"'), 'Widget should have root section element');
        console.assert(content.includes('loadStrategyPlaybooks'), 'Widget should have loadStrategyPlaybooks function');
        console.assert(content.includes('/api/judge/strategy-playbooks'), 'Widget should call the strategy-playbooks API');
        console.log('✅ Test 1 PASSED: Widget file exists and has expected structure');
        return true;
    } catch (error) {
        console.error('❌ Test 1 FAILED:', error.message);
        return false;
    }
}

// Test 2: Widget is registered in index.html
function testWidgetRegisteredInIndex() {
    const fs = require('fs');
    const path = require('path');
    
    const indexPath = path.join(__dirname, '../pages/index.html');
    
    try {
        const content = fs.readFileSync(indexPath, 'utf8');
        console.assert(
            content.includes('strategy-playbooks-widget-container'),
            'Index should have strategy-playbooks-widget-container'
        );
        console.assert(
            content.includes('strategy-playbooks.html'),
            'Index should load strategy-playbooks.html component'
        );
        console.log('✅ Test 2 PASSED: Widget is registered in index.html');
        return true;
    } catch (error) {
        console.error('❌ Test 2 FAILED:', error.message);
        return false;
    }
}

// Test 3: Widget has proper API integration
function testWidgetApiIntegration() {
    const fs = require('fs');
    const path = require('path');

    const widgetPath = path.join(__dirname, '../components/widgets/strategy-playbooks.html');

    try {
        const content = fs.readFileSync(widgetPath, 'utf8');

        // Check for API call
        console.assert(
            content.includes("fetch('/api/judge/strategy-playbooks"),
            'Widget should fetch from /api/judge/strategy-playbooks'
        );

        // Check for query parameters (widget uses limit=5, min_confidence=0.5)
        console.assert(
            content.includes('limit=5') && content.includes('min_confidence=0.5'),
            'Widget should use appropriate default parameters'
        );

        // Check for error handling
        console.assert(
            content.includes('catch') && content.includes('error'),
            'Widget should have error handling'
        );

        console.log('✅ Test 3 PASSED: Widget has proper API integration');
        return true;
    } catch (error) {
        console.error('❌ Test 3 FAILED:', error.message);
        return false;
    }
}

// Test 4: Widget follows design system
function testWidgetDesignSystem() {
    const fs = require('fs');
    const path = require('path');

    const widgetPath = path.join(__dirname, '../components/widgets/strategy-playbooks.html');

    try {
        const content = fs.readFileSync(widgetPath, 'utf8');

        // Check for design token usage
        console.assert(
            content.includes('var(--color-'),
            'Widget should use design tokens'
        );

        // Check for widget structure
        console.assert(
            content.includes('widget-header') &&
            content.includes('widget-body'),
            'Widget should have header/body structure'
        );

        // Check for accessibility
        console.assert(
            content.includes('aria-label='),
            'Widget should have accessibility attributes'
        );

        console.log('✅ Test 4 PASSED: Widget follows design system');
        return true;
    } catch (error) {
        console.error('❌ Test 4 FAILED:', error.message);
        return false;
    }
}

// Test 5: Widget handles all playbook states
function testWidgetStates() {
    const fs = require('fs');
    const path = require('path');

    const widgetPath = path.join(__dirname, '../components/widgets/strategy-playbooks.html');

    try {
        const content = fs.readFileSync(widgetPath, 'utf8');

        // Check for state handling
        console.assert(
            content.includes('playbook-loading'),
            'Widget should have loading state'
        );
        console.assert(
            content.includes('playbook-empty'),
            'Widget should have empty state'
        );
        console.assert(
            content.includes('playbook-list'),
            'Widget should have list state'
        );

        console.log('✅ Test 5 PASSED: Widget handles all playbook states');
        return true;
    } catch (error) {
        console.error('❌ Test 5 FAILED:', error.message);
        return false;
    }
}

// Test 6: Widget displays conflict visibility
function testWidgetConflictVisibility() {
    const fs = require('fs');
    const path = require('path');

    const widgetPath = path.join(__dirname, '../components/widgets/strategy-playbooks.html');

    try {
        const content = fs.readFileSync(widgetPath, 'utf8');

        // Check for conflict display
        console.assert(
            content.includes('playbook-conflicts'),
            'Widget should display conflicts'
        );
        console.assert(
            content.includes('conflicts'),
            'Widget should render conflict data'
        );

        console.log('✅ Test 6 PASSED: Widget displays conflict visibility');
        return true;
    } catch (error) {
        console.error('❌ Test 6 FAILED:', error.message);
        return false;
    }
}

// Run all tests
function runAllTests() {
    console.log('\n🧪 Running Strategy Playbooks Widget Tests (BATCH-15-DEV-02)\n');
    
    const results = [
        testWidgetFileExists(),
        testWidgetRegisteredInIndex(),
        testWidgetApiIntegration(),
        testWidgetDesignSystem(),
        testWidgetStates(),
        testWidgetConflictVisibility()
    ];
    
    const passed = results.filter(r => r).length;
    const total = results.length;
    
    console.log(`\n📊 Test Results: ${passed}/${total} tests passed`);
    
    if (passed === total) {
        console.log('✅ All tests passed! Widget is ready for integration.\n');
        process.exit(0);
    } else {
        console.log(`❌ ${total - passed} test(s) failed. Please review.\n`);
        process.exit(1);
    }
}

// Run if executed directly
if (require.main === module) {
    runAllTests();
}

module.exports = {
    testWidgetFileExists,
    testWidgetRegisteredInIndex,
    testWidgetApiIntegration,
    testWidgetDesignSystem,
    testWidgetStates,
    testWidgetConflictVisibility,
    runAllTests
};
