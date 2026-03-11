const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadConnector(fetchImpl, windowOverrides = {}, runtimeOverrides = {}) {
  const source = fs.readFileSync(path.join(__dirname, 'apiConnector.js'), 'utf8');
  const sandbox = {
    console,
    fetch: fetchImpl,
    window: {
      ...windowOverrides,
    },
    document: {
      readyState: 'loading',
      addEventListener() {},
      createElement() {
        return {
          style: {},
          appendChild() {},
        };
      },
      body: {
        appendChild() {},
      },
    },
    setInterval: runtimeOverrides.setIntervalImpl || function setInterval() {
      return 1;
    },
    clearInterval: runtimeOverrides.clearIntervalImpl || function clearInterval() {},
    CustomEvent: function CustomEvent(type, init = {}) {
      this.type = type;
      this.detail = init.detail;
    },
    Date,
    URLSearchParams,
  };

  sandbox.window.window = sandbox.window;
  sandbox.window.document = sandbox.document;
  sandbox.window.addEventListener = sandbox.window.addEventListener || function addEventListener() {};
  sandbox.window.dispatchEvent = sandbox.window.dispatchEvent || function dispatchEvent() {};

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

test('getStatus prefers same-origin api base when window.location.origin is available', async () => {
  const calls = [];
  const sandbox = loadConnector(
    async (url) => {
      calls.push(url);
      return {
        async json() {
          return {
            ok: true,
            data: {
              status: 'ok',
              source: ['api_status'],
              last_updates: {},
            },
          };
        },
      };
    },
    {
      location: {
        origin: 'https://finance.example.com',
      },
    },
  );

  const payload = await sandbox.window.FinanceAPI.getStatus();

  assert.deepEqual(calls, ['https://finance.example.com/api/status']);
  assert.equal(payload.status, 'ok');
  assert.deepEqual(payload.source, ['api_status']);
});

test('getWalkForwardScoreboard unwraps scoreboard payloads and preserves query params', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    return {
      async json() {
        return {
          ok: true,
          data: {
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
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getWalkForwardScoreboard({ horizon: '1w' });

  assert.deepEqual(calls, ['http://localhost:8050/api/forecasts/scoreboard?horizon=1w']);
  assert.equal(payload.rows[0].metric_key, 'walk_forward_direction_hit_rate');
  assert.equal(payload.rows[0].value, 0.61);
  assert.equal(payload.updated_at, '2026-03-10T10:00:00Z');
  assert.equal(payload.threshold_summary.walk_forward_direction_hit_rate.target, 0.52);
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
              {
                id: 'open_copilot',
                kind: 'open',
                label: 'Open copilot',
                target: '/copilot',
              },
            ],
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getCopilotContext();
  const copilotStart = payload.copilot_start || {};

  assert.deepEqual(calls, ['http://localhost:8050/api/copilot/start']);
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
    [
      { id: 'brief_of_day', target: 'market' },
      { id: 'open_copilot', target: 'copilot' },
    ]
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

test('getCopilotContext normalizes copilot slashed targets to the copilot overlay', async () => {
  const sandbox = loadConnector(async () => ({
    async json() {
      return {
        ok: true,
        data: {
          copilot_start: {
            brief_of_day: {
              title: 'Brief of the day',
              summary: 'Markets remain resilient after the last macro print.',
              sentiment: 'balanced',
              generated_at: '2026-03-09T06:00:00.000Z',
            },
            ask: [
              {
                id: 'ask_copilot',
                label: 'Ask about NVDA',
                prefill: {
                  question: 'What should I watch in NVDA today?',
                  tickers: ['NVDA'],
                },
              },
            ],
            open: [
              {
                id: 'open_copilot',
                label: 'Open copilot',
                target: '/copilot/',
              },
            ],
          },
        },
      };
    },
  }));

  const payload = await sandbox.window.FinanceAPI.getCopilotContext();
  const copilotStart = payload.copilot_start || {};

  assert.deepEqual(copilotStart.open.map((item) => ({ id: item.id, target: item.target })), [
    { id: 'open_copilot', target: 'copilot' },
  ]);
});

test('getCopilotContext forwards scoped tickers to the backend starter endpoint', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    return {
      async json() {
        return {
          ok: true,
          data: {
            scope_tickers: ['NVDA', 'MSFT'],
            copilot_start: {
              brief_of_day: {
                title: 'Brief of the day',
                summary: 'Leadership stays concentrated in AI-linked names.',
                sentiment: 'mixed',
                generated_at: '2026-03-09T05:30:00.000Z',
              },
              ask: [
                {
                  id: 'ask_copilot',
                  label: 'Ask about your list',
                  prefill: {
                    question: 'What should I monitor on NVDA and MSFT today?',
                    tickers: ['NVDA', 'MSFT'],
                  },
                },
              ],
              open: [],
            },
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getCopilotContext(['nvda', 'MSFT', 'nvda']);

  assert.deepEqual(calls, ['http://localhost:8050/api/copilot/start?tickers=NVDA&tickers=MSFT']);
  assert.deepEqual(payload.scope_tickers, ['NVDA', 'MSFT']);
  assert.deepEqual(payload.copilot_start.ask[0].prefill.tickers, ['NVDA', 'MSFT']);
});

test('startAutoRefresh clears scoped copilot starter cache entries before reloading the brief', async () => {
  const copilotStartCalls = [];
  let scheduledRefresh = null;
  const sandbox = loadConnector(
    async (url) => {
      if (url.includes('/api/copilot/start')) {
        copilotStartCalls.push(url);
        return {
          async json() {
            return {
              ok: true,
              data: {
                brief_of_day: {
                  title: 'Brief of the day',
                  summary: `Starter refresh #${copilotStartCalls.length}`,
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
                ],
              },
            };
          },
        };
      }

      if (url.includes('/api/llm/judge/run')) {
        return {
          ok: false,
          async json() {
            return {};
          },
        };
      }

      return {
        ok: true,
        async json() {
          return { ok: true, data: {} };
        },
      };
    },
    {},
    {
      setIntervalImpl(fn) {
        scheduledRefresh = fn;
        return 1;
      },
    },
  );

  const firstPayload = await sandbox.window.FinanceAPI.getCopilotStart(['nvda']);
  const cachedPayload = await sandbox.window.FinanceAPI.getCopilotStart(['nvda']);

  assert.equal(firstPayload.copilot_start.brief_of_day.summary, 'Starter refresh #1');
  assert.equal(cachedPayload.copilot_start.brief_of_day.summary, 'Starter refresh #1');
  assert.deepEqual(copilotStartCalls, ['http://localhost:8050/api/copilot/start?tickers=NVDA']);

  sandbox.window.FinanceAPI.startAutoRefresh(10);
  await scheduledRefresh();

  assert.deepEqual(copilotStartCalls, [
    'http://localhost:8050/api/copilot/start?tickers=NVDA',
    'http://localhost:8050/api/copilot/start',
  ]);
});

test('getCopilotStart unwraps the dedicated starter contract and normalizes open targets', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    return {
      async json() {
        return {
          ok: true,
          data: {
            brief_of_day: {
              title: 'Brief of the day',
              summary: 'Breadth is improving while rates stay range-bound.',
              sentiment: 'mixed',
              generated_at: '2026-03-09T05:30:00.000Z',
              source: ['copilot_start_test'],
            },
            ask: [
              {
                id: 'ask_copilot',
                label: 'Ask about NVDA',
                target: '/copilot/ask',
                prefill: {
                  question: 'What matters most for NVDA today?',
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
                id: 'open_copilot',
                label: 'Open copilot',
                target: '/copilot',
              },
            ],
            scope_tickers: ['NVDA'],
            stats: {
              ask_count: 1,
              open_count: 2,
            },
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getCopilotStart(['nvda']);
  const copilotStart = payload.copilot_start || {};

  assert.deepEqual(calls, ['http://localhost:8050/api/copilot/start?tickers=NVDA']);
  assert.equal(copilotStart.brief_of_day.summary, 'Breadth is improving while rates stay range-bound.');
  assert.deepEqual(
    copilotStart.ask.map((item) => item.id),
    ['ask_copilot']
  );
  assert.deepEqual(
    copilotStart.open.map((item) => ({ id: item.id, target: item.target })),
    [
      { id: 'brief_of_day', target: 'market' },
      { id: 'open_copilot', target: 'copilot' },
    ]
  );
  assert.deepEqual(payload.scope_tickers, ['NVDA']);
  assert.deepEqual(payload.stats, { ask_count: 1, open_count: 2 });
});

test('getCopilotStart maps open_copilot without explicit target to the copilot landing', async () => {
  const sandbox = loadConnector(async () => ({
    async json() {
      return {
        ok: true,
        data: {
          brief_of_day: {
            title: 'Brief of the day',
            summary: 'AI names are still driving momentum.',
            sentiment: 'positive',
            generated_at: '2026-03-09T06:00:00.000Z',
          },
          ask: [],
          open: [
            {
              id: 'open_copilot',
              label: 'Open copilot',
            },
          ],
        },
      };
    },
  }));

  const payload = await sandbox.window.FinanceAPI.getCopilotStart();
  const copilotStart = payload.copilot_start || {};

  assert.deepEqual(
    copilotStart.open.map((item) => ({ id: item.id, target: item.target })),
    [{ id: 'open_copilot', target: 'copilot' }]
  );
});

test('getCopilotStart falls back to copilot context when the starter route is unavailable', async () => {
  const calls = [];
  const sandbox = loadConnector(async (url) => {
    calls.push(url);
    if (url === 'http://localhost:8050/api/copilot/start') {
      throw new Error('starter route unavailable');
    }

    if (url === 'http://localhost:8050/api/brief/daily') {
      return {
        async json() {
          return null;
        },
      };
    }

    assert.equal(url, 'http://localhost:8050/api/copilot/context');
    return {
      async json() {
        return {
          ok: true,
          data: {
            daily_brief: {
              title: 'Brief of the day',
              summary: 'Fallback context still has the brief ready.',
              sentiment: 'mixed',
              generated_at: '2026-03-09T05:30:00.000Z',
            },
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
                  question: 'What matters most for NVDA today?',
                  tickers: ['NVDA'],
                },
              },
            ],
          },
        };
      },
    };
  });

  const payload = await sandbox.window.FinanceAPI.getCopilotStart();
  const copilotStart = payload.copilot_start || {};

  assert.deepEqual(calls, [
    'http://localhost:8050/api/copilot/start',
    'http://localhost:8050/api/brief/daily',
    'http://localhost:8050/api/copilot/context',
  ]);
  assert.equal(copilotStart.brief_of_day.summary, 'Fallback context still has the brief ready.');
  assert.deepEqual(
    copilotStart.ask.map((item) => item.id),
    ['ask_copilot']
  );
  assert.deepEqual(
    copilotStart.open.map((item) => ({ id: item.id, target: item.target })),
    [{ id: 'brief_of_day', target: 'market' }]
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
  assert.equal(health.riskProfile, 'balanced');
  assert.equal(health.stateSummary, '1Y horizon | High conviction | Moderate risk');
  assert.equal(health.allocationLabel, 'Largest saved weight: MSFT 70%');
  assert.equal(health.allocationProgress, 70);
  assert.equal(health.suggestion, 'Saved weights were normalized to sum to 1.0.');
  assert.equal(health.benchmark, 'SPY');
  assert.equal(health.confidence, 65);
  assert.equal(health.status, 'ok');
});

test('transformPortfolioRiskProfileToHealth maps raw risk profile payloads for UI fallback', () => {
  const sandbox = loadConnector(async () => ({
    async json() {
      return {};
    },
  }));

  const health = sandbox.window.FinanceAPI.transformPortfolioRiskProfileToHealth({
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
      risk: { level: 'medium' },
      why: ['Portfolio spans 2 tickers under equal-weight assumptions.'],
      stats: {
        largest_position_ticker: 'MSFT',
        largest_position_weight: 0.7,
      },
    },
  });

  assert.equal(health.portfolioId, 'portfolio-123');
  assert.equal(health.portfolioName, 'Core');
  assert.equal(health.overall, 68);
  assert.equal(health.stateSummary, '1Y horizon | High conviction | Moderate risk');
  assert.equal(health.allocationLabel, 'Largest saved weight: MSFT 70%');
  assert.equal(health.suggestion, 'Portfolio spans 2 tickers under equal-weight assumptions.');
  assert.equal(health.updatedAt, '2026-03-09T06:30:00Z');
});

test('buildLiveFreshnessContract folds portfolio risk profile status into the shared freshness state', () => {
  const sandbox = loadConnector(async () => ({
    async json() {
      return {};
    },
  }));

  const okContract = sandbox.buildLiveFreshnessContract(null, null, {
    status: 'ok',
    freshness: {
      generated_at: '2026-03-09T06:30:00Z',
      ttl_seconds: 90,
    },
  });
  const degradedContract = sandbox.buildLiveFreshnessContract(null, null, {
    status: 'degraded',
    freshness: {
      generated_at: '2026-03-09T05:30:00Z',
      ttl_seconds: 180,
    },
  });

  assert.equal(okContract.contractState, 'ok');
  assert.equal(okContract.freshness.lastFetchedAt, Date.parse('2026-03-09T06:30:00Z'));
  assert.equal(okContract.freshness.ttlMs, 90000);
  assert.equal(degradedContract.contractState, 'degraded');
  assert.equal(degradedContract.freshness.lastFetchedAt, Date.parse('2026-03-09T05:30:00Z'));
  assert.equal(degradedContract.freshness.ttlMs, 180000);
});

test('getLiveDashboardData preserves portfolio risk profile freshness and status for downstream UI mapping', async () => {
  const sandbox = loadConnector(async () => ({
    async json() {
      return {};
    },
  }));

  sandbox.window.livePortfolioRiskProfile = {
    portfolio: { id: 'portfolio-123', name: 'Core' },
    risk: { level: 'medium' },
  };
  sandbox.window.livePortfolioRiskProfileStatus = 'degraded';
  sandbox.window.livePortfolioRiskProfileFreshness = '2026-03-09T06:30:00Z';

  const payload = sandbox.window.getLiveDashboardData();

  assert.deepEqual(payload.data.portfolioRiskProfile, {
    portfolio: { id: 'portfolio-123', name: 'Core' },
    risk: { level: 'medium' },
  });
  assert.equal(payload.data.portfolioRiskProfileStatus, 'degraded');
  assert.equal(payload.data.portfolioRiskProfileFreshness, '2026-03-09T06:30:00Z');
});

test('initLiveData hydrates judgeDecisionJournal without relying on page globals', async () => {
  const sandbox = loadConnector(async (url) => {
    if (url.includes('/api/judge?limit=5')) {
      return {
        async json() {
          return {
            ok: true,
            data: {
              decision_journal: [
                {
                  symbol: 'NVDA',
                  decision: 'HOLD',
                  note: 'Leadership is intact.',
                },
              ],
            },
          };
        },
      };
    }

    if (url.includes('/api/llm/judge/run')) {
      return {
        ok: false,
        async json() {
          return {};
        },
      };
    }

    return {
      ok: true,
      async json() {
        return { ok: true, data: {} };
      },
    };
  });

  await sandbox.window.initLiveData();

  assert.equal(Array.isArray(sandbox.window.judgeDecisionJournal), true);
  assert.equal(JSON.stringify(sandbox.window.judgeDecisionJournal), JSON.stringify([
    {
      symbol: 'NVDA',
      decision: 'HOLD',
      note: 'Leadership is intact.',
    },
  ]));
});
