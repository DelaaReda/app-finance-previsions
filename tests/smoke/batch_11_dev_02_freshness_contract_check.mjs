import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const repoRoot = process.cwd();
const connectorPath = path.join(repoRoot, 'apps/web/src/domains/forecasts/contracts/apiConnector.js');
const appPath = path.join(repoRoot, 'apps/web/src/domains/forecasts/pages/app.js');

const connectorSource = fs.readFileSync(connectorPath, 'utf8');
const appSource = fs.readFileSync(appPath, 'utf8');

function extractBalancedBlock(source, startIndex) {
  let depth = 0;
  let started = false;

  for (let index = startIndex; index < source.length; index += 1) {
    const char = source[index];
    if (char === '{') {
      depth += 1;
      started = true;
    } else if (char === '}') {
      depth -= 1;
      if (started && depth === 0) {
        return source.slice(startIndex, index + 1);
      }
    }
  }

  throw new Error(`Unterminated block starting at ${startIndex}`);
}

function extractFunctionSource(source, name) {
  const marker = `function ${name}(`;
  const start = source.indexOf(marker);
  assert.notEqual(start, -1, `missing function ${name}`);
  const paramsStart = source.indexOf('(', start);
  let paramsDepth = 0;
  let paramsEnd = -1;

  for (let index = paramsStart; index < source.length; index += 1) {
    const char = source[index];
    if (char === '(') {
      paramsDepth += 1;
    } else if (char === ')') {
      paramsDepth -= 1;
      if (paramsDepth === 0) {
        paramsEnd = index;
        break;
      }
    }
  }

  assert.notEqual(paramsEnd, -1, `missing params for ${name}`);
  const bodyStart = source.indexOf('{', paramsEnd);
  assert.notEqual(bodyStart, -1, `missing body for ${name}`);
  return source.slice(start, bodyStart) + extractBalancedBlock(source, bodyStart);
}

function createNode(tagName) {
  return {
    tagName: String(tagName || '').toUpperCase(),
    style: {},
    dataset: {},
    children: [],
    appendChild(child) {
      this.children.push(child);
      return child;
    }
  };
}

function createConnectorContext() {
  const fixtureNow = '2026-03-07T03:00:00.000Z';
  const appendedNodes = [];
  const events = [];
  const intervals = [];

  const document = {
    readyState: 'loading',
    body: {
      appendChild(node) {
        appendedNodes.push(node);
        return node;
      }
    },
    head: createNode('head'),
    documentElement: createNode('html'),
    currentScript: {
      src: 'http://localhost:3000/src/domains/forecasts/pages/index.html'
    },
    addEventListener() {},
    createElement(tagName) {
      return createNode(tagName);
    },
    querySelectorAll() {
      return [];
    }
  };

  const window = {
    document,
    location: { href: 'http://localhost:3000/src/domains/forecasts/pages/index.html' },
    addEventListener() {},
    dispatchEvent(event) {
      events.push(event);
      return true;
    }
  };

  const responses = new Map([
    ['/news/feed?limit=20', { data: { articles: [{ title: 'Markets hold gains', sentiment: 'positive', score: 70, source: 'Reuters', tickers: ['AAPL'], summary: 'AAPL leads', url: 'https://example.com/news/1', published_at: '2026-03-07T02:50:00.000Z' }] } }],
    ['/alerts', { data: { alerts: [{ id: 'alert-1', ticker: 'AAPL', type: 'volatility', severity: 'warning', confidence: 0.74, description: 'Volatility alert', timestamp: '2026-03-07T02:40:00.000Z' }] } }],
    ['/forecasts?limit=20', { data: { rows: [{ ticker: 'AAPL', direction: 'up', confidence: 0.78, horizon: '1d', current_price: 170, target_price: 176, expected_return: 3.5, reasoning: 'Momentum', action: 'buy', risk_level: 'medium', generated_at: '2026-03-07T02:45:00.000Z' }] } }],
    ['/stocks/prices?tickers=NVDA,META,AAPL,MSFT,GOOGL', { data: { prices: {
      AAPL: { points: [[1, 168], [2, 170], [3, 172]] },
      NVDA: { points: [[1, 900], [2, 905], [3, 915]] },
      META: { points: [[1, 480], [2, 482], [3, 486]] },
      MSFT: { points: [[1, 410], [2, 412], [3, 415]] },
      GOOGL: { points: [[1, 150], [2, 151], [3, 153]] }
    } } }],
    ['/dashboard/performance', { top_stocks: [{ symbol: 'AAPL', price: 172, change_pct: 1.2, forecast_pct: 3.5, confidence_pct: 78 }], opportunities: [{ conviction: 'High', expected_return_pct: 4.2, confidence_pct: 81 }] }],
    ['/brief/daily', { data: { headline: 'Briefing', summary: 'Risk remains contained.', sentiment: 'positive', sector_rotation: { top: ['Tech'], bottom: ['Utilities'] }, macro_signals: [{ topic: 'Payrolls', confidence: 0.6 }], generated_at: fixtureNow } }],
    ['/dashboard/allocation', { data: { sectors: [{ sector: 'Technology', change_pct: 1.8, weight_pct: 31.2 }] } }],
    ['/dashboard/market-drivers', { ok: true, freshness: '2026-03-07T02:45:00.000Z', data: { drivers: [{ factor: 'Tech momentum', contribution: 62 }] } }],
    ['/dashboard/kpis', { ok: true, freshness: '2026-03-07T02:55:00.000Z', data: { source: ['dashboard-kpis'], generated_at: '2026-03-07T02:55:00.000Z', portfolio_value: 125000, portfolio_change_pct: 1.4 } }],
    ['/dashboard/portfolio-summary', { ok: true, freshness: '2026-03-07T02:54:00.000Z', data: { source: ['portfolio-summary'], generated_at: '2026-03-07T02:54:00.000Z', total_value: 125000, total_change_pct: 1.4 } }],
    ['/health', { status: 'ok', last_updates: { news: '2026-03-07T02:55:00.000Z', forecasts: '2026-03-07T02:45:00.000Z' } }],
    ['/ingestion/health', { ok: true, data: {
      status: 'degraded',
      generated_at: fixtureNow,
      all_fresh: false,
      degraded_count: 1,
      source: ['api_health', 'ingestion'],
      sources: [
        {
          source: 'news',
          status: 'fresh',
          freshness: {
            timestamp: '2026-03-07T02:55:00.000Z',
            ttl_seconds: 1800,
            age_seconds: 300,
            is_fresh: true
          },
          errors: []
        },
        {
          source: 'macro_series',
          status: 'missing',
          freshness: {
            timestamp: '2026-03-07T02:30:00.000Z',
            ttl_seconds: 604800,
            age_seconds: 1800,
            is_fresh: false
          },
          errors: ['payload_missing']
        }
      ]
    } }]
  ]);

  const fetch = async (url, options = {}) => {
    const requestUrl = String(url).replace('http://localhost:8050/api', '');
    if (requestUrl === '/llm/judge/run') {
      return {
        ok: true,
        async json() {
          return {
            data: {
              stdout: { forecast: 'Breadth remains constructive.' },
              derived: { stats: { avg_confidence: 0.72 }, top_buys: [{ symbol: 'AAPL' }], top_risks: [] },
              model_used: 'EconomicAnalyst'
            }
          };
        }
      };
    }

    const payload = responses.get(requestUrl);
    if (!payload) {
      throw new Error(`Unhandled fetch: ${requestUrl}`);
    }

    return {
      ok: true,
      async json() {
        return payload;
      }
    };
  };

  const DateShim = class extends Date {
    constructor(value) {
      super(value ?? fixtureNow);
    }
    static now() {
      return Date.parse(fixtureNow);
    }
  };

  const context = vm.createContext({
    console,
    fetch,
    window,
    document,
    CustomEvent: class CustomEvent {
      constructor(type, init = {}) {
        this.type = type;
        this.detail = init.detail;
      }
    },
    setInterval(fn, delay) {
      intervals.push({ fn, delay });
      return intervals.length;
    },
    clearInterval() {},
    Date: DateShim,
    Math,
    Promise,
    Array,
    Object,
    Number,
    String,
    Boolean
  });

  context.window.window = context.window;
  context.window.globalThis = context.window;
  context.window.fetch = fetch;
  context.window.CustomEvent = context.CustomEvent;
  context.window.Date = DateShim;
  context.window.console = console;

  return { context, events, appendedNodes, intervals };
}

function createAppContext() {
  const lineage = { textContent: '' };
  const fixtureNow = '2026-03-07T03:00:00.000Z';
  const DateShim = class extends Date {
    constructor(value) {
      super(value ?? fixtureNow);
    }
    static now() {
      return Date.parse(fixtureNow);
    }
  };

  const context = vm.createContext({
    console,
    Array,
    Object,
    Number,
    String,
    Boolean,
    Math,
    Date: DateShim
  });

  const bootstrap = `
    var criticalWidgetHealthOverride = null;
    var liveDataMeta = {};
    var LIVE_FALLBACK_TAG = 'offline-fallback';
    var window = { apiHealth: { status: 'ok', last_updates: { news: '2026-03-07T02:55:00.000Z' } } };
    var document = {
      getElementById(id) {
        return id === 'liveDataProvenance' ? globalThis.lineage : null;
      }
    };
    ${extractFunctionSource(appSource, 'isObject')}
    ${extractFunctionSource(appSource, 'toFiniteNumber')}
    ${extractFunctionSource(appSource, 'toString')}
    ${extractFunctionSource(appSource, 'toArray')}
    ${extractFunctionSource(appSource, 'formatRelativeTime')}
    ${extractFunctionSource(appSource, 'getCriticalWidgetHealthAgeMs')}
    ${extractFunctionSource(appSource, 'getCriticalWidgetHealthStatus')}
    ${extractFunctionSource(appSource, 'updateLiveProvenance')}
    globalThis.batch11Smoke = {
      getCriticalWidgetHealthStatus,
      updateLiveProvenance
    };
  `;

  context.lineage = lineage;
  vm.runInContext(bootstrap, context, { filename: appPath });
  return { context, lineage };
}

const { context: connectorContext, events, appendedNodes, intervals } = createConnectorContext();
vm.runInContext(connectorSource, connectorContext, { filename: connectorPath });

assert.equal(typeof connectorContext.window.refreshLiveData, 'function', 'connector must expose refreshLiveData');
assert.equal(intervals.length, 0, 'connector should not start polling before DOMContentLoaded in smoke context');

const payload = await connectorContext.window.refreshLiveData();
const latestEvent = events.at(-1);

assert.equal(payload.contractState, 'stale', 'connector payload must expose stale contract state');
assert.equal(payload.ingestionHealth.degraded_count, 1, 'connector payload must include ingestion health summary');
assert.equal(payload.freshness.lastFetchedAt, Date.parse('2026-03-07T02:30:00.000Z'), 'connector freshness must reflect oldest ingestion contract timestamp');
assert.equal(payload.freshness.ttlMs, 1800000, 'connector freshness must use ingestion TTL in milliseconds');
assert.equal(latestEvent.type, 'financecopilot:live-dashboard-updated', 'connector must dispatch the live data event');
assert.equal(latestEvent.detail.contractState, 'stale', 'event payload must include freshness contract state');
assert.equal(latestEvent.detail.ingestionHealth.status, 'degraded', 'event payload must include ingestion health data');
assert.ok(latestEvent.detail.warnings.includes('ingestion-contract-stale'), 'connector must warn when ingestion contract is stale');
assert.equal(appendedNodes.some((node) => node.id === 'live-badge'), true, 'connector should render live badge');

const { context: appContext, lineage } = createAppContext();
appContext.liveDataMeta = {
  generatedAt: '2026-03-07T03:00:00.000Z',
  warnings: [],
  sources: ['api-connector'],
  modelVersions: ['live'],
  contractState: 'stale',
  freshness: { lastFetchedAt: Date.parse('2026-03-07T02:30:00.000Z'), ttlMs: 1800000 },
  cache: { lastFetchedAt: Date.parse('2026-03-07T02:30:00.000Z'), ttlMs: 1800000 }
};

const healthStatus = vm.runInContext('batch11Smoke.getCriticalWidgetHealthStatus()', appContext);
assert.equal(healthStatus.state, 'stale', 'app freshness banner must respect contract stale state');

vm.runInContext(`
  batch11Smoke.updateLiveProvenance({
    generatedAt: '2026-03-07T03:00:00.000Z',
    sources: ['api-connector'],
    modelVersions: ['live'],
    warnings: ['ingestion-contract-stale'],
    contractState: 'stale'
  });
`, appContext);
assert.ok(lineage.textContent.includes('freshness: STALE'), 'provenance must surface contract freshness state');

console.log('PASS batch_11_dev_02_freshness_contract_check');
