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
  });
  assert.equal(sandbox.appData.portfolioRiskProfileFreshness, '2026-03-09T06:30:00Z');
  assert.equal(sandbox.liveDataMeta.generatedAt, '2026-03-09T07:00:00Z');
  assert.equal(sandbox.rendered, true);
});

test('applyLiveDashboardData preserves explicit portfolio health payloads', () => {
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

  assert.deepEqual(JSON.parse(JSON.stringify(transformCalls)), []);
  assert.deepEqual(JSON.parse(JSON.stringify(sandbox.appData.portfolioHealth)), explicitPortfolioHealth);
  assert.equal(sandbox.appData.portfolioRiskProfileFreshness, '2026-03-09T06:30:00Z');
  assert.equal(sandbox.rendered, true);
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
