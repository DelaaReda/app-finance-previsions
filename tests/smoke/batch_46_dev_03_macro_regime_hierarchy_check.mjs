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

function createConnectorContext() {
  const fetchCalls = [];
  const fixture = {
    ok: true,
    data: {
      generated_at: '2026-03-11T05:10:00.000Z',
      levels: [
        {
          scope: 'world',
          regime: 'expansion',
          confidence: 0.84,
          summary: 'Global growth remains resilient.',
          drivers: ['Disinflation trend', 'Services demand'],
          risks: ['Shipping bottlenecks'],
        },
        {
          scope: 'continent',
          entity: 'Europe',
          display_name: 'Europe',
          regime: 'slowdown',
          confidence: 0.57,
          summary: 'Europe is softening after weaker industrial data.',
          drivers: ['ECB sensitivity', 'Industrial slowdown'],
          risks: ['Energy inflation'],
        },
        {
          scope: 'country',
          entity: 'Canada',
          display_name: 'Canada',
          regime: 'recovery',
          confidence: 0.71,
          summary: 'Canada benefits from stabilizing credit conditions.',
          drivers: ['Housing stabilization', 'Commodity support'],
          risks: ['Household leverage'],
        },
      ],
      consistency: {
        has_contradictions: true,
        pairs: [
          {
            summary: 'Europe slowdown is diverging from the world expansion baseline.',
          },
        ],
      },
      narrative: {
        summary: 'The hierarchy remains constructive but regionally uneven.',
        regime_bias: 'selective risk-on',
      },
    },
  };

  const context = vm.createContext({
    console,
    fetch: async (url) => {
      fetchCalls.push(String(url));
      return {
        ok: true,
        async json() {
          if (String(url).includes('/forecasts/macro-regime-hierarchy')) {
            return fixture;
          }
          return { ok: true, data: {} };
        },
      };
    },
    window: {
      addEventListener() {},
      dispatchEvent() {},
      location: { origin: 'http://localhost:8050' },
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
      body: { appendChild() {} },
    },
    setInterval() {
      return 1;
    },
    clearInterval() {},
    CustomEvent: class CustomEvent {
      constructor(type, init = {}) {
        this.type = type;
        this.detail = init.detail;
      }
    },
    Date,
    Math,
    Promise,
    Array,
    Object,
    Number,
    String,
    Boolean,
    URLSearchParams,
  });

  context.window.window = context.window;
  context.window.document = context.document;
  context.window.fetch = context.fetch;
  context.window.CustomEvent = context.CustomEvent;

  return { context, fetchCalls };
}

function createTextNode(initialText = '', initialClassName = '') {
  return {
    textContent: initialText,
    className: initialClassName,
  };
}

function createMacroCard(scope) {
  const nodes = {
    '[data-role="macro-confidence"]': createTextNode('', 'macro-confidence'),
    '[data-role="macro-regime"]': createTextNode('', 'regime-badge'),
    '[data-role="macro-label"]': createTextNode(''),
    '[data-role="macro-summary"]': createTextNode(''),
    '[data-role="macro-drivers"]': createTextNode(''),
    '[data-role="macro-risks"]': createTextNode(''),
  };

  return {
    dataset: { scope },
    nodes,
    querySelector(selector) {
      return nodes[selector] || null;
    },
  };
}

function createWidget() {
  const cards = new Map([
    ['world', createMacroCard('world')],
    ['continent', createMacroCard('continent')],
    ['country', createMacroCard('country')],
  ]);

  const widgetNodes = {
    '[data-role="macro-consistency-icon"]': createTextNode('', 'consistency-icon'),
    '[data-role="macro-consistency-text"]': createTextNode(''),
    '[data-role="macro-insight-text"]': createTextNode(''),
    '[data-role="macro-timestamp"]': createTextNode(''),
  };

  return {
    cards,
    querySelector(selector) {
      const scopeMatch = selector.match(/^\[data-role="macro-card"\]\[data-scope="([^"]+)"\]$/);
      if (scopeMatch) {
        return cards.get(scopeMatch[1]) || null;
      }
      return widgetNodes[selector] || null;
    },
  };
}

function createAppContext(widget) {
  const fixtureNow = '2026-03-11T05:20:00.000Z';
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
    Math,
    Promise,
    Array,
    Object,
    Number,
    String,
    Boolean,
    Date: DateShim,
  });

  const bootstrap = `
    var liveDataMeta = {};
    var window = {};
    var document = {
      querySelector(selector) {
        if (selector === '.macro-regime-cards') return globalThis.__macroWidget;
        return null;
      }
    };
    ${extractFunctionSource(appSource, 'isObject')}
    ${extractFunctionSource(appSource, 'toFiniteNumber')}
    ${extractFunctionSource(appSource, 'toString')}
    ${extractFunctionSource(appSource, 'toArray')}
    ${extractFunctionSource(appSource, 'formatRelativeTime')}
    ${extractFunctionSource(appSource, 'renderMacroRegimeCardsWidget')}
    globalThis.batch46Smoke = { renderMacroRegimeCardsWidget };
  `;

  context.__macroWidget = widget;
  vm.runInContext(bootstrap, context, { filename: appPath });
  return context;
}

const { context: connectorContext, fetchCalls } = createConnectorContext();
vm.runInContext(connectorSource, connectorContext, { filename: connectorPath });

const hierarchyPayload = await connectorContext.window.FinanceAPI.getMacroRegimeHierarchy({
  country: 'CA',
  continent: 'North America',
  horizon: '6m',
});

assert.deepEqual(fetchCalls, [
  'http://localhost:8050/api/forecasts/macro-regime-hierarchy?country=CA&continent=North+America&horizon=6m',
]);
assert.equal(hierarchyPayload.levels.length, 3);
assert.equal(hierarchyPayload.consistency.has_contradictions, true);

const widget = createWidget();
const appContext = createAppContext(widget);
appContext.liveDataMeta = { macroRegimeHierarchy: hierarchyPayload };
vm.runInContext('batch46Smoke.renderMacroRegimeCardsWidget()', appContext);

const worldCard = widget.cards.get('world');
const continentCard = widget.cards.get('continent');
const countryCard = widget.cards.get('country');

assert.equal(worldCard.nodes['[data-role="macro-label"]'].textContent, 'World');
assert.equal(worldCard.nodes['[data-role="macro-confidence"]'].textContent, '84%');
assert.equal(worldCard.nodes['[data-role="macro-regime"]'].className, 'regime-badge expansion');

assert.equal(continentCard.nodes['[data-role="macro-label"]'].textContent, 'Europe');
assert.equal(continentCard.nodes['[data-role="macro-confidence"]'].className, 'macro-confidence medium');
assert.equal(
  continentCard.nodes['[data-role="macro-drivers"]'].textContent,
  'ECB sensitivity • Industrial slowdown'
);

assert.equal(countryCard.nodes['[data-role="macro-label"]'].textContent, 'Canada');
assert.equal(countryCard.nodes['[data-role="macro-regime"]'].textContent, 'Recovery');

assert.equal(
  widget.querySelector('[data-role="macro-consistency-text"]').textContent,
  'Cross-level consistency: Europe slowdown is diverging from the world expansion baseline.'
);
assert.equal(
  widget.querySelector('[data-role="macro-consistency-icon"]').className,
  'consistency-icon warning'
);
assert.match(
  widget.querySelector('[data-role="macro-insight-text"]').textContent,
  /Hierarchical model confidence: 71% average\./
);
assert.equal(
  widget.querySelector('[data-role="macro-timestamp"]').textContent,
  'Updated 10m ago'
);

console.log('PASS batch_46_dev_03_macro_regime_hierarchy_check');
