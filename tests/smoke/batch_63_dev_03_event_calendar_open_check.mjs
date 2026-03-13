import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const repoRoot = process.cwd();
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

function createCardContext() {
  const fixtureNow = '2026-03-13T14:30:00.000Z';
  const fallbackState = {
    brief: {
      title: 'Brief of the day',
      summary: 'Fallback summary',
      generatedAt: fixtureNow,
      marketSentiment: 'UNKNOWN',
      marketRegime: 'UNKNOWN',
      topSignals: [],
      topOpportunities: [],
      topRisks: [],
      eventTiming: null,
      sources: [],
      freshness: fixtureNow
    },
    ask: [],
    open: []
  };

  const context = vm.createContext({
    console,
    Date,
    Math,
    Array,
    Object,
    String,
    Number,
    Boolean,
    JSON,
    buildDefaultCopilotStartState() {
      return JSON.parse(JSON.stringify(fallbackState));
    }
  });

  vm.runInContext(`
    ${extractFunctionSource(appSource, 'toString')}
    ${extractFunctionSource(appSource, 'isObject')}
    ${extractFunctionSource(appSource, 'toArray')}
    ${extractFunctionSource(appSource, 'normalizeCopilotStarterTickers')}
    ${extractFunctionSource(appSource, 'normalizeCopilotSourceLabels')}
    ${extractFunctionSource(appSource, 'normalizeCopilotStartList')}
    ${extractFunctionSource(appSource, 'normalizeCopilotStartOpenTarget')}
    ${extractFunctionSource(appSource, 'normalizeCopilotStartAsk')}
    ${extractFunctionSource(appSource, 'normalizeCopilotStartOpen')}
    ${extractFunctionSource(appSource, 'normalizeCopilotStartEventTiming')}
    ${extractFunctionSource(appSource, 'ensureCopilotStartEventCalendarOpen')}
    ${extractFunctionSource(appSource, 'buildCopilotStartState')}
    globalThis.buildCopilotStartState = buildCopilotStartState;
  `, context, { filename: appPath });

  return context;
}

function createNavigationContext() {
  const overlay = {
    classList: {
      removed: [],
      remove(value) {
        this.removed.push(value);
      }
    },
    style: {}
  };
  const input = {
    focusCount: 0,
    focus() {
      this.focusCount += 1;
    }
  };
  const calendarAnchor = {
    scrollCalls: [],
    scrollIntoView(options) {
      this.scrollCalls.push(options);
    }
  };
  const nodes = new Map([
    ['aiCopilotOverlay', overlay],
    ['aiOverlayInput', input],
    ['tab-market', { id: 'tab-market' }],
    ['market-calendar-widget-container', calendarAnchor]
  ]);
  const tabButtons = {
    market: { dataset: { tab: 'market' } }
  };
  const switchCalls = [];
  const toastCalls = [];
  const context = vm.createContext({
    console,
    document: {
      getElementById(id) {
        return nodes.get(id) || null;
      },
      querySelector(selector) {
        if (selector === '.tab-btn[data-tab="market"]') return tabButtons.market;
        return null;
      }
    },
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
    ${extractFunctionSource(appSource, 'resolveCopilotStartOpenDestination')}
    function focusCopilotInput() {
      document.getElementById('aiOverlayInput')?.focus();
    }
    ${extractFunctionSource(appSource, 'runCopilotStartOpen')}
    globalThis.runCopilotStartOpen = runCopilotStartOpen;
  `, context, { filename: appPath });

  return { context, overlay, calendarAnchor, switchCalls, toastCalls, tabButtons };
}

const cardContext = createCardContext();
const state = vm.runInContext(`buildCopilotStartState(${JSON.stringify({
  data: {
    brief_of_day: {
      title: 'Brief of the day',
      summary: 'Watch CPI and two mega-cap earnings prints over the next 48h.',
      market_sentiment: 'MIXED',
      generated_at: '2026-03-13T14:30:00Z',
      freshness: '2026-03-13T14:30:00Z',
      event_timing: {
        summary: 'Two high-impact catalysts land before tomorrow close.',
        events: [
          {
            event_type: 'CPI',
            dominant_horizon: '24h',
            interpretation: 'Inflation surprise risk remains elevated.'
          }
        ]
      }
    },
    ask: [
      {
        id: 'ask_copilot',
        label: 'Ask about today',
        prefill: {
          question: 'What matters most for my portfolio today?'
        }
      }
    ],
    open: [
      {
        id: 'brief_of_day',
        label: 'Open Live Brief',
        target: '/brief/daily'
      }
    ]
  }
})})`, cardContext);

assert.deepEqual(
  JSON.parse(JSON.stringify(state.open.map((item) => ({ id: item.id, target: item.target })))),
  [
    { id: 'brief_of_day', target: 'market' },
    { id: 'event_calendar', target: 'calendar' }
  ],
  'briefs with near-term events should expose an event calendar open action'
);

const page = createNavigationContext();
vm.runInContext(`runCopilotStartOpen('calendar')`, page.context);

assert.equal(page.switchCalls.length, 1, 'calendar action should switch tabs');
assert.equal(page.switchCalls[0].tabName, 'market');
assert.equal(page.switchCalls[0].button, page.tabButtons.market);
assert.equal(page.overlay.style.display, 'none');
assert.deepEqual(page.overlay.classList.removed, ['active']);
assert.deepEqual(
  JSON.parse(JSON.stringify(page.calendarAnchor.scrollCalls)),
  [{ behavior: 'smooth', block: 'start' }],
  'calendar action should scroll to the live calendar widget'
);
assert.equal(page.toastCalls.length, 0, 'calendar action should resolve without an error toast');

console.log('PASS batch_63_dev_03_event_calendar_open_check');
