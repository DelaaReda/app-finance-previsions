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
