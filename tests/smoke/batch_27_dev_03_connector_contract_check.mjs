import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const repoRoot = process.cwd();
const connectorPath = path.join(repoRoot, 'apps/web/src/domains/forecasts/contracts/apiConnector.js');
const legacyConnectorPath = path.join(repoRoot, 'apps/web/src/apiConnector.js');
const appPath = path.join(repoRoot, 'apps/web/src/domains/forecasts/pages/app.js');

const connectorSource = fs.readFileSync(connectorPath, 'utf8');
const legacyConnectorSource = fs.readFileSync(legacyConnectorPath, 'utf8');
const appSource = fs.readFileSync(appPath, 'utf8');

assert.ok(!connectorSource.includes('Math.random'), 'canonical connector must not use Math.random');
assert.ok(!legacyConnectorSource.includes('function transformNewsItem'), 'legacy connector must not duplicate connector transforms');
assert.ok(
  legacyConnectorSource.includes('domains/forecasts/contracts/apiConnector.js'),
  'legacy connector must point at the canonical forecasts connector'
);

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
  const appendedNodes = [];
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

  const events = [];
  const intervals = [];
  const window = {
    document,
    location: { href: 'http://localhost:3000/src/domains/forecasts/pages/index.html' },
    addEventListener() {},
    dispatchEvent(event) {
      events.push(event);
      return true;
    }
  };

  const fixtureNow = '2026-03-07T03:00:00.000Z';
  const fetchLog = [];
  const responses = new Map([
    ['/news/feed?limit=20', { data: { articles: [{ title: 'Markets hold gains', sentiment: 'positive', score: 70, source: 'Reuters', tickers: ['AAPL'], summary: 'AAPL leads', url: 'https://example.com/news/1', published_at: '2026-03-07T01:00:00.000Z' }] } }],
    ['/alerts', { data: { alerts: [{ id: 'alert-1', ticker: 'AAPL', type: 'volatility', severity: 'warning', confidence: 0.74, description: 'Volatility alert', timestamp: '2026-03-07T02:30:00.000Z' }] } }],
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
    ['/dashboard/market-drivers', { data: { drivers: [{ factor: 'Tech momentum', contribution: 62 }] } }],
    ['/dashboard/kpis', { ok: true, data: { source: ['dashboard-kpis'], generated_at: fixtureNow, portfolio_value: 125000, portfolio_change_pct: 1.4 } }],
    ['/dashboard/portfolio-summary', { ok: true, data: { source: ['portfolio-summary'], generated_at: fixtureNow, total_value: 125000, total_change_pct: 1.4 } }],
    ['/health', { last_updates: { news: fixtureNow } }]
  ]);

  const fetch = async (url, options = {}) => {
    const requestUrl = String(url).replace('http://localhost:8050/api', '');
    fetchLog.push({ url: requestUrl, method: options.method || 'GET' });
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
  context.window.setInterval = context.setInterval;
  context.window.clearInterval = context.clearInterval;
  context.window.fetch = fetch;
  context.window.CustomEvent = context.CustomEvent;
  context.window.Date = DateShim;
  context.window.console = console;

  return { context, events, fetchLog, appendedNodes, intervals };
}

const { context, events, fetchLog, appendedNodes, intervals } = createConnectorContext();
vm.runInContext(connectorSource, context, { filename: connectorPath });

assert.equal(typeof context.window.refreshLiveData, 'function', 'connector must expose refreshLiveData');
assert.equal(intervals.length, 0, 'connector should not start polling before DOMContentLoaded in smoke context');

const firstPayload = await context.window.refreshLiveData();
const secondPayload = await context.window.refreshLiveData();

assert.equal(firstPayload.data.newsItems[0].effect, '+2.8%');
assert.equal(secondPayload.data.newsItems[0].effect, firstPayload.data.newsItems[0].effect, 'news effect must be deterministic across refreshes');
assert.deepEqual(firstPayload.data.newsItems, secondPayload.data.newsItems, 'news payload must be stable across refreshes');

for (const key of ['newsItems', 'forecasts', 'tradeIdeas', 'alerts', 'topMovers', 'topStocks', 'story', 'marketCalendar', 'marketDrivers', 'llmJudgeData', 'kpis', 'portfolioSummary']) {
  assert.ok(Object.prototype.hasOwnProperty.call(firstPayload.data, key), `connector payload missing ${key}`);
}

assert.equal(events.at(-1)?.type, 'financecopilot:live-dashboard-updated', 'connector must dispatch the live data event');
assert.equal(fetchLog.some((entry) => entry.url === '/dashboard/market-drivers'), true, 'connector smoke must include backend market drivers fetch');
assert.equal(appendedNodes.some((node) => node.id === 'live-badge'), true, 'connector should render live badge in DOM smoke');

for (const token of ['data.newsItems', 'data.forecasts', 'data.tradeIdeas', 'data.alerts', 'data.topMovers', 'data.kpis', 'data.portfolioSummary', 'data.marketCalendar', 'data.marketDrivers', 'data.topStocks', 'data.story', 'data.llmJudgeData']) {
  assert.ok(appSource.includes(token), `UI contract consumer missing ${token}`);
}

assert.ok(appSource.includes('financecopilot:live-dashboard-updated'), 'UI must listen to the connector live update event');

const legacyDocument = {
  currentScript: { src: 'http://localhost:3000/src/apiConnector.js' },
  head: createNode('head'),
  body: createNode('body'),
  documentElement: createNode('html'),
  createElement(tagName) {
    return createNode(tagName);
  },
  querySelectorAll() {
    return [];
  }
};
const legacyWindow = { document: legacyDocument, location: { href: 'http://localhost:3000/' } };
const legacyContext = vm.createContext({
  window: legacyWindow,
  document: legacyDocument,
  URL,
  console
});
legacyWindow.window = legacyWindow;
vm.runInContext(legacyConnectorSource, legacyContext, { filename: legacyConnectorPath });

const injectedScript = legacyDocument.head.children[0] || legacyDocument.body.children[0] || legacyDocument.documentElement.children[0];
assert.ok(injectedScript, 'legacy connector should inject canonical script');
assert.equal(injectedScript.src, 'http://localhost:3000/src/domains/forecasts/contracts/apiConnector.js');

console.log('PASS batch_27_dev_03_connector_contract_check');
