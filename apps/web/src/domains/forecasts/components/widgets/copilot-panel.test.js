const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const widgetPath = path.join(__dirname, 'copilot-panel.html');
const source = fs.readFileSync(widgetPath, 'utf8');

function extractFunction(name, nextName) {
  const startMarkers = [`function ${name}(`, `async function ${name}(`];
  const start = startMarkers
    .map((marker) => source.indexOf(marker))
    .filter((index) => index !== -1)
    .sort((a, b) => a - b)[0];
  assert.notEqual(start, -1, `missing function ${name}`);
  const nextMarkers = nextName
    ? [`function ${nextName}(`, `async function ${nextName}(`]
    : ['</script>'];
  const end = nextMarkers
    .map((marker) => source.indexOf(marker, start + 1))
    .filter((index) => index !== -1)
    .sort((a, b) => a - b)[0];
  assert.notEqual(end, -1, `missing end marker after ${name}`);
  return source.slice(start, end).trim();
}

function buildHarness({ dashedContainer, camelContainer, panel } = {}) {
  const lookups = {
    'copilot-panel-container': dashedContainer || null,
    copilotPanelContainer: camelContainer || null,
    copilotPanel: panel || null,
  };
  let initCalls = 0;
  const sandbox = {
    document: {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) {
        return lookups[id] || null;
      },
    },
    initCopilotPanel() {
      initCalls += 1;
    },
    window: {},
  };
  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('getCopilotPanelContainer', 'toggleCopilotPanel'),
      extractFunction('toggleCopilotPanel', 'escapeHtml'),
      extractFunction('bootstrapCopilotPanel'),
      'this.getCopilotPanelContainer = getCopilotPanelContainer;',
      'this.toggleCopilotPanel = toggleCopilotPanel;',
      'this.bootstrapCopilotPanel = bootstrapCopilotPanel;',
    ].join('\n\n'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  return {
    sandbox,
    get initCalls() {
      return initCalls;
    },
  };
}

test('toggleCopilotPanel prefers the mounted dashed container id', () => {
  const dashedContainer = { style: { display: 'block' } };
  const camelContainer = { style: { display: 'block' } };
  const harness = buildHarness({ dashedContainer, camelContainer });

  harness.sandbox.toggleCopilotPanel();

  assert.equal(dashedContainer.style.display, 'none');
  assert.equal(camelContainer.style.display, 'block');
  assert.equal(harness.initCalls, 0);
});

test('bootstrapCopilotPanel initializes the visible panel container', () => {
  const dashedContainer = { style: { display: 'none' } };
  const panel = {};
  const harness = buildHarness({ dashedContainer, panel });

  harness.sandbox.bootstrapCopilotPanel();

  assert.equal(dashedContainer.style.display, 'block');
  assert.equal(harness.initCalls, 1);
  assert.equal(harness.sandbox.window.bootstrapCopilotPanel, harness.sandbox.bootstrapCopilotPanel);
});

test('renderCopilotPortfolio displays portfolio context with holdings', () => {
  const portfolioSection = { style: { display: 'none' } };
  const portfolioTitle = { textContent: '' };
  const portfolioTimestamp = { textContent: '' };
  const portfolioHoldings = { innerHTML: '' };
  const portfolioRisk = { innerHTML: '', style: { display: 'none' } };
  const portfolioAlerts = { style: { display: 'block' } };
  const alertList = { innerHTML: '' };

  const sandbox = {
    document: {
      getElementById(id) {
        const els = {
          copilotPortfolioSection: portfolioSection,
          copilotPortfolioTitle: portfolioTitle,
          copilotPortfolioTimestamp: portfolioTimestamp,
          copilotPortfolioHoldings: portfolioHoldings,
          copilotPortfolioRisk: portfolioRisk,
          copilotPortfolioAlerts: portfolioAlerts,
          copilotAlertList: alertList,
        };
        return els[id] || null;
      },
    },
    formatCopilotTimestamp(ts) {
      return ts ? `${ts} ago` : '';
    },
    escapeHtml(text) {
      return String(text || '');
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('renderCopilotPortfolio', 'renderCopilotActions'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  const testData = {
    portfolio_context: {
      portfolio: {
        name: 'Tech Growth',
        tickers: ['NVDA', 'MSFT', 'AAPL'],
        tickers_count: 3,
      },
      risk_profile: 'Aggressive',
      risk_level: 'High',
      benchmark: 'QQQ',
      freshness: '2026-03-20T10:00:00Z',
    },
    allocation_drift_alerts: {
      active: true,
      alerts: [
        {
          id: 'concentration_warning',
          symbol: 'NVDA',
          severity: 'high',
          reason: 'NVDA is 45% of portfolio, above 40% threshold',
        },
      ],
    },
  };

  sandbox.renderCopilotPortfolio(testData);

  assert.equal(portfolioSection.style.display, 'block', 'Portfolio section should be visible');
  assert.equal(portfolioTitle.textContent, 'Tech Growth', 'Portfolio name should be displayed');
  assert.ok(portfolioTimestamp.textContent.includes('ago'), 'Timestamp should be formatted');
  assert.ok(portfolioHoldings.innerHTML.includes('NVDA, MSFT, AAPL'), 'Holdings should show tickers');
  assert.ok(portfolioRisk.innerHTML.includes('Aggressive'), 'Risk profile should be shown');
  assert.ok(portfolioRisk.innerHTML.includes('High'), 'Risk level should be shown');
  assert.ok(portfolioRisk.innerHTML.includes('QQQ'), 'Benchmark should be shown');
  assert.equal(portfolioAlerts.style.display, 'block', 'Alerts section should be visible');
  assert.ok(alertList.innerHTML.includes('NVDA'), 'Alert should mention symbol');
  assert.ok(alertList.innerHTML.includes('45%'), 'Alert should show concentration detail');
});

test('renderCopilotPortfolio hides section when no portfolio context', () => {
  const portfolioSection = { style: { display: 'block' } };

  const sandbox = {
    document: {
      getElementById(id) {
        return id === 'copilotPortfolioSection' ? portfolioSection : null;
      },
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('renderCopilotPortfolio', 'renderCopilotActions'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.renderCopilotPortfolio({});

  assert.equal(portfolioSection.style.display, 'none', 'Portfolio section should be hidden');
});

test('renderCopilotPortfolio shows alert severity styling', () => {
  const portfolioSection = { style: { display: 'none' } };
  const portfolioHoldings = { innerHTML: '' };
  const portfolioRisk = { innerHTML: '', style: { display: 'none' } };
  const portfolioAlerts = { style: { display: 'none' } };
  const alertList = { innerHTML: '' };

  const sandbox = {
    document: {
      getElementById(id) {
        const els = {
          copilotPortfolioSection: portfolioSection,
          copilotPortfolioHoldings: portfolioHoldings,
          copilotPortfolioRisk: portfolioRisk,
          copilotPortfolioAlerts: portfolioAlerts,
          copilotAlertList: alertList,
        };
        return els[id] || null;
      },
    },
    formatCopilotTimestamp() { return ''; },
    escapeHtml(text) { return String(text || ''); },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('renderCopilotPortfolio', 'renderCopilotActions'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  const testData = {
    portfolio_context: {
      portfolio: { tickers: ['AAPL'] },
    },
    allocation_drift_alerts: {
      active: true,
      alerts: [
        { id: 'drift_alert', symbol: 'AAPL', severity: 'medium', reason: 'Weight drift detected' },
      ],
    },
  };

  sandbox.renderCopilotPortfolio(testData);

  assert.ok(alertList.innerHTML.includes('alert-medium'), 'Should include severity class');
  assert.ok(alertList.innerHTML.includes('AAPL'), 'Should show symbol');
});

test('renderCopilotActions uses prompt fallback for ask prefill', () => {
  const askListEl = { innerHTML: '', style: { display: 'block' } };
  const openListEl = { innerHTML: '', style: { display: 'block' } };

  const sandbox = {
    document: {
      getElementById(id) {
        return id === 'copilotAskList'
          ? askListEl
          : id === 'copilotOpenList'
            ? openListEl
            : null;
      },
    },
    copilotState: {
      askActions: [
        {
          kind: 'ask',
          label: 'NVDA memo',
          prompt: 'Give me a 1-week memo on NVDA.',
        },
      ],
      openActions: [],
    },
    escapeHtml(text) {
      return String(text || '');
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('normalizeCopilotTickers', 'resolveCopilotScopeTickers'),
      extractFunction('renderCopilotActions', 'renderCopilotSuggestions'),
    ].join('\n\n'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.renderCopilotActions();

  assert.ok(
    askListEl.innerHTML.includes('executeCopilotAction(&quot;ask&quot;, &quot;&quot;, &quot;Give me a 1-week memo on NVDA.&quot;, [])'),
    'Prompt fallback should be passed to action handler when prefill is absent'
  );
});

test('renderCopilotActions keeps apostrophes safe inside inline ask handlers', () => {
  const askListEl = { innerHTML: '', style: { display: 'block' } };
  const openListEl = { innerHTML: '', style: { display: 'block' } };

  const sandbox = {
    document: {
      getElementById(id) {
        return id === 'copilotAskList'
          ? askListEl
          : id === 'copilotOpenList'
            ? openListEl
            : null;
      },
    },
    copilotState: {
      askActions: [
        {
          kind: 'ask',
          label: 'NVDA catalyst',
          prompt: "What's moving NVDA today?",
        },
      ],
      openActions: [],
    },
    escapeHtml(text) {
      return String(text || '');
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('normalizeCopilotTickers', 'resolveCopilotScopeTickers'),
      extractFunction('renderCopilotActions', 'renderCopilotSuggestions'),
    ].join('\n\n'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.renderCopilotActions();

  assert.ok(
    askListEl.innerHTML.includes('executeCopilotAction(&quot;ask&quot;, &quot;&quot;, &quot;What\'s moving NVDA today?&quot;, [])'),
    'Apostrophes should remain inside a quoted JS string literal instead of breaking the inline handler'
  );
  assert.ok(
    !askListEl.innerHTML.includes("executeCopilotAction('ask'"),
    'Inline handler should no longer rely on single-quoted arguments'
  );
});

test('renderCopilotActions promotes ranked ask action ahead of generic asks', () => {
  const askListEl = { innerHTML: '', style: { display: 'block' } };
  const openListEl = { innerHTML: '', style: { display: 'block' } };

  const sandbox = {
    document: {
      getElementById(id) {
        return id === 'copilotAskList'
          ? askListEl
          : id === 'copilotOpenList'
            ? openListEl
            : null;
      },
    },
    copilotState: {
      briefData: {
        ranked_action: {
          id: 'ranked_today',
          kind: 'ask',
          label: 'Portfolio today',
          target: '/copilot/ask',
          prefill: {
            question: 'What should I do with my portfolio today?',
          },
        },
      },
      askActions: [
        {
          id: 'market_theme',
          kind: 'ask',
          label: 'Best theme now?',
          prompt: 'Which market theme deserves a deep dive right now?',
        },
      ],
      openActions: [],
    },
    escapeHtml(text) {
      return String(text || '');
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('normalizeCopilotTickers', 'resolveCopilotScopeTickers'),
      extractFunction('renderCopilotActions', 'renderCopilotSuggestions'),
    ].join('\n\n'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.renderCopilotActions();

  assert.ok(
    askListEl.innerHTML.includes('Top action: Portfolio today'),
    'Ranked action should be labeled as the top action'
  );
  assert.ok(
    askListEl.innerHTML.indexOf('Top action: Portfolio today') < askListEl.innerHTML.indexOf('Best theme now?'),
    'Ranked action should render before the generic ask actions'
  );
});

test('executeCopilotAction stores ask tickers on the input before focusing the copilot', () => {
  const calls = [];
  const input = {
    value: '',
    dataset: {},
    focus() {
      calls.push({ type: 'focus' });
    },
  };
  const sandbox = {
    document: {
      getElementById(id) {
        return id === 'copilotQuestionInput' ? input : null;
      },
    },
    showToast(message, level) {
      calls.push({ type: 'toast', message, level });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('normalizeCopilotTickers', 'resolveCopilotScopeTickers'),
      extractFunction('executeCopilotAction', 'setCopilotQuestion'),
      extractFunction('setCopilotQuestion', 'focusCopilotInput'),
      extractFunction('focusCopilotInput', 'handleCopilotQuestionKeydown'),
      'this.executeCopilotAction = executeCopilotAction;',
    ].join('\n\n'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.executeCopilotAction('ask', '', "What's moving NVDA today?", ['nvda', 'MSFT', 'nvda']);

  assert.equal(input.value, "What's moving NVDA today?");
  assert.equal(input.dataset.copilotTickers, '["NVDA","MSFT"]');
  assert.deepEqual(calls, [{ type: 'focus' }, { type: 'toast', message: "ask What's moving NVDA today?", level: 'info' }]);
});

test('executeCopilotAction auto-submits ask actions when the widget ask handler is available', () => {
  const calls = [];
  const input = {
    value: '',
    dataset: {},
    focus() {
      calls.push({ type: 'focus' });
    },
  };
  const sandbox = {
    document: {
      getElementById(id) {
        return id === 'copilotQuestionInput' ? input : null;
      },
    },
    sendCopilotQuestion() {
      calls.push({ type: 'send' });
    },
    showToast(message, level) {
      calls.push({ type: 'toast', message, level });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('normalizeCopilotTickers', 'resolveCopilotScopeTickers'),
      extractFunction('executeCopilotAction', 'setCopilotQuestion'),
      extractFunction('setCopilotQuestion', 'focusCopilotInput'),
      extractFunction('focusCopilotInput', 'handleCopilotQuestionKeydown'),
      'this.executeCopilotAction = executeCopilotAction;',
    ].join('\n\n'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.executeCopilotAction('ask', '', 'What should I do with my portfolio today?', ['nvda']);

  assert.equal(input.value, 'What should I do with my portfolio today?');
  assert.equal(input.dataset.copilotTickers, '["NVDA"]');
  assert.deepEqual(calls, [
    { type: 'send' },
    { type: 'toast', message: 'ask What should I do with my portfolio today?', level: 'info' },
  ]);
});

test('sendCopilotQuestion includes scoped tickers from the selected starter action', async () => {
  const fetchCalls = [];
  const loadingStates = [];
  const errorStates = [];
  const input = {
    value: 'What should I do with NVDA today?',
    dataset: {
      copilotTickers: '["NVDA"]',
    },
  };
  const sandbox = {
    document: {
      getElementById(id) {
        return id === 'copilotQuestionInput' ? input : null;
      },
    },
    copilotState: {
      isLoading: false,
      briefData: {
        scope_tickers: ['msft'],
      },
      conversationId: null,
    },
    window: {
      COPILOT_SCOPE_TICKERS: ['AAPL'],
    },
    fetch: async (url, options) => {
      fetchCalls.push({ url, options });
      return {
        ok: true,
        async json() {
          return {
            data: {
              answer: 'Stay selective.',
              follow_up_context: {
                conversation_id: 'conv-123',
              },
            },
          };
        },
      };
    },
    getCopilotNamespace() {
      return 'personal-finance';
    },
    getCopilotApiBase() {
      return 'http://localhost:8050/api';
    },
    showCopilotLoading(flag) {
      loadingStates.push(flag);
    },
    hideCopilotAnswer() {},
    renderCopilotAnswer(data) {
      sandbox.answer = data;
    },
    updateConversationIndicator() {
      sandbox.updatedConversationIndicator = true;
    },
    showCopilotError(flag) {
      errorStates.push(flag);
    },
    console,
  };

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('normalizeCopilotTickers', 'resolveCopilotScopeTickers'),
      extractFunction('resolveCopilotScopeTickers', 'initCopilotPanel'),
      extractFunction('sendCopilotQuestion', 'renderCopilotAnswer'),
      'this.sendCopilotQuestion = sendCopilotQuestion;',
    ].join('\n\n'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  await sandbox.sendCopilotQuestion();

  assert.equal(fetchCalls.length, 1, 'question should hit the ask endpoint once');
  assert.equal(fetchCalls[0].url, 'http://localhost:8050/api/personal-finance/ask');
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), {
    question: 'What should I do with NVDA today?',
    max_sources: 5,
    tickers: ['NVDA', 'MSFT'],
  });
  assert.deepEqual(loadingStates, [true, false]);
  assert.deepEqual(errorStates, [false]);
  assert.equal(sandbox.answer.answer, 'Stay selective.');
  assert.equal(sandbox.copilotState.conversationId, 'conv-123');
  assert.equal(sandbox.updatedConversationIndicator, true);
  assert.equal(input.value, '', 'input should reset after a successful ask');
});

test('executeCopilotAction navigates open route targets with location.assign', () => {
  const calls = [];
  const sandbox = {
    window: {
      location: {
        assign(target) {
          calls.push({ type: 'assign', target });
        },
        hash: '',
      },
    },
    showToast(message, level) {
      calls.push({ type: 'toast', message, level });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('executeCopilotAction', 'setCopilotQuestion'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.executeCopilotAction('open', '/brief/daily');

  assert.deepEqual(calls[0], { type: 'assign', target: '/brief/daily' });
  assert.deepEqual(calls[1], { type: 'toast', message: 'open /brief/daily', level: 'info' });
});

test('executeCopilotAction preserves hash navigation for in-page targets', () => {
  const calls = [];
  const location = { hash: '' };
  const sandbox = {
    window: { location },
    showToast(message, level) {
      calls.push({ message, level });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('executeCopilotAction', 'setCopilotQuestion'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.executeCopilotAction('open', '#copilot');

  assert.equal(location.hash, '#copilot');
  assert.deepEqual(calls, [{ message: 'open #copilot', level: 'info' }]);
});

test('executeCopilotAction routes namespace open targets through copilot open flow', () => {
  const calls = [];
  const sandbox = {
    window: {
      location: {
        assign(target) {
          calls.push({ type: 'assign', target });
        },
      },
      COPILOT_NAMESPACE: 'personal-finance',
    },
    getCopilotNamespace: () => 'personal-finance',
    runCopilotStartOpen(target) {
      calls.push({ type: 'runOpen', target });
    },
    showToast(message, level) {
      calls.push({ type: 'toast', message, level });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('executeCopilotAction', 'setCopilotQuestion'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.executeCopilotAction('open', '/personal-finance/open');

  assert.deepEqual(calls[0], { type: 'runOpen', target: '/personal-finance' });
  assert.deepEqual(calls[1], { type: 'toast', message: 'open /personal-finance/open', level: 'info' });
});

test('executeCopilotAction routes nested copilot target to copilot start flow', () => {
  const calls = [];
  const sandbox = {
    window: {
      location: {
        assign(target) {
          calls.push({ type: 'assign', target });
        },
      },
    },
    getCopilotNamespace: () => 'copilot',
    runCopilotStartOpen(target) {
      calls.push({ type: 'runOpen', target });
    },
    showToast(message, level) {
      calls.push({ type: 'toast', message, level });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('executeCopilotAction', 'setCopilotQuestion'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.executeCopilotAction('open', '/copilot/overview');

  assert.deepEqual(calls[0], { type: 'runOpen', target: '/copilot/overview' });
  assert.deepEqual(calls[1], { type: 'toast', message: 'open /copilot/overview', level: 'info' });
});

test('executeCopilotAction routes market-style open targets through copilot start flow', () => {
  const calls = [];
  const sandbox = {
    window: {
      location: {
        assign(target) {
          calls.push({ type: 'assign', target });
        },
      },
    },
    getCopilotNamespace: () => 'personal-finance',
    runCopilotStartOpen(target) {
      calls.push({ type: 'runOpen', target });
    },
    showToast(message, level) {
      calls.push({ type: 'toast', message, level });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    extractFunction('executeCopilotAction', 'setCopilotQuestion'),
    sandbox,
    { filename: 'copilot-panel.html' },
  );

  sandbox.executeCopilotAction('open', 'market');

  assert.deepEqual(calls[0], { type: 'runOpen', target: 'market' });
  assert.deepEqual(calls[1], { type: 'toast', message: 'open market', level: 'info' });
});
