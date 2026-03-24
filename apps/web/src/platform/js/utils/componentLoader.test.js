const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadComponentLoader({ fetchImpl, target }) {
  const source = fs.readFileSync(path.join(__dirname, 'componentLoader.js'), 'utf8');
  const createdScripts = [];
  const document = {
    querySelector(selector) {
      return selector === '#target' ? target : null;
    },
    createElement(tagName) {
      assert.equal(tagName, 'script');
      const scriptNode = {
        attributes: [],
        textContent: '',
        setAttribute(name, value) {
          this.attributes.push({ name, value });
          this[name] = value;
        },
      };
      createdScripts.push(scriptNode);
      return scriptNode;
    },
  };

  const sandbox = {
    console,
    document,
    fetch: fetchImpl,
    window: {},
  };
  sandbox.window.window = sandbox.window;
  sandbox.globalThis = sandbox;

  const transformed = source.replace(/export\s+/g, '');
  vm.createContext(sandbox);
  vm.runInContext(`${transformed}\nthis.loadComponent = loadComponent;`, sandbox, {
    filename: 'componentLoader.js',
  });

  return { loadComponent: sandbox.loadComponent, createdScripts };
}

test('loadComponent activates injected inline scripts after mounting HTML', async () => {
  const inlineScript = {
    attributes: [{ name: 'data-role', value: 'widget-controller' }],
    textContent: 'window.__copilotBooted = true;',
    parentNode: {
      replaceChild(nextScript, currentScript) {
        target.replacedScript = { nextScript, currentScript };
      },
    },
  };
  const target = {
    innerHTML: '',
    replacedScript: null,
    querySelectorAll(selector) {
      return selector === 'script' ? [inlineScript] : [];
    },
  };
  const { loadComponent, createdScripts } = loadComponentLoader({
    target,
    fetchImpl: async () => ({
      ok: true,
      async text() {
        return '<section>widget</section><script data-role="widget-controller">window.__copilotBooted = true;</script>';
      },
    }),
  });

  const success = await loadComponent('/widgets/copilot-panel.html', '#target');

  assert.equal(success, true);
  assert.equal(target.innerHTML.includes('widget'), true);
  assert.equal(createdScripts.length, 1);
  assert.equal(createdScripts[0].textContent, 'window.__copilotBooted = true;');
  assert.deepEqual(createdScripts[0].attributes, [{ name: 'data-role', value: 'widget-controller' }]);
  assert.equal(target.replacedScript?.currentScript, inlineScript);
  assert.equal(target.replacedScript?.nextScript, createdScripts[0]);
});
