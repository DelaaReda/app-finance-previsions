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
    toFiniteNumber(value, fallback = 0) {
      const normalized = Number(value);
      return Number.isFinite(normalized) ? normalized : fallback;
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

function loadPersonalPolicySettingsHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const sectionSource = extractSection(
    source,
    "const PERSONAL_POLICY_STORAGE_KEY = 'financeCopilot.personalPolicyDraft';",
    '\n\nconst FALLBACK_TRADE_IDEAS = ['
  );
  const sandbox = {
    console,
    document: {
      summaryNode: { textContent: '' },
      getElementById(id) {
        return id === 'policySettingsSummary' ? this.summaryNode : null;
      },
    },
    window: {
      localStorage: {
        storage: new Map(),
        getItem(key) {
          return this.storage.has(key) ? this.storage.get(key) : null;
        },
        setItem(key, value) {
          this.storage.set(key, String(value));
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
    normalizeTicker(value) {
      return typeof value === 'string'
        ? value.trim().toUpperCase().replace(/[^A-Z0-9.-]/g, '')
        : '';
    },
    utcNowIso() {
      return '2026-03-11T10:00:00Z';
    },
    formatRelativeTime(value) {
      return value === '2026-03-11T10:00:00Z' ? 'just now' : 'earlier';
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${sectionSource}
    this.normalizePersonalPolicySettings = normalizePersonalPolicySettings;
    this.loadStoredPersonalPolicySettings = loadStoredPersonalPolicySettings;
    this.storePersonalPolicySettings = storePersonalPolicySettings;
    this.renderPersonalPolicySettingsSummary = renderPersonalPolicySettingsSummary;`,
    sandbox,
    { filename: 'app.js' }
  );

  return sandbox;
}

function loadCopilotFocusHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const buildPromptSource = extractFunction(source, 'buildCopilotFocusPrompt', '\n\nfunction deriveCopilotStartFocusItems');
  const deriveItemsSource = extractFunction(source, 'deriveCopilotStartFocusItems', '\n\nfunction normalizeCopilotStartEventTiming');
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
    normalizeCopilotStarterTickers(value) {
      const seen = new Set();
      return (Array.isArray(value) ? value : [])
        .map((item) => (typeof item === 'string' ? item.trim().toUpperCase() : ''))
        .filter((item) => {
          if (!item || seen.has(item)) return false;
          seen.add(item);
          return true;
        });
    },
    normalizeCopilotStartList(value) {
      return (Array.isArray(value) ? value : [])
        .map((item) => (typeof item === 'string'
          ? item.trim()
          : (item && typeof item === 'object'
            ? String(item.label || item.title || item.name || item.sector || '').trim()
            : '')))
        .filter(Boolean)
        .slice(0, 3);
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${buildPromptSource}\n${deriveItemsSource}\nthis.buildCopilotFocusPrompt = buildCopilotFocusPrompt;\nthis.deriveCopilotStartFocusItems = deriveCopilotStartFocusItems;`,
    sandbox,
    { filename: 'app.js' }
  );

  return sandbox;
}

function loadHeroBriefInlineActionHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const escapeSource = extractFunction(source, 'escapeInlineJsSingleQuotedString', '\n\nfunction buildInlineCopilotTickerArgument');
  const buildSource = extractFunction(source, 'buildInlineCopilotTickerArgument', '\n\n/**\n * Format relative time from ISO timestamp');
  const sandbox = { console, String, Array };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${escapeSource}\n${buildSource}\nthis.escapeInlineJsSingleQuotedString = escapeInlineJsSingleQuotedString;\nthis.buildInlineCopilotTickerArgument = buildInlineCopilotTickerArgument;`,
    sandbox,
    { filename: 'app.js' }
  );

  return sandbox;
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

function loadJudgeDecisionJournalHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const sanitizeSource = extractFunction(source, 'sanitizeJudgeDecisionJournal', '\n\nfunction sanitizeSectorPerformance');
  const renderSource = extractFunction(source, 'renderJudgeDecisionJournal', '\n\nfunction applyLiveDashboardData');
  const container = { innerHTML: '' };
  const sandbox = {
    console,
    document: {
      getElementById(id) {
        return id === 'judgeDecisionJournal' ? container : null;
      },
    },
    extractArray(payload, keys) {
      if (Array.isArray(payload)) return payload;
      if (!payload || typeof payload !== 'object') return [];
      for (const key of keys) {
        if (Array.isArray(payload[key])) return payload[key];
      }
      return [];
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
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${sanitizeSource}\n${renderSource}\nthis.sanitizeJudgeDecisionJournal = sanitizeJudgeDecisionJournal;\nthis.renderJudgeDecisionJournal = renderJudgeDecisionJournal;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, container };
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

function loadRenderMarketCalendar() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'renderMarketCalendar', '\n\n// V13: Render News Feed');
  const noticeNode = { textContent: '' };
  const container = { innerHTML: '' };
  const root = {
    querySelector(selector) {
      if (selector === '.market-calendar-widget .impact-notice') return noticeNode;
      return null;
    },
  };
  const sandbox = {
    console,
    document: root,
    marketCalendar: {
      critical: [],
      notice: '',
      earnings: [],
      economicData: [],
      exDividend: [],
    },
    getFacetteWidgetSlot() {
      return container;
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderMarketCalendar = renderMarketCalendar;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, noticeNode, container, root };
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
  const fusionAttribution = createElementStub();
  const fusionAttributionBand = createElementStub();
  const fusionAttributionSummary = createElementStub();
  const fusionAttributionRows = createElementStub();
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
      if (selector === '[data-role="fusion-attribution"]') return fusionAttribution;
      if (selector === '[data-role="fusion-attribution-band"]') return fusionAttributionBand;
      if (selector === '[data-role="fusion-attribution-summary"]') return fusionAttributionSummary;
      if (selector === '[data-role="fusion-attribution-rows"]') return fusionAttributionRows;
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
    fusionAttribution,
    fusionAttributionBand,
    fusionAttributionSummary,
    fusionAttributionRows,
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

function loadTradeIdeaHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const sanitizeTradeIdeasSource = extractFunction(source, 'sanitizeTradeIdeas', '\n\nfunction normalizePercentValue');
  const normalizePercentValueSource = extractFunction(source, 'normalizePercentValue', '\n\nfunction sanitizeForecastRows');
  const buildTradeIdeasSource = extractFunction(source, 'buildTradeIdeasFromForecasts', '\n\nfunction normalizeKpiHero');
  const inferTradeIdeaSideSource = extractFunction(source, 'inferTradeIdeaSide', '\n\nfunction resolveTradeIdeaDecisionId');
  const resolveTradeIdeaDecisionIdSource = extractFunction(source, 'resolveTradeIdeaDecisionId', '\n\nfunction getTradeIdeaExecutionState');
  const getTradeIdeaExecutionStateSource = extractFunction(source, 'getTradeIdeaExecutionState', '\n\nasync function executeTradeIdea');
  const renderTradeIdeasSource = extractFunction(source, 'renderTradeIdeas', '\n\n// V13: Render Market Calendar');
  const container = { innerHTML: '' };
  const sandbox = {
    console,
    window: {
      liveRecommendations: [],
      tradeIdeas: [],
      copilotDecisionJournal: null,
      FinanceAPI: {},
    },
    FALLBACK_TRADE_IDEAS: [],
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    extractArray(payload, keys) {
      if (!payload || typeof payload !== 'object') return [];
      for (const key of keys) {
        const value = payload[key];
        if (Array.isArray(value)) return value;
      }
      return [];
    },
    toString(value, fallback = '') {
      return value === null || value === undefined ? fallback : String(value);
    },
    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : fallback;
    },
    sanitizeForecastRows(value) {
      return Array.isArray(value) ? value : [];
    },
    getFacetteWidgetSlot() {
      return container;
    },
    showToast() {},
    tradeIdeas: [],
    tradeIdeaExecutionState: Object.create(null),
    copilotDecisionJournal: null,
    document: {},
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${sanitizeTradeIdeasSource}\n${normalizePercentValueSource}\n${buildTradeIdeasSource}\n${inferTradeIdeaSideSource}\n${resolveTradeIdeaDecisionIdSource}\n${getTradeIdeaExecutionStateSource}\n${renderTradeIdeasSource}\nthis.sanitizeTradeIdeas = sanitizeTradeIdeas;\nthis.buildTradeIdeasFromForecasts = buildTradeIdeasFromForecasts;\nthis.renderTradeIdeas = renderTradeIdeas;`,
    sandbox,
    { filename: 'app.js' }
  );

  return { sandbox, container };
}

function loadPaperTradeExecutionFlowHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const inferTradeIdeaSideSource = extractFunction(source, 'inferTradeIdeaSide', '\n\nfunction resolveTradeIdeaDecisionId');
  const resolveTradeIdeaDecisionIdSource = extractFunction(source, 'resolveTradeIdeaDecisionId', '\n\nfunction getTradeIdeaExecutionState');
  const getTradeIdeaExecutionStateSource = extractFunction(source, 'getTradeIdeaExecutionState', '\n\nasync function refreshDecisionJournalAfterPaperTrade');
  const refreshDecisionJournalSource = extractSection(
    source,
    'async function refreshDecisionJournalAfterPaperTrade(',
    '\n\nasync function executeTradeIdea'
  );
  const executeTradeIdeaSource = extractSection(
    source,
    'async function executeTradeIdea(',
    '\n\n// ============ MOBILE NAVIGATION ============'
  );
  const journalRenders = [];
  const toasts = [];
  const sandbox = {
    console,
    window: {
      FinanceAPI: {
        async executePaperTrade() {
          return {
            ok: true,
            data: {
              execution_id: 'exec-aapl-1',
              pnl: { unrealized: 2.15 },
            },
          };
        },
        async getCopilotDecisionJournal() {
          return {
            entries: [
              {
                decision_id: 'dec-aapl-1',
                tickers: ['AAPL'],
                paper_trade_execution: {
                  count: 1,
                  records: [
                    {
                      execution_id: 'exec-aapl-1',
                      ticker: 'AAPL',
                    },
                  ],
                },
              },
            ],
          };
        },
      },
      copilotDecisionJournal: null,
      judgeDecisionJournal: null,
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    extractArray(payload, keys) {
      if (!payload || typeof payload !== 'object') return [];
      for (const key of keys) {
        const value = payload[key];
        if (Array.isArray(value)) return value;
      }
      return [];
    },
    toString(value, fallback = '') {
      return value === null || value === undefined ? fallback : String(value);
    },
    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : fallback;
    },
    sanitizeJudgeDecisionJournal(value) {
      return Array.isArray(value?.entries) ? value.entries : [];
    },
    renderJudgeDecisionJournal(entries) {
      journalRenders.push(entries);
    },
    showToast(message, level) {
      toasts.push({ message, level });
    },
    renderTradeIdeas() {},
    tradeIdeas: [
      {
        symbol: 'AAPL',
        signalType: 'BUY',
        entry: 195,
        decisionId: 'dec-aapl-1',
      },
    ],
    tradeIdeaExecutionState: Object.create(null),
    copilotDecisionJournal: {
      entries: [
        { decision_id: 'dec-aapl-1', tickers: ['AAPL'] },
      ],
    },
    judgeDecisionJournal: [],
    document: {},
  };
  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${inferTradeIdeaSideSource}\n${resolveTradeIdeaDecisionIdSource}\n${getTradeIdeaExecutionStateSource}\n${refreshDecisionJournalSource}\n${executeTradeIdeaSource}\nthis.executeTradeIdea = executeTradeIdea;`,
    sandbox,
    { filename: 'app.js' }
  );

  return { sandbox, journalRenders, toasts };
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
        || normalizedId === 'open_personal_finance_start'
        || normalizedId === 'open_personal_finance_context'
        || normalizedTarget === '/copilot'
        || normalizedTarget === '/copilot/ask'
        || normalizedTarget === '/copilot/start'
        || normalizedTarget === '/copilot/context'
        || normalizedTarget.startsWith('/copilot/')
        || normalizedTarget === 'copilot/ask'
        || normalizedTarget.startsWith('copilot/')
        || normalizedTarget === 'copilot'
        || normalizedTarget === 'copilot/start'
        || normalizedTarget === 'copilot/context'
        || normalizedTarget === 'personal-finance'
        || normalizedTarget === '/personal-finance'
        || normalizedTarget === '/personal-finance/start'
        || normalizedTarget === '/personal-finance/context'
        || normalizedTarget === 'personal-finance/start'
        || normalizedTarget === 'personal-finance/context'
        || normalizedTarget.startsWith('/personal-finance/')
        || normalizedTarget.startsWith('personal-finance/')
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
  const focusHelperSource = extractSection(
    source,
    'function buildCopilotFocusPrompt(',
    '\n\nfunction normalizeCopilotStartEventTiming('
  );
  const functionSource = extractFunction(source, 'renderHeroCopilotBrief', '\n\nfunction renderCopilotStartActions(');
  const elements = {
    heroBriefTitle: createInteractiveElementStub(),
    heroBriefLead: createInteractiveElementStub(),
    heroBriefSummary: createInteractiveElementStub(),
    heroBriefTimestamp: createInteractiveElementStub(),
    heroBriefSignals: createInteractiveElementStub(),
    heroBriefRisks: createInteractiveElementStub(),
    heroBriefExplainability: createInteractiveElementStub(),
    heroBriefTraceability: createInteractiveElementStub(),
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
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
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
    normalizeCopilotStartEventTiming(value) {
      if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
      const summary = typeof value.summary === 'string' ? value.summary.replace(/_/g, ' ').trim() : '';
      const events = (Array.isArray(value.events) ? value.events : [])
        .map((item) => {
          if (!item || typeof item !== 'object' || Array.isArray(item)) return null;
          return {
            eventType: typeof (item.eventType || item.event_type) === 'string'
              ? String(item.eventType || item.event_type).replace(/_/g, ' ').trim()
              : '',
            dominantHorizon: typeof (item.dominantHorizon || item.dominant_horizon) === 'string'
              ? String(item.dominantHorizon || item.dominant_horizon).replace(/_/g, ' ').trim()
              : '',
            interpretation: typeof item.interpretation === 'string' ? item.interpretation.trim() : '',
          };
        })
        .filter((item) => item && (item.eventType || item.dominantHorizon || item.interpretation))
        .slice(0, 2);
      if (!summary && !events.length) return null;
      return {
        summary,
        freshness: typeof value.freshness === 'string' ? value.freshness.trim() : '',
        sourceLabels: sandbox.normalizeCopilotSourceLabels(value.sourceLabels || value.sources || value.source),
        events,
      };
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
  vm.runInContext(`${focusHelperSource}\n${functionSource}\nthis.renderHeroCopilotBrief = renderHeroCopilotBrief;`, sandbox, {
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
    parseCopilotStartTickerTarget() {
      return null;
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
        || normalizedTarget.startsWith('/copilot/')
        || normalizedTarget === 'copilot/'
        || normalizedTarget.startsWith('copilot/')
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

function loadRunCopilotStartOpenTickerHarness() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractSection(
    source,
    'function parseCopilotStartTickerTarget(',
    '\n\nfunction resolveCopilotStartState('
  );
  const overlay = {
    style: { display: '' },
    classList: {
      remove() {},
    },
  };
  const stockInput = { value: '' };
  const calls = {
    openedFacettes: [],
    searches: 0,
    toasts: [],
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
        if (id === 'stockSymbolInput') return stockInput;
        return null;
      },
      querySelector() {
        return null;
      },
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    normalizeCopilotStartOpenTarget(target, id = '') {
      const normalizedTarget = String(target || '').trim().toLowerCase().replace(/[?#].*$/, '').replace(/\/+$/, '');
      const normalizedId = String(id || '').trim().toLowerCase();
      if (
        normalizedId === 'brief_of_day'
        || normalizedTarget === '/brief/daily'
        || normalizedTarget === '/brief'
        || normalizedTarget === 'brief_of_day'
        || normalizedTarget === 'brief'
        || normalizedTarget === 'brief/daily'
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
        || normalizedTarget.startsWith('/copilot/')
        || normalizedTarget === 'copilot/ask'
        || normalizedTarget.startsWith('copilot/')
        || normalizedTarget === 'copilot'
        || normalizedTarget === 'personal-finance'
        || normalizedTarget === '/personal-finance'
        || normalizedTarget.startsWith('/personal-finance/')
        || normalizedTarget.startsWith('personal-finance/')
      ) {
        return 'copilot';
      }
      return normalizedTarget.replace(/^\/+/, '');
    },
    openFacette(target) {
      calls.openedFacettes.push(target);
    },
    searchStock() {
      calls.searches += 1;
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

  return { sandbox, overlay, calls, stockInput };
}

function loadAndRenderHeroBriefHarness(fetchResponse, options = {}) {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractSection(
    source,
    'async function loadAndRenderHeroBrief(',
    '\n\nfunction escapeInlineJsSingleQuotedString('
  );
  const elements = {
    heroBriefSummary: createInteractiveElementStub(),
    heroBriefTitle: createInteractiveElementStub(),
    heroBriefLead: createInteractiveElementStub(),
    heroBriefTimestamp: createInteractiveElementStub(),
  };
  const renderCalls = [];
  const sandbox = {
    console,
    window: {
      API_BASE_URL: 'http://localhost:8050/api',
      FinanceAPI: {},
    },
    document: {
      getElementById(id) {
        return elements[id] || null;
      },
    },
    fetchCalls: [],
    fetch(url) {
      sandbox.fetchCalls.push(url);
      if (fetchResponse instanceof Error) {
        return Promise.reject(fetchResponse);
      }
      return Promise.resolve(fetchResponse);
    },
    buildCopilotStartState(result) {
      const payload = result && typeof result === 'object'
        ? (result.data && typeof result.data === 'object' ? result.data : result)
        : {};
      const briefSource = payload.brief_of_day
        || payload.daily_brief
        || payload.copilot_start?.brief_of_day
        || payload.copilot_start?.value?.brief_of_day
        || {};
      return {
        brief: {
          summary: briefSource.summary || '',
          marketSentiment: briefSource.market_sentiment || briefSource.marketSentiment || 'UNKNOWN',
          topSignals: ['Breadth improving'],
          topRisks: ['CPI tomorrow'],
          freshness: briefSource.freshness || briefSource.generated_at || '',
        },
        ask: [
          {
            label: 'Ask About Today',
            prompt: 'What matters most today?',
            tickers: ['NVDA'],
          },
        ],
        open: [
          {
            label: 'Open Live Brief',
            target: '/brief/daily',
          },
        ],
      };
    },
    renderHeroCopilotBrief(state) {
      renderCalls.push(state);
      sandbox.lastRenderedState = state;
    },
    sanitizeCopilotStart(value) {
      sandbox.sanitizedValue = value;
      return { sanitized: true, value };
    },
    formatRelativeTime() {
      return '2 minutes ago';
    },
    setTimeout(fn) {
      return 0;
    },
  };
  if (typeof options.getCopilotStart === 'function') {
    sandbox.window.FinanceAPI.getCopilotStart = async () => options.getCopilotStart();
  }
  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.loadAndRenderHeroBrief = loadAndRenderHeroBrief;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, elements, renderCalls };
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
    normalizeCopilotSourceLabels(value) {
      const sources = Array.isArray(value) ? value : (value ? [value] : []);
      return sources
        .map((source) => {
          if (source && typeof source === 'object' && !Array.isArray(source)) {
            return String(source.label || source.source || source.ticker || source.type || source.name || '').trim();
          }
          return String(source || '').trim();
        })
        .filter(Boolean);
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

function loadBuildCopilotJudgePayload() {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractFunction(source, 'buildCopilotJudgePayload', '\n\nfunction sanitizeTradeIdeas(');
  const sandbox = {
    console,
    FALLBACK_LLM_JUDGE_DATA: { suggestedActions: [] },
    normalizeVerdict(value, fallback = 'hold') {
      const normalized = String(value || '').trim().toLowerCase();
      return normalized || fallback;
    },
    formatConfidence(value, fallback = 0) {
      const number = Number(value);
      return Number.isFinite(number) ? Math.round(number) : fallback;
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
    normalizeCopilotSourceLabels(value) {
      const sources = Array.isArray(value) ? value : (value ? [value] : []);
      return sources
        .map((source) => {
          if (source && typeof source === 'object' && !Array.isArray(source)) {
            return String(source.label || source.source || source.ticker || source.type || source.name || '').trim();
          }
          return String(source || '').trim();
        })
        .filter(Boolean);
    },
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    normalizeReasoning(value) {
      return Array.isArray(value) ? value : (typeof value === 'string' && value ? [value] : []);
    },
    normalizeCopilotSources(value) {
      return Array.isArray(value) ? value : [];
    },
    normalizeCopilotStarterTickers(value) {
      return Array.isArray(value) ? value : [];
    },
    normalizeCopilotStartList(value) {
      return Array.isArray(value) ? value : [];
    },
    normalizeCopilotSourceLabels(value) {
      return Array.isArray(value) ? value : [];
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.buildCopilotJudgePayload = buildCopilotJudgePayload;`, sandbox, {
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
    normalizeCopilotStartEventTiming(value) {
      if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
      const summary = typeof value.summary === 'string' ? value.summary.replace(/_/g, ' ').trim() : '';
      const events = (Array.isArray(value.events) ? value.events : [])
        .map((item) => {
          if (!item || typeof item !== 'object' || Array.isArray(item)) return null;
          return {
            eventType: typeof (item.eventType || item.event_type) === 'string'
              ? String(item.eventType || item.event_type).replace(/_/g, ' ').trim()
              : '',
            dominantHorizon: typeof (item.dominantHorizon || item.dominant_horizon) === 'string'
              ? String(item.dominantHorizon || item.dominant_horizon).replace(/_/g, ' ').trim()
              : '',
            interpretation: typeof item.interpretation === 'string' ? item.interpretation.trim() : '',
          };
        })
        .filter((item) => item && (item.eventType || item.dominantHorizon || item.interpretation))
        .slice(0, 2);
      if (!summary && !events.length) return null;
      return {
        summary,
        freshness: typeof value.freshness === 'string' ? value.freshness.trim() : '',
        sourceLabels: sandbox.normalizeCopilotSourceLabels(value.sourceLabels || value.sources || value.source),
        events,
      };
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

function loadRenderRebalanceProposalCard({ playbooksPayload, appDataOverride = {} } = {}) {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractSection(
    source,
    'async function renderRebalanceProposalCard(',
    '\n\nfunction renderLiveDashboardWidgets('
  );
  const elements = {
    rebalanceProposalCard: { dataset: {} },
    rebalanceProposalBadge: createElementStub(),
    rebalanceProposalTitle: createElementStub(),
    rebalanceProposalMetrics: createInteractiveElementStub(),
    rebalanceProposalSummary: createElementStub(),
    rebalanceProposalPrimaryAction: createElementStub(),
    rebalanceProposalSecondaryAction: createElementStub(),
  };
  const calls = [];
  const sandbox = {
    console,
    window: {
      FinanceAPI: {
        async getStrategyPlaybooks(params) {
          calls.push(params);
          return playbooksPayload;
        },
      },
    },
    appData: {
      portfolioHealth: {
        portfolioId: 'portfolio-123',
        riskLabel: 'High',
        suggestion: 'Trim concentrated equity exposure.',
        allocationProgress: 70,
        allocationDriftAlerts: {
          active: true,
          alerts: [
            {
              symbol: 'NVDA',
              severity: 'high',
              thresholdPct: 25,
              currentWeightPct: 33,
              reason: 'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.',
            },
          ],
        },
      },
      portfolioRiskProfile: {
        portfolio: {
          id: 'portfolio-123',
        },
      },
      ...appDataOverride,
    },
    document: {
      getElementById(id) {
        return elements[id] || null;
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
      const normalized = Number(value);
      return Number.isFinite(normalized) ? normalized : fallback;
    },
    normalizePercentValue(value, fallback = 0) {
      const normalized = Number(value);
      if (!Number.isFinite(normalized)) return fallback;
      return Math.abs(normalized) <= 1 ? normalized * 100 : normalized;
    },
    normalizeExecutionCostAwareness(value) {
      if (!value || typeof value !== 'object' || Array.isArray(value)) {
        return {};
      }
      const costBreakdown = value.cost_breakdown ?? value.costBreakdown ?? {};
      return {
        totalCostBps: value.total_cost_bps ?? value.totalCostBps ?? costBreakdown.total_cost_bps ?? costBreakdown.totalCostBps,
        feeBps: value.fee_bps ?? value.feeBps ?? costBreakdown.fee_bps ?? costBreakdown.feeBps,
        slippageBps: value.slippage_bps ?? value.slippageBps ?? costBreakdown.slippage_bps ?? costBreakdown.slippageBps,
        estimatedTaxDragBps: value.estimated_tax_drag_bps ?? value.estimatedTaxDragBps ?? value.tax_drag_bps ?? value.taxDragBps ?? costBreakdown.estimated_tax_drag_bps ?? costBreakdown.estimatedTaxDragBps ?? costBreakdown.tax_drag_bps ?? costBreakdown.taxDragBps,
        taxRateAssumption: value.tax_rate_assumption ?? value.taxRateAssumption ?? costBreakdown.tax_rate_assumption ?? costBreakdown.taxRateAssumption,
        taxBucket: value.tax_bucket ?? value.taxBucket ?? costBreakdown.tax_bucket ?? costBreakdown.taxBucket,
        grossExpectedReturnPct: value.gross_expected_return_pct ?? value.grossExpectedReturnPct ?? costBreakdown.gross_expected_return_pct ?? costBreakdown.grossExpectedReturnPct,
        netExpectedReturnPct: value.net_expected_return_pct ?? value.netExpectedReturnPct ?? costBreakdown.net_expected_return_pct ?? costBreakdown.netExpectedReturnPct,
      };
    },
    formatTaxBucketLabel(value) {
      const normalized = typeof value === 'string' ? value.trim() : '';
      if (!normalized) return '';
      return normalized
        .split('_')
        .map((part) => part ? `${part[0].toUpperCase()}${part.slice(1)}` : '')
        .join(' ');
    },
    formatTaxBucketMetric(value) {
      const normalized = typeof value === 'string' ? value.trim() : '';
      const label = normalized
        ? normalized
          .split('_')
          .map((part) => part ? `${part[0].toUpperCase()}${part.slice(1)}` : '')
          .join(' ')
        : '';
      return label ? `Tax bucket ${label}` : '';
    },
    formatBpsValue(value) {
      const normalized = Number(value);
      if (!Number.isFinite(normalized)) return '';
      return `${Number.isInteger(normalized) ? normalized : normalized.toFixed(1).replace(/\.0$/, '')} bps`;
    },
    formatEdgePercentValue(value) {
      const normalized = Number(value);
      if (!Number.isFinite(normalized)) return '';
      return `${normalized.toFixed(1).replace(/\.0$/, '')}%`;
    },
    formatPercentValue(value) {
      const normalized = Number(value);
      if (!Number.isFinite(normalized)) return '0%';
      return `${normalized.toFixed(1).replace(/\.0$/, '')}%`;
    },
    formatSignedValue(value) {
      const normalized = Number(value);
      if (!Number.isFinite(normalized)) return '0';
      if (normalized > 0) return `+${normalized}`;
      return `${normalized}`;
    },
    firstNonEmptyText(value) {
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
      if (Array.isArray(value)) {
        const first = value.find((entry) => typeof entry === 'string' && entry.trim());
        return first ? first.trim() : '';
      }
      return '';
    },
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(`${functionSource}\nthis.renderRebalanceProposalCard = renderRebalanceProposalCard;`, sandbox, {
    filename: 'app.js',
  });

  return { sandbox, elements, calls };
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
    regimeDetection: null,
    allocationDriftAlerts: null,
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
    regimeDetection: null,
    allocationDriftAlerts: null,
  });
  assert.equal(sandbox.appData.portfolioRiskProfileFreshness, '2026-03-09T06:30:00Z');
  assert.equal(sandbox.rendered, true);
});

test('applyLiveDashboardData enriches portfolio health with regime detection and allocation drift alerts from copilot start', () => {
  const { sandbox } = loadApplyLiveDashboardData();

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-11T08:05:00Z',
    data: {
      portfolioHealth: {
        portfolioId: 'portfolio-123',
        suggestion: 'Provided by API',
      },
      copilotStart: {
        regime_detection: {
          label: 'RISK_OFF',
          confidence_pct: 81,
          threshold_reason: 'Volatility regime and breadth deterioration',
        },
        allocation_drift_alerts: {
          active: true,
          alerts: [
            {
              id: 'largest_position_concentration',
              symbol: 'NVDA',
              severity: 'high',
              reason: 'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.',
              threshold_pct: 25,
              current_weight_pct: 33,
            },
          ],
        },
      },
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.appData.portfolioHealth.regimeDetection)), {
    label: 'RISK_OFF',
    confidencePct: 81,
    thresholdReason: 'Volatility regime and breadth deterioration',
  });
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.appData.portfolioHealth.allocationDriftAlerts)), {
    active: true,
    alerts: [
      {
        id: 'largest_position_concentration',
        symbol: 'NVDA',
        severity: 'high',
        reason: 'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.',
        thresholdPct: 25,
        currentWeightPct: 33,
        referenceWeightPct: 0,
      },
    ],
  });
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

test('applyLiveDashboardData stores event impact horizon matrix payloads for the market news widget', () => {
  const { sandbox } = loadApplyLiveDashboardData();

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-11T10:00:00Z',
    data: {
      eventImpactHorizonMatrix: {
        matrix: [
          {
            event_type: 'sanctions',
            article_count: 3,
            recent_count: 2,
            cross_horizon_divergence: 0.18,
            horizons: {
              '1d': { impact_band: 'medium', bias: 'risk_off' },
              '1w': { impact_band: 'medium', bias: 'persistent' },
              '1m': { impact_band: 'high', bias: 'persistent' },
            },
          },
        ],
        templates: {
          cross_horizon_divergence: 'Immediate repricing can diverge from slower confirmation.',
        },
      },
    },
  });

  assert.equal(sandbox.liveDataMeta.eventImpactHorizonMatrix.matrix[0].event_type, 'sanctions');
  assert.equal(sandbox.liveDataMeta.eventImpactHorizonMatrix.matrix[0].horizons['1m'].impact_band, 'high');
  assert.equal(sandbox.rendered, true);
});

test('applyLiveDashboardData stores final global forecast gate payloads for downstream gate summaries', () => {
  const { sandbox } = loadApplyLiveDashboardData();

  sandbox.applyLiveDashboardData({
    generatedAt: '2026-03-11T10:00:00Z',
    data: {
      finalGlobalForecastGate: {
        gate_id: 'final_global_forecast_gate_v1',
        status: 'pass',
        summary: {
          free_data_compliant: true,
          quality_non_regressing: true,
          required_layers_active: ['macro', 'policy', 'insider', 'geopolitical'],
        },
        proofs: {
          FINAL_GLOBAL_FORECAST_GATE_PROOF: {
            quality_sample_size: 42,
          },
        },
      },
    },
  });

  assert.equal(sandbox.liveDataMeta.finalGlobalForecastGate.gate_id, 'final_global_forecast_gate_v1');
  assert.equal(sandbox.liveDataMeta.finalGlobalForecastGate.summary.required_layers_active.length, 4);
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

test('sanitizeJudgeDecisionJournal preserves policy guardrail details for violating recommendations', () => {
  const { sandbox } = loadJudgeDecisionJournalHelpers();
  const rows = JSON.parse(JSON.stringify(sandbox.sanitizeJudgeDecisionJournal({
    verdicts: [
      {
        ticker: 'TSLA',
        verdict: 'hold',
        confidence: 0.78,
        policy_override_reason: 'TSLA is excluded by your personal policy.',
        policy_guardrails: {
          status: 'violated',
          original_action: 'buy',
          effective_action: 'hold',
          violations: [
            { code: 'ticker_excluded', message: 'Ticker is excluded by policy.' },
            { code: 'risk_above_limit', message: 'Risk exceeds your configured ceiling.' },
          ],
        },
      },
    ],
  })));

  assert.equal(rows.length, 1);
  assert.equal(rows[0].note, 'TSLA is excluded by your personal policy.');
  assert.equal(rows[0].policy_guardrails.status, 'violated');
  assert.equal(rows[0].policy_guardrails.originalAction, 'buy');
  assert.equal(rows[0].policy_guardrails.effectiveAction, 'hold');
  assert.deepEqual(rows[0].policy_guardrails.violations.map((item) => item.code), ['ticker_excluded', 'risk_above_limit']);
});

test('sanitizeJudgeDecisionJournal preserves paper trade execution details for the journal widget', () => {
  const { sandbox } = loadJudgeDecisionJournalHelpers();
  const rows = JSON.parse(JSON.stringify(sandbox.sanitizeJudgeDecisionJournal({
    entries: [
      {
        symbol: 'AAPL',
        decision: 'BUY',
        paper_trade_execution: {
          count: 1,
          latest_recorded_at: '2026-03-11T12:00:00Z',
          records: [
            {
              execution_id: 'exec123',
              ticker: 'AAPL',
              side: 'buy',
              quantity: 1,
              assumed_fill_price: 100.25,
              market_price: 102,
              unrealized_pnl: 1.75,
              unrealized_pnl_percent: 0.0175,
              recorded_at: '2026-03-11T12:00:00Z',
            },
          ],
        },
      },
    ],
  })));

  assert.equal(rows.length, 1);
  assert.equal(rows[0].paper_trade_execution.count, 1);
  assert.equal(rows[0].paper_trade_execution.records[0].executionId, 'exec123');
  assert.equal(rows[0].paper_trade_execution.records[0].assumedFillPrice, 100.25);
  assert.equal(rows[0].paper_trade_execution.records[0].unrealizedPnlPercent, 0.0175);
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

test('renderJudgeDecisionJournal surfaces the policy downgrade badge inside the existing journal widget', () => {
  const { sandbox, container } = loadJudgeDecisionJournalHelpers();

  sandbox.renderJudgeDecisionJournal([
    {
      symbol: 'TSLA',
      decision: 'HOLD',
      note: 'TSLA is excluded by your personal policy.',
      confidence: 0.78,
      policy_guardrails: {
        status: 'violated',
        violations: [
          { message: 'Ticker is excluded by policy.' },
          { message: 'Risk exceeds your configured ceiling.' },
        ],
      },
    },
  ]);

  assert.match(container.innerHTML, /Policy downgrade/);
  assert.match(container.innerHTML, /Ticker is excluded by policy\./);
  assert.match(container.innerHTML, /Risk exceeds your configured ceiling\./);
});

test('renderJudgeDecisionJournal surfaces paper trade execution summary inside the existing journal widget', () => {
  const { sandbox, container } = loadJudgeDecisionJournalHelpers();

  sandbox.renderJudgeDecisionJournal([
    {
      symbol: 'AAPL',
      decision: 'BUY',
      paper_trade_execution: {
        count: 1,
        latest_recorded_at: '2026-03-11T12:00:00Z',
        records: [
          {
            execution_id: 'exec123',
            ticker: 'AAPL',
            side: 'buy',
            quantity: 1,
            assumed_fill_price: 100.25,
            unrealized_pnl: 1.75,
            unrealized_pnl_percent: 0.0175,
            recorded_at: '2026-03-11T12:00:00Z',
          },
        ],
      },
    },
  ]);

  assert.match(container.innerHTML, /Paper trade/);
  assert.match(container.innerHTML, /1 execution/);
  assert.match(container.innerHTML, /BUY • 1 share • fill \$100\.25/);
  assert.match(container.innerHTML, /Unrealized P&amp;L: \+\$1\.75 \(\+1\.75%\)/);
});

test('buildTradeIdeasFromForecasts prefers recommendation forecast fusion attribution', () => {
  const { sandbox } = loadTradeIdeaHelpers();
  const ideas = sandbox.buildTradeIdeasFromForecasts([], [
    {
      ticker: 'NVDA',
      decision_id: 'dec-nvda-1',
      action: 'BUY',
      confidence: 0.81,
      score: 0.78,
      current_price: 875,
      target_price: 940,
      cost_awareness: {
        fee_bps: 7,
        slippage_bps: 12,
        estimated_tax_drag_bps: 9,
        total_cost_bps: 28,
        gross_expected_return_pct: 0.123,
        net_expected_return_pct: 0.095,
        tax_bucket: 'short_term',
        tax_rate_assumption: 0.3,
        tax_impact: 'Short-term gains likely',
      },
      forecast_fusion: {
        blended_score: 0.78,
        dominant_layer: 'forecast_confidence',
        attribution: {
          forecast_direction: 'up',
          market_regime: 'BULL_MARKET',
          expected_return: 0.123,
        },
      },
    },
  ]);

  assert.equal(ideas.length, 1);
  assert.equal(ideas[0].symbol, 'NVDA');
  assert.equal(ideas[0].decisionId, 'dec-nvda-1');
  assert.equal(ideas[0].attributionLabel, 'Fusion 78%');
  assert.match(ideas[0].attributionDetail, /Layer: forecast confidence/i);
  assert.match(ideas[0].attributionDetail, /Regime: BULL MARKET/i);
  assert.match(ideas[0].attributionDetail, /Return: \+12\.3%/i);
  assert.equal(ideas[0].feeBps, 7);
  assert.equal(ideas[0].slippageBps, 12);
  assert.equal(ideas[0].estimatedTaxDragBps, 9);
  assert.equal(ideas[0].totalCostBps, 28);
  assert.equal(ideas[0].taxBucket, 'short_term');
  assert.equal(ideas[0].taxRateAssumption, 0.3);
  assert.equal(ideas[0].taxImpact, 'Short-term gains likely');
});

test('buildTradeIdeasFromForecasts normalizes nested judge cost awareness payloads', () => {
  const { sandbox } = loadTradeIdeaHelpers();
  const ideas = sandbox.buildTradeIdeasFromForecasts([], [
    {
      ticker: 'AAPL',
      decision_id: 'dec-aapl-raw',
      action: 'BUY',
      confidence: 0.76,
      score: 0.74,
      current_price: 192,
      target_price: 202,
      cost_awareness: {
        gross_expected_return: 0.05,
        net_expected_return: 0.0389,
        costs_bps: {
          fees: { low: 2, base: 3, high: 4 },
          slippage: { low: 6, base: 8, high: 12 },
          tax_drag: { low: 7.5, base: 10, high: 12.5 },
          total: { low: 15.5, base: 21, high: 28.5 },
        },
        tax_assumptions: {
          holding_period_bucket: 'short_term',
          tax_rate_band: { low: 0.15, base: 0.2, high: 0.25 },
        },
      },
      forecast_fusion: {
        blended_score: 0.74,
        dominant_layer: 'forecast_confidence',
        attribution: {
          forecast_direction: 'up',
          expected_return: 0.05,
        },
      },
    },
  ]);

  assert.equal(ideas.length, 1);
  assert.equal(ideas[0].feeBps, 3);
  assert.equal(ideas[0].slippageBps, 8);
  assert.equal(ideas[0].estimatedTaxDragBps, 10);
  assert.equal(ideas[0].totalCostBps, 21);
  assert.equal(ideas[0].grossExpectedReturnPct, 0.05);
  assert.equal(ideas[0].netExpectedReturnPct, 0.0389);
  assert.equal(ideas[0].taxBucket, 'short_term');
  assert.equal(ideas[0].taxRateAssumption, 0.2);
  assert.equal(ideas[0].taxImpact, 'Tax impact depends on holding period');
});

test('sanitizeTradeIdeas reuses nested cost_breakdown payloads from recommendation responses', () => {
  const { sandbox } = loadTradeIdeaHelpers();

  const ideas = sandbox.sanitizeTradeIdeas([
    {
      ticker: 'IEF',
      action: 'HOLD',
      confidence: 0.74,
      cost_breakdown: {
        fee_bps: 4,
        slippage_bps: 5,
        tax_drag_bps: 9,
        total_cost_bps: 18,
        gross_expected_return_pct: 0.012,
        net_expected_return_pct: 0.0018,
        tax_bucket: 'short_term',
        tax_rate_assumption: 0.3,
        tax_impact: 'Short-term tax drag likely',
      },
    },
  ]);

  assert.equal(ideas.length, 1);
  assert.equal(ideas[0].feeBps, 4);
  assert.equal(ideas[0].slippageBps, 5);
  assert.equal(ideas[0].estimatedTaxDragBps, 9);
  assert.equal(ideas[0].totalCostBps, 18);
  assert.equal(ideas[0].grossExpectedReturnPct, 0.012);
  assert.equal(ideas[0].netExpectedReturnPct, 0.0018);
  assert.equal(ideas[0].taxBucket, 'short_term');
  assert.equal(ideas[0].taxRateAssumption, 0.3);
  assert.equal(ideas[0].taxImpact, 'Short-term tax drag likely');
});

test('renderTradeIdeas renders attribution badge and detail when present', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.tradeIdeas = [
    {
      symbol: 'GLD',
      signalType: 'BUY',
      entry: 210,
      target: 224,
      confidence: 74,
      attributionLabel: 'Fusion 71%',
      attributionDetail: 'Layer: macro alignment • Regime: RISK OFF',
    },
  ];

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, /Fusion 71%/);
  assert.match(container.innerHTML, /Layer: macro alignment/);
  assert.match(container.innerHTML, /Regime: RISK OFF/);
});

test('renderTradeIdeas surfaces fee, slippage, and tax awareness defaults', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.tradeIdeas = [
    {
      symbol: 'GLD',
      signalType: 'BUY',
      entry: 210,
      target: 224,
      confidence: 74,
    },
  ];

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, /Cost check/);
  assert.match(container.innerHTML, /Fees ~0\.05%/);
  assert.match(container.innerHTML, /Slippage ~0\.10%/);
  assert.match(container.innerHTML, /Tax impact depends on holding period/);
});

test('renderTradeIdeas exposes gross versus net edge and warns on thin edge after costs', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.tradeIdeas = [
    {
      symbol: 'GLD',
      signalType: 'BUY',
      entry: 210,
      target: 224,
      confidence: 74,
      feeBps: 5,
      slippageBps: 6,
      estimatedTaxDragBps: 5,
      totalCostBps: 16,
      grossExpectedReturnPct: 0.012,
      netExpectedReturnPct: 0.002,
      taxBucket: 'short_term',
      taxRateAssumption: 0.3,
      taxImpact: 'Short-term tax drag likely',
    },
  ];

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, /Short Term tax 30%/);
  assert.match(container.innerHTML, /Short-term tax drag likely/);
  assert.match(container.innerHTML, /Cost drag 16 bps/);
  assert.match(container.innerHTML, /Tax drag 5 bps/);
  assert.match(container.innerHTML, /Gross edge 1\.2% -> Net edge 0\.2%/);
  assert.match(container.innerHTML, /Low net edge after costs/);
});

test('renderTradeIdeas uses nested cost_breakdown payloads for cost-awareness messaging', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.tradeIdeas = sandbox.sanitizeTradeIdeas([
    {
      symbol: 'GLD',
      signalType: 'BUY',
      entry: 210,
      target: 224,
      confidence: 74,
      cost_breakdown: {
        fee_bps: 4,
        slippage_bps: 5,
        tax_drag_bps: 9,
        total_cost_bps: 18,
        gross_expected_return_pct: 0.012,
        net_expected_return_pct: 0.0018,
        tax_bucket: 'short_term',
        tax_rate_assumption: 0.3,
        tax_impact: 'Short-term tax drag likely',
      },
    },
  ]);

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, /Short Term tax 30%/);
  assert.match(container.innerHTML, /Cost drag 18 bps/);
  assert.match(container.innerHTML, /Tax drag 9 bps/);
  assert.match(container.innerHTML, /Gross edge 1\.2% -> Net edge 0\.2%/);
  assert.match(container.innerHTML, /Low net edge after costs/);
});

test('renderTradeIdeas enables paper trade CTA when a linked decision journal entry exists', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.copilotDecisionJournal = {
    entries: [
      { decision_id: 'dec-aapl-1', tickers: ['AAPL'] },
    ],
  };
  sandbox.window.copilotDecisionJournal = sandbox.copilotDecisionJournal;
  sandbox.tradeIdeas = [
    {
      symbol: 'AAPL',
      signalType: 'BUY',
      entry: 195,
      target: 210,
      confidence: 82,
      attributionLabel: 'Fusion 82%',
      attributionDetail: 'Layer: forecast confidence',
    },
  ];

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, /Paper Trade/);
  assert.doesNotMatch(container.innerHTML, /No Journal/);
  assert.match(container.innerHTML, /executeTradeIdea\('AAPL'\)/);
});

test('renderTradeIdeas locks the paper trade CTA after a recorded execution', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.copilotDecisionJournal = {
    entries: [
      { decision_id: 'dec-aapl-1', tickers: ['AAPL'] },
    ],
  };
  sandbox.window.copilotDecisionJournal = sandbox.copilotDecisionJournal;
  sandbox.tradeIdeas = [
    {
      symbol: 'AAPL',
      signalType: 'BUY',
      entry: 195,
      target: 210,
      confidence: 82,
    },
  ];
  sandbox.tradeIdeaExecutionState['DEC-AAPL-1'] = {
    status: 'recorded',
    executionId: 'exec-aapl-1',
    unrealizedPnl: 2.15,
  };

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, />Recorded</);
  assert.match(container.innerHTML, /<button class="trade-btn" onclick="executeTradeIdea\('AAPL'\)" disabled>/);
  assert.match(container.innerHTML, /Unrealized PnL \+\$2\.15/);
});

test('renderTradeIdeas derives recorded paper-trade state from the decision journal after reload', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.copilotDecisionJournal = {
    entries: [
      {
        decision_id: 'dec-aapl-1',
        tickers: ['AAPL'],
        paper_trade_execution: {
          count: 1,
          records: [
            {
              execution_id: 'exec-aapl-1',
              unrealized_pnl: 2.15,
            },
          ],
        },
      },
    ],
  };
  sandbox.window.copilotDecisionJournal = sandbox.copilotDecisionJournal;
  sandbox.tradeIdeas = [
    {
      symbol: 'AAPL',
      signalType: 'BUY',
      entry: 195,
      target: 210,
      confidence: 82,
    },
  ];

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, />Recorded</);
  assert.match(container.innerHTML, /<button class="trade-btn" onclick="executeTradeIdea\('AAPL'\)" disabled>/);
  assert.match(container.innerHTML, /Paper EXEC-AAPL-1/);
  assert.match(container.innerHTML, /Unrealized PnL \+\$2\.15/);
});

test('renderTradeIdeas disables the paper trade CTA while execution is pending', () => {
  const { sandbox, container } = loadTradeIdeaHelpers();
  sandbox.copilotDecisionJournal = {
    entries: [
      { decision_id: 'dec-aapl-1', tickers: ['AAPL'] },
    ],
  };
  sandbox.window.copilotDecisionJournal = sandbox.copilotDecisionJournal;
  sandbox.tradeIdeas = [
    {
      symbol: 'AAPL',
      signalType: 'BUY',
      entry: 195,
      target: 210,
      confidence: 82,
    },
  ];
  sandbox.tradeIdeaExecutionState['DEC-AAPL-1'] = {
    status: 'pending',
  };

  sandbox.renderTradeIdeas();

  assert.match(container.innerHTML, />Executing\.\.\.</);
  assert.match(container.innerHTML, /<button class="trade-btn" onclick="executeTradeIdea\('AAPL'\)" disabled>/);
});

test('executeTradeIdea refreshes the decision journal after a recorded paper trade', async () => {
  const { sandbox, journalRenders, toasts } = loadPaperTradeExecutionFlowHelpers();

  await sandbox.executeTradeIdea('AAPL');

  assert.equal(journalRenders.length, 1);
  assert.equal(journalRenders[0][0].paper_trade_execution.count, 1);
  assert.equal(sandbox.window.copilotDecisionJournal.entries[0].paper_trade_execution.count, 1);
  assert.equal(sandbox.tradeIdeaExecutionState['DEC-AAPL-1'].executionId, 'exec-aapl-1');
  assert.deepEqual(toasts, [{ message: 'Paper trade recorded for AAPL', level: 'success' }]);
});

test('executeTradeIdea blocks duplicate paper trade submissions for an in-flight execution', async () => {
  const { sandbox, toasts } = loadPaperTradeExecutionFlowHelpers();
  sandbox.tradeIdeaExecutionState['DEC-AAPL-1'] = { status: 'pending' };

  await sandbox.executeTradeIdea('AAPL');

  assert.deepEqual(toasts, [{ message: 'Paper trade already executing for AAPL', level: 'warning' }]);
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

test('renderForecastScenarioWidget surfaces normalized forecast fusion attribution weights', () => {
  const {
    sandbox,
    fusionAttribution,
    fusionAttributionBand,
    fusionAttributionSummary,
    fusionAttributionRows,
  } = loadRenderForecastScenarioWidget();
  sandbox.liveForecastRows = [
    {
      ticker: 'NVDA',
      direction: 'up',
      expectedReturn: 4.5,
      forecastFusion: {
        layers: [
          { layer: 'forecast_confidence', contribution: 0.30 },
          { layer: 'momentum', contribution: 0.20 },
          { layer: 'news', contribution: 0.10 },
        ],
      },
    },
    {
      ticker: 'MSFT',
      direction: 'neutral',
      expectedReturn: 1.2,
      forecastFusion: {
        layers: [
          { layer: 'forecast_confidence', contribution: 0.25 },
          { layer: 'macro_alignment', contribution: 0.15 },
        ],
      },
    },
  ];

  sandbox.renderForecastScenarioWidget();

  assert.equal(fusionAttribution.hidden, false);
  assert.equal(fusionAttributionBand.textContent, 'Live');
  assert.equal(fusionAttributionBand.className, 'scenario-geopolitical-badge band-low');
  assert.equal(fusionAttributionSummary.textContent, 'Dominant layer: forecast confidence (55%)');
  assert.match(fusionAttributionRows.innerHTML, /forecast confidence/);
  assert.match(fusionAttributionRows.innerHTML, /55%/);
  assert.match(fusionAttributionRows.innerHTML, /macro alignment/);
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
    confidence: 0.58,
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
      contradiction_count: 2,
      contradiction_summary: '2 contradictions detected between macro layers',
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
  assert.equal(consistencyText.textContent, 'Cross-level consistency: 2 contradictions detected between macro layers');
  assert.match(insightText.textContent, /Macro hierarchy is mixed across the stack\./);
  assert.match(insightText.textContent, /Regime bias: Risk Off\./);
  assert.match(insightText.textContent, /Hierarchical model confidence: 58% aggregate\./);
  assert.equal(timestamp.textContent, 'Updated relative:2026-03-11T10:00:00Z');
});

test('renderMarketCalendar shows the critical 24h/48h lane and updates notice copy', () => {
  const { sandbox, noticeNode, container, root } = loadRenderMarketCalendar();

  sandbox.marketCalendar = {
    critical: [
      { label: 'NVDA earnings', date: 'Mar 11', impact: 'High', window: '24H' },
      { label: 'CPI release', date: 'Mar 12', impact: 'High', window: '48H' },
    ],
    notice: '2 critical events in the next 48h',
    earnings: [{ stock: 'NVDA', date: 'Mar 11', impact: 'High' }],
    economicData: [{ event: 'CPI release', date: 'Mar 12', impact: 'High' }],
    exDividend: [],
  };

  sandbox.renderMarketCalendar(root);

  assert.equal(noticeNode.textContent, '2 critical events in the next 48h');
  assert.match(container.innerHTML, /Critical Events \(24h\/48h\)/);
  assert.match(container.innerHTML, /NVDA earnings/);
  assert.match(container.innerHTML, /24H · Mar 11/);
  assert.match(container.innerHTML, /CPI release/);
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

test('runCopilotStartOpen opens the overlay for a personal-finance namespace target', () => {
  const { sandbox, overlay, calls } = loadRunCopilotStartOpen();

  sandbox.runCopilotStartOpen('/personal-finance');

  assert.equal(calls.toggled, 1);
  assert.equal(calls.focused, 1);
  assert.equal(overlay.style.display, 'block');
  assert.deepEqual(calls.switched, []);
  assert.deepEqual(calls.toasts, []);
});

test('runCopilotStartOpen opens the overlay for a nested copilot target', () => {
  const { sandbox, overlay, calls } = loadRunCopilotStartOpen();

  sandbox.runCopilotStartOpen('/copilot/overview');

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

test('runCopilotStartOpen opens a ticker deep dive from starter actions', () => {
  const { sandbox, overlay, calls, stockInput } = loadRunCopilotStartOpenTickerHarness();

  sandbox.runCopilotStartOpen('ticker:NVDA');

  assert.equal(overlay.style.display, 'none');
  assert.deepEqual(calls.openedFacettes, ['deep-dive']);
  assert.equal(stockInput.value, 'NVDA');
  assert.equal(calls.searches, 1);
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
    regimeDetection: {
      label: 'RISK_OFF',
      confidencePct: 81,
      thresholdReason: 'Volatility regime and breadth deterioration',
    },
    allocationDriftAlerts: {
      active: true,
      alerts: [
        {
          thresholdPct: 25,
          currentWeightPct: 33,
          reason: 'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.',
        },
      ],
    },
  });

  sandbox.renderPortfolioHealthFullDetails();

  assert.equal(elements.portfolioHealthFullAllocationFill.style.width, '70%');
  assert.equal(elements.portfolioHealthFullAllocationFill.textContent, '70%');
  assert.equal(elements.portfolioHealthFullAllocationLabel.textContent, 'Largest saved weight: MSFT 70%');
  assert.equal(elements.portfolioHealthFullRiskFill.style.width, '85%');
  assert.equal(elements.portfolioHealthFullRiskFill.textContent, 'High');
  assert.equal(elements.portfolioHealthFullProfileBadge.className, 'context-badge warning');
  assert.equal(elements.portfolioHealthFullProfileBadge.textContent, 'Risk Off');
  assert.equal(elements.portfolioHealthFullRiskSummary.textContent, 'Risk concentration: High | Benchmark QQQ | Regime RISK OFF (81%)');
  assert.equal(elements.portfolioHealthFullConfidenceFill.style.width, '61%');
  assert.equal(elements.portfolioHealthFullConfidenceFill.textContent, '61%');
  assert.equal(elements.portfolioHealthFullStateSummary.textContent, '6M horizon | Medium conviction | High risk');
  assert.equal(elements.portfolioHealthSuggestionPrimary.className, 'suggestion-item high');
  assert.equal(elements.portfolioHealthSuggestionPrimaryText.textContent, 'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.');
  assert.equal(elements.portfolioHealthSuggestionSecondary.className, 'suggestion-item medium');
  assert.equal(elements.portfolioHealthSuggestionSecondaryText.textContent, 'Volatility regime and breadth deterioration');
  assert.equal(elements.portfolioHealthSuggestionTertiary.className, 'suggestion-item high');
  assert.equal(elements.portfolioHealthSuggestionTertiaryText.textContent, 'Drift threshold 25% | Current 33%');
});

test('renderRebalanceProposalCard upgrades the existing recommendation card from rebalancing strategy playbooks', async () => {
  const { sandbox, elements, calls } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      data: {
        playbooks: [
          {
            ticker: 'IEF',
            turnover: 10,
            risk_delta: -2,
            confidence: 0.74,
            decision: 'hold',
            horizon: '1m',
            summary: ['Reduce drawdown concentration'],
            cost_awareness: {
              total_cost_bps: 6.9,
              fee_bps: 2,
              slippage_bps: 4,
              estimated_tax_drag_bps: 0.9,
              tax_rate_assumption: 0.3,
              tax_bucket: 'short_term',
              gross_expected_return_pct: 0.018,
              net_expected_return_pct: 0.01731,
            },
          },
        ],
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [
    {
      limit: 1,
      min_confidence: 0,
      profile: 'rebalancing_optimizer_lite',
      portfolio_id: 'portfolio-123',
      sort_by: 'confidence',
      sort_order: 'desc',
    },
  ]);
  assert.equal(elements.rebalanceProposalTitle.textContent, 'Rebalance Toward IEF');
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Turnover delta: 10%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Risk delta: -2/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Cost drag: 6.9 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Fees 2 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Slippage 4 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax 0.9 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax rate 30%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Gross edge 1.8%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Net edge 1.7%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax bucket Short Term/);
  assert.equal(elements.rebalanceProposalSummary.textContent, 'Reduce drawdown concentration | HOLD | 1M | Gross edge 1.8% -> Net edge 1.7%');
  assert.equal(elements.rebalanceProposalBadge.textContent, '74% confidence');
  assert.equal(elements.rebalanceProposalBadge.className, 'conviction-badge status status--warning');
  assert.equal(elements.rebalanceProposalPrimaryAction.textContent, 'Open Plan');
});

test('renderRebalanceProposalCard preserves negative net edge when costs exceed expected return', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      data: {
        playbooks: [
          {
            ticker: 'IEF',
            turnover: 10,
            risk_delta: -2,
            confidence: 0.74,
            decision: 'hold',
            horizon: '1m',
            summary: ['Reduce drawdown concentration'],
            cost_awareness: {
              total_cost_bps: 30,
              fee_bps: 10,
              slippage_bps: 8,
              estimated_tax_drag_bps: 12,
              gross_expected_return_pct: 0.0011,
              net_expected_return_pct: -0.0019,
            },
          },
        ],
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'Reduce drawdown concentration | HOLD | 1M | Gross edge 0.1% -> Net edge -0.2% | Costs overwhelm edge | Tax drag dominates costs',
  );
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Cost drag: 30 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Gross edge 0.1%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Net edge -0.2%/);
});

test('renderRebalanceProposalCard calls out short-term tax drag when it is the main cost headwind', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      data: {
        playbooks: [
          {
            ticker: 'IEF',
            turnover: 10,
            risk_delta: -2,
            confidence: 0.74,
            decision: 'hold',
            horizon: '1m',
            summary: ['Reduce drawdown concentration'],
            cost_awareness: {
              total_cost_bps: 18,
              fee_bps: 4,
              slippage_bps: 5,
              estimated_tax_drag_bps: 9,
              tax_bucket: 'short_term',
              gross_expected_return_pct: 0.012,
              net_expected_return_pct: 0.0018,
            },
          },
        ],
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'Reduce drawdown concentration | HOLD | 1M | Gross edge 1.2% -> Net edge 0.2% | Low net edge after costs | Short Term tax drag dominates costs',
  );
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax 9 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax bucket Short Term/);
});

test('renderRebalanceProposalCard reuses nested cost_breakdown fields when playbooks adopt the decision-response shape', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      data: {
        playbooks: [
          {
            ticker: 'IEF',
            turnover: 10,
            risk_delta: -2,
            confidence: 0.74,
            decision: 'hold',
            horizon: '1m',
            summary: ['Reduce drawdown concentration'],
            cost_awareness: {
              cost_breakdown: {
                total_cost_bps: 18,
                fee_bps: 4,
                slippage_bps: 5,
                tax_drag_bps: 9,
                tax_bucket: 'short_term',
                tax_rate_assumption: 0.3,
                gross_expected_return_pct: 0.012,
                net_expected_return_pct: 0.0018,
              },
            },
          },
        ],
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'Reduce drawdown concentration | HOLD | 1M | Gross edge 1.2% -> Net edge 0.2% | Low net edge after costs | Short Term tax drag dominates costs',
  );
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Cost drag: 18 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Fees 4 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Slippage 5 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax 9 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax rate 30%/);
});

test('renderRebalanceProposalCard normalizes percent-style gross and net edge payloads', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      data: {
        playbooks: [
          {
            ticker: 'IEF',
            turnover: 10,
            risk_delta: -2,
            confidence: 0.74,
            decision: 'hold',
            horizon: '1m',
            summary: ['Reduce drawdown concentration'],
            cost_awareness: {
              total_cost_bps: 6.9,
              fee_bps: 2,
              slippage_bps: 4,
              estimated_tax_drag_bps: 0.9,
              grossExpectedReturnPct: 1.8,
              netExpectedReturnPct: 1.7,
            },
          },
        ],
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'Reduce drawdown concentration | HOLD | 1M | Gross edge 1.8% -> Net edge 1.7%',
  );
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Cost drag: 6.9 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Gross edge 1.8%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Net edge 1.7%/);
});

test('renderRebalanceProposalCard flags thin positive net edge after costs', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      data: {
        playbooks: [
          {
            ticker: 'IEF',
            turnover: 10,
            risk_delta: -2,
            confidence: 0.74,
            decision: 'hold',
            horizon: '1m',
            summary: ['Reduce drawdown concentration'],
            cost_awareness: {
              total_cost_bps: 16,
              fee_bps: 5,
              slippage_bps: 6,
              estimated_tax_drag_bps: 5,
              gross_expected_return_pct: 0.012,
              net_expected_return_pct: 0.002,
            },
          },
        ],
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'Reduce drawdown concentration | HOLD | 1M | Gross edge 1.2% -> Net edge 0.2% | Low net edge after costs',
  );
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Cost drag: 16 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Fees 5 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Slippage 6 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Tax 5 bps/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Gross edge 1.2%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Net edge 0.2%/);
});

test('renderRebalanceProposalCard keeps fallback turnover and risk deltas when optimizer playbooks are unavailable', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: null,
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(elements.rebalanceProposalTitle.textContent, 'Rebalance NVDA Exposure');
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Turnover delta: 8%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Risk delta: -2/);
  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.',
  );
  assert.equal(elements.rebalanceProposalBadge.textContent, 'Policy-aware fallback');
  assert.equal(elements.rebalanceProposalSecondaryAction.textContent, 'Schedule');
});

test('renderRebalanceProposalCard keeps fallback copy for degraded empty rebalancing envelopes', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      status: 'degraded',
      error: 'portfolio context unavailable',
      data: {
        status: 'degraded',
        warnings: ['portfolio_context_unavailable'],
        playbooks: [],
        count: 0,
        filters_applied: {
          profile: 'rebalancing_optimizer_lite',
        },
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(elements.rebalanceProposalTitle.textContent, 'Rebalance NVDA Exposure');
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Turnover delta: 8%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Risk delta: -2/);
  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.',
  );
  assert.equal(elements.rebalanceProposalBadge.textContent, 'Policy-aware fallback');
  assert.equal(elements.rebalanceProposalPrimaryAction.textContent, 'See Plan');
});

test('renderRebalanceProposalCard keeps fallback copy for degraded non-empty rebalancing envelopes', async () => {
  const { sandbox, elements } = loadRenderRebalanceProposalCard({
    playbooksPayload: {
      status: 'degraded',
      error: 'provider timeout',
      data: {
        status: 'degraded',
        warnings: ['partial_data_provider_timeout'],
        playbooks: [
          {
            ticker: 'IEF',
            turnover: 10,
            risk_delta: -2,
            confidence: 0.74,
            decision: 'hold',
            horizon: '1m',
            summary: ['Reduce drawdown concentration'],
            cost_awareness: {
              total_cost_bps: 6.9,
              net_expected_return_pct: 0.01731,
            },
          },
        ],
      },
    },
  });

  await sandbox.renderRebalanceProposalCard();

  assert.equal(elements.rebalanceProposalTitle.textContent, 'Rebalance NVDA Exposure');
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Turnover delta: 8%/);
  assert.match(elements.rebalanceProposalMetrics.innerHTML, /Risk delta: -2/);
  assert.equal(
    elements.rebalanceProposalSummary.textContent,
    'NVDA is 33.00% of saved weights, above the 25.00% playbook concentration proxy.',
  );
  assert.equal(elements.rebalanceProposalBadge.textContent, 'Policy-aware fallback');
  assert.equal(elements.rebalanceProposalPrimaryAction.textContent, 'See Plan');
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

test('sanitizeCopilotStart maps nested copilot open targets to copilot', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    open: [
      {
        id: 'copilot_overview',
        label: 'Open copilot overview',
        target: '/copilot/overview',
      },
    ],
  });

  assert.equal(result.open.length, 1);
  assert.equal(result.open[0].id, 'copilot_overview');
  assert.equal(result.open[0].target, 'copilot');
});

test('sanitizeCopilotStart maps personal-finance starter alias targets to copilot', () => {
  const sandbox = loadSanitizeCopilotStart();

  const result = sandbox.sanitizeCopilotStart({
    open: [
      {
        id: 'open_personal_finance_start',
        label: 'Open personal finance start',
        target: '/personal-finance/start',
      },
    ],
  });

  assert.equal(result.open.length, 1);
  assert.deepEqual(result.open.map((item) => ({ id: item.id, target: item.target })), [
    { id: 'open_personal_finance_start', target: 'copilot' },
  ]);
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
  const suggestionLabels = Array.from(elements.heroSuggestionChips.children).map((node) => node.textContent);
  assert.equal(suggestionLabels[0], 'Regime: RISK ON');
  assert.equal(suggestionLabels.length, 3);
  assert.equal(
    suggestionLabels.filter((label) => label.startsWith('Ask about ')).length,
    2,
  );

  Array.from(elements.heroSuggestionChips.children)
    .filter((node) => typeof node.click === 'function' && node.textContent.startsWith('Ask about '))
    .forEach((node) => node.click());

  const normalizedPromptCalls = JSON.parse(JSON.stringify(promptCalls));
  assert.equal(normalizedPromptCalls[0].prompt, 'What matters most today?');
  assert.deepEqual(normalizedPromptCalls[0].tickers, ['NVDA', 'MSFT']);
  assert.equal(normalizedPromptCalls.length, 3);
  assert.ok(normalizedPromptCalls.some((item) => item.prompt.startsWith('Give me a deep dive on ')));
  assert.deepEqual(JSON.parse(JSON.stringify(openCalls)), ['market']);
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

test('renderHeroCopilotBrief surfaces prioritized risk details and duplicate suppression summary', () => {
  const state = {
    brief: {
      title: 'Daily Brief',
      summary: 'Concentrated event risk remains on the tape.',
      marketSentiment: 'RISK_OFF',
      topRiskItems: [
        {
          ticker: 'NVDA',
          priority: 'high',
          suppression_reason: 'duplicate_fatigue',
          urgent_bypass: true,
        },
      ],
      suppressedRisks: [
        {
          ticker: 'QQQ',
          suppression_reason: 'duplicate_fatigue',
        },
      ],
      alertingMetadata: {
        suppressed_risk_count: 2,
        suppression_window_minutes: 15,
      },
      freshness: '2026-03-10T10:00:00Z',
      sources: [],
    },
    ask: [],
    open: [],
  };
  const { sandbox, elements } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(
    elements.heroBriefRisks.textContent,
    'Risks: HIGH · NVDA · reason duplicate fatigue · urgent bypass | Suppressed duplicates: 2 in 15m window'
  );
  assert.equal(elements.heroBriefRisks.style.display, 'block');
});

test('buildCopilotStartState normalizes brief event timing for copilot starter surfaces', () => {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractSection(
    source,
    'function normalizeCopilotStarterTickers(',
    '\n\nfunction focusCopilotInput('
  );
  const sandbox = {
    console,
    Date,
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    normalizeCopilotSourceLabels(value) {
      return (Array.isArray(value) ? value : value ? [value] : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean);
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${functionSource}\nthis.buildCopilotStartState = buildCopilotStartState;`,
    sandbox,
    { filename: 'app.js' }
  );

  const state = sandbox.buildCopilotStartState({
    data: {
      copilot_start: {
        brief_of_day: {
          summary: 'Stay selective around major catalysts.',
          event_timing: {
            summary: 'Critical events are clustered into the next 48h.',
            freshness: '2026-03-11T10:00:00Z',
            source: ['brief_calendar'],
            events: [
              {
                event_type: 'fed_minutes',
                dominant_horizon: '24h',
                interpretation: 'Rates could reset quickly after the release.',
              },
            ],
          },
        },
      },
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(state.brief.eventTiming)), {
    summary: 'Critical events are clustered into the next 48h.',
    freshness: '2026-03-11T10:00:00Z',
    sourceLabels: ['brief_calendar'],
    events: [
      {
        eventType: 'fed minutes',
        dominantHorizon: '24h',
        interpretation: 'Rates could reset quickly after the release.',
      },
    ],
  });
});

test('buildCopilotStartState derives ticker open actions from focus tickers', () => {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const functionSource = extractSection(
    source,
    'function normalizeCopilotStarterTickers(',
    '\n\nfunction focusCopilotInput('
  );
  const sandbox = {
    console,
    Date,
    isObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value);
    },
    toArray(value, fallback = []) {
      return Array.isArray(value) ? value : fallback;
    },
    toString(value, fallback = '') {
      return typeof value === 'string' ? value : fallback;
    },
    normalizeCopilotSourceLabels(value) {
      return (Array.isArray(value) ? value : value ? [value] : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean);
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${functionSource}\nthis.buildCopilotStartState = buildCopilotStartState;`,
    sandbox,
    { filename: 'app.js' }
  );

  const state = sandbox.buildCopilotStartState({
    data: {
      scope_tickers: ['NVDA'],
      copilot_start: {
        brief_of_day: {
          summary: 'Leadership remains concentrated in NVDA and MSFT.',
          top_signals: ['NVDA', 'MSFT'],
        },
        open: [
          {
            id: 'brief_of_day',
            label: 'Open Live Brief',
            target: '/brief/daily',
          },
        ],
      },
    },
  });

  assert.deepEqual(
    JSON.parse(JSON.stringify(state.open.map((item) => ({ id: item.id, target: item.target })))),
    [
      { id: 'brief_of_day', target: 'market' },
      { id: 'open_nvda', target: 'ticker:NVDA' },
      { id: 'open_msft', target: 'ticker:MSFT' },
    ]
  );
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

test('renderHeroCopilotBrief tolerates missing context effective tickers in explainability metadata', () => {
  const state = {
    brief: {
      title: 'Daily Brief',
      summary: 'Leadership remains intact while event risk rises.',
      marketSentiment: 'RISK_ON',
      freshness: '2026-03-09T08:00:00Z',
      sources: ['brief_daily'],
    },
    contextInfluence: {
      mode: 'portfolio_aware',
      portfolioApplied: true,
      source: 'saved_portfolio',
    },
    ask: [],
    open: [],
  };
  const { sandbox, elements } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(
    elements.heroBriefExplainability.textContent,
    'Explainability graph: Context portfolio aware -> saved portfolio -> Regime RISK ON'
  );
  assert.equal(
    elements.heroBriefTraceability.textContent,
    'Source traceability: brief_daily -> saved portfolio • freshness 2 minutes ago'
  );
});

test('renderHeroCopilotBrief surfaces critical upcoming events from the normalized brief contract', () => {
  const state = {
    brief: {
      title: 'Daily Brief',
      summary: 'Watch event density before adding risk.',
      marketSentiment: 'NEUTRAL',
      topSignals: ['Semis leadership intact'],
      topRisks: ['Headline volatility'],
      freshness: '2026-03-09T08:00:00Z',
      sources: ['brief_daily'],
      event_timing: {
        summary: 'Critical events are clustered into the next 48h.',
        events: [
          {
            event_type: 'fed_minutes',
            dominant_horizon: '24h',
            interpretation: 'Rates could reset quickly after the release.',
          },
        ],
      },
    },
    ask: [],
    open: [],
  };
  const { sandbox, elements } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(
    elements.heroBriefRisks.textContent,
    'Risks: Headline volatility | Upcoming events: Critical events are clustered into the next 48h. • fed minutes • 24h'
  );
  assert.equal(elements.heroBriefRisks.style.display, 'block');
});

test('renderHeroCopilotBrief renders explainability graph and source traceability from hero brief state', () => {
  const state = {
    brief: {
      title: 'Daily Brief',
      summary: 'Stay selective around catalysts.',
      marketSentiment: 'NEUTRAL',
      topSignals: ['Semis leadership intact'],
      topRisks: ['Headline volatility'],
      freshness: '2026-03-09T08:00:00Z',
      sources: ['brief_daily', 'forecasts'],
      event_timing: {
        summary: 'Critical events are clustered into the next 48h.',
        source: ['brief_calendar'],
        events: [],
      },
    },
    contextInfluence: {
      mode: 'portfolio_aware',
      portfolioApplied: true,
      source: 'saved_portfolio',
      effectiveTickers: ['NVDA', 'MSFT'],
    },
    ask: [],
    open: [],
  };
  const { sandbox, elements } = loadRenderHeroCopilotBriefWithHeroIds(state);

  sandbox.renderHeroCopilotBrief(state);

  assert.equal(
    elements.heroBriefExplainability.textContent,
    'Explainability graph: Context portfolio aware -> saved portfolio -> NVDA, MSFT -> Regime NEUTRAL -> Signals Semis leadership intact -> Risks Headline volatility'
  );
  assert.equal(elements.heroBriefExplainability.style.display, 'block');
  assert.equal(
    elements.heroBriefTraceability.textContent,
    'Source traceability: brief_daily -> forecasts -> brief_calendar -> saved portfolio • freshness 2 minutes ago'
  );
  assert.equal(elements.heroBriefTraceability.style.display, 'block');
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

test('buildCopilotChatResponseHtml renders personal policy guardrail badges and details', () => {
  const sandbox = loadBuildCopilotChatResponseHtml();

  const html = sandbox.buildCopilotChatResponseHtml({
    consensus: 'BUY',
    confidence: 71,
    risk: { level: 'high', caveat: 'Volatility is still elevated.' },
    model: 'Copilot',
    qualityStatus: 'ok',
    generatedAt: '2026-03-10T10:00:00Z',
    why: ['Momentum is strong but outside the allowed policy envelope.'],
    dataSources: [{ label: 'judge_live' }],
    policyGuardrails: {
      status: 'violated',
      policyId: 'personal-default',
      originalAction: 'BUY',
      effectiveAction: 'HOLD',
      violationCount: 2,
      violations: [
        { code: 'ticker_excluded', message: 'TSLA is excluded by personal policy.' },
        { code: 'action_blocked', message: 'buy is blocked by personal policy.' },
      ],
    },
    memo: {
      summary: 'Momentum is strong but blocked by personal policy.',
      regime: 'risk_on',
      freshness: '2026-03-10T10:00:00Z',
    },
  });

  assert.match(html, /<span class="source-badge">Policy blocked<\/span>/);
  assert.match(html, /Personal policy:<\/strong> HOLD instead of BUY • personal-default • 2 violations/);
  assert.match(html, /TSLA is excluded by personal policy\./);
  assert.match(html, /buy is blocked by personal policy\./);
});

test('buildCopilotJudgePayload normalizes regime detection and allocation drift alerts from the copilot contract', () => {
  const sandbox = loadBuildCopilotJudgePayload();

  const payload = sandbox.buildCopilotJudgePayload({
    verdict: 'buy',
    confidence: 71,
    answer: 'Stay constructive but trim concentration.',
    regime_detection: {
      label: 'bull_market',
      confidence_pct: 73,
      threshold_reason: 'vix_bas',
      source: ['forecasts', 'macro'],
      generated_at: '2026-03-10T10:00:00Z',
    },
    allocation_drift_alerts: {
      active: true,
      alerts: [
        {
          id: 'largest_position_concentration',
          reason: 'guardrail_proxy_triggered',
          threshold_pct: 20,
          actual_pct: 72,
          basis: 'position_weight_proxy',
        },
      ],
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(payload.regimeDetection)), {
    label: 'BULL_MARKET',
    confidencePct: 73,
    thresholdReason: 'vix bas',
    sources: ['forecasts', 'macro'],
    generatedAt: '2026-03-10T10:00:00Z',
  });
  assert.deepEqual(JSON.parse(JSON.stringify(payload.allocationDriftAlerts)), {
    active: true,
    alerts: [
      {
        id: 'largest_position_concentration',
        title: 'largest position concentration',
        reason: 'guardrail proxy triggered',
        thresholdPct: 20,
        actualPct: 72,
        basis: 'position weight proxy',
      },
    ],
  });
});

test('buildCopilotJudgePayload normalizes personal policy guardrails from the judge contract', () => {
  const sandbox = loadBuildCopilotJudgePayload();

  const payload = sandbox.buildCopilotJudgePayload({
    verdict: 'buy',
    policy_guardrails: {
      status: 'violated',
      policy_id: 'personal-default',
      policy_version: '2026-03-11T09:00:00Z',
      original_action: 'buy',
      effective_action: 'hold',
      violations: [
        {
          code: 'ticker_excluded',
          message: 'TSLA is excluded by personal policy.',
        },
      ],
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(payload.policyGuardrails)), {
    status: 'violated',
    policyId: 'personal-default',
    policyVersion: '2026-03-11T09:00:00Z',
    originalAction: 'BUY',
    effectiveAction: 'HOLD',
    violationCount: 1,
    violations: [
      {
        code: 'ticker_excluded',
        message: 'TSLA is excluded by personal policy.',
      },
    ],
  });
});

test('buildCopilotJudgePayload normalizes event timing details from the copilot contract', () => {
  const sandbox = loadBuildCopilotJudgePayload();

  const payload = sandbox.buildCopilotJudgePayload({
    verdict: 'hold',
    event_timing: {
      summary: 'Timing risk elevated around earnings (1w).',
      freshness: '2026-03-10T10:00:00Z',
      source: ['copilot_event_timing', 'judge_event_matrix'],
      events: [
        {
          event_type: 'earnings',
          dominant_horizon: '1w',
          interpretation: 'High earnings density over the next week.',
        },
      ],
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(payload.eventTiming)), {
    summary: 'Timing risk elevated around earnings (1w).',
    freshness: '2026-03-10T10:00:00Z',
    sourceLabels: ['copilot_event_timing', 'judge_event_matrix'],
    events: [
      {
        eventType: 'earnings',
        dominantHorizon: '1w',
        interpretation: 'High earnings density over the next week.',
      },
    ],
  });
});

test('personal policy settings normalize and persist a local editor draft', () => {
  const sandbox = loadPersonalPolicySettingsHelpers();

  const normalized = sandbox.normalizePersonalPolicySettings({
    excludedTickers: [' tsla ', 'TSLA', ' nvda '],
    blockedActions: ['BUY', 'invalid', 'sell'],
    maxRiskLevel: 'high',
  });

  assert.deepEqual(JSON.parse(JSON.stringify(normalized)), {
    excludedTickers: ['TSLA', 'NVDA'],
    blockedActions: ['buy', 'sell'],
    maxRiskLevel: 'high',
    version: '',
    updatedAt: '',
  });

  const stored = sandbox.storePersonalPolicySettings({
    excludedTickers: ['msft'],
    blockedActions: ['hold'],
    maxRiskLevel: 'medium',
  });

  assert.equal(stored.updatedAt, '2026-03-11T10:00:00Z');
  assert.equal(stored.version, '2026-03-11T10:00:00Z');

  const loaded = sandbox.loadStoredPersonalPolicySettings();
  assert.deepEqual(JSON.parse(JSON.stringify(loaded)), {
    excludedTickers: ['MSFT'],
    blockedActions: ['hold'],
    maxRiskLevel: 'medium',
    version: '2026-03-11T10:00:00Z',
    updatedAt: '2026-03-11T10:00:00Z',
  });
});

test('personal policy settings summary renders the saved draft state', () => {
  const sandbox = loadPersonalPolicySettingsHelpers();

  sandbox.renderPersonalPolicySettingsSummary({
    excludedTickers: ['TSLA', 'QQQ'],
    blockedActions: ['buy'],
    maxRiskLevel: 'medium',
    version: 'policy-2026-03-11T10:00:00Z',
    updatedAt: '2026-03-11T10:00:00Z',
  });

  assert.equal(
    sandbox.document.summaryNode.textContent,
    'Excluded: TSLA, QQQ • Blocked: BUY • Max risk: MEDIUM • Version policy-2026-03-11T10:00:00Z • Updated just now'
  );
});

test('buildCopilotJudgePayload normalizes explainability graph traceability details from the judge contract', () => {
  const sandbox = loadBuildCopilotJudgePayload();

  const payload = sandbox.buildCopilotJudgePayload({
    verdict: 'buy',
    explainability: {
      schema_version: 'judge_explainability_graph_v1',
      generated_at: '2026-03-10T10:00:00Z',
      source_traceability: [
        {
          verdict_id: 'verdict:judge_demo_nvda',
          ticker: 'NVDA',
          primary_source_count: 1,
          supporting_sources: [
            {
              source_id: 'news:reuters',
              label: 'NVIDIA demand accelerates',
              kind: 'news_item',
              weight: 0.91,
              freshness: { age_hours: 4.0 },
            },
          ],
        },
      ],
      stats: {
        verdict_count: 1,
        source_count: 1,
        edge_count: 1,
        avg_source_weight: 0.91,
      },
    },
  });

  assert.deepEqual(JSON.parse(JSON.stringify(payload.explainability)), {
    schemaVersion: 'judge_explainability_graph_v1',
    generatedAt: '2026-03-10T10:00:00Z',
    stats: {
      verdictCount: 1,
      sourceCount: 1,
      edgeCount: 1,
      avgSourceWeight: 0.91,
    },
    sourceTraceability: [
      {
        ticker: 'NVDA',
        verdictId: 'verdict:judge_demo_nvda',
        primarySourceCount: 1,
        supportingSources: [
          {
            sourceId: 'news:reuters',
            label: 'NVIDIA demand accelerates',
            kind: 'news item',
            weight: 0.91,
            freshnessAgeHours: 4,
          },
        ],
      },
    ],
  });
});

test('buildCopilotChatResponseHtml renders regime detection and allocation drift alert details', () => {
  const sandbox = loadBuildCopilotChatResponseHtml();

  const html = sandbox.buildCopilotChatResponseHtml({
    consensus: 'BUY',
    confidence: 71,
    risk: { level: 'medium', caveat: 'CPI is the main near-term risk.' },
    model: 'Copilot',
    qualityStatus: 'ok',
    generatedAt: '2026-03-10T10:00:00Z',
    why: ['Semis leadership remains intact.'],
    dataSources: [{ label: 'judge_live' }],
    regimeDetection: {
      label: 'BULL MARKET',
      confidencePct: 73,
      thresholdReason: 'vix bas',
      sources: ['forecasts', 'macro'],
    },
    allocationDriftAlerts: {
      active: true,
      alerts: [
        {
          title: 'largest position concentration',
          reason: 'guardrail proxy triggered',
          thresholdPct: 20,
          actualPct: 72,
          basis: 'position weight proxy',
        },
      ],
    },
    memo: {
      summary: 'Leadership remains intact while breadth improves.',
      regime: 'risk_on',
      freshness: '2026-03-10T10:00:00Z',
    },
  });

  assert.match(html, /Regime engine:<\/strong> BULL MARKET • 73% confidence • vix bas • sources forecasts, macro/);
  assert.match(html, /Allocation drift alerts:/);
  assert.match(html, /largest position concentration/);
  assert.match(html, /actual 72% vs threshold 20%/);
  assert.match(html, /basis position weight proxy/);
});

test('buildCopilotChatResponseHtml renders explainability graph and source traceability from normalized copilot contract', () => {
  const sandbox = loadBuildCopilotChatResponseHtml();

  const html = sandbox.buildCopilotChatResponseHtml({
    consensus: 'BUY',
    confidence: 71,
    risk: { level: 'medium', caveat: 'Macro volatility still matters.' },
    model: 'Copilot',
    qualityStatus: 'ok',
    generatedAt: '2026-03-10T10:00:00Z',
    why: ['Breadth keeps improving while semis leadership holds.'],
    dataSources: ['judge_live', 'forecasts'],
    contextInfluence: {
      mode: 'portfolio_aware',
      portfolioApplied: true,
      source: 'saved_portfolio',
      effectiveTickers: ['NVDA', 'MSFT'],
    },
    regimeDetection: {
      label: 'BULL MARKET',
      confidencePct: 73,
      thresholdReason: 'vix bas',
      sources: ['forecasts', 'macro'],
    },
    eventTiming: {
      summary: 'Timing risk elevated around earnings (1w).',
      freshness: '2026-03-10T10:00:00Z',
      sourceLabels: ['copilot_event_timing', 'macro'],
      events: [],
    },
    memo: {
      summary: 'Leadership remains intact while breadth improves.',
      regime: 'risk_on',
      freshness: '2026-03-10T10:00:00Z',
    },
  });

  assert.match(html, /Explainability graph:<\/strong> Context portfolio aware -> saved portfolio -> NVDA, MSFT -> Regime BULL MARKET -> 73% confidence -> Event timing -> Timing risk elevated around earnings \(1w\)\. -> Reasoning -> Breadth keeps improving while semis leadership holds\. -> Verdict -> BUY/);
  assert.match(html, /Source traceability:<\/strong> judge_live -> forecasts -> macro -> copilot_event_timing/);
});

test('buildCopilotChatResponseHtml renders event timing notes when the copilot contract includes them', () => {
  const sandbox = loadBuildCopilotChatResponseHtml();

  const html = sandbox.buildCopilotChatResponseHtml({
    consensus: 'HOLD',
    confidence: 64,
    risk: { level: 'medium', caveat: 'Event density is rising.' },
    model: 'Copilot',
    qualityStatus: 'ok',
    generatedAt: '2026-03-10T10:00:00Z',
    why: ['Stay selective while event risk resets positioning.'],
    dataSources: [{ label: 'judge_live' }],
    eventTiming: {
      summary: 'Timing risk elevated around earnings (1w).',
      freshness: '2026-03-10T10:00:00Z',
      sourceLabels: ['copilot_event_timing', 'judge_event_matrix'],
      events: [
        {
          eventType: 'earnings',
          dominantHorizon: '1w',
          interpretation: 'High earnings density over the next week.',
        },
      ],
    },
    memo: {
      summary: 'Wait for post-event confirmation before pressing risk.',
      regime: 'neutral',
      freshness: '2026-03-10T10:00:00Z',
    },
  });

  assert.match(html, /Event timing:<\/strong> Timing risk elevated around earnings \(1w\)\./);
  assert.match(html, /<strong>earnings • 1w<\/strong>: High earnings density over the next week\./);
  assert.match(html, /Sources copilot_event_timing, judge_event_matrix • Updated 2 minutes ago/);
});

test('buildCopilotChatResponseHtml renders explainability graph stats and source traceability from the judge contract', () => {
  const sandbox = loadBuildCopilotChatResponseHtml();

  const html = sandbox.buildCopilotChatResponseHtml({
    consensus: 'BUY',
    confidence: 71,
    risk: { level: 'medium', caveat: 'CPI is the main near-term risk.' },
    model: 'Copilot',
    qualityStatus: 'ok',
    generatedAt: '2026-03-10T10:00:00Z',
    why: ['Semis leadership remains intact.'],
    dataSources: [{ label: 'judge_live' }],
    explainability: {
      schemaVersion: 'judge_explainability_graph_v1',
      stats: {
        verdictCount: 1,
        sourceCount: 1,
        edgeCount: 1,
        avgSourceWeight: 0.91,
      },
      sourceTraceability: [
        {
          ticker: 'NVDA',
          primarySourceCount: 1,
          supportingSources: [
            {
              label: 'NVIDIA demand accelerates',
              kind: 'news item',
              weight: 0.91,
              freshnessAgeHours: 4,
            },
          ],
        },
      ],
    },
    memo: {
      summary: 'Leadership remains intact while breadth improves.',
      regime: 'risk_on',
      freshness: '2026-03-10T10:00:00Z',
    },
  });

  assert.match(html, /Explainability graph:<\/strong> 1 verdict • 1 source • 1 link • avg weight 0\.91 • judge_explainability_graph_v1/);
  assert.match(html, /<strong>NVDA<\/strong> • 1 primary source • NVIDIA demand accelerates \(news item, weight 0\.91, 4h old\)/);
  assert.doesNotMatch(html, /Source traceability:<\/strong>/);
});

test('buildCopilotChatResponseHtml renders explainability graph and source traceability from normalized memo inputs', () => {
  const sandbox = loadBuildCopilotChatResponseHtml();

  const html = sandbox.buildCopilotChatResponseHtml({
    consensus: 'BUY',
    confidence: 71,
    risk: { level: 'medium', caveat: 'CPI is the main near-term risk.' },
    model: 'Copilot',
    qualityStatus: 'ok',
    generatedAt: '2026-03-10T10:00:00Z',
    why: ['Semis leadership remains intact.'],
    dataSources: [{ label: 'judge_live' }, { label: 'news_stream' }],
    contextInfluence: {
      mode: 'portfolio_aware',
      portfolioApplied: true,
      effectiveTickers: ['NVDA', 'MSFT'],
      source: 'saved_portfolio',
    },
    regimeDetection: {
      label: 'BULL MARKET',
      confidencePct: 73,
      thresholdReason: 'vix bas',
      sources: ['forecasts', 'macro'],
    },
    eventTiming: {
      summary: 'Timing risk elevated around earnings (1w).',
      freshness: '2026-03-10T10:00:00Z',
      sourceLabels: ['copilot_event_timing', 'judge_event_matrix'],
      events: [
        {
          eventType: 'earnings',
          dominantHorizon: '1w',
          interpretation: 'High earnings density over the next week.',
        },
      ],
    },
    memo: {
      summary: 'Leadership remains intact while breadth improves.',
      regime: 'risk_on',
      freshness: '2026-03-10T10:00:00Z',
    },
  });

  assert.match(html, /Explainability graph:<\/strong> Context portfolio aware -> saved portfolio -> NVDA, MSFT -> Regime BULL MARKET -> 73% confidence -> Event timing -> Timing risk elevated around earnings \(1w\)\. -> Reasoning -> Semis leadership remains intact\. -> Verdict -> BUY/);
  assert.match(html, /Source traceability:<\/strong> judge_live -> news_stream -> forecasts -> macro -> copilot_event_timing/);
  assert.doesNotMatch(html, /\[object Object\]/);
});

test('app.js exposes runCopilotStartOpen for the static landing brief CTA', () => {
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');

  assert.match(source, /window\.runCopilotStartPrompt = runCopilotStartPrompt;/);
  assert.match(source, /window\.runCopilotStartOpen = runCopilotStartOpen;/);
  assert.match(html, /onclick="runCopilotStartOpen\('brief'\)"/);
});

test('hero-what-need component reuses shared copilot starter helpers for ask/open actions', () => {
  const html = fs.readFileSync(path.join(__dirname, '../components/sections/hero-what-need.html'), 'utf8');

  assert.match(html, /onclick="runCopilotStartPrompt\('Give me today\\\\'s portfolio brief as a short memo with verdict, main drivers, risks, confidence, freshness, and sources\.'\)"/);
  assert.match(html, /onclick="runCopilotStartOpen\('brief'\)"/);
  assert.match(html, /onclick="runCopilotStartPrompt\('Explain what matters in today\\\\'s portfolio brief and what I should watch next\.'\)"/);
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
    'id="heroBriefExplainability"',
    'id="heroBriefTraceability"',
    'id="heroBriefTimestamp"',
    'id="heroBriefActions"',
    'id="heroSuggestionChips"',
  ].forEach((snippet) => {
    assert.ok(html.includes(snippet), `Expected ${snippet} in index.html`);
  });
});

test('loadAndRenderHeroBrief reuses the shared starter renderer and stores the sanitized starter payload', async () => {
  const responsePayload = {
    ok: true,
    data: {
      brief_of_day: {
        summary: 'Breadth improves while event risk stays elevated.',
        market_sentiment: 'NEUTRAL',
        freshness: '2026-03-10T10:00:00Z',
      },
      ask: [{ label: 'Ask About Today', prompt: 'What matters most today?' }],
      open: [{ label: 'Open Live Brief', target: '/brief/daily' }],
    },
  };
  const { sandbox, elements, renderCalls } = loadAndRenderHeroBriefHarness({
    ok: true,
    json: async () => responsePayload,
  });

  await sandbox.loadAndRenderHeroBrief();

  assert.deepEqual(sandbox.fetchCalls, ['http://localhost:8050/api/copilot/start']);
  assert.deepEqual(sandbox.sanitizedValue, responsePayload.data);
  assert.deepEqual(sandbox.window.copilotStart, { sanitized: true, value: responsePayload.data });
  assert.equal(elements.heroBriefSummary.style.opacity, '1');
  assert.equal(renderCalls.length, 1);
});

test('loadAndRenderHeroBrief keeps the failure fallback when the starter request fails', async () => {
  const { sandbox, elements, renderCalls } = loadAndRenderHeroBriefHarness(new Error('network down'));

  await sandbox.loadAndRenderHeroBrief();

  assert.equal(renderCalls.length, 0);
  assert.equal(elements.heroBriefSummary.textContent, 'Unable to load brief. Please check your connection and try again.');
  assert.equal(elements.heroBriefSummary.style.color, '#ef4444');
  assert.equal(elements.heroBriefTimestamp.textContent, 'Update failed');
  assert.equal(elements.heroBriefTitle.textContent, '⚠️ Brief unavailable');
});

test('loadAndRenderHeroBrief prefers FinanceAPI.getCopilotStart so namespaced copilot routes reuse the shared connector', async () => {
  const responsePayload = {
    brief_of_day: {
      summary: 'Personal finance starter should come from the shared connector.',
      market_sentiment: 'BULLISH',
      freshness: '2026-03-10T10:00:00Z',
    },
    ask: [{ label: 'Ask About Today', prompt: 'What changed for my portfolio today?', tickers: ['NVDA'] }],
    open: [{ label: 'Open Copilot', target: '/personal-finance' }],
  };
  const { sandbox, renderCalls } = loadAndRenderHeroBriefHarness(null, {
    getCopilotStart: async () => responsePayload,
  });

  await sandbox.loadAndRenderHeroBrief();

  assert.deepEqual(sandbox.fetchCalls, []);
  assert.deepEqual(sandbox.sanitizedValue, responsePayload);
  assert.deepEqual(sandbox.window.copilotStart, { sanitized: true, value: responsePayload });
  assert.equal(renderCalls.length, 1);
});

test('loadAndRenderHeroBrief renders the normalized starter brief when the backend only returns copilot_start', async () => {
  const responsePayload = {
    copilot_start: {
      brief_of_day: {
        summary: 'Starter-only brief is still visible in the hero.',
        market_sentiment: 'BULLISH',
        freshness: '2026-03-10T10:00:00Z',
      },
      ask: [{ label: 'Ask About Today', prompt: 'What changed for my portfolio today?' }],
      open: [{ label: 'Open Copilot', target: '/personal-finance' }],
    },
  };
  const { sandbox, elements, renderCalls } = loadAndRenderHeroBriefHarness(null, {
    getCopilotStart: async () => responsePayload,
  });

  await sandbox.loadAndRenderHeroBrief();

  assert.equal(elements.heroBriefSummary.textContent, 'Starter-only brief is still visible in the hero.');
  assert.equal(elements.heroBriefTitle.textContent, '🟢 Brief of the day');
  assert.equal(elements.heroBriefLead.textContent, 'Market shows bullish bias. A 30-second portfolio memo before you dive deeper.');
  assert.equal(elements.heroBriefTimestamp.textContent, 'Updated 2 minutes ago');
  assert.equal(renderCalls.length, 1);
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

test('updateLiveProvenance includes final global gate status and quality evidence', () => {
  const { sandbox, lineage } = loadForecastSlaHelpers();

  sandbox.updateLiveProvenance({
    generatedAt: '2026-03-10T10:02:00Z',
    sources: ['api-connector'],
    modelVersions: ['live'],
    contractState: 'ok',
    finalGlobalForecastGate: {
      status: 'pass',
      summary: {
        free_data_compliant: true,
        quality_non_regressing: true,
        required_layers_active: ['macro', 'policy', 'insider', 'geopolitical'],
      },
      proofs: {
        FINAL_GLOBAL_FORECAST_GATE_PROOF: {
          quality_sample_size: 42,
        },
      },
    },
  });

  assert.match(lineage.textContent, /final gate: PASS \| 4 layers \| free-data ok, quality ok \| sample 42/);
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

test('sanitizeAlertTimeline prefers backend priority bands for queue ordering', () => {
  const { sandbox } = loadAlertTimelineHelpers();

  const rows = sandbox.sanitizeAlertTimeline([
    {
      ticker: 'AAPL',
      type: 'risk',
      category: 'market_data',
      description: 'Lower-priority volatility watch.',
      severity: 'critical',
      priority_band: 'medium',
      confidence: 0.82,
      timestamp: '2026-03-10T10:00:00Z',
    },
    {
      ticker: 'NVDA',
      type: 'positive-breakout',
      category: 'forecast',
      description: 'Backend queue marked this as urgent despite modest severity.',
      severity: 'low',
      priority_band: 'urgent',
      confidence: 0.31,
      timestamp: '2026-03-10T09:00:00Z',
    },
  ]);

  assert.equal(rows.length, 2);
  assert.equal(rows[0].ticker, 'NVDA');
  assert.equal(rows[0].priorityBand, 'urgent');
  assert.equal(rows[0].priorityBandLabel, 'Urgent');
  assert.equal(rows[1].priorityBand, 'medium');
});

test('renderAlertTimeline includes policy summary copy in the visible card body', () => {
  const { sandbox, timelineContainer } = loadAlertTimelineHelpers();

  sandbox.renderAlertTimeline([
    {
      ticker: 'US',
      type: 'news',
      category: 'policy-impact',
      description: 'Disclosure rules proposed for cloud and semiconductor firms. • transmission: technology -> NVDA, MSFT',
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
  assert.match(timelineContainer.innerHTML, /transmission: technology -> NVDA, MSFT/);
});

test('renderAlertTimeline surfaces top queue summary and urgency tier badges', () => {
  const { sandbox, timelineContainer } = loadAlertTimelineHelpers();
  sandbox.alertTimelineMeta = {
    suppressedCount: 3,
    suppressionWindowMinutes: 15,
    topPriorityBand: 'urgent',
  };

  sandbox.renderAlertTimeline([
    {
      ticker: 'MSFT',
      type: 'risk',
      category: 'market_data',
      source: 'alerts_engine',
      description: 'Cloud margin drift now requires a portfolio review.',
      severity: 'medium',
      priority_band: 'urgent',
      priority_rank: 1,
      suppression: {
        repeat_count: 4,
      },
      confidence: 0.88,
      timestamp: '2026-03-10T09:00:00Z',
    },
    {
      ticker: 'QQQ',
      type: 'news',
      category: 'policy-impact',
      source: 'policy_feed',
      description: 'Semiconductor export wording remains under review.',
      severity: 'info',
      priority_band: 'high',
      confidence: 0.42,
      timestamp: '2026-03-10T08:00:00Z',
    },
  ]);

  assert.match(timelineContainer.innerHTML, /Top queue: MSFT Risk • Urgent queue/);
  assert.match(timelineContainer.innerHTML, /Urgent 1/);
  assert.match(timelineContainer.innerHTML, /Action 1/);
  assert.match(timelineContainer.innerHTML, /Held 3/);
  assert.match(timelineContainer.innerHTML, /15m window/);
  assert.match(timelineContainer.innerHTML, /Urgent queue • repeat 4x • alerts engine • 88% confidence • 2 minutes ago/);
});

test('deriveCopilotStartFocusItems surfaces brief-driven ticker and theme starter chips', () => {
  const sandbox = loadCopilotFocusHelpers();

  const items = sandbox.deriveCopilotStartFocusItems({
    scope_tickers: ['nvda'],
    brief: {
      topOpportunities: ['AI Infrastructure'],
      topRisks: ['Rates'],
    },
    ask: [{ label: 'Ask About Today' }],
    open: [{ label: 'Open Live Brief' }],
  });

  assert.equal(items.length, 2);
  assert.equal(items[0].label, 'Ask about NVDA');
  assert.equal(items[0].prompt, "Give me a deep dive on NVDA and explain today's setup, verdict, risks, confidence, freshness, and sources.");
  assert.deepEqual(Array.from(items[0].tickers), ['NVDA']);
  assert.equal(items[1].label, 'Ask about AI Infrastructure');
  assert.deepEqual(Array.from(items[1].tickers), []);
});

test('deriveCopilotStartFocusItems skips duplicates already exposed by ask/open actions', () => {
  const sandbox = loadCopilotFocusHelpers();

  const items = sandbox.deriveCopilotStartFocusItems({
    scope_tickers: ['msft'],
    brief: {
      topSignals: ['MSFT', 'Cloud'],
    },
    ask: [{ label: 'Ask About Today' }],
    open: [{ label: 'Open MSFT' }],
  });

  assert.equal(items.length, 1);
  assert.equal(items[0].label, 'Ask about Cloud');
  assert.deepEqual(Array.from(items[0].tickers), []);
});

test('deriveCopilotStartFocusItems skips duplicates already exposed by ask labels', () => {
  const sandbox = loadCopilotFocusHelpers();

  const items = sandbox.deriveCopilotStartFocusItems({
    scope_tickers: ['nvda'],
    brief: {
      topSignals: ['NVDA', 'AI Infrastructure'],
    },
    ask: [{ label: 'Ask about NVDA' }],
    open: [{ label: 'Open Live Brief' }],
  });

  assert.equal(items.length, 1);
  assert.equal(items[0].label, 'Ask about AI Infrastructure');
  assert.deepEqual(Array.from(items[0].tickers), []);
});

test('buildInlineCopilotTickerArgument keeps inline copilot chip onclick payloads attribute-safe', () => {
  const sandbox = loadHeroBriefInlineActionHelpers();

  assert.equal(
    sandbox.buildInlineCopilotTickerArgument(['AAPL', `BRK.B`, `O'Reilly`]),
    ", ['AAPL', 'BRK.B', 'O\\'Reilly']"
  );
  assert.equal(sandbox.buildInlineCopilotTickerArgument([]), '');
});
