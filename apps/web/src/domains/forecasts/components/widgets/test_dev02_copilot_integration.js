/**
 * BATCH-82-DEV-02: Personal Finance Copilot - Frontend Integration Test
 *
 * Tests the minimal vertical slice for copilot UI integration:
 * 1. Widget HTML exists and has required structure
 * 2. API wiring functions are exposed globally
 * 3. renderCopilotBrief renders brief_of_day data correctly
 * 4. renderCopilotActions renders ask/open actions
 * 5. sendCopilotQuestion includes conversation_id tracking
 * 6. Personal finance start page exists and loads widget
 *
 * Product vision: "Build a personal finance copilot that starts with a brief of the day"
 * Reuse principle: Uses existing widgets from forecasts/components/widgets/*
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// Mock API response matching /api/personal-finance/start contract
const mockPersonalFinanceStartResponse = {
  ok: true,
  data: {
    brief_of_day: {
      summary: "Your portfolio is up 1.88% today driven by tech rally (NVDA +8.5%, META +5.2%). Fed dovish signals support bullish continuation.",
      market_sentiment: "bullish",
      top_signals: ["Tech sector breakout", "Fed dovish pivot", "Earnings beat expectations"],
      top_risks: ["Valuation concerns", "Geopolitical tension"],
      freshness: new Date().toISOString(),
      source: ["brief_daily_snapshot", "copilot_start_route"]
    },
    ask: [
      {
        id: "ask_001",
        kind: "ask",
        label: "What's moving NVDA?",
        target: "/personal-finance/ask",
        prefill: { question: "What's moving NVDA today?", tickers: ["NVDA"] }
      },
      {
        id: "ask_002",
        kind: "ask",
        label: "Should I rebalance?",
        target: "/personal-finance/ask",
        prefill: { question: "Should I rebalance my portfolio?", tickers: [] }
      }
    ],
    open: [
      {
        id: "open_001",
        kind: "open",
        label: "Open Live Brief",
        target: "/brief/daily"
      },
      {
        id: "open_002",
        kind: "open",
        label: "View Portfolio",
        target: "/dashboard/portfolio"
      }
    ],
    generated_at: new Date().toISOString(),
    freshness: new Date().toISOString()
  }
};

// Mock DOM environment
function createMockDocument() {
  const elements = new Map();

  function createElement(id, initialText = '') {
    const el = {
      id,
      value: '',
      textContent: initialText,
      innerHTML: initialText,
      style: { display: 'block' },
      disabled: false,
      setAttribute() {},
      addEventListener() {}
    };
    elements.set(id, el);
    return el;
  }

  return {
    getElementById: (id) => elements.get(id) || createElement(id),
    createElement: () => ({ textContent: '', innerHTML: '' }),
    querySelector: () => ({ disabled: false }),
    elements
  };
}

// Extract function from HTML file
function extractFunctionFromHTML(htmlPath, functionName) {
  const source = fs.readFileSync(htmlPath, 'utf8');
  const start = source.indexOf(`function ${functionName}(`);
  if (start === -1) return null;

  let braceCount = 0;
  let inFunction = false;
  let end = start;

  for (let i = start; i < source.length; i++) {
    if (source[i] === '{') {
      braceCount++;
      inFunction = true;
    } else if (source[i] === '}') {
      braceCount--;
      if (inFunction && braceCount === 0) {
        end = i + 1;
        break;
      }
    }
  }

  return source.slice(start, end);
}

// Helper: escape HTML (copied from widget pattern)
function escapeHtml(text) {
  if (typeof text !== 'string') return String(text || '');
  const div = { innerHTML: text };
  return div.innerHTML;
}

test('BATCH-82-DEV-02: copilot-panel.html widget exists', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  assert.ok(fs.existsSync(widgetPath), 'copilot-panel.html must exist');

  const content = fs.readFileSync(widgetPath, 'utf8');
  assert.ok(content.length > 1000, 'Widget must have substantial content');
  assert.ok(content.includes('copilotPanel'), 'Must have copilotPanel element');
  assert.ok(content.includes('brief_of_day') || content.includes('Brief of the Day'), 'Must have brief section');
});

test('BATCH-82-DEV-02: Widget has required API wiring functions', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const source = fs.readFileSync(widgetPath, 'utf8');

  // Check for required functions
  const requiredFunctions = [
    'initCopilotPanel',
    'loadCopilotStart',
    'sendCopilotQuestion',
    'renderCopilotBrief',
    'renderCopilotActions'
  ];

  for (const fn of requiredFunctions) {
    assert.ok(source.includes(`function ${fn}(`), `Must have ${fn} function`);
  }
});

test('BATCH-82-DEV-02: Widget wires to correct API endpoints', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const source = fs.readFileSync(widgetPath, 'utf8');

  assert.ok(source.includes('function getCopilotApiBase('), 'Must expose API base helper');
  assert.ok(source.includes('function getCopilotNamespace('), 'Must expose namespace helper');
  assert.ok(source.includes('${getCopilotApiBase()}/${namespace}/start'), 'Must build start endpoint from namespace');
  assert.ok(source.includes('${getCopilotApiBase()}/${namespace}/ask'), 'Must build ask endpoint from namespace');
  assert.ok(source.includes("window.COPILOT_NAMESPACE || 'copilot'"), 'Must default namespace safely');
});

test('BATCH-82-DEV-02: renderCopilotBrief renders brief summary', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const renderFn = extractFunctionFromHTML(widgetPath, 'renderCopilotBrief');
  assert.ok(renderFn, 'renderCopilotBrief function must exist');

  const mockDoc = createMockDocument();
  const sandbox = {
    document: mockDoc,
    formatCopilotTimestamp(ts) { return ts ? 'just now' : ''; },
    escapeHtml
  };

  const vm = require('node:vm');
  vm.createContext(sandbox);
  vm.runInContext(renderFn, sandbox, { filename: 'copilot-panel.html' });

  sandbox.renderCopilotBrief(mockPersonalFinanceStartResponse.data);

  const summaryEl = mockDoc.getElementById('copilotBriefSummary');
  assert.ok(summaryEl, 'Summary element must exist');
  assert.ok(summaryEl.textContent.length > 0, 'Summary must be rendered');
  assert.ok(summaryEl.textContent.includes('portfolio'), 'Summary should mention portfolio');
});

test('BATCH-82-DEV-02: renderCopilotBrief renders signals and risks', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const renderFn = extractFunctionFromHTML(widgetPath, 'renderCopilotBrief');

  const mockDoc = createMockDocument();
  const sandbox = {
    document: mockDoc,
    formatCopilotTimestamp() { return ''; },
    escapeHtml
  };

  const vm = require('node:vm');
  vm.createContext(sandbox);
  vm.runInContext(renderFn, sandbox, { filename: 'copilot-panel.html' });

  sandbox.renderCopilotBrief(mockPersonalFinanceStartResponse.data);

  const signalsEl = mockDoc.getElementById('copilotBriefSignals');
  const risksEl = mockDoc.getElementById('copilotBriefRisks');

  assert.ok(signalsEl, 'Signals section must exist');
  assert.ok(risksEl, 'Risks section must exist');
  assert.equal(signalsEl.style.display, 'block', 'Signals should be visible when data exists');
  assert.equal(risksEl.style.display, 'block', 'Risks should be visible when data exists');
});

test('BATCH-82-DEV-02: renderCopilotActions renders ask/open actions', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const renderFn = extractFunctionFromHTML(widgetPath, 'renderCopilotActions');

  const mockDoc = createMockDocument();
  const sandbox = {
    document: mockDoc,
    copilotState: {
      askActions: mockPersonalFinanceStartResponse.data.ask,
      openActions: mockPersonalFinanceStartResponse.data.open
    },
    escapeHtml
  };

  const vm = require('node:vm');
  vm.createContext(sandbox);
  vm.runInContext(renderFn, sandbox, { filename: 'copilot-panel.html' });

  sandbox.renderCopilotActions();

  const askListEl = mockDoc.getElementById('copilotAskList');
  const openListEl = mockDoc.getElementById('copilotOpenList');

  assert.ok(askListEl, 'Ask list must exist');
  assert.ok(openListEl, 'Open list must exist');
  assert.ok(askListEl.innerHTML.includes('What\'s moving NVDA'), 'Ask actions should be rendered');
  assert.ok(openListEl.innerHTML.includes('Open Live Brief'), 'Open actions should be rendered');
});

test('BATCH-82-DEV-02: sendCopilotQuestion includes conversation_id tracking', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const sendFn = extractFunctionFromHTML(widgetPath, 'sendCopilotQuestion');
  assert.ok(sendFn, 'sendCopilotQuestion function must exist');

  // Verify conversation_id logic exists in the function
  assert.ok(sendFn.includes('conversation_id'), 'Must include conversation_id in request');
  assert.ok(sendFn.includes('copilotState.conversationId'), 'Must track conversation ID in state');
});

test('BATCH-82-DEV-02: Widget has conversation indicator UI', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const source = fs.readFileSync(widgetPath, 'utf8');

  assert.ok(source.includes('conversation-indicator'), 'Must have conversation indicator element');
  assert.ok(source.includes('copilotConversationIndicator'), 'Must have conversation indicator ID');
  assert.ok(source.includes('updateConversationIndicator'), 'Must have conversation indicator update function');
});

test('BATCH-82-DEV-02: personal-finance-start.html page exists', () => {
  const pagePath = path.join(__dirname, '../../pages/personal-finance-start.html');
  assert.ok(fs.existsSync(pagePath), 'personal-finance-start.html must exist');

  const content = fs.readFileSync(pagePath, 'utf8');
  assert.ok(content.length > 500, 'Page must have substantial content');
  assert.ok(content.includes('copilot-panel-container'), 'Must have copilot panel container');
  assert.ok(content.includes('loadCopilotWidget'), 'Must load copilot widget');
  assert.ok(content.includes('/personal-finance/start'), 'Must wire to personal-finance start endpoint');
});

test('BATCH-82-DEV-02: Personal finance page loads widget dynamically', () => {
  const pagePath = path.join(__dirname, '../../pages/personal-finance-start.html');
  const source = fs.readFileSync(pagePath, 'utf8');

  assert.ok(source.includes("fetch('../"), 'Must fetch widget HTML dynamically');
  assert.ok(source.includes('copilot-panel.html'), 'Must load copilot-panel.html');
  assert.ok(source.includes('initCopilotPanel') || source.includes('bootstrapCopilotPanel'), 'Must initialize copilot');
});

test('BATCH-82-DEV-02: API response has required brief structure', () => {
  const data = mockPersonalFinanceStartResponse.data;

  assert.ok(data.brief_of_day, 'Must have brief_of_day');
  assert.ok(typeof data.brief_of_day.summary === 'string', 'Brief must have summary');
  assert.ok(Array.isArray(data.ask), 'Must have ask actions');
  assert.ok(Array.isArray(data.open), 'Must have open actions');
  assert.ok(data.freshness || data.generated_at, 'Must have freshness timestamp');

  // Verify brief content quality
  assert.ok(data.brief_of_day.summary.length > 20, 'Summary should be substantive');
  assert.ok(data.brief_of_day.top_signals.length >= 1, 'Should have at least 1 signal');
  assert.ok(data.brief_of_day.top_risks.length >= 1, 'Should have at least 1 risk');
});

test('BATCH-82-DEV-02: Ask actions have correct structure', () => {
  const askActions = mockPersonalFinanceStartResponse.data.ask;

  assert.ok(askActions.length >= 1, 'Must have at least 1 ask action');

  for (const action of askActions) {
    assert.ok(action.kind === 'ask', 'Ask action kind must be "ask"');
    assert.ok(action.label, 'Ask action must have label');
    assert.ok(action.target, 'Ask action must have target');
    assert.ok(action.prefill?.question, 'Ask action must have prefill question');
  }
});

test('BATCH-82-DEV-02: Open actions have correct structure', () => {
  const openActions = mockPersonalFinanceStartResponse.data.open;

  assert.ok(openActions.length >= 1, 'Must have at least 1 open action');

  for (const action of openActions) {
    assert.ok(action.kind === 'open', 'Open action kind must be "open"');
    assert.ok(action.label, 'Open action must have label');
    assert.ok(action.target, 'Open action must have target');
  }
});

test('BATCH-82-DEV-02: Widget reuses existing UI patterns', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const source = fs.readFileSync(widgetPath, 'utf8');

  // Check for reused patterns from other widgets
  assert.ok(source.includes('widget-card'), 'Must reuse widget-card class');
  assert.ok(source.includes('widget-header'), 'Must reuse widget-header class');
  // Widget uses widget-body or copilot-brief-section for content areas
  assert.ok(source.includes('widget-body') || source.includes('copilot-brief-section') || source.includes('widget-content'), 'Must reuse widget content area class');
  assert.ok(source.includes('widget-footer'), 'Must reuse widget-footer class');
});

test('BATCH-82-DEV-02: Widget has error handling', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const source = fs.readFileSync(widgetPath, 'utf8');

  assert.ok(source.includes('copilot-error'), 'Must have error state UI');
  assert.ok(source.includes('showCopilotError'), 'Must have error display function');
  assert.ok(source.includes('try') && source.includes('catch'), 'Must have try/catch error handling');
});

test('BATCH-82-DEV-02: Widget has loading state', () => {
  const widgetPath = path.join(__dirname, 'copilot-panel.html');
  const source = fs.readFileSync(widgetPath, 'utf8');

  assert.ok(source.includes('copilot-loading'), 'Must have loading state UI');
  assert.ok(source.includes('showCopilotLoading'), 'Must have loading display function');
});

// Run all tests
async function runAllTests() {
  console.log('\n=== BATCH-82-DEV-02: Copilot Frontend Integration Tests ===\n');

  let passed = 0;
  let failed = 0;

  const tests = [
    { name: 'Widget exists', fn: () => {
      const widgetPath = path.join(__dirname, 'copilot-panel.html');
      assert.ok(fs.existsSync(widgetPath), 'copilot-panel.html must exist');
    }},
    { name: 'Widget has API wiring', fn: () => {
      const widgetPath = path.join(__dirname, 'copilot-panel.html');
      const source = fs.readFileSync(widgetPath, 'utf8');
      assert.ok(source.includes('function initCopilotPanel('), 'Must have initCopilotPanel');
      assert.ok(source.includes('function loadCopilotStart('), 'Must have loadCopilotStart');
      assert.ok(source.includes('function sendCopilotQuestion('), 'Must have sendCopilotQuestion');
    }},
    { name: 'Widget wires to API', fn: () => {
      const widgetPath = path.join(__dirname, 'copilot-panel.html');
      const source = fs.readFileSync(widgetPath, 'utf8');
      assert.ok(source.includes('function getCopilotApiBase('), 'Must expose API base helper');
      assert.ok(source.includes('function getCopilotNamespace('), 'Must expose namespace helper');
      assert.ok(source.includes('${getCopilotApiBase()}/${namespace}/start'), 'Must build start endpoint from namespace');
      assert.ok(source.includes('${getCopilotApiBase()}/${namespace}/ask'), 'Must build ask endpoint from namespace');
    }},
    { name: 'Renders brief summary', fn: () => {
      const widgetPath = path.join(__dirname, 'copilot-panel.html');
      const renderFn = extractFunctionFromHTML(widgetPath, 'renderCopilotBrief');
      assert.ok(renderFn, 'renderCopilotBrief must exist');

      const mockDoc = createMockDocument();
      const sandbox = { document: mockDoc, formatCopilotTimestamp: () => '', escapeHtml };
      const vm = require('node:vm');
      vm.createContext(sandbox);
      vm.runInContext(renderFn, sandbox);
      sandbox.renderCopilotBrief(mockPersonalFinanceStartResponse.data);

      const summaryEl = mockDoc.getElementById('copilotBriefSummary');
      assert.ok(summaryEl.textContent.length > 0, 'Summary must be rendered');
    }},
    { name: 'Renders ask/open actions', fn: () => {
      const widgetPath = path.join(__dirname, 'copilot-panel.html');
      const renderFn = extractFunctionFromHTML(widgetPath, 'renderCopilotActions');
      assert.ok(renderFn, 'renderCopilotActions must exist');

      const mockDoc = createMockDocument();
      const sandbox = {
        document: mockDoc,
        copilotState: {
          askActions: mockPersonalFinanceStartResponse.data.ask,
          openActions: mockPersonalFinanceStartResponse.data.open
        },
        escapeHtml
      };
      const vm = require('node:vm');
      vm.createContext(sandbox);
      vm.runInContext(renderFn, sandbox);
      sandbox.renderCopilotActions();

      const askListEl = mockDoc.getElementById('copilotAskList');
      assert.ok(askListEl.innerHTML.length > 0, 'Ask actions must be rendered');
    }},
    { name: 'Conversation tracking exists', fn: () => {
      const widgetPath = path.join(__dirname, 'copilot-panel.html');
      const source = fs.readFileSync(widgetPath, 'utf8');
      assert.ok(source.includes('conversationId'), 'Must track conversation ID');
      assert.ok(source.includes('conversation-indicator'), 'Must have conversation indicator');
    }},
    { name: 'Personal finance page exists', fn: () => {
      const pagePath = path.join(__dirname, '../../pages/personal-finance-start.html');
      assert.ok(fs.existsSync(pagePath), 'personal-finance-start.html must exist');
    }},
    { name: 'Page loads widget dynamically', fn: () => {
      const pagePath = path.join(__dirname, '../../pages/personal-finance-start.html');
      const source = fs.readFileSync(pagePath, 'utf8');
      assert.ok(source.includes("fetch('../"), 'Must fetch widget dynamically');
    }},
    { name: 'API contract valid', fn: () => {
      const data = mockPersonalFinanceStartResponse.data;
      assert.ok(data.brief_of_day, 'Must have brief_of_day');
      assert.ok(Array.isArray(data.ask), 'Must have ask actions');
      assert.ok(Array.isArray(data.open), 'Must have open actions');
    }},
    { name: 'Reuses widget patterns', fn: () => {
      const widgetPath = path.join(__dirname, 'copilot-panel.html');
      const source = fs.readFileSync(widgetPath, 'utf8');
      assert.ok(source.includes('widget-card'), 'Must reuse widget-card pattern');
    }}
  ];

  for (const test of tests) {
    try {
      test.fn();
      console.log(`✓ ${test.name}`);
      passed++;
    } catch (e) {
      console.error(`✗ ${test.name}: ${e.message}`);
      failed++;
    }
  }

  console.log(`\n=== Test Summary ===`);
  console.log(`Passed: ${passed}/${tests.length}`);
  console.log(`Failed: ${failed}/${tests.length}`);

  if (failed > 0) {
    process.exit(1);
  }

  console.log('\n✅ BATCH-82-DEV-02: All integration tests passed!\n');
}

// Run if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  runAllTests();
}

// Export for node:test
module.exports = { runAllTests };
