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

function extractSection(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  assert.notEqual(start, -1, `Expected section starting with ${startMarker}`);
  const end = source.indexOf(endMarker, start);
  assert.notEqual(end, -1, `Expected section ending with ${endMarker}`);
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
    resolveCopilotStartState(value) {
      if (value && typeof value === 'object' && !Array.isArray(value) && value.brief) {
        return value;
      }

      const raw = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
      const brief = raw.brief_of_day && typeof raw.brief_of_day === 'object' ? raw.brief_of_day : {};
      const scopeTickers = Array.isArray(raw.scope_tickers)
        ? raw.scope_tickers
          .map((ticker) => String(ticker || '').trim().toUpperCase())
          .filter((ticker, index, list) => ticker && list.indexOf(ticker) === index)
        : [];

      return {
        brief: {
          summary: typeof brief.summary === 'string' ? brief.summary : 'No daily brief available yet.',
          freshness: typeof brief.freshness === 'string' ? brief.freshness : '',
        },
        ask: Array.isArray(raw.ask)
          ? raw.ask.map((item, index) => ({
            id: typeof item?.id === 'string' ? item.id : `ask-${index}`,
            label: typeof item?.label === 'string' ? item.label : 'Ask copilot',
            prompt: typeof item?.prompt === 'string' ? item.prompt : '',
            tickers: Array.isArray(item?.tickers) && item.tickers.length
              ? item.tickers
              : scopeTickers,
          }))
          : [],
        open: Array.isArray(raw.open)
          ? raw.open.map((item, index) => ({
            id: typeof item?.id === 'string' ? item.id : `open-${index}`,
            label: typeof item?.label === 'string' ? item.label : 'Open',
            target: typeof item?.target === 'string' && item.target.trim().toLowerCase() === '/brief/daily'
              ? 'market'
              : (typeof item?.target === 'string' ? item.target.replace(/^\/+/, '') : ''),
          }))
          : [],
      };
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

function createInteractiveElementStub() {
  let innerHTML = '';
  return {
    textContent: '',
    className: '',
    style: {},
    dataset: {},
    children: [],
    listeners: {},
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    addEventListener(eventName, handler) {
      this.listeners[eventName] = handler;
    },
    click() {
      if (typeof this.listeners.click === 'function') {
        this.listeners.click();
      }
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
    get innerHTML() {
      return innerHTML;
    },
    set innerHTML(value) {
      innerHTML = value;
      if (value === '') {
        this.children = [];
      }
    },
  };
}

function loadSanitizeCopilotStart() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'sanitizeCopilotStart', '\n\nconst ALERT_SEVERITY_ORDER');
  const sandbox = {
    console,
    FALLBACK_COPILOT_START: {
      brief_of_day: {
        title: 'Brief of the day',
        summary: 'No daily brief available yet.',
        market_sentiment: 'UNKNOWN',
        top_signals: [],
        top_risks: [],
        macro_signals: [],
        sector_rotation: {
          top: [],
          bottom: [],
        },
        generated_at: '',
        freshness: '',
        source: ['brief_daily_fallback'],
      },
      ask: [
        {
          id: 'portfolio_today',
          label: 'Portfolio today?',
          prompt: 'What should I do with my portfolio today?',
        },
      ],
      open: [
        {
          id: 'market',
          label: 'Open market view',
          target: 'market',
        },
      ],
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
    normalizeCopilotStarterTickers(value) {
      const seen = new Set();
      return (Array.isArray(value) ? value : [])
        .map((ticker) => String(ticker || '').trim().toUpperCase())
        .filter((ticker) => {
          if (!ticker || seen.has(ticker)) {
            return false;
          }
          seen.add(ticker);
          return true;
        });
    },
    normalizeCopilotStartOpenTarget(target, id = '') {
      const normalizedTarget = String(target || '').trim().toLowerCase();
      const normalizedId = String(id || '').trim().toLowerCase();
      if (normalizedId === 'brief_of_day' || normalizedTarget === '/brief/daily') {
        return 'market';
      }
      return normalizedTarget.replace(/^\/+/, '');
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.sanitizeCopilotStart = sanitizeCopilotStart;`, sandbox, {
    filename: 'app.js',
  });

  return sandbox;
}

function loadRenderHeroCopilotBriefWithHeroIds(resolvedState) {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'renderHeroCopilotBrief', '\n\nfunction renderCopilotStartActions(');
  const elements = {
    heroBriefTitle: createInteractiveElementStub(),
    heroBriefLead: createInteractiveElementStub(),
    heroBriefSummary: createInteractiveElementStub(),
    heroBriefTimestamp: createInteractiveElementStub(),
    heroBriefSignals: createInteractiveElementStub(),
    heroBriefRisks: createInteractiveElementStub(),
    heroBriefActions: createInteractiveElementStub(),
    heroSuggestionChips: createInteractiveElementStub(),
  };
  const promptCalls = [];
  const openCalls = [];
  const sandbox = {
    console,
    document: {
      getElementById(id) {
        return elements[id] || null;
      },
      querySelector() {
        return null;
      },
      createElement() {
        return createInteractiveElementStub();
      },
    },
    buildDefaultCopilotStartState() {
      return {
        brief: {
          title: 'Brief of the day',
          summary: 'No daily brief available yet.',
          marketSentiment: 'UNKNOWN',
          topSignals: [],
          topRisks: [],
          freshness: '',
        },
        ask: [
          {
            id: 'portfolio_today',
            label: 'Portfolio today?',
            prompt: 'What should I do with my portfolio today?',
            tickers: [],
          },
        ],
        open: [
          {
            id: 'market',
            label: 'Open market view',
            target: 'market',
          },
        ],
      };
    },
    resolveCopilotStartState() {
      return resolvedState;
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    formatRelativeTime(value) {
      return value === '2026-03-09T08:00:00Z' ? '2 minutes ago' : 'just now';
    },
    runCopilotStartPrompt(prompt, tickers = []) {
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

  return { sandbox, elements, promptCalls, openCalls };
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
  const functionSource = extractSection(
    source,
    'function normalizeCopilotStarterTickers(',
    '\n\nfunction renderCopilotStartActions('
  );
  const summaryEl = createElementStub();
  const timestampEl = createElementStub();
  const actionsRoot = createActionsRootStub();
  const overlay = {
    style: { display: '' },
    classList: {
      remove() {},
    },
  };
  const input = {
    value: '',
    dataset: {},
    focus() {
      input.focused = (input.focused || 0) + 1;
    },
  };
  const marketTab = { id: 'tab-market' };
  const marketTabButton = { id: 'tab-btn-market' };
  const promptCalls = [];
  const openCalls = [];
  const sandbox = {
    console,
    Array,
    JSON,
    setTimeout(fn) {
      fn();
      return 0;
    },
    document: {
      querySelector(selector) {
        if (selector === '.hero-daily-brief .ai-summary-content') return summaryEl;
        if (selector === '.hero-daily-brief .ai-timestamp') return timestampEl;
        if (selector === '.hero-daily-brief .hero-brief-actions') return actionsRoot;
        if (selector === '.tab-btn[data-tab="market"]') return marketTabButton;
        return null;
      },
      getElementById(id) {
        if (id === 'aiCopilotOverlay') return overlay;
        if (id === 'aiOverlayInput') return input;
        if (id === 'tab-market') return marketTab;
        return null;
      },
      createElement() {
        return createButtonStub();
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
    formatRelativeTime() {
      return '2 minutes ago';
    },
    sendOverlayMessage() {
      promptCalls.push({
        prompt: input.value,
        tickers: JSON.parse(input.dataset.copilotTickers || '[]'),
      });
    },
    toggleAICopilot() {
      overlay.style.display = 'block';
    },
    safeSwitchTab(_button, target) {
      openCalls.push(target);
    },
    showToast(target) {
      openCalls.push(`toast:${target}`);
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderHeroCopilotBrief = renderHeroCopilotBrief;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, summaryEl, timestampEl, actionsRoot, promptCalls, openCalls, overlay, input };
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
  assert.equal(timestampEl.textContent, 'Updated 2 minutes ago');
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

test('renderHeroCopilotBrief accepts raw copilot_start payloads from app state', () => {
  const { sandbox, summaryEl, timestampEl, actionsRoot, promptCalls, openCalls, input } = loadRenderHeroCopilotBrief();

  sandbox.renderHeroCopilotBrief({
    brief_of_day: {
      summary: 'Rotation is narrow but the tape remains constructive.',
      freshness: '2026-03-09T06:58:00Z',
    },
    ask: [
      {
        label: 'Ask about today',
        prompt: "What matters most in today's brief?",
      },
    ],
    open: [
      {
        label: 'Open live brief',
        target: '/brief/daily',
      },
    ],
    scope_tickers: ['nvda', 'MSFT', 'nvda'],
  });

  assert.equal(summaryEl.textContent, 'Rotation is narrow but the tape remains constructive.');
  assert.equal(timestampEl.textContent, 'Updated 2 minutes ago');
  assert.equal(actionsRoot.children.length, 2);

  actionsRoot.children[0].listeners.click();
  actionsRoot.children[1].listeners.click();

  assert.equal(input.dataset.copilotTickers, JSON.stringify(['NVDA', 'MSFT']));
  assert.deepEqual(JSON.parse(JSON.stringify(promptCalls)), [
    {
      prompt: "What matters most in today's brief?",
      tickers: ['NVDA', 'MSFT'],
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

test('sanitizeCopilotStart preserves starter tickers and normalizes brief open targets', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    ask: [
      {
        id: 'macro_check',
        label: 'Macro check',
        prompt: 'What changed in my macro setup?',
        prefill: {
          tickers: ['nvda', ' msft ', 'NVDA'],
        },
      },
    ],
    open: [
      {
        id: 'brief_of_day',
        label: 'Open live brief',
        target: '/brief/daily',
      },
    ],
  });

  assert.deepEqual(JSON.parse(JSON.stringify(result.ask[0].tickers)), ['NVDA', 'MSFT']);
  assert.equal(result.open[0].target, 'market');
});

test('renderHeroCopilotBrief hydrates the landing brief and wires ask/open actions', () => {
  const state = {
    brief: {
      title: 'Opening Brief',
      summary: 'Risk is concentrated in tech while breadth improves underneath.',
      marketSentiment: 'RISK_ON',
      topSignals: ['Breadth improving', 'Rates easing'],
      topRisks: ['CPI tomorrow'],
      freshness: '2026-03-09T08:00:00Z',
    },
    ask: [
      {
        id: 'ask_today',
        label: 'Ask About Today',
        prompt: 'What matters most today?',
        tickers: ['NVDA', 'MSFT'],
      },
      {
        id: 'watch_next',
        label: 'Watch next',
        prompt: 'What should I watch next?',
        tickers: [],
      },
    ],
    open: [
      {
        id: 'market',
        label: 'Open Live Brief',
        target: 'market',
      },
      {
        id: 'opportunities',
        label: 'Open opportunities',
        target: 'opportunities',
      },
    ],
  };
  const { sandbox, elements, promptCalls, openCalls } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(elements.heroBriefTitle.textContent, 'Opening Brief');
  assert.equal(elements.heroBriefLead.textContent, 'A 30-second portfolio memo before you dive deeper. Tone: risk on.');
  assert.equal(elements.heroBriefSummary.textContent, 'Risk is concentrated in tech while breadth improves underneath.');
  assert.equal(elements.heroBriefTimestamp.textContent, 'Updated 2 minutes ago');
  assert.equal(elements.heroBriefSignals.textContent, 'Signals: Breadth improving • Rates easing');
  assert.equal(elements.heroBriefSignals.style.display, 'block');
  assert.equal(elements.heroBriefRisks.textContent, 'Risks: CPI tomorrow');
  assert.equal(elements.heroBriefRisks.style.display, 'block');

  assert.equal(elements.heroBriefActions.children.length, 2);
  assert.equal(elements.heroBriefActions.children[0].textContent, 'Ask About Today');
  assert.equal(elements.heroBriefActions.children[1].textContent, 'Open Live Brief');

  elements.heroBriefActions.children[0].click();
  elements.heroBriefActions.children[1].click();

  assert.deepEqual(JSON.parse(JSON.stringify(promptCalls)), [
    {
      prompt: 'What matters most today?',
      tickers: ['NVDA', 'MSFT'],
    },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(openCalls)), ['market']);

  assert.equal(elements.heroSuggestionChips.children.length, 2);
  assert.equal(elements.heroSuggestionChips.children[0].textContent, 'Watch next');
  assert.equal(elements.heroSuggestionChips.children[1].textContent, 'Open opportunities');

  elements.heroSuggestionChips.children[0].click();
  elements.heroSuggestionChips.children[1].click();

  assert.deepEqual(JSON.parse(JSON.stringify(promptCalls)), [
    {
      prompt: 'What matters most today?',
      tickers: ['NVDA', 'MSFT'],
    },
    {
      prompt: 'What should I watch next?',
      tickers: [],
    },
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(openCalls)), ['market', 'opportunities']);
});
