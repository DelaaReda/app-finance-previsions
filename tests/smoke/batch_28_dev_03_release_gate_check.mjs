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
  const paramsStart = source.indexOf('(', start);
  assert.notEqual(paramsStart, -1, `missing params for function ${name}`);
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
  assert.notEqual(paramsEnd, -1, `unterminated params for function ${name}`);
  const bodyStart = source.indexOf('{', paramsEnd);
  assert.notEqual(bodyStart, -1, `missing body for function ${name}`);
  return source.slice(start, bodyStart) + extractBalancedBlock(source, bodyStart);
}

function extractConstAssignment(source, name) {
  const marker = `const ${name} = `;
  const start = source.indexOf(marker);
  assert.notEqual(start, -1, `missing const ${name}`);
  const bodyStart = source.indexOf('{', start);
  assert.notEqual(bodyStart, -1, `missing body for const ${name}`);
  const body = extractBalancedBlock(source, bodyStart);
  return `${source.slice(start, bodyStart)}${body};`;
}

function createMockNode(id, { display = 'block', visibility = 'visible', rectCount = 1 } = {}) {
  return {
    id,
    isConnected: true,
    _display: display,
    _visibility: visibility,
    _rectCount: rectCount,
    offsetParent: display === 'none' || visibility === 'hidden' ? null : {},
    getClientRects() {
      return Array.from({ length: this._rectCount }, () => ({}));
    }
  };
}

function createFrontendContext() {
  const fixtureNow = '2026-03-07T23:07:31.000Z';
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
    Date: DateShim,
  });

  const bootstrap = `
    var criticalWidgetHealthOverride = null;
    var liveDataMeta = {};
    var v16State = { currentFacette: 'overview' };
    var window = {
      apiHealth: null,
      getComputedStyle(node) {
        return {
          display: node && node._display ? node._display : 'block',
          visibility: node && node._visibility ? node._visibility : 'visible'
        };
      }
    };
    var document = {
      querySelector() {
        return null;
      }
    };
    ${extractConstAssignment(appSource, 'CRITICAL_WIDGET_HEALTH_TARGETS')}
    ${extractFunctionSource(appSource, 'isObject')}
    ${extractFunctionSource(appSource, 'toFiniteNumber')}
    ${extractFunctionSource(appSource, 'toString')}
    ${extractFunctionSource(appSource, 'toArray')}
    ${extractFunctionSource(appSource, 'getCriticalWidgetHealthAgeMs')}
    ${extractFunctionSource(appSource, 'getCriticalWidgetHealthStatus')}
    ${extractFunctionSource(appSource, 'isCriticalWidgetHealthHostVisible')}
    ${extractFunctionSource(appSource, 'resolveCriticalWidgetHealthHost')}
    globalThis.batch28Smoke = {
      getCriticalWidgetHealthStatus,
      resolveCriticalWidgetHealthHost,
      isCriticalWidgetHealthHostVisible,
      CRITICAL_WIDGET_HEALTH_TARGETS
    };
  `;

  vm.runInContext(bootstrap, context, { filename: appPath });
  return context;
}

function configureScenario(context, { liveDataMeta, apiHealth, selectorMap = new Map(), currentFacette = 'overview' }) {
  context.criticalWidgetHealthOverride = null;
  context.liveDataMeta = liveDataMeta;
  context.v16State.currentFacette = currentFacette;
  context.window.apiHealth = apiHealth;
  context.document.querySelector = (selector) => selectorMap.get(selector) || null;
}

function assertState(label, context, expectedState, config) {
  configureScenario(context, config);
  const status = vm.runInContext('batch28Smoke.getCriticalWidgetHealthStatus()', context);
  const actualState = status && status.state ? status.state : null;
  assert.equal(actualState, expectedState, `${label} expected ${expectedState} got ${actualState}`);
}

function assertHeroHost(label, context, selectorMap, expectedHostId) {
  configureScenario(context, {
    liveDataMeta: {
      generatedAt: '2026-03-07T23:07:00Z',
      warnings: [],
      sources: ['live_api'],
      freshness: { lastFetchedAt: Date.parse('2026-03-07T23:07:00Z'), ttlMs: 60000 }
    },
    apiHealth: { status: 'ok', last_updates: { news: '2026-03-07T23:07:00Z' } },
    selectorMap,
  });
  const host = vm.runInContext(
    'batch28Smoke.resolveCriticalWidgetHealthHost(batch28Smoke.CRITICAL_WIDGET_HEALTH_TARGETS.hero)',
    context
  );
  assert.ok(host, `${label} should resolve a host`);
  assert.equal(host.id, expectedHostId, `${label} resolved unexpected host`);
}

const context = createFrontendContext();

assertState('nominal', context, null, {
  liveDataMeta: {
    generatedAt: '2026-03-07T23:07:00Z',
    warnings: [],
    sources: ['live_api'],
    freshness: { lastFetchedAt: Date.parse('2026-03-07T23:07:00Z'), ttlMs: 60000 }
  },
  apiHealth: { status: 'ok', last_updates: { news: '2026-03-07T23:07:00Z' } },
});

assertState('timeout', context, 'error', {
  liveDataMeta: {
    generatedAt: '2026-03-07T23:07:00Z',
    warnings: ['judge request timeout'],
    sources: ['live_api'],
    freshness: { lastFetchedAt: Date.parse('2026-03-07T23:07:00Z'), ttlMs: 60000 }
  },
  apiHealth: { status: 'ok', last_updates: { news: '2026-03-07T23:07:00Z' } },
});

assertState('incomplete-payload', context, 'degraded', {
  liveDataMeta: {
    generatedAt: '2026-03-07T23:07:00Z',
    warnings: ['partial payload missing macro block'],
    sources: ['market_fallback'],
    freshness: { lastFetchedAt: Date.parse('2026-03-07T23:07:00Z'), ttlMs: 60000 }
  },
  apiHealth: { status: 'ok', last_updates: { news: '2026-03-07T23:07:00Z' } },
});

assertState('stale-cache', context, 'stale', {
  liveDataMeta: {
    generatedAt: '2026-03-07T23:02:00Z',
    warnings: [],
    sources: ['live_api'],
    freshness: { lastFetchedAt: Date.parse('2026-03-07T23:02:00Z'), ttlMs: 60000 }
  },
  apiHealth: { status: 'ok', last_updates: { news: '2026-03-07T23:04:00Z' } },
});

assertHeroHost(
  'desktop-hero-host',
  context,
  new Map([
    ['#heroSection', createMockNode('heroSection-hidden', { display: 'none', rectCount: 0 })],
    ['#hero-glassmorphic-container .hero-glassmorphic', createMockNode('hero-glassmorphic-desktop')],
  ]),
  'hero-glassmorphic-desktop'
);

assertHeroHost(
  'compact-hero-host',
  context,
  new Map([
    ['#heroSection', createMockNode('heroSection-hidden', { display: 'none', rectCount: 0 })],
    ['#hero-glassmorphic-container .hero-glassmorphic', createMockNode('hero-glassmorphic-hidden', { visibility: 'hidden', rectCount: 0 })],
    ['#mainHeroSection', createMockNode('mainHeroSection-hidden', { display: 'none', rectCount: 0 })],
    ['#hero-what-need-container', createMockNode('hero-what-need-compact')],
  ]),
  'hero-what-need-compact'
);

console.log('PASS batch_28_dev_03_release_gate_check');
