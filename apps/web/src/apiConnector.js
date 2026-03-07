/**
 * Legacy compatibility shim.
 * The forecasts connector lives in domains/forecasts/contracts/apiConnector.js.
 */

(function loadCanonicalForecastsConnector() {
  const doc = window.document;
  if (!doc || typeof doc.createElement !== 'function') {
    return;
  }

  if (window.FinanceAPI) {
    return;
  }

  const currentScript = doc.currentScript;
  const currentSrc = currentScript && currentScript.src
    ? currentScript.src
    : new URL('apiConnector.js', window.location && window.location.href ? window.location.href : 'http://localhost/').href;
  const canonicalSrc = new URL('./domains/forecasts/contracts/apiConnector.js', currentSrc).href;
  const existingScripts = typeof doc.querySelectorAll === 'function'
    ? Array.from(doc.querySelectorAll('script[src]'))
    : [];

  if (existingScripts.some((node) => node && node.src === canonicalSrc)) {
    return;
  }

  const script = doc.createElement('script');
  script.src = canonicalSrc;
  script.async = false;
  script.dataset.financecopilotConnector = 'legacy-alias';
  (doc.head || doc.body || doc.documentElement).appendChild(script);
})();
