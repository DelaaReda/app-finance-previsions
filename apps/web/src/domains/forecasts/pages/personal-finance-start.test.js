const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const pagePath = path.join(__dirname, 'personal-finance-start.html');
const source = fs.readFileSync(pagePath, 'utf8');

function extractFunction(name, nextName) {
  const startMarkers = [`function ${name}(`, `async function ${name}(`];
  const start = startMarkers
    .map((marker) => source.indexOf(marker))
    .filter((index) => index !== -1)
    .sort((a, b) => a - b)[0];
  assert.notEqual(start, -1, `missing function ${name}`);
  const nextMarkers = nextName
    ? [`function ${nextName}(`, `async function ${nextName}(`]
    : ['// Load widget when DOM is ready'];
  const end = nextMarkers
    .map((marker) => source.indexOf(marker, start + 1))
    .filter((index) => index !== -1)
    .sort((a, b) => a - b)[0];
  assert.notEqual(end, -1, `missing end marker after ${name}`);
  return source.slice(start, end).trim();
}

function createScriptNode({ attrs = [], textContent = '', onReplace } = {}) {
  const node = {
    attributes: attrs,
    textContent,
    parentNode: null,
  };
  node.parentNode = {
    replaceChild(nextScript, currentScript) {
      onReplace?.(nextScript, currentScript);
    },
  };
  return node;
}

test('injectWidgetMarkup activates embedded widget scripts after HTML injection', () => {
  const replacedScripts = [];
  const scriptNode = createScriptNode({
    attrs: [{ name: 'type', value: 'text/javascript' }],
    textContent: 'window.bootstrapCopilotPanel = function() {};',
    onReplace(nextScript) {
      replacedScripts.push(nextScript);
    },
  });

  const container = {
    innerHTML: '',
    querySelectorAll(selector) {
      return selector === 'script' ? [scriptNode] : [];
    },
  };

  const sandbox = {
    document: {
      createElement(tag) {
        return {
          tagName: tag,
          attributes: [],
          textContent: '',
          setAttribute(name, value) {
            this.attributes.push({ name, value });
          },
        };
      },
    },
  };
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    [
      extractFunction('cloneInlineScript', 'activateInlineScripts'),
      extractFunction('activateInlineScripts', 'injectWidgetMarkup'),
      extractFunction('injectWidgetMarkup', 'loadCopilotWidget'),
      'this.injectWidgetMarkup = injectWidgetMarkup;',
    ].join('\n\n'),
    sandbox,
    { filename: 'personal-finance-start.html' },
  );

  sandbox.injectWidgetMarkup(container, '<section>widget</section><script></script>');

  assert.equal(container.innerHTML, '<section>widget</section><script></script>');
  assert.equal(replacedScripts.length, 1, 'embedded script should be reinserted for execution');
  assert.deepEqual(replacedScripts[0].attributes, [{ name: 'type', value: 'text/javascript' }]);
  assert.equal(replacedScripts[0].textContent, 'window.bootstrapCopilotPanel = function() {};');
});

test('loadCopilotWidget rewires the start endpoint after widget scripts are activated', async () => {
  const fetchCalls = [];
  const container = {
    innerHTML: '',
    querySelectorAll(selector) {
      if (selector !== 'script') return [];
      return [
        createScriptNode({
          textContent: 'widget bootstrap',
          onReplace() {
            sandbox.window.loadCopilotStart = async function widgetOriginal() {
              return 'original';
            };
            sandbox.window.initCopilotPanel = function initCopilotPanel() {
              sandbox.initCalls += 1;
            };
            sandbox.window.bootstrapCopilotPanel = function bootstrapCopilotPanel() {
              sandbox.bootstrapCalls += 1;
            };
          },
        }),
      ];
    },
  };

  const sandbox = {
    initCalls: 0,
    bootstrapCalls: 0,
    fetch: async (url, options) => {
      fetchCalls.push({ url, options });
      if (url === '../components/widgets/copilot-panel.html') {
        return {
          ok: true,
          async text() {
            return '<div id="copilotPanel"></div><script>widget bootstrap</script>';
          },
        };
      }
      if (url === 'http://localhost:8050/api/judge/personal-finance/start') {
        return {
          ok: true,
          async json() {
            return {
                data: {
              freshness: '2026-03-23T20:00:00Z',
                ask: [
                  { label: 'Ask', target: '/copilot/ask' },
                  { label: 'Ask portfolio', target: '/copilot/personal-finance/ask' },
                ],
                open: [
                  { label: 'Open', target: '/copilot/open' },
                  { label: 'Open portfolio', target: '/copilot/personal-finance/open' },
                ],
              },
            };
          },
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    },
    document: {
      createElement(tag) {
        return {
          tagName: tag,
          attributes: [],
          textContent: '',
          setAttribute(name, value) {
            this.attributes.push({ name, value });
          },
        };
      },
      getElementById(id) {
        return id === 'copilot-panel-container' ? container : null;
      },
      readyState: 'complete',
    },
    window: {
      FinanceAPI: { BASE_URL: 'http://localhost:8050/api' },
      copilotState: { isLoading: false },
      location: {},
    },
    renderCopilotBrief(data) {
      sandbox.brief = data;
    },
    renderCopilotPortfolio(data) {
      sandbox.portfolio = data;
    },
    renderCopilotActions() {
      sandbox.renderActionsCalls = (sandbox.renderActionsCalls || 0) + 1;
    },
    updateCopilotLiveBadge(data) {
      sandbox.liveBadge = data;
    },
    showCopilotLoading(flag) {
      sandbox.loadingStates = [...(sandbox.loadingStates || []), flag];
    },
    showCopilotError(flag) {
      sandbox.errorStates = [...(sandbox.errorStates || []), flag];
    },
    console,
    setTimeout(fn) {
      fn();
      return 1;
    },
  };
  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(
    [
      "window.COPILOT_API_BASE = window.FinanceAPI?.BASE_URL || 'http://localhost:8050/api';",
      "window.COPILOT_NAMESPACE = 'personal-finance';",
      extractFunction('cloneInlineScript', 'activateInlineScripts'),
      extractFunction('activateInlineScripts', 'injectWidgetMarkup'),
      extractFunction('injectWidgetMarkup', 'loadCopilotWidget'),
      extractFunction('loadCopilotWidget', 'rewriteNamespaceTargets'),
      extractFunction('rewriteNamespaceTargets'),
      'this.loadCopilotWidget = loadCopilotWidget;',
    ].join('\n\n'),
    sandbox,
    { filename: 'personal-finance-start.html' },
  );

  await sandbox.loadCopilotWidget();
  await sandbox.window.loadCopilotStart();

  assert.equal(fetchCalls[0].url, '../components/widgets/copilot-panel.html');
  assert.equal(fetchCalls[1].url, 'http://localhost:8050/api/judge/personal-finance/start');
  assert.equal(sandbox.initCalls, 1, 'widget init should run after scripts activate');
  assert.equal(sandbox.bootstrapCalls, 0, 'init path should be preferred when available');
  assert.equal(sandbox.renderActionsCalls, 1, 'actions should render after data load');
    assert.equal(sandbox.brief.ask[0].target, '/personal-finance/ask');
    assert.equal(sandbox.brief.ask[1].target, '/personal-finance/ask');
    assert.equal(sandbox.brief.open[0].target, '/personal-finance');
    assert.equal(sandbox.brief.open[1].target, '/personal-finance');
  assert.deepEqual(sandbox.loadingStates, [true, false]);
  assert.deepEqual(sandbox.errorStates, [false]);
});
