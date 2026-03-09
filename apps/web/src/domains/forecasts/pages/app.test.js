const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function extractFunction(source, functionName, nextMarker = '\n\nwindow.addEventListener(LIVE_DATA_EVENT') {
  const start = source.indexOf(`function ${functionName}(`);
  assert.notEqual(start, -1, `Expected ${functionName} to exist in app.js`);
  const end = source.indexOf(nextMarker, start);
  assert.notEqual(end, -1, `Expected end marker after ${functionName} in app.js`);
  return source.slice(start, end);
}

function loadApplyLiveDashboardData() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'applyLiveDashboardData');
  const transformCalls = [];
  const sandbox = {
    console,
    Date,
    LIVE_FALLBACK_TAG: 'live-fallback',
    window: {
      FinanceAPI: {
        transformPortfolioRiskProfileToHealth(input) {
          transformCalls.push(input);
          return {
            portfolioId: input.data?.portfolio?.id || null,
            updatedAt: input.freshness || null,
            status: input.status || null,
            suggestion: 'Derived from raw risk profile',
            riskProfile: 'balanced',
            stateSummary: '1Y horizon | High conviction | Moderate risk',
          };
        },
      },
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    sanitizeTradeIdeas(value) {
      return Array.isArray(value) ? value : [];
    },
    sanitizeForecastRows(value) {
      return Array.isArray(value) ? value : [];
    },
    sanitizeTopMovers(value) {
      return Array.isArray(value) ? value : [];
    },
    sanitizeAlertTimeline(value) {
      return Array.isArray(value) ? value : [];
    },
    normalizeKpiHero() {
      return {};
    },
    sanitizeMarketCalendar(value) {
      return value || null;
    },
    sanitizeNewsItems(value) {
      return Array.isArray(value) ? value : [];
    },
    sanitizeMarketDrivers(value) {
      return Array.isArray(value) ? value : [];
    },
    buildTradeIdeasFromForecasts() {
      return [];
    },
    inferTopStocksFromMovers(_movers, fallback = []) {
      return fallback;
    },
    sanitizeCopilotStart(value) {
      return value;
    },
    buildCopilotStartState(value) {
      return value;
    },
    renderHeroCopilotBrief(value) {
      sandbox.heroBriefState = value;
    },
    sanitizeTopStockRows(value) {
      return value;
    },
    normalizeAppData(value) {
      return value;
    },
    FALLBACK_LLM_JUDGE_DATA: {},
    renderLiveDashboardWidgets() {
      sandbox.rendered = true;
    },
    liveDataMeta: null,
    tradeIdeas: null,
    liveForecastRows: null,
    liveTopMovers: null,
    liveAlerts: null,
    liveKpis: null,
    livePortfolioSummary: null,
    marketCalendar: null,
    newsItems: null,
    marketDrivers: null,
    appData: null,
    llmJudgeData: null,
  };

  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.applyLiveDashboardData = applyLiveDashboardData;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, transformCalls };
}

function createElementStub() {
  return {
    textContent: '',
    className: '',
    style: {},
  };
}

function createActionsRootStub() {
  const root = {
    children: [],
    _innerHTML: '',
    appendChild(node) {
      this.children.push(node);
    },
  };

  Object.defineProperty(root, 'innerHTML', {
    get() {
      return this._innerHTML;
    },
    set(value) {
      this._innerHTML = value;
      if (value === '') {
        this.children = [];
      }
    },
  });

  return root;
}

function createButtonStub() {
  return {
    type: '',
    className: '',
    textContent: '',
    listeners: {},
    addEventListener(eventName, handler) {
      this.listeners[eventName] = handler;
    },
  };
}

function loadRunCopilotStartPrompt() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'runCopilotStartPrompt', '\n\nfunction runCopilotStartOpen(');
  const overlay = { style: { display: '' } };
  const input = { value: '', dataset: {} };
  const calls = {
    focused: 0,
    sent: 0,
    toggled: 0,
  };
  const sandbox = {
    console,
    JSON,
    setTimeout(fn) {
      fn();
      return 0;
    },
    document: {
      getElementById(id) {
        if (id === 'aiCopilotOverlay') return overlay;
        if (id === 'aiOverlayInput') return input;
        return null;
      },
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    normalizeCopilotStarterTickers(value) {
      const seen = new Set();
      return Array.isArray(value)
        ? value
          .map((item) => String(item || '').trim().toUpperCase())
          .filter((ticker) => {
            if (!ticker || seen.has(ticker)) return false;
            seen.add(ticker);
            return true;
          })
        : [];
    },
    focusCopilotInput() {
      calls.focused += 1;
    },
    sendOverlayMessage() {
      calls.sent += 1;
    },
    toggleAICopilot() {
      calls.toggled += 1;
      overlay.style.display = 'block';
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.runCopilotStartPrompt = runCopilotStartPrompt;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, overlay, input, calls };
}

function loadRenderHeroCopilotBrief() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'renderHeroCopilotBrief', '\n\nfunction renderCopilotStartActions(');
  const summaryEl = createElementStub();
  const timestampEl = createElementStub();
  const actionsRoot = createActionsRootStub();
  const promptCalls = [];
  const openCalls = [];
  const sandbox = {
    console,
    Array,
    document: {
      querySelector(selector) {
        if (selector === '.hero-daily-brief .ai-summary-content') return summaryEl;
        if (selector === '.hero-daily-brief .ai-timestamp') return timestampEl;
        if (selector === '.hero-daily-brief .hero-brief-actions') return actionsRoot;
        return null;
      },
      createElement() {
        return createButtonStub();
      },
    },
    buildDefaultCopilotStartState() {
      return {
        brief: {
          summary: 'No daily brief available yet.',
          freshness: '',
        },
        ask: [
          {
            label: 'Ask About Today',
            prompt: 'What changed today?',
            tickers: [],
          },
        ],
        open: [
          {
            label: 'Open Live Brief',
            target: 'market',
          },
        ],
      };
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    formatRelativeTime() {
      return '2 minutes ago';
    },
    runCopilotStartPrompt(prompt, tickers) {
      promptCalls.push({ prompt, tickers });
    },
    runCopilotStartOpen(target) {
      openCalls.push(target);
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderHeroCopilotBrief = renderHeroCopilotBrief;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, summaryEl, timestampEl, actionsRoot, promptCalls, openCalls };
}

function loadRenderPortfolioHealthFullDetails(portfolioHealth) {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'renderPortfolioHealthFullDetails', '\n\nfunction drawHealthGauge(');
  const elements = {
    portfolioHealthFullAllocationFill: createElementStub(),
    portfolioHealthFullAllocationLabel: createElementStub(),
    portfolioHealthFullRiskFill: createElementStub(),
    portfolioHealthFullProfileBadge: createElementStub(),
    portfolioHealthFullRiskSummary: createElementStub(),
    portfolioHealthFullConfidenceFill: createElementStub(),
    portfolioHealthFullStateSummary: createElementStub(),
    portfolioHealthSuggestionPrimary: createElementStub(),
    portfolioHealthSuggestionPrimaryText: createElementStub(),
    portfolioHealthSuggestionSecondary: createElementStub(),
    portfolioHealthSuggestionSecondaryText: createElementStub(),
    portfolioHealthSuggestionTertiary: createElementStub(),
    portfolioHealthSuggestionTertiaryText: createElementStub(),
  };
  const sandbox = {
    console,
    appData: {
      portfolioHealth,
    },
    FALLBACK_APP_DATA: {
      portfolioHealth: {
        suggestion: 'Diversify Tech → Healthcare',
        riskLabel: 'Medium',
        riskTone: 'neutral',
        riskProfile: 'balanced',
        confidence: 82,
        stateSummary: '1Y horizon | High conviction | Moderate risk',
        allocationLabel: 'Largest saved weight: NVDA 45%',
        allocationProgress: 75,
        benchmark: 'SPY',
      },
    },
    document: {
      getElementById(id) {
        return elements[id] || null;
      },
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    toFiniteNumber(value, fallback = 0) {
      const normalized = Number(value);
      return Number.isFinite(normalized) ? normalized : fallback;
    },
    mapPortfolioHealthTone(value) {
      const tone = String(value || '').toLowerCase();
      return tone === 'positive' || tone === 'warning' || tone === 'neutral' ? tone : 'neutral';
    },
    formatPortfolioHealthProfile(value) {
      const normalized = String(value || 'balanced').replace(/[_-]+/g, ' ').trim();
      if (!normalized) {
        return 'Balanced';
      }
      return normalized
        .split(/\s+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderPortfolioHealthFullDetails = renderPortfolioHealthFullDetails;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, elements };
}

test('applyLiveDashboardData derives portfolio health from raw risk profile payloads', () => {
  const { sandbox, transformCalls } = loadApplyLiveDashboardData();
  const rawRiskProfile = {
    portfolio: { id: 'portfolio-123', name: 'Core' },
    risk: { level: 'medium' },
  };

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-09T07:00:00Z',
    data: {
      portfolioRiskProfile: rawRiskProfile,
      portfolioRiskProfileStatus: 'degraded',
      portfolioRiskProfileFreshness: '2026-03-09T06:30:00Z',
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(transformCalls)), [
    {
      data: rawRiskProfile,
      freshness: '2026-03-09T06:30:00Z',
      status: 'degraded',
    },
  ]);
  assert.equal(sandbox.appData.portfolioRiskProfile, rawRiskProfile);
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.appData.portfolioHealth)), {
    portfolioId: 'portfolio-123',
    updatedAt: '2026-03-09T06:30:00Z',
    status: 'degraded',
    suggestion: 'Derived from raw risk profile',
    riskProfile: 'balanced',
    stateSummary: '1Y horizon | High conviction | Moderate risk',
  });
  assert.equal(sandbox.appData.portfolioRiskProfileFreshness, '2026-03-09T06:30:00Z');
  assert.equal(sandbox.liveDataMeta.generatedAt, '2026-03-09T07:00:00Z');
  assert.equal(sandbox.rendered, true);
});

test('applyLiveDashboardData backfills portfolio health core fields from the raw risk profile payload', () => {
  const { sandbox, transformCalls } = loadApplyLiveDashboardData();
  const explicitPortfolioHealth = {
    portfolioId: 'portfolio-123',
    overall: 91,
    suggestion: 'Provided by API',
  };

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-09T07:00:00Z',
    data: {
      portfolioHealth: explicitPortfolioHealth,
      portfolioRiskProfile: {
        portfolio: { id: 'portfolio-123', name: 'Core' },
        risk: { level: 'medium' },
      },
      portfolioRiskProfileFreshness: '2026-03-09T06:30:00Z',
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(transformCalls)), [
    {
      data: {
        portfolio: { id: 'portfolio-123', name: 'Core' },
        risk: { level: 'medium' },
      },
      freshness: '2026-03-09T06:30:00Z',
      status: null,
    },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.appData.portfolioHealth)), {
    portfolioId: 'portfolio-123',
    updatedAt: '2026-03-09T06:30:00Z',
    status: null,
    suggestion: 'Provided by API',
    riskProfile: 'balanced',
    stateSummary: '1Y horizon | High conviction | Moderate risk',
    overall: 91,
  });
  assert.equal(sandbox.appData.portfolioRiskProfileFreshness, '2026-03-09T06:30:00Z');
  assert.equal(sandbox.rendered, true);
});

test('applyLiveDashboardData hydrates the hero brief from live copilot_start data', () => {
  const { sandbox } = loadApplyLiveDashboardData();

  sandbox.buildCopilotStartState = (value) => ({
    brief: {
      summary: value.copilot_start.brief_of_day.summary,
      freshness: value.copilot_start.brief_of_day.freshness,
    },
    ask: [
      {
        label: 'Ask about today',
        prompt: 'What matters today?',
        tickers: ['NVDA'],
      },
    ],
    open: [
      {
        label: 'Open live brief',
        target: 'market',
      },
    ],
  });

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-09T07:00:00Z',
    data: {
      copilot_start: {
        brief_of_day: {
          summary: 'Breadth is narrow but stable.',
          freshness: '2026-03-09T06:55:00Z',
        },
      },
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.heroBriefState)), {
    brief: {
      summary: 'Breadth is narrow but stable.',
      freshness: '2026-03-09T06:55:00Z',
    },
    ask: [
      {
        label: 'Ask about today',
        prompt: 'What matters today?',
        tickers: ['NVDA'],
      },
    ],
    open: [
      {
        label: 'Open live brief',
        target: 'market',
      },
    ],
  });
});

test('runCopilotStartPrompt opens the overlay before sending a hero starter prompt', () => {
  const { sandbox, overlay, input, calls } = loadRunCopilotStartPrompt();

  sandbox.runCopilotStartPrompt("Give me today's brief.", ['nvda', 'NVDA', 'msft']);

  assert.equal(calls.toggled, 1);
  assert.equal(calls.focused, 1);
  assert.equal(calls.sent, 1);
  assert.equal(overlay.style.display, 'block');
  assert.equal(input.value, "Give me today's brief.");
  assert.equal(input.dataset.copilotTickers, JSON.stringify(['NVDA', 'MSFT']));
});

test('renderHeroCopilotBrief swaps the static hero copy for live brief and actions', () => {
  const { sandbox, summaryEl, timestampEl, actionsRoot, promptCalls, openCalls } = loadRenderHeroCopilotBrief();

  sandbox.renderHeroCopilotBrief({
    brief: {
      summary: 'Rates are calm while leadership stays narrow.',
      freshness: '2026-03-09T06:58:00Z',
    },
    ask: [
      {
        label: 'Ask about NVDA',
        prompt: 'Explain what matters for NVDA today.',
        tickers: ['NVDA'],
      },
    ],
    open: [
      {
        label: 'Open live brief',
        target: 'market',
      },
      {
        label: 'Open copilot',
        target: 'copilot',
      },
    ],
  });

  assert.equal(summaryEl.textContent, 'Rates are calm while leadership stays narrow.');
  assert.equal(timestampEl.textContent, 'Generated 2 minutes ago');
  assert.equal(actionsRoot.children.length, 2);
  assert.equal(actionsRoot.children[0].textContent, 'Ask about NVDA');
  assert.equal(actionsRoot.children[1].textContent, 'Open live brief');

  actionsRoot.children[0].listeners.click();
  actionsRoot.children[1].listeners.click();

  assert.deepEqual(JSON.parse(JSON.stringify(promptCalls)), [
    {
      prompt: 'Explain what matters for NVDA today.',
      tickers: ['NVDA'],
    },
  ]);
  assert.deepEqual(openCalls, ['market']);
});

test('renderPortfolioHealthFullDetails maps portfolio state and risk profile into the full analysis panel', () => {
  const { sandbox, elements } = loadRenderPortfolioHealthFullDetails({
    allocationProgress: 70,
    allocationLabel: 'Largest saved weight: MSFT 70%',
    riskLabel: 'High',
    riskTone: 'warning',
    riskProfile: 'risk_off',
    benchmark: 'QQQ',
    confidence: 61,
    stateSummary: '6M horizon | Medium conviction | High risk',
    suggestion: 'Trim NVDA position',
    status: 'degraded',
  });

  sandbox.renderPortfolioHealthFullDetails();

  assert.equal(elements.portfolioHealthFullAllocationFill.style.width, '70%');
  assert.equal(elements.portfolioHealthFullAllocationFill.textContent, '70%');
  assert.equal(elements.portfolioHealthFullAllocationLabel.textContent, 'Largest saved weight: MSFT 70%');
  assert.equal(elements.portfolioHealthFullRiskFill.style.width, '85%');
  assert.equal(elements.portfolioHealthFullRiskFill.textContent, 'High');
  assert.equal(elements.portfolioHealthFullProfileBadge.className, 'context-badge warning');
  assert.equal(elements.portfolioHealthFullProfileBadge.textContent, 'Risk Off');
  assert.equal(elements.portfolioHealthFullRiskSummary.textContent, 'Risk concentration: High | Benchmark QQQ');
  assert.equal(elements.portfolioHealthFullConfidenceFill.style.width, '61%');
  assert.equal(elements.portfolioHealthFullConfidenceFill.textContent, '61%');
  assert.equal(elements.portfolioHealthFullStateSummary.textContent, '6M horizon | Medium conviction | High risk');
  assert.equal(elements.portfolioHealthSuggestionPrimary.className, 'suggestion-item high');
  assert.equal(elements.portfolioHealthSuggestionPrimaryText.textContent, 'Trim NVDA position');
  assert.equal(elements.portfolioHealthSuggestionSecondary.className, 'suggestion-item medium');
  assert.equal(elements.portfolioHealthSuggestionSecondaryText.textContent, '6M horizon | Medium conviction | High risk');
  assert.equal(elements.portfolioHealthSuggestionTertiary.className, 'suggestion-item high');
  assert.equal(elements.portfolioHealthSuggestionTertiaryText.textContent, 'Largest saved weight: MSFT 70%');
});
