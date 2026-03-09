const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadConnector(fetchImpl) {
  const source = fs.readFileSync(path.join(__dirname, 'apiConnector.js'), 'utf8');
  const sandbox = {
    console,
    fetch: fetchImpl,
    window: {},
    document: {
      readyState: 'loading',
      addEventListener() {},
    },
    setInterval() {
      return 1;
    },
    clearInterval() {},
    CustomEvent: function CustomEvent(type, init = {}) {
      this.type = type;
      this.detail = init.detail;
    },
    Date,
    URLSearchParams,
  };

  sandbox.window.window = sandbox.window;
  sandbox.window.document = sandbox.document;

  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: 'apiConnector.js' });
  return sandbox;
}

test('getStatus unwraps the canonical /status envelope', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    return {
      async json() {
        return {
          ok: true,
          data: {
            status: 'ok',
            source: ['api_status'],
            last_updates: { news: '2026-03-08T06:00:00Z' },
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getStatus();

  assert.deepEqual(calls, ['http://localhost:8050/api/status']);
  assert.equal(payload.status, 'ok');
  assert.deepEqual(payload.source, ['api_status']);
  assert.equal(payload.last_updates.news, '2026-03-08T06:00:00Z');
});

test('getStatus falls back to /health when /status is unavailable', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    if (url.endsWith('/api/status')) {
      return {
        async json() {
          return null;
        },
      };
    }

    return {
      async json() {
        return {
          ok: true,
          data: {
            status: 'degraded',
            source: ['api_health'],
            last_updates: {},
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getStatus();

  assert.deepEqual(calls, [
    'http://localhost:8050/api/status',
    'http://localhost:8050/api/health',
  ]);
  assert.equal(payload.status, 'degraded');
  assert.deepEqual(payload.source, ['api_health']);
});

test('getCopilotContext normalizes brief-first entry points into ask/open starters', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    return {
      async json() {
        return {
          ok: true,
          data: {
            daily_brief: {
              title: 'Brief of the day',
              summary: 'Rates stay range-bound while mega-cap earnings keep leadership narrow.',
              sentiment: 'mixed',
              generated_at: '2026-03-09T05:30:00.000Z',
            },
            scope_tickers: ['NVDA'],
            entry_points: [
              {
                id: 'brief_of_day',
                kind: 'open',
                label: 'Open the live brief',
                target: '/brief/daily',
              },
              {
                id: 'ask_copilot',
                kind: 'ask',
                label: 'Ask about NVDA',
                target: '/copilot/ask',
                prefill: {
                  question: 'Give me a 1-week investment memo on NVDA.',
                  tickers: ['NVDA'],
                },
              },
            ],
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getCopilotContext();
  const copilotStart = payload.copilot_start || {};

  assert.deepEqual(calls, ['http://localhost:8050/api/copilot/context']);
  assert.equal(
    copilotStart.brief_of_day.summary,
    'Rates stay range-bound while mega-cap earnings keep leadership narrow.'
  );
  assert.deepEqual(
    copilotStart.ask.map((item) => item.id),
    ['ask_copilot']
  );
  assert.equal(
    copilotStart.ask[0].prefill.question,
    'Give me a 1-week investment memo on NVDA.'
  );
  assert.deepEqual(copilotStart.ask[0].prefill.tickers, ['NVDA']);
  assert.deepEqual(
    copilotStart.open.map((item) => ({ id: item.id, target: item.target })),
    [{ id: 'brief_of_day', target: 'market' }]
  );
});

test('getCopilotContext normalizes direct copilot_start open targets for the existing tabs', async () => {
  const sandbox = loadConnector(async () => ({
    async json() {
      return {
        ok: true,
        data: {
          copilot_start: {
            brief_of_day: {
              title: 'Brief of the day',
              summary: 'Markets are holding a narrow leadership profile.',
              sentiment: 'mixed',
              generated_at: '2026-03-09T05:30:00.000Z',
            },
            ask: [
              {
                id: 'ask_copilot',
                label: 'Ask about NVDA',
                prefill: {
                  question: 'Give me a 1-week investment memo on NVDA.',
                  tickers: ['NVDA'],
                },
              },
            ],
            open: [
              {
                id: 'brief_of_day',
                label: 'Open the live brief',
                target: '/brief/daily',
              },
              {
                id: 'copilot',
                label: 'Open copilot',
                target: '/copilot',
              },
            ],
          },
        },
      };
    },
  }));

  const payload = await sandbox.window.FinanceAPI.getCopilotContext();
  const copilotStart = payload.copilot_start || {};

  assert.deepEqual(
    copilotStart.open.map((item) => ({ id: item.id, target: item.target })),
    [
      { id: 'brief_of_day', target: 'market' },
      { id: 'copilot', target: 'copilot' },
    ]
  );
});

test('getPortfolioRiskProfile resolves the default saved portfolio and unwraps the risk profile envelope', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    if (url === 'http://localhost:8050/api/portfolios') {
      return {
        async json() {
          return {
            ok: true,
            data: {
              portfolios: [
                { id: 'portfolio-123', name: 'Core' },
              ],
            },
          };
        },
      };
    }

    if (url === 'http://localhost:8050/api/portfolios/portfolio-123/risk-profile?benchmark=SPY') {
      return {
        async json() {
          return {
            ok: true,
            status: 'ok',
            freshness: '2026-03-09T06:30:00Z',
            data: {
              portfolio: { id: 'portfolio-123', name: 'Core' },
              benchmark: 'SPY',
              risk_profile: 'balanced',
              risk: { level: 'medium', caveat: '' },
            },
          };
        },
      };
    }

    throw new Error(`Unexpected URL ${url}`);
  });

  const payload = await sandbox.window.FinanceAPI.getPortfolioRiskProfile();

  assert.deepEqual(calls, [
    'http://localhost:8050/api/portfolios',
    'http://localhost:8050/api/portfolios/portfolio-123/risk-profile?benchmark=SPY',
  ]);
  assert.equal(payload.portfolioId, 'portfolio-123');
  assert.equal(payload.status, 'ok');
  assert.equal(payload.freshness, '2026-03-09T06:30:00Z');
  assert.equal(payload.data.portfolio.id, 'portfolio-123');
  assert.equal(payload.data.risk_profile, 'balanced');
});

test('getPortfolioHealth maps portfolio state and risk profile into widget data', async () => {
  const sandbox = loadConnector(async (url) => {
    if (url === 'http://localhost:8050/api/portfolios') {
      return {
        async json() {
          return {
            ok: true,
            data: {
              portfolios: [
                { id: 'portfolio-123', name: 'Core' },
              ],
            },
          };
        },
      };
    }

    if (url === 'http://localhost:8050/api/portfolios/portfolio-123/risk-profile?benchmark=SPY') {
      return {
        async json() {
          return {
            ok: true,
            status: 'ok',
            freshness: '2026-03-09T06:30:00Z',
            data: {
              portfolio: {
                id: 'portfolio-123',
                name: 'Core',
                state: {
                  horizon: '1y',
                  conviction: 'high',
                  risk_tolerance: 'moderate',
                },
              },
              benchmark: 'SPY',
              risk_profile: 'balanced',
              risk: { level: 'medium', caveat: '' },
              warnings: ['Saved weights were normalized to sum to 1.0.'],
              why: ['Portfolio spans 2 tickers under equal-weight assumptions.'],
              confidence: 0.65,
              stats: {
                largest_position_ticker: 'MSFT',
                largest_position_weight: 0.7,
              },
            },
          };
        },
      };
    }

    throw new Error(`Unexpected URL ${url}`);
  });

  const health = await sandbox.window.FinanceAPI.getPortfolioHealth();

  assert.equal(health.portfolioId, 'portfolio-123');
  assert.equal(health.portfolioName, 'Core');
  assert.equal(health.overall, 68);
  assert.equal(health.riskLabel, 'Medium');
  assert.equal(health.riskTone, 'neutral');
  assert.equal(health.stateSummary, '1Y horizon | High conviction | Moderate risk');
  assert.equal(health.allocationLabel, 'Largest saved weight: MSFT 70%');
  assert.equal(health.allocationProgress, 70);
  assert.equal(health.suggestion, 'Saved weights were normalized to sum to 1.0.');
  assert.equal(health.confidence, 65);
  assert.equal(health.status, 'ok');
});
