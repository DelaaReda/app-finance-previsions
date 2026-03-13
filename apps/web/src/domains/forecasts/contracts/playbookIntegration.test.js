const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadIntegration(playbooks) {
  const source = fs.readFileSync(path.join(__dirname, 'playbookIntegration.js'), 'utf8');
  const sandbox = {
    console,
    window: {
      getStrategyPlaybooks: async () => ({
        data: {
          playbooks,
        },
      }),
    },
  };

  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: 'playbookIntegration.js' });

  return sandbox.window.PlaybookIntegration;
}

test('getExpectedReturn falls back to gross expected return without cost awareness', async () => {
  const integration = loadIntegration([
    {
      ticker: 'AAPL',
      expected_return: 0.018,
    },
  ]);

  const html = await integration.getExpectedReturn('AAPL');

  assert.match(html, /title="Expected return"/);
  assert.match(html, />\+1\.80%</);
});

test('getExpectedReturn exposes low net edge with gross to net tooltip and cost breakdown', async () => {
  const integration = loadIntegration([
    {
      ticker: 'IEF',
      expected_return: 0.012,
      cost_awareness: {
        gross_expected_return_pct: 0.012,
        net_expected_return_pct: 0.002,
        fee_bps: 5,
        slippage_bps: 6,
        estimated_tax_drag_bps: 5,
      },
    },
  ]);

  const html = await integration.getExpectedReturn('IEF');

  assert.match(html, />Low Net \+0\.20%</);
  assert.match(html, /Gross edge \+1\.20% -&gt; Net edge \+0\.20%/);
  assert.match(html, /Fees 5 bps/);
  assert.match(html, /Slippage 6 bps/);
  assert.match(html, /Tax drag 5 bps/);
  assert.match(html, /Low net edge after costs/);
});

test('getExpectedReturn normalizes percent-style gross and net payloads', async () => {
  const integration = loadIntegration([
    {
      ticker: 'TLT',
      expected_return: 1.8,
      cost_awareness: {
        gross_expected_return_pct: 1.8,
        net_expected_return_pct: 1.7,
        fee_bps: 6,
        slippage_bps: 4,
        estimated_tax_drag_bps: 1,
      },
    },
  ]);

  const html = await integration.getExpectedReturn('TLT');

  assert.match(html, /class="playbook-return positive"/);
  assert.match(html, />Net \+1\.70%</);
  assert.match(html, /Gross edge \+1\.80% -&gt; Net edge \+1\.70%/);
  assert.doesNotMatch(html, /Net \+170\.00%/);
});
