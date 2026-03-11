/**
 * Strategy Playbooks Widget - Frontend Tests
 * BATCH-15-DEV-02
 * 
 * Tests for the strategy playbooks widget integration
 */

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

// Test 1: Widget file exists and is valid HTML
function testWidgetFileExists() {
    const fs = require('fs');
    const path = require('path');

    const widgetPath = path.join(__dirname, '../components/widgets/strategy-playbooks.html');

    try {
        const content = fs.readFileSync(widgetPath, 'utf8');
        assert(content.includes('<section class="widget-card strategy-playbooks-widget"'), 'Widget should have root section element');
        assert(content.includes('loadStrategyPlaybooks'), 'Widget should have loadStrategyPlaybooks function');
        assert(content.includes('window.getStrategyPlaybooks'), 'Widget should reuse the shared strategy-playbooks API helper');
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
        assert(
            content.includes('strategy-playbooks-widget-container'),
            'Index should have strategy-playbooks-widget-container'
        );
        assert(
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
        assert(
            content.includes('window.getStrategyPlaybooks'),
            'Widget should use the shared strategy-playbooks API helper'
        );

        // Check for default parameters used in the widget script
        assert(
            content.includes('limit: 20') && content.includes('min_confidence: 0.3'),
            'Widget should use appropriate default parameters'
        );

        // Check for error handling
        assert(
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

// Test 7: Widget exposes forecast fusion attribution
function testWidgetForecastFusionVisibility() {
    const fs = require('fs');
    const path = require('path');

    const widgetPath = path.join(__dirname, '../components/widgets/strategy-playbooks.html');

    try {
        const content = fs.readFileSync(widgetPath, 'utf8');

        assert(
            content.includes('renderForecastFusion') && content.includes('playbook.forecast_fusion'),
            'Widget should render forecast fusion when backend provides it'
        );
        assert(
            content.includes('playbook-fusion-chip') && content.includes('dominant_layer'),
            'Widget should surface fusion attribution chips'
        );

        console.log('✅ Test 7 PASSED: Widget exposes forecast fusion attribution');
        return true;
    } catch (error) {
        console.error('❌ Test 7 FAILED:', error.message);
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
        assert(
            content.includes('var(--color-'),
            'Widget should use design tokens'
        );

        // Check for widget structure
        assert(
            content.includes('widget-header') &&
            content.includes('widget-body'),
            'Widget should have header/body structure'
        );

        // Check for accessibility
        assert(
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
        assert(
            content.includes('playbook-loading-state'),
            'Widget should have loading state'
        );
        assert(
            content.includes('playbook-empty-state'),
            'Widget should have empty state'
        );
        assert(
            content.includes('playbooks-list'),
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
        assert(
            content.includes('conflict_warning') || content.includes('playbook-conflict'),
            'Widget should display conflicts'
        );
        assert(
            content.includes('conflicts'),
            'Widget should render conflict data'
        );

        assert(
            content.includes('renderPolicyGuardrail') && content.includes('playbook.policy_guardrails'),
            'Widget should render personal policy guardrails from the playbook contract'
        );

        assert(
            content.includes('playbook-policy-guardrail') && content.includes('Personal Policy Guardrail'),
            'Widget should expose a policy guardrail panel'
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
        testWidgetConflictVisibility(),
        testWidgetForecastFusionVisibility()
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
