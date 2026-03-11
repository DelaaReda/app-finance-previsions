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
    sanitizeInsiderBehavior(value) {
      return value && typeof value === 'object' ? value : null;
    },
    buildTradeIdeasFromForecasts() {
      return [];
    },
    summarizeForecastSla() {
      return null;
    },
    inferTopStocksFromMovers(_movers, fallback = []) {
      return fallback;
    },
    sanitizeCopilotStart(value) {
      return value && typeof value === 'object' ? value : {};
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
    sanitizeJudgeDecisionJournal(value) {
      const rows = Array.isArray(value) ? value : [];
      return rows.slice(0, 8).map((entry) => ({
        symbol: entry.symbol || 'Décision',
        decision: entry.decision || 'N/A',
        note: entry.note || '',
        rationale: entry.rationale || '',
        confidence: entry.confidence || null,
        timestamp: entry.timestamp || null,
        outcome_feedback: entry.outcome_feedback || null
      }));
    },
    FALLBACK_LLM_JUDGE_DATA: {},
    renderLiveDashboardWidgets() {
      sandbox.rendered = true;
    },
    liveDataMeta: null,
    tradeIdeas: null,
    liveForecastRows: null,
    liveForecastScoreboard: null,
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

function loadForecastSlaHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const sanitizeForecastRowsSource = extractFunction(source, 'sanitizeForecastRows', '\n\nfunction sanitizeTopMovers');
  const summarizeForecastSlaSource = extractFunction(source, 'summarizeForecastSla', '\n\nfunction syncDashboardCards');
  const updateLiveProvenanceSource = extractFunction(source, 'updateLiveProvenance', '\n\nfunction summarizeForecastSla');
  const lineage = { textContent: '' };
  const sandbox = {
    console,
    LIVE_FALLBACK_TAG: 'live-fallback',
    document: {
      getElementById(id) {
        return id === 'liveDataProvenance' ? lineage : null;
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
    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : fallback;
    },
    normalizePercentValue(value) {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) return 0;
      return Math.abs(numeric) <= 1 ? numeric * 100 : numeric;
    },
    formatRelativeTime() {
      return '2 minutes ago';
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${sanitizeForecastRowsSource}\n${updateLiveProvenanceSource}\n${summarizeForecastSlaSource}\nthis.sanitizeForecastRows = sanitizeForecastRows;\nthis.updateLiveProvenance = updateLiveProvenance;\nthis.summarizeForecastSla = summarizeForecastSla;`,
    sandbox,
    { filename: 'app.js' }
  );

  return { sandbox, lineage };
}

function loadMacroRegimeCardsRenderer() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'renderMacroRegimeCardsWidget', '\n\nfunction renderForecastScenarioWidget');
  const nodes = new Map();
  const makeNode = (initialClassName = '') => ({
    textContent: '',
    className: initialClassName,
  });
  const worldCard = {
    querySelector(selector) {
      return nodes.get(`world:${selector}`) || null;
    },
  };
  const continentCard = {
    querySelector(selector) {
      return nodes.get(`continent:${selector}`) || null;
    },
  };
  const countryCard = {
    querySelector(selector) {
      return nodes.get(`country:${selector}`) || null;
    },
  };

  ['world', 'continent', 'country'].forEach((scope) => {
    nodes.set(`${scope}:[data-role="macro-label"]`, makeNode());
    nodes.set(`${scope}:[data-role="macro-confidence"]`, makeNode('macro-confidence medium'));
    nodes.set(`${scope}:[data-role="macro-regime"]`, makeNode('regime-badge recovery'));
    nodes.set(`${scope}:[data-role="macro-summary"]`, makeNode());
    nodes.set(`${scope}:[data-role="macro-drivers"]`, makeNode());
    nodes.set(`${scope}:[data-role="macro-risks"]`, makeNode());
  });
  const consistencyIcon = makeNode('consistency-icon ok');
  const consistencyText = makeNode();
  const insightText = makeNode();
  const timestamp = makeNode();
  const widget = {
    querySelector(selector) {
      if (selector === '[data-role="macro-card"][data-scope="world"]') return worldCard;
      if (selector === '[data-role="macro-card"][data-scope="continent"]') return continentCard;
      if (selector === '[data-role="macro-card"][data-scope="country"]') return countryCard;
      if (selector === '[data-role="macro-consistency-icon"]') return consistencyIcon;
      if (selector === '[data-role="macro-consistency-text"]') return consistencyText;
      if (selector === '[data-role="macro-insight-text"]') return insightText;
      if (selector === '[data-role="macro-timestamp"]') return timestamp;
      return null;
    },
  };

  const sandbox = {
    console,
    liveDataMeta: {
      macroRegimeHierarchy: null,
    },
    window: {
      macroRegimeHierarchy: null,
    },
    document: {
      querySelector(selector) {
        if (selector === '.macro-regime-cards') return widget;
        return null;
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
    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : fallback;
    },
    formatRelativeTime(value) {
      return `relative:${value}`;
    },
  };
  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderMacroRegimeCardsWidget = renderMacroRegimeCardsWidget;`, sandbox, {
    filename: 'app.js',
  });

  return {
    sandbox,
    nodes,
    consistencyIcon,
    consistencyText,
    insightText,
    timestamp,
  };
}

function loadSanitizeInsiderBehavior() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'sanitizeInsiderBehavior', '\n\nfunction sanitizeJudgeDecisionJournal');
  const sandbox = {
    console,
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : fallback;
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.sanitizeInsiderBehavior = sanitizeInsiderBehavior;`, sandbox, {
    filename: 'app.js',
  });

  return sandbox;
}

function loadAlertTimelineHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const helpersSource = extractSection(source, 'const ALERT_SEVERITY_ORDER = {', '\n\nfunction sanitizeMarketCalendar');
  const timelineContainer = { innerHTML: '' };
  const sandbox = {
    console,
    Date,
    document: {
      getElementById(id) {
        return id === 'timelineContainer' ? timelineContainer : null;
      },
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    toString(value, fallback = '') {
      return value === null || value === undefined ? fallback : String(value);
    },
    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : fallback;
    },
    formatRelativeTime() {
      return '2 minutes ago';
    },
    toggleAlertDetails() {},
    showToast() {},
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${helpersSource}\nthis.sanitizeAlertTimeline = sanitizeAlertTimeline;\nthis.renderAlertTimeline = renderAlertTimeline;`,
    sandbox,
    { filename: 'app.js' }
  );

  return { sandbox, timelineContainer };
}

function loadRenderForecastScenarioWidget() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'renderForecastScenarioWidget', '\n\nfunction renderTopMoversWidget');
  const scenarioContext = createElementStub();
  const widgetTimestamp = createElementStub();
  const geopoliticalRisk = createElementStub();
  const geopoliticalGraph = createElementStub();
  const geopoliticalAlertCopy = createElementStub();
  const geopoliticalAlertBand = createElementStub();
  const shockChain = createElementStub();
  const shockChainBand = createElementStub();
  const shockChainUpstream = createElementStub();
  const shockChainTransmission = createElementStub();
  const shockChainWatchlist = createElementStub();
  const shockChainAssumptionVersion = createElementStub();
  const shockChainAssumptionCopy = createElementStub();
  const shockChainCopy = createElementStub();
  const bars = Array.from({ length: 3 }, () => {
    const fill = createElementStub();
    const label = createElementStub();
    return {
      fill,
      label,
      querySelector(selector) {
        if (selector === '.scenario-bar-fill') return fill;
        if (selector === '.scenario-label') return label;
        return null;
      },
    };
  });
  const scenarioWidget = {
    querySelector(selector) {
      if (selector === '.scenario-context') return scenarioContext;
      if (selector === '.widget-timestamp') return widgetTimestamp;
      if (selector === '[data-role="geopolitical-risk"]') return geopoliticalRisk;
      if (selector === '[data-role="geo-graph"]') return geopoliticalGraph;
      if (selector === '[data-role="geo-alert-copy"]') return geopoliticalAlertCopy;
      if (selector === '[data-role="geo-alert-band"]') return geopoliticalAlertBand;
      if (selector === '[data-role="shock-chain"]') return shockChain;
      if (selector === '[data-role="shock-chain-band"]') return shockChainBand;
      if (selector === '[data-role="shock-chain-upstream"]') return shockChainUpstream;
      if (selector === '[data-role="shock-chain-transmission"]') return shockChainTransmission;
      if (selector === '[data-role="shock-chain-watchlist"]') return shockChainWatchlist;
      if (selector === '[data-role="shock-chain-assumption-version"]') return shockChainAssumptionVersion;
      if (selector === '[data-role="shock-chain-assumption-copy"]') return shockChainAssumptionCopy;
      if (selector === '[data-role="shock-chain-copy"]') return shockChainCopy;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === '.scenario-bar-item') return bars;
      return [];
    },
  };
  const sandbox = {
    console,
    document: {
      querySelector(selector) {
        if (selector === '.forecast-scenarios-widget') return scenarioWidget;
        return null;
      },
    },
    sanitizeForecastRows(value) {
      return Array.isArray(value) ? value : [];
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    liveForecastRows: [],
    liveForecastScoreboard: null,
    liveDataMeta: null,
    window: {},
    toString(value, fallback = '') {
      return value === null || value === undefined ? fallback : String(value);
    },
    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : fallback;
    },
    escapeHtml(value) {
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },
    formatRelativeTime() {
      return '2 minutes ago';
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderForecastScenarioWidget = renderForecastScenarioWidget;`, sandbox, {
    filename: 'app.js',
  });

  return {
    sandbox,
    bars,
    scenarioContext,
    widgetTimestamp,
    geopoliticalRisk,
    geopoliticalGraph,
    geopoliticalAlertCopy,
    geopoliticalAlertBand,
    shockChain,
    shockChainBand,
    shockChainUpstream,
    shockChainTransmission,
    shockChainWatchlist,
    shockChainAssumptionVersion,
    shockChainAssumptionCopy,
    shockChainCopy,
  };
}

function loadRenderMarketDrivers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'renderMarketDrivers', '\n\n// V13: Ask LLM Judge');
  const container = createInteractiveElementStub();
  const sandbox = {
    console,
    marketDrivers: [
      { factor: 'Technical Signals', contribution: 40, color: '#1F40AF' },
    ],
    insiderBehavior: {
      fallbackUsed: false,
      summaryWarning: 'Insider activity is evidence with uncertainty, never a standalone directive.',
      policy: 'Insider activity is evidence with uncertainty, never a standalone directive.',
      signals: [
        {
          ticker: 'NVDA',
          confidence: 61,
          uncertaintyLevel: 'medium',
          summary: 'Insider activity for NVDA suggests accumulation bias.',
          netTrades30d: 4,
          reviewNote: 'Use insider behavior only as corroborating evidence.',
          filingSource: 'public_form4',
          sources: ['forecasts_insider_behavior', 'sec_edgar_form4'],
          uncertaintyFactors: ['limited_sample_size', 'single_cluster_activity'],
        },
      ],
    },
    document: {},
    getFacetteWidgetSlot() {
      return container;
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderMarketDrivers = renderMarketDrivers;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, container };
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
          id: 'brief_of_day',
          label: 'Open Live Brief',
          target: '/brief/daily',
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
      const normalizedTarget = String(target || '')
        .trim()
        .toLowerCase()
        .replace(/[?#].*$/, '')
        .replace(/\/+$/, '');
      const normalizedId = String(id || '').trim().toLowerCase();
      if (
        normalizedId === 'brief_of_day'
        || normalizedTarget === '/brief/daily'
        || normalizedTarget === '/brief'
        || normalizedTarget === 'brief/daily'
        || normalizedTarget === 'brief_of_day'
        || normalizedTarget === 'brief'
        || normalizedTarget === 'live_brief'
        || normalizedTarget === 'daily_brief'
      ) {
        return 'market';
      }
      if (
        normalizedId === 'ask_copilot'
        || normalizedId === 'open_copilot'
        || normalizedId === 'copilot'
        || normalizedTarget === '/copilot'
        || normalizedTarget === '/copilot/ask'
        || normalizedTarget === 'copilot/ask'
        || normalizedTarget === 'copilot'
      ) {
        return 'copilot';
      }
      return normalizedTarget.replace(/^\/+/, '');
    },
    normalizeCopilotStartList(value) {
      return (Array.isArray(value) ? value : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean)
        .slice(0, 3);
    },
    normalizeCopilotSourceLabels(value) {
      return (Array.isArray(value) ? value : value ? [value] : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean);
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
            id: 'brief_of_day',
            label: 'Open Live Brief',
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
    normalizeCopilotStartList(value) {
      return (Array.isArray(value) ? value : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean)
        .slice(0, 3);
    },
    normalizeCopilotSourceLabels(value) {
      return (Array.isArray(value) ? value : value ? [value] : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean);
    },
    normalizeCopilotStarterTickers(value) {
      const seen = new Set();
      return (Array.isArray(value) ? value : [])
        .map((item) => String(item || '').trim().toUpperCase())
        .filter((ticker) => {
          if (!ticker || seen.has(ticker)) return false;
          seen.add(ticker);
          return true;
        });
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

function loadRobustnessGoNoGoDecision(statusOverride = null) {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'buildRobustnessGoNoGoDecision', '\n\nfunction openDrillDown(');
  const sandbox = {
    console,
    LIVE_FALLBACK_TAG: 'live-fallback',
    liveDataMeta: {
      generatedAt: '2026-03-09T08:00:00Z',
      sources: ['test-feed'],
      modelVersions: ['v-test'],
      warnings: [],
    },
    getCriticalWidgetHealthStatus() {
      return statusOverride;
    },
    buildCriticalWidgetHealthDetail() {
      return 'Generated fallback detail';
    },
    toString(value, fallback = '') {
      return value === null || value === undefined ? fallback : String(value);
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.buildRobustnessGoNoGoDecision = buildRobustnessGoNoGoDecision;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox };
}

function loadRobustnessDrillOpenFlow(statusOverride = null) {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const marker = '\n\nfunction openDrillDown(';
  const decisionSource = extractFunction(source, 'buildRobustnessGoNoGoDecision', marker);
  const openRobustnessSource = extractFunction(source, 'openRobustnessDrill', marker);
  const openDrillDownSource = extractFunction(source, 'openDrillDown', '\n\nfunction closeDrillDown(');

  const modal = createElementStub();
  const title = createElementStub();
  const body = createElementStub();
  const calls = {
    display: 0,
  };
  const sandbox = {
    console,
    document: {
      getElementById(id) {
        if (id === 'drillDownModal') return modal;
        if (id === 'drillDownTitle') return title;
        if (id === 'drillDownBody') return body;
        return null;
      },
    },
    LIVE_FALLBACK_TAG: 'live-fallback',
    liveDataMeta: {
      generatedAt: '2026-03-09T08:00:00Z',
      sources: ['test-feed'],
      modelVersions: ['v-test'],
      warnings: ['volatility'],
    },
    getCriticalWidgetHealthStatus() {
      return statusOverride;
    },
    buildCriticalWidgetHealthDetail() {
      return 'Generated fallback detail';
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    toString(value, fallback = '') {
      return value === null || value === undefined ? fallback : String(value);
    },
    formatRelativeTime() {
      return '2 minutes ago';
    },
    showToast() {
      calls.display += 1;
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${decisionSource}\n\n${openRobustnessSource}\n\n${openDrillDownSource}\n\nthis.openRobustnessDrill = openRobustnessDrill;`, sandbox, {
    filename: 'app.js',
  });

  return {
    sandbox,
    modal,
    title,
    body,
    calls,
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

function loadRunCopilotStartOpen() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractSection(
    source,
    'function resolveCopilotStartOpenDestination(',
    '\n\nfunction resolveCopilotStartState('
  );
  const overlay = {
    style: { display: '' },
    classList: {
      remove() {},
    },
  };
  const calls = {
    focused: 0,
    toggled: 0,
    switched: [],
    scrolled: 0,
    toasts: [],
  };
  const overviewAnchor = {
    scrollIntoView() {
      calls.scrolled += 1;
    },
  };
  const sandbox = {
    console,
    setTimeout(fn) {
      fn();
      return 0;
    },
    document: {
      getElementById(id) {
        if (id === 'aiCopilotOverlay') return overlay;
        if (id === 'tab-overview') return { id: 'tab-overview' };
        if (id === 'tab-market') return { id: 'tab-market' };
        if (id === 'market-pulse-widget-container') return overviewAnchor;
        return null;
      },
      querySelector(selector) {
        if (selector === '.tab-btn[data-tab="overview"]') {
          return { id: 'tab-btn-overview' };
        }
        if (selector === '.tab-btn[data-tab="market"]') {
          return { id: 'tab-btn-market' };
        }
        return null;
      },
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    normalizeCopilotStartOpenTarget(target, id = '') {
      const normalizedTarget = String(target || '').trim().toLowerCase();
      const normalizedId = String(id || '').trim().toLowerCase();
      if (
        normalizedId === 'brief_of_day'
        || normalizedTarget === '/brief/daily'
        || normalizedTarget === 'brief_of_day'
        || normalizedTarget === 'brief'
        || normalizedTarget === 'live_brief'
        || normalizedTarget === 'daily_brief'
      ) {
        return 'market';
      }
      if (
        normalizedId === 'ask_copilot'
        || normalizedId === 'open_copilot'
        || normalizedId === 'copilot'
        || normalizedTarget === '/copilot'
        || normalizedTarget === '/copilot/'
        || normalizedTarget === '/copilot/ask'
        || normalizedTarget === 'copilot/'
      ) {
        return 'copilot';
      }
      return normalizedTarget.replace(/^\/+/, '');
    },
    focusCopilotInput() {
      calls.focused += 1;
    },
    toggleAICopilot() {
      calls.toggled += 1;
      overlay.style.display = 'block';
    },
    safeSwitchTab(_button, target) {
      calls.switched.push(target);
    },
    showToast(message) {
      calls.toasts.push(message);
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.runCopilotStartOpen = runCopilotStartOpen;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, overlay, calls };
}

function loadBuildCopilotChatResponseHtml() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'buildCopilotChatResponseHtml', '\n\nlet copilotContextRequest = null;');
  const sandbox = {
    console,
    escapeHtml(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    toFiniteNumber(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? number : fallback;
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    formatRelativeTime(value) {
      return value === '2026-03-10T10:00:00Z' ? '2 minutes ago' : 'just now';
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.buildCopilotChatResponseHtml = buildCopilotChatResponseHtml;`, sandbox, {
    filename: 'app.js',
  });
  return sandbox;
}

function loadHydrateCopilotOverlayStart({
  getCopilotStart,
  getCopilotContext,
  builtState,
  sanitizedStart,
} = {}) {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = `let copilotContextRequest = null;\n${extractFunction(
    source,
    'hydrateCopilotOverlayStart',
    '\n\nasync function submitCopilotChat('
  )}`;
  const contextValue = createElementStub();
  const calls = {
    starter: 0,
    context: 0,
    warnings: [],
    labels: [],
    messages: [],
    actions: [],
    hero: [],
    sanitized: [],
  };
  const sandbox = {
    console: {
      ...console,
      warn(...args) {
        calls.warnings.push(args.map((value) => String(value)).join(' '));
      },
    },
    document: {
      getElementById(id) {
        if (id === 'aiContextValue') return contextValue;
        return null;
      },
    },
    window: {
      FinanceAPI: {},
      copilotStart: null,
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
    sanitizeCopilotStart(value) {
      calls.sanitized.push(value);
      return sanitizedStart || {
        brief_of_day: {
          summary: 'Fallback brief',
          freshness: '2026-03-09T07:00:00Z',
        },
        ask: [],
        open: [],
      };
    },
    buildCopilotStartState(value) {
      calls.builtFrom = value;
      return builtState || {
        brief: {
          summary: 'Fallback brief',
          freshness: '2026-03-09T07:00:00Z',
        },
        ask: [],
        open: [],
      };
    },
    updateCopilotContextLabel(state) {
      calls.labels.push(state);
    },
    renderCopilotStartMessage(state) {
      calls.messages.push(state);
    },
    renderCopilotStartActions(state) {
      calls.actions.push(state);
    },
    renderHeroCopilotBrief(state) {
      calls.hero.push(state);
    },
  };

  if (typeof getCopilotStart === 'function') {
    sandbox.window.FinanceAPI.getCopilotStart = async () => {
      calls.starter += 1;
      return getCopilotStart();
    };
  }

  if (typeof getCopilotContext === 'function') {
    sandbox.window.FinanceAPI.getCopilotContext = async () => {
      calls.context += 1;
      return getCopilotContext();
    };
  }

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.hydrateCopilotOverlayStart = hydrateCopilotOverlayStart;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, contextValue, calls };
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
  const overviewTab = { id: 'tab-overview' };
  const overviewTabButton = { id: 'tab-btn-overview' };
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
        if (selector === '.tab-btn[data-tab="overview"]') return overviewTabButton;
        if (selector === '.tab-btn[data-tab="market"]') return marketTabButton;
        return null;
      },
      getElementById(id) {
        if (id === 'aiCopilotOverlay') return overlay;
        if (id === 'aiOverlayInput') return input;
        if (id === 'tab-overview') return overviewTab;
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
    normalizeCopilotStartList(value) {
      return (Array.isArray(value) ? value : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean)
        .slice(0, 3);
    },
    normalizeCopilotSourceLabels(value) {
      return (Array.isArray(value) ? value : value ? [value] : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean);
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

test('buildRobustnessGoNoGoDecision returns GO for healthy state', () => {
  const { sandbox } = loadRobustnessGoNoGoDecision(null);
  const result = sandbox.buildRobustnessGoNoGoDecision();

  assert.equal(result.decision, 'GO');
  assert.equal(result.state, 'ok');
  assert.equal(result.detail, 'Generated fallback detail');
});

test('buildRobustnessGoNoGoDecision handles case-insensitive degraded states', () => {
  const { sandbox } = loadRobustnessGoNoGoDecision({
    state: 'DEGRADED',
    reason: 'partial signals',
  });
  const result = sandbox.buildRobustnessGoNoGoDecision();

  assert.equal(result.decision, 'NO-GO');
  assert.equal(result.state, 'degraded');
});

test('buildRobustnessGoNoGoDecision treats warning as NO-GO', () => {
  const { sandbox } = loadRobustnessGoNoGoDecision({
    state: 'warning',
    reason: 'critical quality warning detected',
  });
  const result = sandbox.buildRobustnessGoNoGoDecision();

  assert.equal(result.decision, 'NO-GO');
  assert.equal(result.state, 'warning');
});

test('buildRobustnessGoNoGoDecision returns NO-GO for unhealthy states', () => {
  const { sandbox } = loadRobustnessGoNoGoDecision({
    state: 'degraded',
    reason: 'partial signals',
  });
  const result = sandbox.buildRobustnessGoNoGoDecision();

  assert.equal(result.decision, 'NO-GO');
  assert.equal(result.state, 'degraded');
  assert.equal(result.detail, 'partial signals');
});

test('buildRobustnessGoNoGoDecision treats unknown state as NO-GO', () => {
  const { sandbox } = loadRobustnessGoNoGoDecision({
    state: 'unknown',
    reason: 'health check inconclusive',
  });
  const result = sandbox.buildRobustnessGoNoGoDecision();

  assert.equal(result.decision, 'NO-GO');
  assert.equal(result.state, 'unknown');
  assert.equal(result.detail, 'health check inconclusive');
});

test('openRobustnessDrill opens readiness modal with GO payload', () => {
  const { sandbox, modal, title, body } = loadRobustnessDrillOpenFlow(null);
  const payload = sandbox.openRobustnessDrill();

  assert.equal(modal.style.display, 'flex');
  assert.equal(title.textContent, 'Robustness Drill: GO / NO-GO');
  assert.equal(payload.content.includes('GO'), true);
  assert.match(body.innerHTML, /All critical signals are in tolerance/);
  assert.match(body.innerHTML, /context-badge positive/);
});

test('openRobustnessDrill opens readiness modal with NO-GO payload when degraded', () => {
  const { sandbox, modal, title, body } = loadRobustnessDrillOpenFlow({
    state: 'degraded',
    reason: 'partial signals',
  });
  const payload = sandbox.openRobustnessDrill();

  assert.equal(modal.style.display, 'flex');
  assert.equal(title.textContent, 'Robustness Drill: GO / NO-GO');
  assert.equal(payload.content.includes('NO-GO'), true);
  assert.match(body.innerHTML, /Critical quality warning detected/);
  assert.match(body.innerHTML, /context-badge warning/);
});

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
  const expectedStoredState = {
    brief_of_day: {
      summary: 'Breadth is narrow but stable.',
      freshness: '2026-03-09T06:55:00Z',
    },
    ask: [
      {
        label: 'Ask about today',
        prompt: 'What matters today?',
      },
    ],
    open: [
      {
        label: 'Open live brief',
        target: 'brief',
      },
    ],
    scope_tickers: ['NVDA', 'MSFT'],
  };

  sandbox.buildCopilotStartState = (value) => {
    sandbox.copilotStartStateInput = value;
    return {
      built_from: value,
    };
  };

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-09T07:00:00Z',
    data: {
      scope_tickers: ['NVDA', 'MSFT'],
      copilot_start: {
        brief_of_day: {
          summary: 'Breadth is narrow but stable.',
          freshness: '2026-03-09T06:55:00Z',
        },
        ask: [
          {
            label: 'Ask about today',
            prompt: 'What matters today?',
          },
        ],
        open: [
          {
            label: 'Open live brief',
            target: 'brief',
          },
        ],
      },
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.window.copilotStart)), expectedStoredState);
  if (sandbox.copilotStartStateInput) {
    const serializedBuildInput = JSON.parse(JSON.stringify(sandbox.copilotStartStateInput));
    const allowedBuildInputs = [
      {
        copilot_start: expectedStoredState,
        scope_tickers: ['NVDA', 'MSFT'],
      },
      {
        data: {
          copilot_start: expectedStoredState,
          scope_tickers: ['NVDA', 'MSFT'],
        },
      },
    ];
    assert.equal(
      allowedBuildInputs.some((candidate) => JSON.stringify(candidate) === JSON.stringify(serializedBuildInput)),
      true
    );
    assert.deepEqual(JSON.parse(JSON.stringify(sandbox.heroBriefState)), {
      built_from: serializedBuildInput,
    });
  } else {
    const serializedHeroState = JSON.parse(JSON.stringify(sandbox.heroBriefState));
    const allowedHeroStates = [
      expectedStoredState,
      {
        data: {
          copilot_start: expectedStoredState,
          scope_tickers: ['NVDA', 'MSFT'],
        },
      },
    ];
    assert.equal(
      allowedHeroStates.some((candidate) => JSON.stringify(candidate) === JSON.stringify(serializedHeroState)),
      true
    );
  }
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.appData.copilotStart.scope_tickers)), ['NVDA', 'MSFT']);
});

test('applyLiveDashboardData stores walk-forward scoreboard payloads for forecast widgets', () => {
  const { sandbox } = loadApplyLiveDashboardData();
  const scoreboard = {
    rows: [
      {
        metric_key: 'walk_forward_direction_hit_rate',
        scope: 'overall',
        value: 0.61,
        target: 0.52,
        status: 'pass',
      },
    ],
    updated_at: '2026-03-10T10:00:00Z',
    threshold_summary: {
      walk_forward_direction_hit_rate: {
        target: 0.52,
        status: 'pass',
      },
    },
  };

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-10T10:01:00Z',
    data: {
      forecasts: [],
      forecastScoreboard: scoreboard,
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.liveForecastScoreboard)), scoreboard);
  assert.equal(sandbox.rendered, true);
});

test('applyLiveDashboardData stores insider behavior payloads for existing widgets', () => {
  const { sandbox } = loadApplyLiveDashboardData();
  const insiderBehavior = {
    engineId: 'insider_behavior_intelligence_v1',
    fallbackUsed: false,
    summaryWarning: 'Insider activity is evidence with uncertainty, never a standalone directive.',
    signals: [
      {
        ticker: 'NVDA',
        confidence: 61,
        uncertaintyLevel: 'medium',
        summary: 'Insider activity suggests accumulation bias.',
        netTrades30d: 4,
        filingSource: 'public_form4',
        sources: ['forecasts_insider_behavior', 'sec_edgar_form4'],
        uncertaintyFactors: ['limited_sample_size'],
      },
    ],
  };

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-11T05:00:00Z',
    data: {
      insiderBehavior,
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.appData.insiderBehavior)), insiderBehavior);
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.insiderBehavior)), insiderBehavior);
  assert.equal(sandbox.rendered, true);
});

test('sanitizeInsiderBehavior preserves already-normalized guardrail and provenance fields', () => {
  const sandbox = loadSanitizeInsiderBehavior();

  const result = JSON.parse(JSON.stringify(sandbox.sanitizeInsiderBehavior({
    engineId: 'insider_behavior_intelligence_v1',
    fallbackUsed: true,
    summaryWarning: 'Insider activity is evidence with uncertainty, never a standalone directive.',
    policy: 'Use insider behavior only as corroborating evidence.',
    signals: [
      {
        ticker: 'nvda',
        confidence: 61,
        uncertaintyLevel: 'medium',
        summary: 'Insider activity suggests accumulation bias.',
        netTrades30d: 4,
        reviewNote: 'Wait for corroboration.',
        filingSource: 'public_form4',
        sources: ['forecasts_insider_behavior', 'sec_edgar_form4'],
        uncertaintyFactors: ['limited_sample_size'],
      },
    ],
  })));

  assert.equal(result.engineId, 'insider_behavior_intelligence_v1');
  assert.equal(result.fallbackUsed, true);
  assert.equal(result.summaryWarning, 'Insider activity is evidence with uncertainty, never a standalone directive.');
  assert.equal(result.policy, 'Use insider behavior only as corroborating evidence.');
  assert.deepEqual(result.signals[0], {
    ticker: 'NVDA',
    stance: 'insufficient_evidence',
    summary: 'Insider activity suggests accumulation bias.',
    confidence: 61,
    uncertaintyLevel: 'medium',
    uncertaintyFactors: ['limited_sample_size'],
    netTrades30d: 4,
    reviewNote: 'Wait for corroboration.',
    sources: ['forecasts_insider_behavior', 'sec_edgar_form4'],
    filingSource: 'public_form4',
  });
});

test('renderMarketDrivers appends insider behavior summary to the existing widget', () => {
  const { sandbox, container } = loadRenderMarketDrivers();

  sandbox.renderMarketDrivers();

  assert.match(container.innerHTML, /Technical Signals/);
  assert.match(container.innerHTML, /Insider behavior/);
  assert.match(container.innerHTML, /NVDA/);
  assert.match(container.innerHTML, /61% confidence/);
  assert.match(container.innerHTML, /30d net trades: 4/);
  assert.match(container.innerHTML, /never a standalone directive/);
  assert.match(container.innerHTML, /Provenance: public_form4/);
  assert.match(container.innerHTML, /Uncertainty factors: limited_sample_size, single_cluster_activity/);
});

test('renderForecastScenarioWidget prefers threshold_summary over scoreboard rows for hit-rate copy', () => {
  const { sandbox, scenarioContext, widgetTimestamp } = loadRenderForecastScenarioWidget();
  sandbox.liveForecastRows = [
    { ticker: 'NVDA', direction: 'up', expectedReturn: 4.5 },
    { ticker: 'MSFT', direction: 'neutral', expectedReturn: 1.2 },
    { ticker: 'AAPL', direction: 'down', expectedReturn: -2.3 },
  ];
  sandbox.liveForecastScoreboard = {
    rows: [
      {
        metric_key: 'walk_forward_mae',
        scope: 'overall',
        value: 0.07,
        status: 'unknown',
      },
    ],
    updated_at: '2026-03-10T10:00:00Z',
    threshold_summary: {
      walk_forward_direction_hit_rate: {
        value: 0.61,
        target: 0.52,
        status: 'pass',
      },
    },
  };

  sandbox.renderForecastScenarioWidget();

  assert.equal(
    scenarioContext.textContent,
    'Top live forecasts: NVDA, MSFT, AAPL • Walk-forward hit rate 61% vs 52% target'
  );
  assert.equal(widgetTimestamp.textContent, 'On target • Walk-forward 2 minutes ago');
});

test('renderForecastScenarioWidget surfaces geopolitical conflict escalation from live payload', () => {
  const {
    sandbox,
    geopoliticalRisk,
    geopoliticalGraph,
    geopoliticalAlertCopy,
    geopoliticalAlertBand,
  } = loadRenderForecastScenarioWidget();
  sandbox.liveForecastRows = [
    { ticker: 'NVDA', direction: 'up', expectedReturn: 4.5 },
    { ticker: 'MSFT', direction: 'neutral', expectedReturn: 1.2 },
    { ticker: 'AAPL', direction: 'down', expectedReturn: -2.3 },
  ];
  sandbox.liveDataMeta = {
    geopoliticalRiskGraph: {
      nodes: [
        { label: 'Ukraine', escalation_score: 87, escalation_band: 'critical', latest_at: '2026-03-10T10:00:00Z' },
        { label: 'Taiwan', escalation_score: 58, escalation_band: 'high', latest_at: '2026-03-10T09:30:00Z' },
      ],
      alerts: [
        { region: 'Ukraine', escalation_band: 'critical', escalation_score: 87, timestamp: '2026-03-10T10:00:00Z' },
      ],
    },
  };

  sandbox.renderForecastScenarioWidget();

  assert.equal(geopoliticalRisk.hidden, false);
  assert.match(geopoliticalGraph.innerHTML, /Ukraine/);
  assert.match(geopoliticalGraph.innerHTML, /width: 87%/);
  assert.equal(geopoliticalAlertBand.textContent, 'Critical');
  assert.equal(geopoliticalAlertBand.className, 'scenario-geopolitical-badge band-critical');
  assert.equal(
    geopoliticalAlertCopy.textContent,
    'Conflict escalation critical in Ukraine (87/100) • refreshed 2 minutes ago'
  );
});

test('renderForecastScenarioWidget surfaces a supply-chain shock propagation chain from existing live datasets', () => {
  const {
    sandbox,
    shockChain,
    shockChainBand,
    shockChainUpstream,
    shockChainTransmission,
    shockChainWatchlist,
    shockChainAssumptionVersion,
    shockChainAssumptionCopy,
    shockChainCopy,
  } = loadRenderForecastScenarioWidget();
  sandbox.liveForecastRows = [
    { ticker: 'NVDA', direction: 'up', expectedReturn: 4.5 },
    { ticker: 'CAT', direction: 'neutral', expectedReturn: 1.2 },
    { ticker: 'XOM', direction: 'down', expectedReturn: -2.3 },
  ];
  sandbox.liveDataMeta = {
    geopoliticalRiskGraph: {
      nodes: [
        { label: 'Taiwan', escalation_score: 73, escalation_band: 'high', latest_at: '2026-03-10T10:00:00Z' },
      ],
      alerts: [
        { region: 'Taiwan', escalation_band: 'high', escalation_score: 73, timestamp: '2026-03-10T10:00:00Z' },
      ],
    },
    globalSignalMesh: {
      coverage: {
        layers: ['macro', 'policy', 'geopolitical'],
      },
    },
  };
  sandbox.window.policyImpact = {
    events: [
      {
        sectors: ['technology', 'industrials', 'energy'],
        status: 'effective',
      },
    ],
  };

  sandbox.renderForecastScenarioWidget();

  assert.equal(shockChain.hidden, false);
  assert.equal(shockChainBand.textContent, 'High');
  assert.equal(shockChainBand.className, 'scenario-geopolitical-badge band-high');
  assert.equal(shockChainUpstream.textContent, 'Taiwan high shock (73/100)');
  assert.equal(shockChainTransmission.textContent, 'technology -> industrials -> energy • mesh macro / policy / geopolitical');
  assert.equal(shockChainWatchlist.textContent, 'NVDA -> CAT -> XOM');
  assert.equal(shockChainAssumptionVersion.textContent, 'taiwan:high:effective:v20260310t100000z');
  assert.equal(
    shockChainAssumptionCopy.textContent,
    'Audit trail: geo Taiwan • sectors technology, industrials, energy • mesh macro/policy/geopolitical • watchlist NVDA, CAT, XOM.'
  );
  assert.equal(
    shockChainCopy.textContent,
    'Taiwan shock is the active upstream driver; transmission is being watched through technology, industrials, energy before it reaches NVDA, CAT, XOM forecasts • policy status effective.'
  );
});

test('renderForecastScenarioWidget surfaces macro hierarchy coverage and contradiction copy', () => {
  const { sandbox, scenarioContext } = loadRenderForecastScenarioWidget();
  sandbox.liveForecastRows = [
    { ticker: 'WORLD', layer: 'LAYER-5', region: 'World', regime: 'risk_off', direction: 'down', expectedReturn: -1.1 },
    { ticker: 'EU', layer: 'LAYER-4', region: 'Europe', regime: 'risk_off', direction: 'down', expectedReturn: -0.8 },
    { ticker: 'US', layer: 'LAYER-3', region: 'United States', regime: 'risk_on', direction: 'up', expectedReturn: 1.4 },
  ];

  sandbox.renderForecastScenarioWidget();

  assert.equal(
    scenarioContext.textContent,
    'Top live forecasts: WORLD, EU, US • Macro hierarchy: 1 world, 1 continent, 1 country • Contradiction: World risk_off vs United States risk_on'
  );
});

test('renderMacroRegimeCardsWidget hydrates world continent country cards from live hierarchy payload', () => {
  const {
    sandbox,
    nodes,
    consistencyIcon,
    consistencyText,
    insightText,
    timestamp,
  } = loadMacroRegimeCardsRenderer();

  sandbox.liveDataMeta.macroRegimeHierarchy = {
    generated_at: '2026-03-11T10:00:00Z',
    levels: [
      {
        scope: 'world',
        entity: 'world',
        regime: 'risk_off',
        confidence: 0.82,
        summary: 'Global liquidity is tightening.',
        drivers: ['Dollar strength', 'Manufacturing slowdown'],
        risks: ['Cross-asset volatility'],
      },
      {
        scope: 'continent',
        entity: 'north_america',
        display_name: 'North America',
        regime: 'slowdown',
        confidence: 0.64,
        summary: 'Growth is cooling across North America.',
        drivers: ['Higher real yields'],
        risks: ['Consumer retrenchment'],
      },
      {
        scope: 'country',
        entity: 'US',
        display_name: 'United States',
        regime: 'recovery',
        confidence: 0.58,
        summary: 'Domestic demand is stabilizing.',
        drivers: ['Labor resilience'],
        risks: ['Policy execution risk'],
      },
    ],
    consistency: {
      has_contradictions: true,
      pairs: [{ summary: 'World risk-off conflicts with United States recovery' }],
    },
    narrative: {
      summary: 'Macro hierarchy is mixed across the stack.',
      regime_bias: 'risk_off',
    },
  };

  sandbox.renderMacroRegimeCardsWidget();

  assert.equal(nodes.get('world:[data-role="macro-label"]').textContent, 'World');
  assert.equal(nodes.get('world:[data-role="macro-confidence"]').textContent, '82%');
  assert.equal(nodes.get('world:[data-role="macro-confidence"]').className, 'macro-confidence high');
  assert.equal(nodes.get('world:[data-role="macro-regime"]').className, 'regime-badge recession');
  assert.equal(nodes.get('continent:[data-role="macro-label"]').textContent, 'North America');
  assert.equal(nodes.get('country:[data-role="macro-summary"]').textContent, 'Domestic demand is stabilizing.');
  assert.equal(nodes.get('country:[data-role="macro-drivers"]').textContent, 'Labor resilience');
  assert.equal(nodes.get('country:[data-role="macro-risks"]').textContent, 'Policy execution risk');
  assert.equal(consistencyIcon.textContent, '!');
  assert.equal(consistencyIcon.className, 'consistency-icon warning');
  assert.equal(consistencyText.textContent, 'Cross-level consistency: World risk-off conflicts with United States recovery');
  assert.match(insightText.textContent, /Macro hierarchy is mixed across the stack\./);
  assert.match(insightText.textContent, /Regime bias: Risk Off\./);
  assert.match(insightText.textContent, /Hierarchical model confidence: 68% average\./);
  assert.equal(timestamp.textContent, 'Updated relative:2026-03-11T10:00:00Z');
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

test('runCopilotStartOpen opens the overlay when the hero starter targets copilot', () => {
  const { sandbox, overlay, calls } = loadRunCopilotStartOpen();

  sandbox.runCopilotStartOpen('/copilot');

  assert.equal(calls.toggled, 1);
  assert.equal(calls.focused, 1);
  assert.equal(overlay.style.display, 'block');
  assert.deepEqual(calls.switched, []);
  assert.deepEqual(calls.toasts, []);
});

test('runCopilotStartOpen opens the overlay for a trailing-slash copilot target', () => {
  const { sandbox, overlay, calls } = loadRunCopilotStartOpen();

  sandbox.runCopilotStartOpen('/copilot/');

  assert.equal(calls.toggled, 1);
  assert.equal(calls.focused, 1);
  assert.equal(overlay.style.display, 'block');
  assert.deepEqual(calls.switched, []);
  assert.deepEqual(calls.toasts, []);
});

test('runCopilotStartOpen routes the landing brief to overview and scrolls the live brief widget', () => {
  const { sandbox, overlay, calls } = loadRunCopilotStartOpen();

  sandbox.runCopilotStartOpen('/brief/daily');

  assert.equal(overlay.style.display, 'none');
  assert.deepEqual(calls.switched, ['market']);
  assert.equal(calls.scrolled, 0);
  assert.deepEqual(calls.toasts, []);
});

test('runCopilotStartOpen reports unsupported landing actions instead of opening copilot', () => {
  const { sandbox, overlay, calls } = loadRunCopilotStartOpen();

  sandbox.runCopilotStartOpen('/not-a-real-target');

  assert.equal(overlay.style.display, '');
  assert.equal(calls.toggled, 0);
  assert.equal(calls.focused, 0);
  assert.deepEqual(calls.switched, []);
  assert.equal(calls.scrolled, 0);
  assert.deepEqual(calls.toasts, ['Open /not-a-real-target is unavailable']);
});

test('hydrateCopilotOverlayStart falls back to getCopilotContext and persists the shared starter payload', async () => {
  const legacyPayload = {
    data: {
      copilot_start: {
        brief_of_day: {
          summary: 'Leadership is narrowing while rates stay calm.',
          freshness: '2026-03-09T07:05:00Z',
        },
        ask: [
          {
            id: 'ask_today',
            label: 'Ask about today',
            prompt: 'What matters most today?',
          },
        ],
        open: [
          {
            id: 'brief_of_day',
            label: 'Open live brief',
            target: 'brief',
          },
        ],
      },
    },
  };
  const builtState = {
    brief: {
      summary: 'Leadership is narrowing while rates stay calm.',
      freshness: '2026-03-09T07:05:00Z',
    },
    ask: [
      {
        id: 'ask_today',
        label: 'Ask about today',
        prompt: 'What matters most today?',
      },
    ],
    open: [
      {
        id: 'brief_of_day',
        label: 'Open live brief',
        target: 'brief',
      },
    ],
  };
  const sanitizedStart = legacyPayload.data.copilot_start;
  const { sandbox, contextValue, calls } = loadHydrateCopilotOverlayStart({
    getCopilotStart: async () => {
      throw new Error('starter unavailable');
    },
    getCopilotContext: async () => legacyPayload,
    builtState,
    sanitizedStart,
  });

  const result = await sandbox.hydrateCopilotOverlayStart();

  assert.equal(contextValue.textContent, 'Loading brief of the day...');
  assert.equal(calls.starter, 1);
  assert.equal(calls.context, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.sanitized[0])), sanitizedStart);
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.window.copilotStart)), sanitizedStart);
  assert.deepEqual(JSON.parse(JSON.stringify(result)), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.labels[0])), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.messages[0])), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.actions[0])), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.hero[0])), builtState);
  assert.match(calls.warnings[0], /falling back to getCopilotContext/);
});

test('hydrateCopilotOverlayStart builds overlay state from sanitized starter payload', async () => {
  const starterPayload = {
    brief_of_day: {
      summary: 'Momentum remains constructive on mega-cap tech.',
      freshness: '2026-03-09T08:10:00Z',
    },
    ask: [
      {
        id: 'ask_today',
        target: '/copilot/ask',
      },
    ],
    open: [
      {
        id: 'open_copilot',
        target: '/copilot',
      },
    ],
    scope_tickers: ['NVDA', 'MSFT'],
  };
  const sanitizedStart = {
    brief_of_day: {
      title: 'Brief of the day',
      summary: 'Momentum remains constructive on mega-cap tech.',
      market_sentiment: 'BULLISH',
      top_signals: ['AI strength', 'Breadth expanding'],
      top_risks: ['Rate uncertainty'],
      macro_signals: ['Inflation stable'],
      sector_rotation: {
        top: ['Mega-cap AI'],
        bottom: ['Energy'],
      },
      generated_at: '2026-03-09T08:05:00Z',
      freshness: '2026-03-09T08:10:00Z',
      source: ['copilot_start_test'],
    },
    ask: [
      {
        id: 'ask_today',
        label: 'Ask about today',
        prompt: 'What should I do with my portfolio today?',
        tickers: ['NVDA', 'MSFT'],
      },
    ],
    open: [
      {
        id: 'open_copilot',
        label: 'Open copilot',
        target: 'copilot',
      },
    ],
    scope_tickers: ['NVDA', 'MSFT'],
  };
  const builtState = {
    brief: {
      title: 'Brief of the day',
      summary: 'Momentum remains constructive on mega-cap tech.',
      marketSentiment: 'BULLISH',
      topSignals: ['AI strength', 'Breadth expanding'],
      topRisks: ['Rate uncertainty'],
      freshness: '2026-03-09T08:10:00Z',
    },
    ask: [
      {
        id: 'ask_today',
        label: 'Ask about today',
        prompt: 'What should I do with my portfolio today?',
        tickers: ['NVDA', 'MSFT'],
      },
    ],
    open: [
      {
        id: 'open_copilot',
        label: 'Open copilot',
        target: 'copilot',
      },
    ],
  };

  const { sandbox, contextValue, calls } = loadHydrateCopilotOverlayStart({
    getCopilotStart: async () => starterPayload,
    sanitizedStart,
    builtState,
  });

  const result = await sandbox.hydrateCopilotOverlayStart();

  assert.equal(contextValue.textContent, 'Loading brief of the day...');
  assert.equal(calls.starter, 1);
  assert.equal(calls.context, 0);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.sanitized[0])), starterPayload);
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.window.copilotStart)), sanitizedStart);
  assert.deepEqual(JSON.parse(JSON.stringify(result)), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.labels[0])), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.messages[0])), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.actions[0])), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.hero[0])), builtState);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.builtFrom.copilot_start)), sanitizedStart);
  assert.deepEqual(JSON.parse(JSON.stringify(calls.builtFrom.scope_tickers || [])), ['NVDA', 'MSFT']);
});

test('renderHeroCopilotBrief swaps the static hero copy for live brief and actions', () => {
  const { sandbox, summaryEl, timestampEl, actionsRoot, promptCalls, openCalls } = loadRenderHeroCopilotBrief();

  sandbox.renderHeroCopilotBrief({
    brief: {
      summary: 'Rates are calm while leadership stays narrow.',
      freshness: '2026-03-09T06:58:00Z',
      sources: [],
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
        target: 'brief',
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

test('sanitizeCopilotStart maps open_copilot open action to copilot without relying on target', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    open: [
      {
        id: 'open_copilot',
        label: 'Open copilot',
      },
    ],
  });

  assert.equal(result.open.length, 1);
  assert.equal(result.open[0].id, 'open_copilot');
  assert.equal(result.open[0].target, 'copilot');
});

test('sanitizeCopilotStart maps trailing-slash copilot open action to copilot', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    open: [
      {
        id: 'open_copilot',
        label: 'Open copilot',
        target: '/copilot/',
      },
    ],
  });

  assert.equal(result.open.length, 1);
  assert.equal(result.open[0].id, 'open_copilot');
  assert.equal(result.open[0].target, 'copilot');
});

test('sanitizeCopilotStart maps trimmed brief open target variants to market', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    open: [
      {
        id: 'daily_brief',
        label: 'Open live brief',
        target: '/brief/daily/?source=hero',
      },
    ],
  });

  assert.equal(result.open.length, 1);
  assert.equal(result.open[0].id, 'daily_brief');
  assert.equal(result.open[0].target, 'market');
});

test('sanitizeCopilotStart prefers direct ask tickers over prefill tickers', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    ask: [
      {
        id: 'ask_today',
        label: 'Ask about today',
        prompt: 'What matters most today?',
        tickers: ['nvda', ' msft ', 'NVDA'],
        prefill: {
          tickers: ['spy'],
        },
      },
    ],
  });

  assert.deepEqual(JSON.parse(JSON.stringify(result.ask[0].tickers)), ['NVDA', 'MSFT']);
});

test('sanitizeCopilotStart uses ask.question then prefill.question when prompt is missing', () => {
  const sandbox = loadSanitizeCopilotStart();
  sandbox.FALLBACK_COPILOT_START.ask = [
    { id: 'portfolio_today', label: 'Portfolio today?', prompt: 'What should I do with my portfolio today?' },
    { id: 'market_theme', label: 'Best theme now?', prompt: 'Which market theme deserves a deep dive right now?' },
    { id: 'nvda_memo', label: 'NVDA 1-week memo', prompt: 'Give me a 1-week investment memo on NVDA.' },
  ];

  const result = sandbox.sanitizeCopilotStart({
    ask: [
      {
        id: 'ask_question',
        label: 'Open AI view',
        question: 'What should I watch in tech?',
      },
      {
        id: 'ask_prefill',
        label: 'Open NVDA memo',
        prefill: {
          question: 'Give me NVDA-specific risks.',
        },
      },
      {
        id: 'ask_prompt',
        label: 'Explicit prompt',
        prefill: {
          question: 'Should ignore this.',
        },
        prompt: 'What is the macro backdrop?',
      },
    ],
  });

  assert.equal(result.ask[0].id, 'ask_question');
  assert.equal(result.ask[0].prompt, 'What should I watch in tech?');
  assert.equal(result.ask[1].prompt, 'Give me NVDA-specific risks.');
  assert.equal(result.ask[2].prompt, 'What is the macro backdrop?');
});

test('sanitizeCopilotStart preserves scoped tickers for downstream hero prompts', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    scope_tickers: ['nvda', ' msft ', 'NVDA'],
    ask: [
      {
        id: 'ask_today',
        label: 'Ask about today',
        prompt: 'What matters most today?',
      },
    ],
  });

  assert.deepEqual(JSON.parse(JSON.stringify(result.scope_tickers)), ['NVDA', 'MSFT']);
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
      sources: [],
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
        id: 'brief_of_day',
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
  assert.equal(elements.heroBriefLead.textContent, 'A 30-second portfolio memo before you dive deeper. Regime: risk on.');
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

  assert.equal(elements.heroSuggestionChips.children.length, 3);
  assert.equal(elements.heroSuggestionChips.children[0].textContent, 'Regime: RISK ON');
  assert.equal(elements.heroSuggestionChips.children[1].textContent, 'Watch next');
  assert.equal(elements.heroSuggestionChips.children[2].textContent, 'Open opportunities');

  elements.heroSuggestionChips.children[1].click();
  elements.heroSuggestionChips.children[2].click();

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

test('renderHeroCopilotBrief accepts normalized backend snake_case brief fields and falls back to opportunities', () => {
  const state = {
    brief: {
      title: 'Daily Brief',
      summary: 'Semiconductors lead while macro remains stable.',
      market_sentiment: 'BULLISH',
      marketRegime: 'BULLISH',
      topSignals: [],
      topOpportunities: ['NVDA breakout', 'Semis leadership'],
      topRisks: ['CPI tomorrow'],
      top_opportunities: ['NVDA breakout', 'Semis leadership'],
      top_risks: ['CPI tomorrow'],
      generated_at: '2026-03-10T10:00:00Z',
      freshness: '2026-03-10T10:00:00Z',
      sources: [],
    },
    ask: [],
    open: [],
  };
  const { sandbox, elements } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(elements.heroBriefTitle.textContent, 'Daily Brief');
  assert.equal(elements.heroBriefLead.textContent, 'A 30-second portfolio memo before you dive deeper. Regime: bullish.');
  assert.equal(elements.heroBriefSummary.textContent, 'Semiconductors lead while macro remains stable.');
  assert.equal(elements.heroBriefSignals.textContent, 'Opportunities: NVDA breakout • Semis leadership');
  assert.equal(elements.heroBriefSignals.style.display, 'block');
  assert.equal(elements.heroBriefRisks.textContent, 'Risks: CPI tomorrow');
  assert.equal(elements.heroBriefRisks.style.display, 'block');
});

test('renderHeroCopilotBrief surfaces saved portfolio context in hero metadata', () => {
  const state = {
    brief: {
      title: 'Daily Brief',
      summary: 'Saved holdings tilt the watchlist toward mega-cap tech.',
      marketSentiment: 'NEUTRAL',
      topSignals: [],
      topRisks: [],
      freshness: '2026-03-09T08:00:00Z',
      sources: ['copilot_start_test'],
    },
    contextInfluence: {
      mode: 'portfolio_aware',
      portfolioApplied: true,
      source: 'saved_portfolio',
      effectiveTickers: ['AAPL', 'MSFT'],
    },
    ask: [],
    open: [],
  };
  const { sandbox, elements } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(
    elements.heroBriefLead.textContent,
    'A 30-second portfolio memo before you dive deeper. Regime: neutral. Saved portfolio context applied.'
  );
  assert.equal(elements.heroSuggestionChips.children.length, 3);
  assert.equal(elements.heroSuggestionChips.children[0].textContent, 'Regime: NEUTRAL');
  assert.equal(elements.heroSuggestionChips.children[1].textContent, 'Context: portfolio aware portfolio • AAPL, MSFT • saved portfolio');
  assert.equal(elements.heroSuggestionChips.children[2].textContent, 'Sources: copilot_start_test');
});

test('renderHeroCopilotBrief treats stale normalized brief status as degraded metadata', () => {
  const state = {
    brief: {
      title: 'Daily Brief',
      summary: 'Macro inputs are delayed but the live shell still has a fallback view.',
      marketSentiment: 'NEUTRAL',
      topSignals: [],
      topRisks: [],
      freshness: '2026-03-09T08:00:00Z',
      sources: ['brief_daily'],
      status: 'stale',
      degradedReason: 'market_data_delayed',
    },
    ask: [],
    open: [],
  };
  const { sandbox, elements } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(
    elements.heroBriefLead.textContent,
    'A 30-second portfolio memo before you dive deeper. Regime: neutral. Fallback context: market data delayed.'
  );
  assert.equal(elements.heroBriefTimestamp.textContent, 'Updated 2 minutes ago • 1 source • degraded');
  assert.equal(elements.heroSuggestionChips.children.length, 3);
  assert.equal(elements.heroSuggestionChips.children[0].textContent, 'Regime: NEUTRAL');
  assert.equal(elements.heroSuggestionChips.children[1].textContent, 'Sources: brief_daily');
  assert.equal(elements.heroSuggestionChips.children[2].textContent, 'Degraded');
});

test('buildCopilotChatResponseHtml renders freshness, source, and degraded badges for normalized memo payloads', () => {
  const sandbox = loadBuildCopilotChatResponseHtml();

  const html = sandbox.buildCopilotChatResponseHtml({
    consensus: 'BUY',
    confidence: 71,
    risk: { level: 'medium', caveat: 'CPI is the main near-term risk.' },
    model: 'Copilot',
    qualityStatus: 'degraded',
    generatedAt: '2026-03-10T10:00:00Z',
    why: ['Semis leadership remains intact.'],
    dataSources: [{ label: 'judge_live' }],
    contextInfluence: {
      mode: 'portfolio_aware',
      portfolioApplied: true,
      effectiveTickers: ['NVDA', 'MSFT'],
      source: 'saved_portfolio',
    },
    memo: {
      summary: 'Leadership remains intact while breadth improves.',
      regime: 'risk_on',
      horizon: '1 week',
      topOpportunities: ['NVDA relative strength'],
      topRisks: ['CPI surprise'],
      degraded: true,
      degradedReason: 'partial_context',
      freshness: '2026-03-10T10:00:00Z',
    },
  });

  assert.match(html, /<span class="source-badge">Freshness: 2 minutes ago<\/span>/);
  assert.match(html, /<span class="source-badge">Sources: judge_live<\/span>/);
  assert.match(html, /<span class="source-badge">Degraded<\/span>/);
  assert.match(html, /Context:<\/strong> portfolio aware • saved portfolio applied • focus NVDA, MSFT • source saved portfolio/);
  assert.match(html, /Degraded:<\/strong> partial context/i);
});

test('app.js exposes runCopilotStartOpen for the static landing brief CTA', () => {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');

  assert.match(source, /window\.runCopilotStartOpen = runCopilotStartOpen;/);
  assert.match(html, /onclick="runCopilotStartOpen\('brief'\)"/);
});

test('index.html exposes the hero brief slots required by the copilot starter', () => {
  const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');

  [
    'class="ai-daily-summary hero-daily-brief"',
    'id="heroBriefTitle"',
    'id="heroBriefLead"',
    'id="heroBriefSummary"',
    'id="heroBriefSignals"',
    'id="heroBriefRisks"',
    'id="heroBriefTimestamp"',
    'id="heroBriefActions"',
    'id="heroSuggestionChips"',
  ].forEach((snippet) => {
    assert.ok(html.includes(snippet), `Expected ${snippet} in index.html`);
  });
});

test('sanitizeForecastRows preserves forecast provenance SLA metadata for UI consumers', () => {
  const { sandbox } = loadForecastSlaHelpers();

  const [row] = sandbox.sanitizeForecastRows([
    {
      ticker: 'NVDA',
      confidence: 0.72,
      expected_return: 0.034,
      updated_at: '2026-03-10T10:00:00Z',
      provenance: {
        source: ['forecast_hybrid_v1'],
        sla: {
          updated_at: '2026-03-10T10:00:00Z',
          target_max_age_seconds: 600,
          within_target: true,
        },
      },
    },
  ]);

  assert.equal(row.updatedAt, '2026-03-10T10:00:00Z');
  assert.equal(row.provenance.sla.target_max_age_seconds, 600);
  assert.equal(row.provenance.sla.within_target, true);
});

test('sanitizeForecastRows preserves macro hierarchy metadata for country continent world slices', () => {
  const { sandbox } = loadForecastSlaHelpers();

  const [row] = sandbox.sanitizeForecastRows([
    {
      ticker: 'WORLD',
      layer: 'LAYER-5',
      region: 'World',
      regime: 'risk_off',
      geography: {
        scope: 'global',
      },
    },
  ]);

  assert.equal(row.layer, 'LAYER-5');
  assert.equal(row.region, 'World');
  assert.equal(row.regime, 'risk_off');
  assert.deepEqual(row.geography, { scope: 'global' });
});

test('updateLiveProvenance surfaces aggregated forecast SLA compliance', () => {
  const { sandbox, lineage } = loadForecastSlaHelpers();
  const rows = sandbox.sanitizeForecastRows([
    {
      ticker: 'NVDA',
      confidence: 0.72,
      expected_return: 0.034,
      updated_at: '2026-03-10T10:00:00Z',
      provenance: {
        sla: {
          updated_at: '2026-03-10T10:00:00Z',
          target_max_age_seconds: 600,
          within_target: true,
        },
      },
    },
    {
      ticker: 'TSLA',
      confidence: 0.41,
      expected_return: -0.012,
      updated_at: '2026-03-10T09:45:00Z',
      provenance: {
        sla: {
          updated_at: '2026-03-10T09:45:00Z',
          target_max_age_seconds: 600,
          within_target: false,
        },
      },
    },
  ]);

  sandbox.updateLiveProvenance({
    generatedAt: '2026-03-10T10:02:00Z',
    sources: ['api-connector'],
    modelVersions: ['hybrid_v1'],
    contractState: 'degraded',
    forecastSla: sandbox.summarizeForecastSla(rows),
  });

  assert.match(lineage.textContent, /freshness: DEGRADED/);
  assert.match(lineage.textContent, /forecast SLA: 1\/2 within 10m/);
});

test('updateLiveProvenance includes global signal mesh source and license coverage', () => {
  const { sandbox, lineage } = loadForecastSlaHelpers();

  sandbox.updateLiveProvenance({
    generatedAt: '2026-03-10T10:02:00Z',
    sources: ['api-connector'],
    modelVersions: ['live'],
    contractState: 'ok',
    globalSignalMesh: {
      stats: {
        source_count: 9,
        nominal_source_count: 7,
        license_class_counts: {
          public_open_data: 5,
          public_market_data_terms: 2,
          publisher_terms_via_rss: 2,
        },
      },
      coverage: {
        layers: ['macro', 'market', 'news', 'policy', 'insider', 'geopolitical'],
      },
    },
  });

  assert.match(lineage.textContent, /mesh: 9 sources \(7 nominal\) across 6 layers/);
  assert.match(lineage.textContent, /licenses: public_open_data:5, public_market_data_terms:2/);
});

test('sanitizeAlertTimeline surfaces policy status and jurisdiction in alert titles', () => {
  const { sandbox } = loadAlertTimelineHelpers();

  const rows = sandbox.sanitizeAlertTimeline([
    {
      ticker: 'UK',
      type: 'news',
      category: 'policy-impact',
      description: 'Energy oversight rules tighten for utilities.',
      severity: 'medium',
      confidence: 0.68,
      timestamp: '2026-03-10T11:00:00Z',
      signals: {
        jurisdiction: 'UK',
        status: 'adopted',
      },
    },
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].title, 'UK Policy • ADOPTED');
  assert.equal(rows[0].summary, 'Energy oversight rules tighten for utilities.');
});

test('renderAlertTimeline includes policy summary copy in the visible card body', () => {
  const { sandbox, timelineContainer } = loadAlertTimelineHelpers();

  sandbox.renderAlertTimeline([
    {
      ticker: 'US',
      type: 'news',
      category: 'policy-impact',
      description: 'Disclosure rules proposed for cloud and semiconductor firms.',
      severity: 'info',
      confidence: 0.41,
      timestamp: '2026-03-10T09:00:00Z',
      signals: {
        jurisdiction: 'US',
        status: 'proposed',
      },
    },
  ]);

  assert.match(timelineContainer.innerHTML, /US Policy • PROPOSED/);
  assert.match(timelineContainer.innerHTML, /Disclosure rules proposed for cloud and semiconductor firms\./);
});
