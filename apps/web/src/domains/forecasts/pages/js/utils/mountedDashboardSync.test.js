const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadSync(overrides = {}) {
  const source = fs.readFileSync(path.join(__dirname, 'mountedDashboardSync.js'), 'utf8');
  const heroSection = { style: {} };
  const mainHeroSection = { style: {} };
  const dispatchedEvents = [];

  const windowObject = {
    FINANCECOPILOT_LIVE_EVENT: 'financecopilot:test-refresh',
    getLiveDashboardData() {
      return {
        data: {
          story: {
            headline: 'Brief of the day'
          }
        }
      };
    },
    dispatchEvent(event) {
      dispatchedEvents.push(event);
    },
    document: {
      getElementById(id) {
        if (id === 'heroSection') return heroSection;
        if (id === 'mainHeroSection') return mainHeroSection;
        return null;
      }
    },
    ...overrides
  };

  function CustomEvent(type, init = {}) {
    this.type = type;
    this.detail = init.detail;
  }

  windowObject.CustomEvent = windowObject.CustomEvent || CustomEvent;

  const sandbox = {
    window: windowObject,
    globalThis: windowObject,
    CustomEvent: windowObject.CustomEvent,
    console
  };

  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: 'mountedDashboardSync.js' });

  return {
    windowObject,
    heroSection,
    mainHeroSection,
    dispatchedEvents
  };
}

test('syncMountedDashboardUI replays live data and restores the hero entry point', () => {
  const { windowObject, heroSection, mainHeroSection, dispatchedEvents } = loadSync();

  const result = windowObject.syncMountedDashboardUI();

  assert.equal(dispatchedEvents.length, 1);
  assert.equal(dispatchedEvents[0].type, 'financecopilot:test-refresh');
  assert.deepEqual(dispatchedEvents[0].detail, {
    data: {
      story: {
        headline: 'Brief of the day'
      }
    }
  });
  assert.equal(heroSection.style.display, 'block');
  assert.equal(mainHeroSection.style.display, 'none');
  assert.equal(result.eventName, 'financecopilot:test-refresh');
});

test('syncMountedDashboardUI skips dispatch cleanly when live helpers are absent', () => {
  const { windowObject, heroSection, mainHeroSection, dispatchedEvents } = loadSync({
    FINANCECOPILOT_LIVE_EVENT: undefined,
    getLiveDashboardData: undefined,
    dispatchEvent: undefined
  });

  const result = windowObject.syncMountedDashboardUI();

  assert.equal(dispatchedEvents.length, 0);
  assert.equal(result.eventName, 'financecopilot:live-dashboard-updated');
  assert.equal(Object.keys(result.payload).length, 0);
  assert.equal(heroSection.style.display, 'block');
  assert.equal(mainHeroSection.style.display, 'none');
});
