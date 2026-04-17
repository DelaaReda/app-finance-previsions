/* Frontend Sentry bootstrap for static UI runtime */
(function () {
  var SENTRY_CDN = "https://browser.sentry-cdn.com/8.43.0/bundle.tracing.replay.min.js";
  var DEFAULT_API_BASE =
    typeof window !== "undefined" && window.location && window.location.origin
      ? window.location.origin.replace(/\/$/, "")
      : "http://3.98.20.77";
  var sdkLoadPromise = null;
  var initialized = false;

  function toNumber(value, fallback) {
    var n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    if (n < 0) return 0;
    if (n > 1) return 1;
    return n;
  }

  function getApiBase() {
    var fromWindow = window.__FINANCE_API_BASE_URL__;
    if (typeof fromWindow === "string" && fromWindow.trim()) {
      return fromWindow.trim().replace(/\/$/, "");
    }
    try {
      var fromStorage = localStorage.getItem("finance.apiBaseUrl");
      if (fromStorage && fromStorage.trim()) {
        return fromStorage.trim().replace(/\/$/, "");
      }
    } catch (err) {
      // no-op
    }
    return DEFAULT_API_BASE;
  }

  async function fetchPublicConfig() {
    var apiBase = getApiBase();
    var url = apiBase + "/api/frontend/config";
    try {
      var response = await fetch(url, {
        method: "GET",
        mode: "cors",
        cache: "no-store",
      });
      if (!response.ok) {
        return null;
      }
      var payload = await response.json();
      var sentryCfg = payload && payload.data && payload.data.sentry;
      return sentryCfg || null;
    } catch (err) {
      console.warn("[telemetry] frontend config fetch failed:", err);
      return null;
    }
  }

  function loadSentrySdk() {
    if (window.Sentry) {
      return Promise.resolve();
    }
    if (sdkLoadPromise) {
      return sdkLoadPromise;
    }
    sdkLoadPromise = new Promise(function (resolve, reject) {
      var existing = document.querySelector("script[data-finance-sentry='1']");
      if (existing) {
        existing.addEventListener("load", function () {
          resolve();
        });
        existing.addEventListener("error", function (event) {
          reject(event);
        });
        return;
      }
      var script = document.createElement("script");
      script.src = SENTRY_CDN;
      script.async = true;
      script.crossOrigin = "anonymous";
      script.dataset.financeSentry = "1";
      script.onload = function () {
        resolve();
      };
      script.onerror = function (event) {
        reject(event);
      };
      document.head.appendChild(script);
    });
    return sdkLoadPromise;
  }

  function sentryIntegrations() {
    var integrations = [];
    if (!window.Sentry) return integrations;
    if (typeof window.Sentry.browserTracingIntegration === "function") {
      integrations.push(window.Sentry.browserTracingIntegration());
    } else if (typeof window.Sentry.BrowserTracing === "function") {
      integrations.push(new window.Sentry.BrowserTracing());
    }
    if (typeof window.Sentry.replayIntegration === "function") {
      integrations.push(window.Sentry.replayIntegration());
    } else if (typeof window.Sentry.Replay === "function") {
      integrations.push(new window.Sentry.Replay());
    }
    return integrations;
  }

  function initSentry(config) {
    if (initialized || !window.Sentry) {
      return;
    }
    if (!config || !config.enabled || !config.dsn) {
      return;
    }

    window.Sentry.init({
      dsn: config.dsn,
      environment: config.environment || "production",
      release: config.release || undefined,
      tracesSampleRate: toNumber(config.traces_sample_rate, 0.2),
      replaysSessionSampleRate: toNumber(config.replays_session_sample_rate, 0.0),
      replaysOnErrorSampleRate: toNumber(config.replays_on_error_sample_rate, 1.0),
      tracePropagationTargets:
        (config.trace_propagation_targets && config.trace_propagation_targets.length
          ? config.trace_propagation_targets
          : ["localhost", "127.0.0.1", /^\/api\//]),
      ignoreErrors: [
        "ResizeObserver loop limit exceeded",
        "Script error.",
      ],
      integrations: sentryIntegrations(),
    });

    window.Sentry.setTag("app.name", "finance-copilot-frontend");
    window.Sentry.setTag("app.surface", "static-ui");
    initialized = true;
    console.log("[telemetry] Sentry frontend initialized");
  }

  function installHelpers() {
    window.triggerFrontendSentryError = function triggerFrontendSentryError() {
      throw new Error("frontend sentry debug route");
    };
  }

  async function bootstrap() {
    installHelpers();
    var cfg = await fetchPublicConfig();
    if (!cfg || !cfg.enabled || !cfg.dsn) {
      return;
    }
    try {
      await loadSentrySdk();
      initSentry(cfg);
    } catch (err) {
      console.warn("[telemetry] Sentry SDK load/init failed:", err);
    }
  }

  window.financeTelemetry = {
    bootstrap: bootstrap,
    fetchPublicConfig: fetchPublicConfig,
  };
  bootstrap();
})();
