import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const repoRoot = process.cwd();
const connectorPath = path.join(repoRoot, 'apps/web/src/domains/forecasts/contracts/apiConnector.js');
const connectorSource = fs.readFileSync(connectorPath, 'utf8');
const appPath = path.join(repoRoot, 'apps/web/src/domains/forecasts/pages/app.js');
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
  const bodyStart = source.indexOf('{', start);
  assert.notEqual(bodyStart, -1, `missing body for function ${name}`);
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
  const document = {
    readyState: 'loading',
    body: createNode('body'),
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
    dispatchEvent() {
      return true;
    }
  };

  const fixtureNow = '2026-03-09T05:30:00.000Z';
  const responses = new Map([
    ['/copilot/context', {
      ok: true,
      data: {
        daily_brief: {
          title: 'Brief of the day',
          summary: 'Rates stay range-bound while mega-cap earnings keep leadership narrow.',
          sentiment: 'mixed',
          generated_at: fixtureNow
        },
        scope_tickers: ['NVDA'],
        entry_points: [
          {
            id: 'brief_of_day',
            kind: 'open',
            label: 'Open the live brief',
            target: '/brief/daily'
          },
          {
            id: 'ask_copilot',
            kind: 'ask',
            label: 'Ask about NVDA',
            target: '/copilot/ask',
            prefill: {
              question: 'Give me a 1-week investment memo on NVDA.',
              tickers: ['NVDA']
            }
          }
        ]
      }
    }]
  ]);

  const fetch = async (url) => {
    const requestUrl = String(url).replace('http://localhost:8050/api', '');
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
    setInterval() {
      return 1;
    },
    clearInterval() {},
    Date,
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
  context.window.setInterval = context.setInterval;
  context.window.clearInterval = context.clearInterval;
  context.window.CustomEvent = context.CustomEvent;
  context.window.console = console;

  return context;
}

function createClassList() {
  return {
    removed: [],
    remove(value) {
      this.removed.push(value);
    }
  };
}

function createPageContext() {
  const overlay = {
    classList: createClassList(),
    style: {}
  };
  const input = {
    focusCount: 0,
    focus() {
      this.focusCount += 1;
    }
  };
  const nodes = new Map([
    ['aiCopilotOverlay', overlay],
    ['aiOverlayInput', input],
    ['tab-market', { id: 'tab-market' }]
  ]);
  const tabButtons = {
    market: { dataset: { tab: 'market' } },
    copilot: { dataset: { tab: 'copilot' } }
  };
  const switchCalls = [];
  const toastCalls = [];
  const document = {
    getElementById(id) {
      return nodes.get(id) || null;
    },
    querySelector(selector) {
      if (selector === '.tab-btn[data-tab="market"]') return tabButtons.market;
      if (selector === '.tab-btn[data-tab="copilot"]') return tabButtons.copilot;
      return null;
    }
  };

  const context = vm.createContext({
    console,
    document,
    setTimeout(fn) {
      fn();
      return 1;
    },
    clearTimeout() {},
    safeSwitchTab(button, tabName) {
      switchCalls.push({ button, tabName });
    },
    showToast(message, type) {
      toastCalls.push({ message, type });
    }
  });

  vm.runInContext(`
    ${extractFunctionSource(appSource, 'toString')}
    ${extractFunctionSource(appSource, 'normalizeCopilotStartOpenTarget')}
    function focusCopilotInput() {
      document.getElementById('aiOverlayInput')?.focus();
    }
    ${extractFunctionSource(appSource, 'runCopilotStartOpen')}
    globalThis.runCopilotStartOpen = runCopilotStartOpen;
  `, context, { filename: appPath });

  return { context, overlay, input, switchCalls, toastCalls, tabButtons };
}

const context = createConnectorContext();
vm.runInContext(connectorSource, context, { filename: connectorPath });

assert.equal(typeof context.window.FinanceAPI?.getCopilotContext, 'function', 'connector must expose getCopilotContext');

const payload = await context.window.FinanceAPI.getCopilotContext();
const copilotStart = payload.copilot_start || {};

assert.equal(copilotStart.brief_of_day?.summary, 'Rates stay range-bound while mega-cap earnings keep leadership narrow.');
assert.deepEqual(
  copilotStart.ask.map((item) => item.id),
  ['ask_copilot'],
  'fallback entry_points ask actions must be preserved'
);
assert.equal(copilotStart.ask[0]?.prefill?.question, 'Give me a 1-week investment memo on NVDA.');
assert.deepEqual(copilotStart.ask[0]?.prefill?.tickers, ['NVDA']);
assert.deepEqual(
  copilotStart.open.map((item) => ({ id: item.id, target: item.target })),
  [{ id: 'brief_of_day', target: 'market' }],
  'brief open action must map to the existing market tab target'
);

const page = createPageContext();
vm.runInContext(`runCopilotStartOpen('/brief/daily')`, page.context);
assert.equal(page.switchCalls.length, 1, 'raw brief route should switch tabs');
assert.equal(page.switchCalls[0].tabName, 'market');
assert.equal(page.switchCalls[0].button, page.tabButtons.market);
assert.equal(page.overlay.style.display, 'none');
assert.deepEqual(page.overlay.classList.removed, ['active']);

vm.runInContext(`runCopilotStartOpen('/copilot/ask')`, page.context);
assert.equal(page.input.focusCount, 1, 'copilot route should focus the overlay input');
assert.equal(page.switchCalls.length, 1, 'copilot route should not switch away from the overlay');
assert.equal(page.toastCalls.length, 0, 'normalized routes should not emit open errors');

console.log('PASS batch_60_dev_03_copilot_context_check');
