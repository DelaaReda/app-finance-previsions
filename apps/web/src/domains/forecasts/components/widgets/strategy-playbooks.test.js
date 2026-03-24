const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function loadStrategyPlaybookHelpers() {
  const source = fs.readFileSync(path.join(__dirname, 'strategy-playbooks.html'), 'utf8');
  const scriptStart = source.indexOf('<script>');
  const scriptEnd = source.indexOf('</script>', scriptStart);

  assert.notEqual(scriptStart, -1, 'Expected widget script block');
  assert.notEqual(scriptEnd, -1, 'Expected widget script closing tag');

  const scriptBody = source.slice(scriptStart + '<script>'.length, scriptEnd);
  const sandbox = {
    console,
    setTimeout,
    clearTimeout,
    window: {},
    document: {
      addEventListener() {},
      createElement() {
        return {
          _textContent: '',
          set textContent(value) {
            this._textContent = String(value);
          },
          get textContent() {
            return this._textContent;
          },
          get innerHTML() {
            return escapeHtml(this._textContent);
          },
        };
      },
    },
  };
  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    `${scriptBody}
this.renderPlaybookCard = renderPlaybookCard;
this.summarizeCostAwareness = summarizeCostAwareness;`,
    sandbox,
    { filename: 'strategy-playbooks.html' }
  );

  return sandbox;
}

test('renderPlaybookCard promotes net edge and warning state when costs sharply compress upside', () => {
  const sandbox = loadStrategyPlaybookHelpers();

  const html = sandbox.renderPlaybookCard({
    ticker: 'IEF',
    decision: 'hold',
    confidence: 0.74,
    expected_return: 0.012,
    risk_level: 'medium',
    summary: ['Reduce drawdown concentration'],
    cost_awareness: {
      total_cost_bps: 16,
      fee_bps: 5,
      slippage_bps: 6,
      estimated_tax_drag_bps: 5,
      gross_expected_return_pct: 0.012,
      net_expected_return_pct: 0.002,
    },
  });

  assert.match(html, /Review costs first/);
  assert.match(html, /playbook-cost-alert warning/);
  assert.match(html, /Low net edge after costs/);
  assert.match(html, /Net Edge/);
  assert.match(html, /\+0\.2%/);
  assert.match(html, /Gross edge 1\.2% -&gt; Net edge 0\.2%/);
});

test('renderPlaybookCard flags when costs turn a trade negative after tax, fees, and slippage', () => {
  const sandbox = loadStrategyPlaybookHelpers();

  const html = sandbox.renderPlaybookCard({
    ticker: 'IEF',
    decision: 'hold',
    confidence: 0.74,
    expected_return: 0.0011,
    risk_level: 'medium',
    summary: ['Reduce drawdown concentration'],
    cost_awareness: {
      total_cost_bps: 30,
      fee_bps: 10,
      slippage_bps: 8,
      estimated_tax_drag_bps: 12,
      gross_expected_return_pct: 0.0011,
      net_expected_return_pct: -0.0019,
      tax_impact: 'Short-term gains likely',
    },
  });

  assert.match(html, /Costs block action/);
  assert.match(html, /playbook-cost-alert critical/);
  assert.match(html, /Costs overwhelm edge/);
  assert.match(html, /-0\.2%/);
  assert.match(html, /Tax note Short-term gains likely/);
});

test('renderPlaybookCard normalizes percent-style gross and net edge payloads', () => {
  const sandbox = loadStrategyPlaybookHelpers();

  const html = sandbox.renderPlaybookCard({
    ticker: 'IEF',
    decision: 'hold',
    confidence: 0.74,
    expected_return: 1.8,
    risk_level: 'medium',
    summary: ['Reduce drawdown concentration'],
    cost_awareness: {
      total_cost_bps: 6.9,
      fee_bps: 2,
      slippage_bps: 4,
      estimated_tax_drag_bps: 0.9,
      gross_expected_return_pct: 1.8,
      net_expected_return_pct: 1.7,
    },
  });

  assert.match(html, /Net Edge/);
  assert.match(html, /\+1\.7%/);
  assert.match(html, /Gross edge 1\.8% -&gt; Net edge 1\.7%/);
  assert.doesNotMatch(html, /Gross edge 180% -&gt; Net edge 170%/);
});
