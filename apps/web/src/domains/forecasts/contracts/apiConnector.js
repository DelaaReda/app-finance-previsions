/**
 * Finance Copilot API Connector
 * Bridges the live backend API to app.js window globals
 * Auto-refresh every 2 minutes
 */

function normalizeApiBase(value) {
  return typeof value === 'string' ? value.trim().replace(/\/+$/, '') : '';
}

function resolveApiBase(win = typeof window !== 'undefined' ? window : null) {
  const configuredBase = normalizeApiBase(
    win && typeof win === 'object'
      ? (win.FINANCECOPILOT_API_BASE || win.__FINANCECOPILOT_API_BASE || '')
      : '',
  );
  if (configuredBase) {
    return configuredBase;
  }

  const origin = normalizeApiBase(
    win && win.location && typeof win.location.origin === 'string'
      ? win.location.origin
      : '',
  );
  if (origin) {
    return `${origin}/api`;
  }

  return 'http://localhost:8050/api';
}

const API_BASE = resolveApiBase();

// Cache with TTL
const cache = {
  data: {},
  timestamps: {},
  TTL: 120000 // 2 minutes
};

function clearCacheEntry(key) {
  delete cache.data[key];
  delete cache.timestamps[key];
}

function clearCacheEntriesWithPrefix(prefix) {
  Object.keys(cache.data)
    .filter((key) => key === prefix || key.startsWith(prefix))
    .forEach((key) => clearCacheEntry(key));
}

function getResponseData(payload) {
  if (!payload) return {};
  if (typeof payload === 'object' && payload.data !== undefined) return payload.data || {};
  return payload;
}

function extractArray(payload, keys) {
  if (!payload || typeof payload !== 'object') return [];
  for (const key of keys) {
    const value = payload[key];
    if (Array.isArray(value)) return value;
  }
  return [];
}

function extractObject(payload, keys) {
  if (!payload || typeof payload !== 'object') return {};
  for (const key of keys) {
    const value = payload[key];
    if (value && typeof value === 'object' && !Array.isArray(value)) return value;
  }
  return {};
}

function isObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

async function fetchWithCache(endpoint, key) {
  const now = Date.now();
  if (cache.data[key] && (now - cache.timestamps[key]) < cache.TTL) {
    return cache.data[key];
  }
  try {
    const response = await fetch(API_BASE + endpoint);
    const data = await response.json();
    cache.data[key] = data;
    cache.timestamps[key] = now;
    return data;
  } catch (error) {
    console.warn('[API] Error fetching ' + endpoint + ':', error.message);
    return cache.data[key] || null;
  }
}

// ─── Data fetchers ────────────────────────────────────────────────────────────

function normalizeNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseIsoTimestamp(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function resolveFreshnessTimestamp(value) {
  if (!value) return null;
  if (typeof value === 'string') return parseIsoTimestamp(value);
  if (typeof value === 'object' && !Array.isArray(value)) {
    return (
      parseIsoTimestamp(value.timestamp)
      || parseIsoTimestamp(value.generated_at)
      || parseIsoTimestamp(value.generatedAt)
      || parseIsoTimestamp(value.last_update)
      || parseIsoTimestamp(value.last_success_at)
    );
  }
  return null;
}

function normalizeFreshnessStatus(value) {
  const status = String(value || '').trim().toLowerCase();
  if (!status) return '';
  if (status === 'fresh' || status === 'ok' || status === 'healthy') return 'fresh';
  if (status === 'stale' || status === 'aged' || status === 'delay' || status === 'delayed') return 'stale';
  return 'degraded';
}

async function getNewsFeed(limit) {
  if (!limit) limit = 20;
  const payload = getResponseData(await fetchWithCache('/news/feed?limit=' + limit, 'news'));
  return extractArray(payload, ['articles', 'items', 'news']);
}

async function getForecasts(limit) {
  if (!limit) limit = 20;
  const payload = getResponseData(await fetchWithCache('/forecasts?limit=' + limit, 'forecasts'));
  return extractArray(payload, ['rows', 'forecasts', 'data']) || [];
}

async function getDailyRecommendations(limit) {
  const safeLimit = Number.isFinite(Number(limit)) && Number(limit) > 0 ? Math.min(6, Math.floor(Number(limit))) : 3;
  const payload = getResponseData(await fetchWithCache(`/recommendations/daily?limit=${safeLimit}`, `recommendations_daily:${safeLimit}`));
  return payload && typeof payload === 'object' ? payload : {};
}

async function getWalkForwardScoreboard(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const horizon = String(safeParams.horizon || '').trim();
  const debug = safeParams.debug === true;

  if (horizon) {
    search.set('horizon', horizon);
  }
  if (debug) {
    search.set('debug', 'true');
  }

  const query = search.toString();
  const endpoint = `/forecasts/scoreboard${query ? `?${query}` : ''}`;
  const cacheKey = `forecasts_scoreboard:${query || 'default'}`;
  const payload = getResponseData(await fetchWithCache(endpoint, cacheKey));
  return payload && typeof payload === 'object' ? payload : {};
}

async function getGeopoliticalRiskGraph(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const limit = Number(safeParams.limit);
  const region = String(safeParams.region || '').trim();

  if (region) {
    search.set('region', region);
  }
  if (Number.isFinite(limit) && limit > 0) {
    search.set('limit', String(Math.min(20, Math.max(1, Math.floor(limit)))));
  }

  const query = search.toString();
  const endpoint = `/judge/geopolitical-risk-graph${query ? `?${query}` : ''}`;
  const cacheKey = `judge_geopolitical_risk_graph:${query || 'default'}`;
  const payload = getResponseData(await fetchWithCache(endpoint, cacheKey));
  return payload && typeof payload === 'object' ? payload : {};
}

async function getStockPrices() {
  const payload = getResponseData(await fetchWithCache('/stocks/prices?tickers=NVDA,META,AAPL,MSFT,GOOGL', 'stocks'));
  return extractObject(payload, ['prices', 'tickers', 'data']) || {};
}

async function getTopMovers() {
  const payload = getResponseData(await fetchWithCache('/stocks/top-legacy?limit=10', 'movers'));
  return payload;
}

async function getAlerts() {
  const payload = getResponseData(await fetchWithCache('/alerts', 'alerts'));
  return {
    alerts: extractArray(payload, ['alerts', 'data', 'rows']),
    generatedAt: String(payload?.generated_at || payload?.generatedAt || ''),
    suppressedCount: normalizeNumber(payload?.suppressed_count ?? payload?.suppressedCount, 0),
    queue: extractObject(payload, ['queue']) || {},
    stats: extractObject(payload, ['stats']) || {},
    pipeline: extractObject(payload, ['pipeline']) || {},
  };
}

async function getDashboardPerformance() {
  const payload = getResponseData(await fetchWithCache('/dashboard/performance', 'dashboard_performance'));
  return payload || {};
}

function normalizeCopilotContextTickers(value) {
  const values = Array.isArray(value)
    ? value
    : (typeof value === 'string' ? value.split(',') : []);
  const normalized = [];
  values.forEach((item) => {
    const ticker = String(item || '').trim().toUpperCase();
    if (ticker && !normalized.includes(ticker)) {
      normalized.push(ticker);
    }
  });
  return normalized;
}

function buildCopilotScopedEndpoint(basePath, tickers) {
  const query = normalizeCopilotContextTickers(tickers)
    .map((ticker) => `tickers=${encodeURIComponent(ticker)}`)
    .join('&');
  return {
    endpoint: query ? `${basePath}?${query}` : basePath,
    query,
  };
}

async function loadCopilotContext(tickers) {
  const { endpoint, query } = buildCopilotScopedEndpoint('/copilot/context', tickers);
  const payload = getResponseData(await fetchWithCache(endpoint, `copilot_context:${query || 'default'}`));
  const normalized = payload && typeof payload === 'object' ? { ...payload } : {};
  const copilotStart = transformCopilotStart(normalized.copilot_start || normalized.copilotStart, normalized);
  if (Object.keys(copilotStart.brief_of_day).length || copilotStart.ask.length || copilotStart.open.length) {
    normalized.copilot_start = copilotStart;
  }
  return normalized;
}

async function getCopilotContext(tickers) {
  return getCopilotStart(tickers);
}

async function getCopilotStart(tickers) {
  const { endpoint, query } = buildCopilotScopedEndpoint('/copilot/start', tickers);
  const payload = getResponseData(await fetchWithCache(endpoint, `copilot_start:${query || 'default'}`));
  const normalized = payload && typeof payload === 'object' ? { ...payload } : {};
  const copilotStart = transformCopilotStart(
    normalized.copilot_start || normalized.copilotStart || normalized,
    normalized
  );

  if (Object.keys(copilotStart.brief_of_day).length || copilotStart.ask.length || copilotStart.open.length) {
    normalized.copilot_start = copilotStart;
    return normalized;
  }

  // Fallback: load daily brief directly if copilot start is empty
  try {
    const dailyBrief = await getDailyBrief();
    if (dailyBrief && Object.keys(dailyBrief).length > 0) {
      normalized.brief_of_day = dailyBrief;
      normalized.brief = dailyBrief;
      return normalized;
    }
  } catch (error) {
    console.warn('[Copilot] getDailyBrief fallback failed:', error?.message || error);
  }

  return loadCopilotContext(tickers);
}

async function getDailyBrief() {
  const payload = getResponseData(await fetchWithCache('/brief/daily', 'brief_daily'));
  return payload || {};
}

async function getSectorPerformanceData() {
  const payload = getResponseData(await fetchWithCache('/dashboard/allocation', 'dashboard_allocation'));
  if (!payload || typeof payload !== 'object') {
    return {};
  }
  return { sectors: extractArray(payload, ['sectors', 'data', 'sector_data']) };
}

async function getLlmJudgeSnapshot() {
  try {
    const response = await fetch(API_BASE + '/llm/judge/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: "Quel est le jugement de marché le plus fiable pour un investisseur aujourd'hui ?",
        tickers: 'NVDA,META,AAPL,MSFT,GOOGL',
        max_er: 0.08,
        min_conf: 0.6
      })
    });
    if (!response.ok) return null;
    return getResponseData(await response.json());
  } catch (error) {
    console.warn('[API] Error fetching llm judge:', error.message);
    return null;
  }
}

async function getHealth() {
  const payload = getResponseData(await fetchWithCache('/health', 'health'));
  return payload && typeof payload === 'object' ? payload : null;
}

async function getStatus() {
  const payload = getResponseData(await fetchWithCache('/status', 'status'));
  if (payload && typeof payload === 'object' && Object.keys(payload).length > 0) {
    return payload;
  }
  return await getHealth();
}

async function getIngestionHealth() {
  const payload = getResponseData(await fetchWithCache('/ingestion/health', 'ingestion-health'));
  return payload && typeof payload === 'object' ? payload : null;
}

async function getGlobalSignalMesh() {
  const payload = getResponseData(await fetchWithCache('/forecasts/global-signal-mesh', 'global-signal-mesh'));
  if (!payload || typeof payload !== 'object') return null;

  const provenance = isObject(payload.provenance) ? payload.provenance : {};
  const sla = isObject(provenance.sla) ? provenance.sla : {};
  const cacheMeta = isObject(payload.cache) ? payload.cache : {};
  const ttlSeconds = normalizeNumber(sla.target_max_age_seconds || cacheMeta.ttl_seconds, 0);
  const normalizedStatus = normalizeFreshnessStatus(
    payload.status
      || sla.freshness_status
      || sla.status
      || (isObject(payload.freshness) ? payload.freshness.status : '')
  );
  const updatedAt = String(
    sla.updated_at || payload.freshness || payload.generated_at || payload.generatedAt || '',
  ).trim();

  return {
    ...payload,
    status: normalizedStatus,
    freshness: {
      ...sla,
      updated_at: updatedAt,
      ttl_seconds: ttlSeconds > 0 ? ttlSeconds : 0,
    },
  };
}

async function getFinalGlobalForecastGate(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const country = String(safeParams.country || '').trim();
  const horizon = String(safeParams.horizon || '').trim();
  const debug = safeParams.debug === true;

  if (country) search.set('country', country);
  if (horizon) search.set('horizon', horizon);
  if (debug) search.set('debug', 'true');

  const query = search.toString();
  const payload = getResponseData(
    await fetchWithCache(
      `/forecasts/final-global-gate${query ? `?${query}` : ''}`,
      `final-global-forecast-gate:${query || 'default'}`
    )
  );
  if (!payload || typeof payload !== 'object') return null;

  const proofs = isObject(payload.proofs) ? payload.proofs : {};
  const finalGateProof = isObject(proofs.FINAL_GLOBAL_FORECAST_GATE_PROOF)
    ? proofs.FINAL_GLOBAL_FORECAST_GATE_PROOF
    : {};
  const cacheMeta = isObject(payload.cache) ? payload.cache : {};
  const freshnessSource = isObject(payload.freshness) ? payload.freshness : {};
  const ttlSeconds = normalizeNumber(
    freshnessSource.ttl_seconds || finalGateProof.ttl_seconds || cacheMeta.ttl_seconds,
    0,
  );
  const normalizedStatus = normalizeFreshnessStatus(
    payload.status
      || finalGateProof.status
      || freshnessSource.status
  );
  const updatedAt = String(
    finalGateProof.updated_at
      || payload.generated_at
      || payload.freshness
      || payload.generatedAt
      || '',
  ).trim();

  return {
    ...payload,
    status: normalizedStatus || String(payload.status || '').trim().toLowerCase(),
    freshness: {
      ...freshnessSource,
      updated_at: updatedAt,
      ttl_seconds: ttlSeconds > 0 ? ttlSeconds : 0,
    },
  };
}

async function getMacroRegimeHierarchy(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const country = String(safeParams.country || 'US').trim();
  const continent = String(safeParams.continent || '').trim();
  const horizon = String(safeParams.horizon || '3m').trim();
  const debug = safeParams.debug === true;

  if (country) search.set('country', country);
  if (continent) search.set('continent', continent);
  if (horizon) search.set('horizon', horizon);
  if (debug) search.set('debug', 'true');

  const query = search.toString();
  const payload = getResponseData(
    await fetchWithCache(`/forecasts/macro-regime-hierarchy${query ? `?${query}` : ''}`, `macro-regime-hierarchy:${query || 'default'}`)
  );
  return payload && typeof payload === 'object' ? payload : null;
}

async function getEventImpactHorizonMatrix(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const eventType = String(safeParams.event_type || safeParams.eventType || '').trim();
  const limit = Number(safeParams.limit);

  if (eventType) search.set('event_type', eventType);
  if (Number.isFinite(limit) && limit > 0) {
    search.set('limit', String(Math.min(10, Math.max(1, Math.floor(limit)))));
  }

  const query = search.toString();
  const endpoint = `/judge/event-impact-horizon-matrix${query ? `?${query}` : ''}`;
  const cacheKey = `judge_event_impact_horizon_matrix:${query || 'default'}`;
  const payload = getResponseData(await fetchWithCache(endpoint, cacheKey));
  return payload && typeof payload === 'object' ? payload : null;
}

async function getPolicyImpact(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const jurisdiction = String(safeParams.jurisdiction || '').trim();
  const status = String(safeParams.status || '').trim();
  const sector = String(safeParams.sector || '').trim();
  const limit = Number(safeParams.limit);
  const debug = safeParams.debug === true;

  if (jurisdiction) search.set('jurisdiction', jurisdiction);
  if (status) search.set('status', status);
  if (sector) search.set('sector', sector);
  if (Number.isFinite(limit) && limit > 0) {
    search.set('limit', String(Math.min(25, Math.max(1, Math.floor(limit)))));
  }
  if (debug) search.set('debug', 'true');

  const query = search.toString();
  const endpoint = `/forecasts/policy-impact${query ? `?${query}` : ''}`;
  const cacheKey = `policy-impact:${query || 'default'}`;
  const payload = getResponseData(await fetchWithCache(endpoint, cacheKey));
  return payload && typeof payload === 'object' ? payload : null;
}

async function getInsiderBehavior(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const tickers = Array.isArray(safeParams.tickers)
    ? safeParams.tickers
    : (typeof safeParams.tickers === 'string' ? safeParams.tickers.split(',') : []);
  const limit = Number(safeParams.limit);
  const debug = safeParams.debug === true;

  tickers
    .map((ticker) => String(ticker || '').trim().toUpperCase())
    .filter(Boolean)
    .forEach((ticker) => search.append('tickers', ticker));

  if (Number.isFinite(limit) && limit > 0) {
    search.set('limit', String(Math.min(25, Math.max(1, Math.floor(limit)))));
  }
  if (debug) {
    search.set('debug', 'true');
  }

  const query = search.toString();
  const endpoint = `/forecasts/insider-behavior${query ? `?${query}` : ''}`;
  const cacheKey = `insider-behavior:${query || 'default'}`;
  const payload = getResponseData(await fetchWithCache(endpoint, cacheKey));
  return payload && typeof payload === 'object' ? payload : null;
}

async function getDashboardKPIs() {
  const payload = await fetchWithCache('/dashboard/kpis', 'kpis');
  if (!payload) return null;
  const data = payload.data || payload;
  if (!data || typeof data !== 'object') return null;
  return {
    ok: payload.ok ?? true,
    data,
    freshness: payload.freshness || data.generated_at || data.generatedAt,
    source: data.source || payload.source || ['dashboard-kpis']
  };
}

async function getPortfolioSummary() {
  const payload = await fetchWithCache('/dashboard/portfolio-summary', 'portfolio-summary');
  if (!payload) return null;
  return {
    ok: payload.ok ?? true,
    data: payload.data || {},
    freshness: payload.freshness || payload.generated_at || payload.data?.generated_at || new Date().toISOString(),
    source: payload.data?.source || ['portfolio-summary']
  };
}

async function getPortfolios() {
  const payload = getResponseData(await fetchWithCache('/portfolios', 'portfolios'));
  return extractArray(payload, ['portfolios', 'items', 'data']);
}

async function getPortfolioRiskProfile(portfolioId, options = {}) {
  const safeOptions = options && typeof options === 'object' ? options : {};
  let resolvedPortfolioId = String(portfolioId || safeOptions.portfolioId || '').trim();
  if (!resolvedPortfolioId) {
    const portfolios = await getPortfolios();
    resolvedPortfolioId = portfolios[0] && portfolios[0].id ? String(portfolios[0].id).trim() : '';
  }
  if (!resolvedPortfolioId) {
    return null;
  }

  const benchmark = String(safeOptions.benchmark || 'SPY').trim().toUpperCase() || 'SPY';
  const startDate = String(safeOptions.startDate || safeOptions.start_date || '').trim();
  const endDate = String(safeOptions.endDate || safeOptions.end_date || '').trim();
  const params = new URLSearchParams({ benchmark });
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);

  const endpoint = `/portfolios/${encodeURIComponent(resolvedPortfolioId)}/risk-profile?${params.toString()}`;
  const cacheKey = `portfolio-risk-profile-${resolvedPortfolioId}-${benchmark}-${startDate || 'auto'}-${endDate || 'auto'}`;
  const payload = await fetchWithCache(endpoint, cacheKey);
  if (!payload) return null;
  const data = getResponseData(payload);
  if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
    return null;
  }

  return {
    ok: payload.ok ?? true,
    status: payload.status || data.status || 'ok',
    data,
    freshness: payload.freshness || data.freshness || data.generated_at || new Date().toISOString(),
    source: data.source || payload.source || ['portfolio-risk-profile'],
    error: payload.error || data.error || null,
    portfolioId: resolvedPortfolioId
  };
}

function titleCaseLabel(value, fallback = 'Unknown') {
  const normalized = String(value || '').trim().replace(/[_-]+/g, ' ');
  if (!normalized) return fallback;
  return normalized
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function buildPortfolioStateSummary(state) {
  const safeState = state && typeof state === 'object' ? state : {};
  const parts = [];
  const horizon = String(safeState.horizon || '').trim();
  const conviction = String(safeState.conviction || '').trim();
  const riskTolerance = String(safeState.risk_tolerance || safeState.riskTolerance || '').trim();

  if (horizon) {
    parts.push(`${horizon.toUpperCase()} horizon`);
  }
  if (conviction) {
    parts.push(`${titleCaseLabel(conviction)} conviction`);
  }
  if (riskTolerance) {
    parts.push(`${titleCaseLabel(riskTolerance)} risk`);
  }

  return parts.join(' | ');
}

function mapPortfolioHealthScore(riskLevel, status) {
  const normalizedRisk = String(riskLevel || '').trim().toLowerCase();
  const normalizedStatus = String(status || '').trim().toLowerCase();
  let score = 68;
  if (normalizedRisk === 'low') {
    score = 84;
  } else if (normalizedRisk === 'high') {
    score = 52;
  }
  if (normalizedStatus === 'degraded') {
    score -= 8;
  }
  return Math.max(0, Math.min(100, score));
}

function transformPortfolioHealth(payload) {
  if (!payload || typeof payload !== 'object') return null;

  const data = getResponseData(payload);
  const portfolio = extractObject(data, ['portfolio']);
  const risk = extractObject(data, ['risk']);
  const stats = extractObject(data, ['stats']);
  const state = extractObject(portfolio, ['state']);
  const warnings = extractArray(data, ['warnings']);
  const why = extractArray(data, ['why']);
  const riskLevel = String(risk.level || data.risk_level || 'medium').trim().toLowerCase() || 'medium';
  const largestWeight = normalizeNumber(stats.largest_position_weight, 0);
  const largestWeightPct = Math.max(0, Math.min(100, Math.round(largestWeight * 100)));
  const largestTicker = String(stats.largest_position_ticker || '').trim().toUpperCase();
  const stateSummary = buildPortfolioStateSummary(state);
  const status = String(payload.status || data.status || 'ok').trim().toLowerCase() || 'ok';
  const suggestion = String(
    warnings[0]
      || why[0]
      || (stateSummary ? `Saved state synced: ${stateSummary}.` : 'Portfolio risk profile synced.'),
  ).trim();

  let allocationLabel = 'Largest saved weight unavailable';
  if (largestTicker && largestWeightPct > 0) {
    allocationLabel = `Largest saved weight: ${largestTicker} ${largestWeightPct}%`;
  } else if (stats.weights_source === 'equal_weight_fallback') {
    allocationLabel = 'Equal-weight fallback in use';
  }

  return {
    portfolioId: String(portfolio.id || payload.portfolioId || '').trim() || null,
    portfolioName: String(portfolio.name || '').trim() || 'Portfolio',
    overall: mapPortfolioHealthScore(riskLevel, status),
    suggestion,
    riskLabel: titleCaseLabel(riskLevel, 'Medium'),
    riskTone: riskLevel === 'low' ? 'positive' : riskLevel === 'high' ? 'warning' : 'neutral',
    stateSummary: stateSummary || 'Saved portfolio state unavailable',
    allocationLabel,
    allocationProgress: largestWeightPct,
    benchmark: String(data.benchmark || 'SPY').trim().toUpperCase() || 'SPY',
    updatedAt: payload.freshness || data.freshness || data.generated_at || new Date().toISOString(),
    status,
    riskProfile: String(data.risk_profile || 'balanced').trim().toLowerCase() || 'balanced',
    confidence: Math.max(0, Math.min(100, Math.round(normalizeNumber(data.confidence, 0.45) * 100))),
    warnings,
    why,
    source: Array.isArray(data.source) ? data.source : (Array.isArray(payload.source) ? payload.source : ['portfolio-risk-profile'])
  };
}

async function getPortfolioHealth(portfolioId, options = {}) {
  const payload = await getPortfolioRiskProfile(portfolioId, options);
  return payload ? transformPortfolioHealth(payload) : null;
}

async function getMarketDriversSnapshot() {
  const payload = await fetchWithCache('/dashboard/market-drivers', 'market-drivers');
  if (!payload) return null;
  return {
    ok: payload.ok ?? true,
    data: getResponseData(payload),
    freshness: payload.freshness || payload.generated_at || payload.data?.generated_at || new Date().toISOString(),
    source: payload.data?.source || payload.source || ['dashboard-market-drivers']
  };
}

async function getJudgeAnalysis(limit) {
  if (!limit) limit = 5;
  const payload = await fetchWithCache('/judge?limit=' + limit, `judge:${limit}`);
  if (!payload) return {};
  return payload.data && typeof payload.data === 'object' ? payload.data : payload;
}

async function getCopilotDecisionJournal(params = {}) {
  const safeParams = params && typeof params === 'object' ? params : {};
  const search = new URLSearchParams();
  const limit = Number(safeParams.limit);
  const ticker = String(safeParams.ticker || safeParams.symbol || '').trim().toUpperCase();
  const verdict = String(safeParams.verdict || '').trim().toLowerCase();
  const horizon = String(safeParams.horizon || '').trim();

  if (Number.isFinite(limit) && limit > 0) {
    search.set('limit', String(Math.min(50, Math.max(1, Math.floor(limit)))));
  }
  if (ticker) {
    search.set('tickers', ticker);
  }
  if (verdict) {
    search.set('verdict', verdict);
  }
  if (horizon) {
    search.set('horizon', horizon);
  }

  const query = search.toString();
  const endpoint = `/copilot/decision-journal${query ? `?${query}` : ''}`;
  const payload = getResponseData(await fetchWithCache(endpoint, `copilot_decision_journal:${query || 'default'}`));
  return payload && typeof payload === 'object' ? payload : {};
}

async function executePaperTrade(payload = {}) {
  const body = payload && typeof payload === 'object' ? payload : {};

  try {
    const response = await fetch(API_BASE + '/copilot/paper-trades/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const responsePayload = await response.json();
    if (!response.ok) {
      return {
        ok: false,
        error: responsePayload?.detail || responsePayload?.message || 'paper_trade_execute_failed',
        data: responsePayload?.data || null,
      };
    }

    clearCacheEntriesWithPrefix('copilot_decision_journal:');
    return {
      ok: responsePayload?.ok ?? true,
      data: responsePayload?.data || responsePayload,
    };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'paper_trade_execute_failed',
      data: null,
    };
  }
}

async function askCopilot(question, tickers) {
  if (!tickers) tickers = [];
  try {
    const response = await fetch(API_BASE + '/copilot/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, tickers, max_sources: 5 })
    });
    const payload = await response.json();
    const data = getResponseData(payload);
    const normalizedData = data && typeof data === 'object' ? { ...data } : {};
    const memo = normalizeAskMemoPayload(
      normalizedData.memo && typeof normalizedData.memo === 'object'
        ? normalizedData.memo
        : normalizedData
    );

    return {
      ...payload,
      data: {
        ...normalizedData,
        memo,
        answer: normalizedData.answer || memo.summary || normalizedData.reasoning || '',
        reasoning: normalizedData.reasoning || normalizedData.why || memo.main_reasons || [],
        verdict: normalizedData.verdict || normalizedData.action || memo.verdict || '',
        confidence: normalizedData.confidence ?? memo.confidence,
        risk_level: normalizedData.risk_level || normalizedData.riskLevel || memo.risk_level || (memo.risk && memo.risk.level) || '',
        risk_caveat: normalizedData.risk_caveat || memo.risk_caveat || (memo.risk && memo.risk.caveat) || '',
        sources: Array.isArray(normalizedData.sources) && normalizedData.sources.length ? normalizedData.sources : memo.sources,
        freshness: normalizedData.freshness || memo.freshness || normalizedData.generated_at || '',
        generated_at: normalizedData.generated_at || normalizedData.generatedAt || memo.generated_at || memo.freshness || '',
        quality_status: normalizedData.quality_status || normalizedData.qualityStatus || (memo.degraded ? 'degraded' : ''),
        degraded_reason: normalizedData.degraded_reason || normalizedData.degradedReason || memo.degraded_reason || memo.degradedReason || '',
        context_influence: normalizedData.context_influence || normalizedData.contextInfluence || null,
        contextInfluence: normalizedData.contextInfluence || normalizedData.context_influence || null
      }
    };
  } catch (error) {
    return { data: { answer: 'Service temporarily unavailable', sources: [] } };
  }
}

function normalizeAskMemoPayload(payload) {
  const source = payload && typeof payload === 'object' ? payload : {};
  if (!Object.keys(source).length) {
    return {};
  }

  const normalizedAlerting = normalizeAlertingRichPayload(source, {
    opportunityKeys: ['top_opportunities', 'topOpportunities', 'opportunities', 'top_signals', 'signals'],
  });
  const mainReasons = normalizeConnectorStringList(
    source.main_reasons || source.mainReasons || source.reasons || source.drivers || source.why
  );

  return {
    ...source,
    summary: source.summary || source.answer || source.thesis || source.overview || '',
    verdict: source.verdict || source.action || source.recommendation || '',
    market_regime: source.market_regime || source.marketRegime || source.regime || '',
    horizon: source.horizon || '',
    top_opportunities: normalizedAlerting.topOpportunities,
    top_risks: normalizedAlerting.topRisks,
    top_risk_items: normalizedAlerting.topRiskItems,
    topRiskItems: normalizedAlerting.topRiskItems,
    main_reasons: mainReasons,
    next_steps: normalizeConnectorStringList(source.next_steps || source.nextSteps),
    invalidation: normalizeConnectorStringList(source.invalidation),
    freshness: normalizedAlerting.freshness,
    generated_at: source.generated_at || source.generatedAt || normalizedAlerting.freshness || '',
    sources: normalizedAlerting.sources,
    source: normalizedAlerting.sources,
    suppressed_risks: normalizedAlerting.suppressedRisks,
    suppressedRisks: normalizedAlerting.suppressedRisks,
    alerting_metadata: normalizedAlerting.alertingMetadata,
    alertingMetadata: normalizedAlerting.alertingMetadata,
    degraded: normalizedAlerting.degraded,
    degraded_reason: normalizedAlerting.degradedReason
  };
}

async function searchUniverse(query, options) {
  if (!query) {
    return {
      query: '',
      results: { stocks: [], news: [], briefs: [], forecasts: [] },
      total: 0,
      search_metadata: { types_searched: [], sort_by: 'relevance' }
    };
  }

  const safeOptions = options && typeof options === 'object' ? options : {};
  const limit = safeOptions.limit
    ? Math.min(100, Math.max(1, Math.floor(Number(safeOptions.limit) || 20)))
    : 20;
  const type = (safeOptions.type || safeOptions.types || 'all').toString().trim() || 'all';
  const sortBy = (safeOptions.sortBy || safeOptions.sort_by || 'relevance').toString().trim() || 'relevance';
  const tickersInput = Array.isArray(safeOptions.tickers)
    ? safeOptions.tickers.filter(Boolean).map((ticker) => String(ticker).trim().toUpperCase()).filter(Boolean).join(',')
    : (safeOptions.tickers || '').toString().trim();

  const params = new URLSearchParams({
    q: String(query).trim(),
    type,
    limit: String(limit),
    sort_by: sortBy
  });
  if (tickersInput) {
    params.set('tickers', tickersInput);
  }

  const endpoint = `/search/universal?${params.toString()}`;
  const cacheKey = `search-universal-${String(query).trim().toLowerCase()}-${type}-${limit}-${sortBy}-${tickersInput || 'all'}`;
  const payload = getResponseData(await fetchWithCache(endpoint, cacheKey));
  if (!payload || typeof payload !== 'object') {
    return {
      query: String(query).trim(),
      results: { stocks: [], news: [], briefs: [], forecasts: [] },
      total: 0,
      search_metadata: { types_searched: [type] }
    };
  }

  const data = payload.data ? payload.data : payload;
  const results = data.results || {};
  const safeResults = {
    stocks: Array.isArray(results.stocks) ? results.stocks : [],
    news: Array.isArray(results.news) ? results.news : [],
    briefs: Array.isArray(results.brefs) ? results.brefs : (Array.isArray(results.briefs) ? results.briefs : []),
    forecasts: Array.isArray(results.forecasts) ? results.forecasts : []
  };

  return {
    query: data.query || String(query).trim(),
    results: safeResults,
    total: Number(data.total) || 0,
    search_metadata: data.search_metadata || { types_searched: [type], tickers_filtered: tickersInput || null, sort_by: sortBy }
  };
}

// ─── Transform API data → app.js format ──────────────────────────────────────

function formatNewsEffect(item, sentimentEffect) {
  const rawEffect = item.effect_percent ?? item.change_percent ?? item.market_effect_pct;
  const fallbackEffect = normalizeNumber(item.score, 50) / 25;
  const magnitude = Math.max(0.1, Math.abs(normalizeNumber(rawEffect, fallbackEffect)));
  return `${sentimentEffect}${magnitude.toFixed(1)}%`;
}

function transformNewsItem(item) {
  const sentimentEffect = item.sentiment === 'positive' ? '+' : item.sentiment === 'negative' ? '-' : '~';
  const score = item.score != null ? item.score : 50;
  const impact = (score / 10).toFixed(1);
  const published = item.published_at || item.date || '';
  let timeAgo = 'Recently';
  if (published) {
    const diff = Date.now() - new Date(published).getTime();
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor(diff / 60000);
    timeAgo = hours > 0 ? hours + 'h ago' : mins + 'm ago';
  }
  return {
    headline: item.title || 'No title',
    impact: parseFloat(impact),
    effect: formatNewsEffect(item, sentimentEffect),
    time: timeAgo,
    source: item.source || 'API',
    ticker: Array.isArray(item.tickers) && item.tickers.length > 0
      ? String(item.tickers[0]).toUpperCase()
      : (item.ticker ? String(item.ticker).toUpperCase() : ''),
    category: (item.tickers && item.tickers.length > 0) ? item.tickers[0] : 'Market',
    sentiment: item.sentiment || 'neutral',
    summary: item.summary || '',
    url: item.url || ''
  };
}

function transformForecast(row) {
  const dir = row.direction === 'up' ? '↑' : row.direction === 'down' ? '↓' : '→';
  const confidence = row.confidence != null ? Math.round(row.confidence * 100) : 0;
  const forecastFusion = row && typeof row.forecast_fusion === 'object' && !Array.isArray(row.forecast_fusion)
    ? row.forecast_fusion
    : (row && typeof row.forecastFusion === 'object' && !Array.isArray(row.forecastFusion) ? row.forecastFusion : null);
  return {
    ticker: row.ticker,
    direction: row.direction,
    directionArrow: dir,
    confidence: confidence,
    horizon: row.horizon || '1d',
    currentPrice: row.current_price || 0,
    targetPrice: row.target_price || 0,
    expectedReturn: row.expected_return || 0,
    reasoning: row.reasoning || row.why || '',
    action: row.action || 'hold',
    riskLevel: row.risk_level || 'medium',
    generatedAt: row.generated_at || row.timestamp || '',
    forecast_fusion: forecastFusion,
    forecastFusion,
  };
}

function transformSectorPerformance(payload) {
  const sectors = extractArray(payload, ['sectors', 'data', 'sector_data']) || [];
  return sectors
    .map((sector) => {
      const rawSector = sector || {};
      const sectorName = (rawSector.sector || rawSector.name || 'Unknown');
      const change = normalizeNumber(rawSector.change_pct ?? rawSector.change ?? rawSector.change_7d ?? rawSector.delta_pct, 0);
      const weight = normalizeNumber(rawSector.weight_pct ?? rawSector.weight ?? rawSector.weight_percent ?? 0, 0);
      const absChange = Math.abs(change);
      const direction = change > 0 ? 'UP' : change < 0 ? 'DOWN' : 'FLAT';
      const icon = change > 0 ? '↑' : change < 0 ? '↓' : '→';
      return {
        sector: sectorName,
        change,
        changeLabel: `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`,
        trendDirection: direction,
        trendIcon: icon,
        absChange,
        weightLabel: `${weight.toFixed(2)}%`,
        holdings: weight > 0,
        weight
      };
    })
    .filter((sector) => !!sector.sector);
}

function transformTopStocks(payload) {
  const topStocks = extractArray(payload, ['top_stocks']) || [];
  return topStocks
    .map((row) => {
      const rawRow = row || {};
      const symbol = (rawRow.symbol || rawRow.ticker || 'UNKNOWN').toUpperCase();
      const forecast = normalizeNumber(rawRow.forecast_pct ?? rawRow.forecast ?? 0, 0);
      const confidence = normalizeNumber(rawRow.confidence_pct ?? rawRow.confidence ?? 0, 0);
      return {
        symbol,
        price: normalizeNumber(rawRow.price, 0),
        change: normalizeNumber(rawRow.change_pct ?? rawRow.change ?? 0, 0),
        forecast: `${normalizeNumber(forecast, 0) >= 0 ? '+' : ''}${normalizeNumber(forecast, 0).toFixed(1)}%`,
        confidence: Math.max(0, Math.min(100, Math.round(normalizeNumber(confidence, 0))))
      };
    })
    .filter((stock) => !!stock.symbol);
}

function transformAlert(payload) {
  const raw = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
  const confidenceRaw = normalizeNumber(raw.confidence ?? raw.score ?? raw.probability, 0);
  const confidence = confidenceRaw > 1 ? confidenceRaw : confidenceRaw * 100;
  const timestamp = raw.timestamp || raw.generated_at || raw.generatedAt || raw.generated_at_iso || new Date().toISOString();
  const type = String(raw.type || raw.alertType || 'market-alert').trim().toLowerCase();
  const ticker = String(raw.ticker || raw.symbol || 'MARKET').trim().toUpperCase() || 'MARKET';
  const description = String(
    raw.description ||
    raw.message ||
    raw.detail ||
    `${ticker} ${type.replace(/-/g, ' ')} detected`
  ).trim();

  return {
    id: raw.id || `alert-${type}-${ticker}-${Date.now()}`,
    type,
    ticker,
    severity: String(raw.severity || 'info').toLowerCase(),
    confidence: Math.max(0, Math.min(100, Math.round(confidence))),
    timestamp,
    category: String(raw.category || '').toLowerCase(),
    description,
    detail: description,
    priority_band: String(raw.priority_band || raw.priorityBand || '').toLowerCase(),
    priority_rank: normalizeNumber(raw.priority_rank ?? raw.priorityRank, 0),
    priority_score: normalizeNumber(raw.priority_score ?? raw.priorityScore, 0),
    suppression: raw.suppression && typeof raw.suppression === 'object' && !Array.isArray(raw.suppression) ? raw.suppression : {},
    signals: raw.signals && typeof raw.signals === 'object' && !Array.isArray(raw.signals) ? raw.signals : {}
  };
}

function policyStatusSeverity(status) {
  const normalizedStatus = String(status || '').trim().toLowerCase();
  if (normalizedStatus === 'effective') return 'high';
  if (normalizedStatus === 'adopted') return 'medium';
  return 'info';
}

function summarizePolicyTransmission(raw, sectors, companies) {
  const transmission = isObject(raw.transmission) ? raw.transmission : {};
  const transmissionCompanies = Array.isArray(transmission.companies) ? transmission.companies : [];
  const transmissionSectors = normalizeConnectorStringList(transmission.primary_sectors || sectors);
  const highlightedCompanies = transmissionCompanies
    .map((row) => {
      if (isObject(row)) {
        return String(row.ticker || row.company_name || '').trim().toUpperCase();
      }
      return String(row || '').trim().toUpperCase();
    })
    .filter(Boolean);
  const companyList = highlightedCompanies.length ? highlightedCompanies : companies;

  if (!transmissionSectors.length && !companyList.length) {
    return '';
  }

  const sectorCopy = transmissionSectors.length ? transmissionSectors.slice(0, 2).join(', ') : 'broad market';
  const companyCopy = companyList.length ? companyList.slice(0, 3).join(', ') : 'watchlist names';
  return `transmission: ${sectorCopy} -> ${companyCopy}`;
}

function getPolicyTransmissionConfidence(raw, sectors, companies) {
  const baseConfidence = Math.max(0, Math.min(100, Math.round(normalizeNumber(raw.impact_score, 0) * 100)));
  const transmission = isObject(raw.transmission) ? raw.transmission : {};
  const transmissionCompanies = Array.isArray(transmission.companies) ? transmission.companies : [];
  const primarySectors = normalizeConnectorStringList(transmission.primary_sectors || sectors);
  const uncertaintyFactors = [];
  let penalty = 0;

  if (!transmissionCompanies.length && !companies.length) {
    uncertaintyFactors.push('no_company_mapping');
    penalty += 24;
  }
  if (primarySectors.length !== 1) {
    uncertaintyFactors.push('multi_sector_transmission');
    penalty += 12;
  }
  if (transmissionCompanies.some((row) => isObject(row) && String(row.transmission_path || '').trim() === 'policy_watchlist_indirect')) {
    uncertaintyFactors.push('indirect_company_mapping');
    penalty += 10;
  }

  const adjustedConfidence = Math.max(15, Math.min(100, baseConfidence - penalty));
  const uncertaintyLevel = penalty >= 22 ? 'high' : penalty >= 10 ? 'medium' : 'low';
  return {
    value: adjustedConfidence,
    level: uncertaintyLevel,
    factors: uncertaintyFactors,
  };
}

function transformPolicyImpactEvent(event) {
  const raw = event && typeof event === 'object' && !Array.isArray(event) ? event : {};
  const companies = Array.isArray(raw.companies)
    ? raw.companies.map((item) => String(item || '').trim().toUpperCase()).filter(Boolean)
    : [];
  const sectors = Array.isArray(raw.sectors)
    ? raw.sectors.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  const jurisdiction = String(raw.jurisdiction || 'global').trim().toUpperCase() || 'GLOBAL';
  const status = String(raw.status || 'monitoring').trim().toLowerCase() || 'monitoring';
  const effectiveDate = String(raw.effective_date || '').trim();
  const primaryTicker = companies[0] || jurisdiction;
  const summaryParts = [
    String(raw.summary || raw.title || `${jurisdiction} policy change detected`).trim(),
    `${jurisdiction} ${status}`,
  ];
  if (effectiveDate) {
    summaryParts.push(`effective ${effectiveDate}`);
  }
  if (sectors.length > 0) {
    summaryParts.push(`sectors: ${sectors.slice(0, 2).join(', ')}`);
  }
  const transmissionSummary = summarizePolicyTransmission(raw, sectors, companies);
  if (transmissionSummary) {
    summaryParts.push(transmissionSummary);
  }
  const transmissionConfidence = getPolicyTransmissionConfidence(raw, sectors, companies);

  return {
    id: raw.event_id || `policy-impact-${primaryTicker}-${status}-${effectiveDate || 'na'}`,
    type: 'news',
    ticker: primaryTicker,
    severity: policyStatusSeverity(status),
    confidence: transmissionConfidence.value,
    timestamp: raw.evidence && raw.evidence.published_at ? raw.evidence.published_at : new Date().toISOString(),
    category: 'policy-impact',
    description: summaryParts.filter(Boolean).join(' • '),
    detail: String(raw.title || raw.summary || '').trim(),
    signals: {
      jurisdiction,
      status,
      effective_date: effectiveDate || null,
      sectors,
      companies,
      transmission_path: String(raw.transmission?.path || '').trim() || null,
      transmission_summary: transmissionSummary || null,
      transmission_company_count: Number(raw.transmission?.company_count) || companies.length || 0,
      transmission_uncertainty_level: transmissionConfidence.level,
      transmission_uncertainty_factors: transmissionConfidence.factors,
    },
  };
}

function transformOpportunities(payload) {
  const opportunities = extractArray(payload, ['opportunities']) || [];
  return opportunities.map((row) => {
    const rawRow = row || {};
    return {
      conviction: rawRow.conviction || 'Medium',
      return: normalizeNumber(rawRow.expected_return_pct ?? rawRow.return_pct ?? 0, 0),
      confidence: Math.max(0, Math.min(100, Math.round(normalizeNumber(rawRow.confidence_pct ?? rawRow.confidence ?? 60, 60))))
    };
  });
}

function transformBrief(payload) {
  const briefPayload = normalizeBriefOfDayPayload(payload);
  const source = Object.keys(briefPayload).length
    ? briefPayload
    : (payload && typeof payload === 'object' ? payload : {});
  const payloadSummary = source.summary || source.message || source.overview;
  const sectorRotation = source.sector_rotation || source.sectorRotation || {};
  const topSectors = (Array.isArray(sectorRotation.top) ? sectorRotation.top : []).map((entry) => String(entry || '').trim()).filter(Boolean);
  const bottomSectors = (Array.isArray(sectorRotation.bottom) ? sectorRotation.bottom : []).map((entry) => String(entry || '').trim()).filter(Boolean);
  const summary = payloadSummary || 'Le marché reste actif avec une lecture mitigée.';
  const headline = source.title || source.headline || 'Aperçu du marché';
  const sentiment = source.market_regime || source.market_sentiment || source.regime || source.sentiment || 'neutral';
  const timestamp = source.freshness || source.generated_at || source.generatedAt || source.generated_at_iso || new Date().toISOString();
  const rotationText = [];
  if (topSectors.length > 0) {
    rotationText.push(`Top secteurs : ${topSectors.slice(0, 3).join(' · ')}`);
  }
  if (bottomSectors.length > 0) {
    rotationText.push(`Sectors faibles : ${bottomSectors.slice(0, 3).join(' · ')}`);
  }
  const content = [summary, ...rotationText].filter(Boolean).join('\n\n');
  return {
    headline,
    content,
    sentiment,
    timestamp,
    sectorRotationTop: topSectors,
    sectorRotationBottom: bottomSectors,
    sectorRotationSummary: rotationText.join(' | '),
    sources: normalizeConnectorSourceList(source.sources || source.source),
    degraded: source.degraded === true
  };
}

function normalizeConnectorStringList(value) {
  const values = Array.isArray(value)
    ? value
    : (typeof value === 'string' ? value.split(/[\n,]+/) : []);
  return values
    .map((entry) => String(entry || '').trim())
    .filter(Boolean);
}

function normalizeAlertingRichPayload(source, options = {}) {
  const safeSource = source && typeof source === 'object' ? source : {};
  const opportunityKeys = Array.isArray(options.opportunityKeys) && options.opportunityKeys.length
    ? options.opportunityKeys
    : ['top_opportunities', 'topOpportunities', 'top_signals', 'topSignals', 'signals'];
  const topOpportunities = normalizeConnectorStringList(
    opportunityKeys.map((key) => safeSource[key]).find((value) => value !== undefined)
  );
  const topRiskItems = normalizeBriefRiskEntries(
    safeSource.top_risk_items || safeSource.topRiskItems || safeSource.top_risks || safeSource.topRisks || safeSource.risks
  );
  const topRisks = topRiskItems.length
    ? topRiskItems.map((entry) => String(entry.label || '').trim()).filter(Boolean)
    : normalizeConnectorStringList(safeSource.top_risks || safeSource.topRisks || safeSource.risks);
  const suppressedRisks = normalizeBriefRiskEntries(safeSource.suppressed_risks || safeSource.suppressedRisks);
  const sources = normalizeConnectorSourceList(safeSource.sources || safeSource.source);
  const freshness = safeSource.freshness || safeSource.generated_at || safeSource.generatedAt || '';
  const degradedReason = safeSource.degraded_reason || safeSource.degradedReason || '';
  const alertingMetadata = safeSource.alerting_metadata && typeof safeSource.alerting_metadata === 'object'
    ? safeSource.alerting_metadata
    : (safeSource.alertingMetadata && typeof safeSource.alertingMetadata === 'object' ? safeSource.alertingMetadata : {});
  const degraded = safeSource.degraded === true
    || normalizeFreshnessStatus(safeSource.status || safeSource.quality_status || safeSource.qualityStatus) === 'degraded'
    || Boolean(degradedReason);

  return {
    topOpportunities,
    topRiskItems,
    topRisks,
    suppressedRisks,
    sources,
    freshness,
    degradedReason,
    alertingMetadata,
    degraded,
  };
}

function normalizeBriefRiskEntries(value) {
  const values = Array.isArray(value)
    ? value
    : (value ? [value] : []);
  return values
    .map((entry) => {
      if (entry && typeof entry === 'object') {
        const label = String(
          entry.label
            || entry.ticker
            || entry.risk
            || entry.title
            || entry.summary
            || ''
        ).trim();
        return {
          ...entry,
          label,
        };
      }
      const label = String(entry || '').trim();
      return label ? { label } : null;
    })
    .filter(Boolean);
}

function normalizeConnectorSourceList(value) {
  const values = Array.isArray(value)
    ? value
    : (value ? [value] : []);
  return values.filter((entry) => entry !== null && entry !== undefined && entry !== '');
}

function appendUniqueSourceEntries(target, value) {
  normalizeConnectorSourceList(value).forEach((entry) => {
    if (!target.includes(entry)) {
      target.push(entry);
    }
  });
}

function collectLiveDashboardSources() {
  const sources = [];
  appendUniqueSourceEntries(sources, 'api-connector');
  appendUniqueSourceEntries(sources, window.storyData && window.storyData.sources);
  appendUniqueSourceEntries(sources, window.liveForecastScoreboard && window.liveForecastScoreboard.source);
  appendUniqueSourceEntries(sources, window.globalSignalMesh && window.globalSignalMesh.source);
  appendUniqueSourceEntries(sources, window.policyImpact && window.policyImpact.source);
  appendUniqueSourceEntries(sources, window.apiHealth && window.apiHealth.source);
  appendUniqueSourceEntries(sources, window.livePortfolioRiskProfile && window.livePortfolioRiskProfile.source);
  appendUniqueSourceEntries(sources, window.liveKpis && window.liveKpis.source);
  appendUniqueSourceEntries(sources, window.livePortfolioSummary && window.livePortfolioSummary.source);
  return sources.length ? sources : ['api-connector'];
}

function normalizeBriefOfDayPayload(payload) {
  const source = payload && typeof payload === 'object' ? payload : {};
  if (!Object.keys(source).length) {
    return {};
  }

  const normalizedAlerting = normalizeAlertingRichPayload(source);
  const marketRegime = String(
    source.market_regime
      || source.marketRegime
      || source.market_sentiment
      || source.marketSentiment
      || source.regime
      || source.sentiment
      || ''
  ).trim().toUpperCase();

  return {
    ...source,
    summary: source.summary || source.message || source.overview || '',
    market_regime: marketRegime || String(source.market_regime || '').trim().toUpperCase(),
    market_sentiment: marketRegime || String(source.market_sentiment || source.sentiment || '').trim().toUpperCase(),
    regime: marketRegime || String(source.regime || '').trim().toUpperCase(),
    top_opportunities: normalizedAlerting.topOpportunities,
    top_signals: normalizedAlerting.topOpportunities,
    top_risks: normalizedAlerting.topRisks,
    top_risk_items: normalizedAlerting.topRiskItems,
    topRiskItems: normalizedAlerting.topRiskItems,
    suppressed_risks: normalizedAlerting.suppressedRisks,
    suppressedRisks: normalizedAlerting.suppressedRisks,
    freshness: normalizedAlerting.freshness,
    generated_at: source.generated_at || source.generatedAt || normalizedAlerting.freshness || new Date().toISOString(),
    sources: normalizedAlerting.sources,
    source: normalizedAlerting.sources,
    alerting_metadata: normalizedAlerting.alertingMetadata,
    alertingMetadata: normalizedAlerting.alertingMetadata,
    degraded: normalizedAlerting.degraded,
    degraded_reason: normalizedAlerting.degradedReason,
  };
}

function transformCopilotStart(payload, fallbackPayload = null) {
  const source = payload && typeof payload === 'object' ? payload : {};
  const fallbackSource = fallbackPayload && typeof fallbackPayload === 'object' ? fallbackPayload : {};
  const entryPoints = extractArray(fallbackSource, ['entry_points', 'entryPoints']);
  const briefOfDay = extractObject(source, ['brief_of_day', 'briefOfDay']);
  const fallbackBrief = extractObject(fallbackSource, ['daily_brief', 'dailyBrief']);
  const askItems = extractArray(source, ['ask']);
  const openItems = extractArray(source, ['open'])
    .map((item) => {
      if (!item || typeof item !== 'object') return item;
      return {
        ...item,
        target: normalizeCopilotOpenTarget(item.target, item.id)
      };
    })
    .filter((item) => item && item.target);
  const normalizedAsk = askItems.length
    ? askItems
    : entryPoints.filter((item) => {
      if (!item || typeof item !== 'object') return false;
      const kind = String(item.kind || '').toLowerCase();
      const target = String(item.target || '').toLowerCase();
      return kind === 'ask' || target === '/copilot/ask';
    });
  const normalizedOpen = openItems.length
    ? openItems
    : entryPoints
      .filter((item) => {
        if (!item || typeof item !== 'object') return false;
        const kind = String(item.kind || '').toLowerCase();
        const target = String(item.target || '').toLowerCase();
        return kind === 'open' || (target && target !== '/copilot/ask');
      })
      .map((item) => ({
        ...item,
        target: normalizeCopilotOpenTarget(item.target, item.id)
      }))
      .filter((item) => item.target);
  const resolvedBrief = Object.keys(briefOfDay).length ? briefOfDay : fallbackBrief;

  return {
    brief_of_day: normalizeBriefOfDayPayload(resolvedBrief),
    ask: normalizedAsk,
    open: normalizedOpen,
    regime_detection: extractObject(source, ['regime_detection', 'regimeDetection'])
      || extractObject(fallbackSource, ['regime_detection', 'regimeDetection']),
    allocation_drift_alerts: extractObject(source, ['allocation_drift_alerts', 'allocationDriftAlerts'])
      || extractObject(fallbackSource, ['allocation_drift_alerts', 'allocationDriftAlerts'])
  };
}

function mapRegimeAlertSeverity(label, confidence) {
  const normalizedLabel = String(label || '').trim().toLowerCase();
  const normalizedConfidence = normalizeNumber(confidence, 0);
  if (
    normalizedLabel.includes('risk_off')
    || normalizedLabel.includes('bear')
    || normalizedLabel.includes('defensive')
    || normalizedLabel.includes('recession')
  ) {
    return 'high';
  }
  if (normalizedConfidence >= 0.75 || normalizedConfidence >= 75) {
    return 'medium';
  }
  return 'info';
}

function buildCopilotContextAlerts(payload) {
  const source = payload && typeof payload === 'object' ? payload : {};
  const alerts = [];
  const regimeDetection = extractObject(source, ['regime_detection', 'regimeDetection']);
  const allocationDrift = extractObject(source, ['allocation_drift_alerts', 'allocationDriftAlerts']);

  if (Object.keys(regimeDetection).length) {
    const label = String(regimeDetection.label || regimeDetection.regime || '').trim().toUpperCase();
    const confidence = normalizeNumber(regimeDetection.confidence, 0);
    const thresholdReason = String(regimeDetection.threshold_reason || regimeDetection.thresholdReason || '').trim();
    if (label) {
      alerts.push({
        id: String(regimeDetection.id || `copilot-regime-${label.toLowerCase()}`),
        ticker: 'MARKET',
        type: 'market-alert',
        category: 'regime-detection',
        severity: mapRegimeAlertSeverity(label, confidence),
        confidence,
        timestamp: regimeDetection.generated_at || regimeDetection.generatedAt || new Date().toISOString(),
        description: thresholdReason
          ? `Regime ${label.replace(/_/g, ' ')} detected. ${thresholdReason}`
          : `Regime ${label.replace(/_/g, ' ')} detected.`,
        signals: {
          label,
          threshold_reason: thresholdReason,
          source: normalizeConnectorSourceList(regimeDetection.source || regimeDetection.sources),
        },
      });
    }
  }

  const driftRows = Array.isArray(allocationDrift.alerts) ? allocationDrift.alerts : [];
  driftRows.forEach((row, index) => {
    if (!row || typeof row !== 'object') return;
    const symbol = String(row.symbol || row.ticker || 'PORTFOLIO').trim().toUpperCase() || 'PORTFOLIO';
    const reason = String(row.reason || row.description || '').trim();
    if (!reason) return;
    alerts.push({
      id: String(row.id || `copilot-drift-${symbol.toLowerCase()}-${index}`),
      ticker: symbol,
      type: 'market-alert',
      category: 'allocation-drift',
      severity: String(row.severity || 'medium').trim().toLowerCase() || 'medium',
      confidence: normalizeNumber(row.threshold_pct, 0),
      timestamp: row.generated_at || row.generatedAt || regimeDetection.generated_at || new Date().toISOString(),
      description: reason,
      signals: {
        basis: row.basis || '',
        threshold_pct: normalizeNumber(row.threshold_pct, 0),
        current_weight_pct: normalizeNumber(row.current_weight_pct, 0),
        reference_weight_pct: normalizeNumber(row.reference_weight_pct, 0),
      },
    });
  });

  return alerts;
}

function normalizeCopilotOpenTarget(target, id) {
  const normalizedTarget = String(target || '').trim().toLowerCase();
  const normalizedId = String(id || '').trim().toLowerCase();
  if (
    normalizedId === 'brief_of_day'
    || normalizedTarget === '/brief/daily'
    || normalizedTarget === 'brief_of_day'
    || normalizedTarget === 'brief'
    || normalizedTarget === 'live_brief'
    || normalizedTarget === 'daily_brief'
  ) {
    return 'market';
  }
  if (
    normalizedId === 'ask_copilot'
    || normalizedId === 'open_copilot'
    || normalizedId === 'copilot'
    || normalizedTarget === '/copilot/ask'
    || normalizedTarget === '/copilot'
    || normalizedTarget === '/copilot/'
    || normalizedTarget === 'copilot'
    || normalizedTarget === 'copilot/'
  ) {
    return 'copilot';
  }
  return normalizedTarget.replace(/^\/+/, '');
}

function buildTradeIdeasFromForecasts(rows) {
  if (!Array.isArray(rows) || !rows.length) return [];
  return rows.slice(0, 6).map((row) => {
    const currentPrice = normalizeNumber(row.currentPrice ?? row.current_price ?? 0, 0);
    const targetPrice = normalizeNumber(row.targetPrice ?? row.target_price ?? currentPrice, currentPrice);
    const confidence = normalizeNumber(row.confidence ?? row.confidence_pct ?? 0, 0);
    return {
      symbol: String(row.ticker || row.symbol || 'MARKET').toUpperCase(),
      signalType: String(row.action || row.direction || 'hold').toUpperCase(),
      entry: currentPrice,
      target: targetPrice,
      confidence: Math.max(0, Math.min(100, Math.round(confidence)))
    };
  });
}

function resolveDriverColor(factor) {
  const normalized = String(factor || '').toLowerCase();
  if (normalized.includes('tech')) return '#1F40AF';
  if (normalized.includes('sent')) return '#8B5CF6';
  if (normalized.includes('news') || normalized.includes('nouv')) return '#F59E0B';
  if (normalized.includes('macro')) return '#10B981';
  return '#1F40AF';
}

function transformMarketDrivers(payload) {
  const data = getResponseData(payload);
  const drivers = extractArray(data, ['drivers', 'items', 'data']);
  return drivers.map((item) => ({
    factor: item.factor || 'Market',
    contribution: Math.max(0, Math.min(100, Math.round(normalizeNumber(item.contribution, 0)))),
    color: item.color || resolveDriverColor(item.factor)
  }));
}

function normalizeRiskContributionScore(value) {
  const raw = normalizeNumber(value, 0);
  const scaled = raw > 1 ? raw : raw * 100;
  return Math.max(0, Math.min(100, Math.round(scaled)));
}

function mergeGeopoliticalDriver(drivers, geopoliticalRiskGraph) {
  const baseDrivers = Array.isArray(drivers) ? drivers.filter((item) => item && typeof item === 'object') : [];
  const payload = geopoliticalRiskGraph && typeof geopoliticalRiskGraph === 'object' ? geopoliticalRiskGraph : null;
  if (!payload) return baseDrivers;

  const alerts = Array.isArray(payload.alerts) ? payload.alerts.filter((item) => item && typeof item === 'object') : [];
  const nodes = Array.isArray(payload.nodes) ? payload.nodes.filter((item) => item && typeof item === 'object') : [];
  const topRisk = alerts[0] || nodes[0] || null;
  if (!topRisk) return baseDrivers;

  const contribution = normalizeRiskContributionScore(topRisk.escalation_score);
  const hasExistingGeopoliticalDriver = baseDrivers.some((item) => {
    const factor = String(item.factor || '').trim().toLowerCase();
    return factor.includes('geopolit') || factor.includes('conflict');
  });
  if (hasExistingGeopoliticalDriver) return baseDrivers;

  return [
    {
      factor: 'Geopolitical',
      contribution,
      color: '#B45309',
    },
    ...baseDrivers,
  ].slice(0, Math.max(baseDrivers.length, 4));
}

function formatCalendarDate(value, fallback) {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return fallback || 'TBA';
  return new Date(parsed).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function mapImpactLabel(value) {
  const score = normalizeNumber(value, 0);
  if (score >= 0.75 || score >= 75) return 'High';
  if (score >= 0.45 || score >= 45) return 'Medium';
  return 'Low';
}

function looksLikeEarningsEvent(item) {
  const text = `${item.title || ''} ${item.summary || ''}`.toLowerCase();
  return ['earnings', 'revenue', 'guidance', 'quarter', 'eps', 'results'].some((token) => text.includes(token));
}

function buildMarketCalendar(brief, newsItems, alerts) {
  const safeBrief = brief && typeof brief === 'object' ? brief : {};
  const newsRows = Array.isArray(newsItems) ? newsItems : [];
  const alertRows = Array.isArray(alerts) ? alerts : [];
  const keyEvents = Array.isArray(safeBrief.key_events) ? safeBrief.key_events : [];

  const critical = keyEvents
    .slice(0, 4)
    .map((item, index) => {
      const row = item && typeof item === 'object' ? item : { label: String(item || '').trim() };
      const label = String(
        row.label
          || row.title
          || row.name
          || row.event
          || row.stock
          || row.ticker
          || row.symbol
          || ''
      ).trim();
      if (!label) return null;
      const category = String(row.category || row.type || row.event_type || '').trim().toLowerCase();
      const eventDate = row.date || row.timestamp || row.starts_at || row.generated_at || safeBrief.generated_at;
      return {
        label,
        date: formatCalendarDate(eventDate, index < 2 ? 'Today' : 'Soon'),
        impact: mapImpactLabel(row.impact_score ?? row.score ?? (index < 2 ? 0.85 : 0.7)),
        window: String(row.window || row.horizon || (index === 0 ? '24h' : '48h')).trim().toUpperCase(),
        category: category || (/earn/i.test(label) ? 'earnings' : 'macro'),
      };
    })
    .filter(Boolean);

  const earnings = newsRows
    .filter((item) => looksLikeEarningsEvent(item))
    .slice(0, 3)
    .map((item) => ({
      stock: item.tickers && item.tickers.length ? String(item.tickers[0]).toUpperCase() : 'MARKET',
      date: formatCalendarDate(item.published_at || item.date || item.created_at, 'TBA'),
      impact: mapImpactLabel(item.score ?? item.relevance ?? 0.6),
      holding: Boolean(item.tickers && item.tickers.length)
    }));

  critical
    .filter((item) => item.category.includes('earn'))
    .forEach((item) => {
      if (earnings.length >= 3) return;
      earnings.push({
        stock: item.label,
        date: item.date,
        impact: item.impact,
        holding: false,
      });
    });

  const macroSignals = Array.isArray(safeBrief.macro_signals) ? safeBrief.macro_signals : [];
  const economicData = macroSignals.slice(0, 3).map((item) => ({
    event: item.topic || item.name || 'Macro signal',
    date: formatCalendarDate(safeBrief.generated_at, 'Today'),
    impact: mapImpactLabel(item.confidence ?? item.score ?? 0.5)
  }));

  critical
    .filter((item) => !item.category.includes('earn'))
    .forEach((item) => {
      if (economicData.length >= 3) return;
      economicData.push({
        event: item.label,
        date: item.date,
        impact: item.impact,
      });
    });

  const exDividend = alertRows
    .filter((item) => String(item.type || '').toLowerCase().includes('dividend'))
    .slice(0, 2)
    .map((item) => ({
      stock: String(item.ticker || item.symbol || 'MARKET').toUpperCase(),
      date: formatCalendarDate(item.timestamp || item.generated_at, 'TBA'),
      amount: normalizeNumber(item.amount, 0)
    }));

  return {
    critical,
    notice: critical.length
      ? `${critical.length} critical event${critical.length > 1 ? 's' : ''} in the next 48h`
      : '',
    earnings,
    economicData,
    exDividend,
  };
}

function hasCalendarEntries(calendar) {
  if (!calendar || typeof calendar !== 'object') return false;
  return ['earnings', 'economicData', 'exDividend'].some((key) => Array.isArray(calendar[key]) && calendar[key].length > 0);
}

function transformJudgeData(payload) {
  if (!payload || typeof payload !== 'object') return null;
  const stdout = payload.stdout || {};
  const derived = payload.derived || {};
  const stats = derived.stats || {};
  const topBuys = extractArray(derived, ['top_buys']) || [];
  const topRisks = extractArray(derived, ['top_risks']) || [];
  const confidence = Math.round(normalizeNumber(stats.avg_confidence ?? stats.avg_er_high_conf ?? 0, 0) * 100);
  let consensus = 'HOLD';
  if (topBuys.length > topRisks.length) {
    consensus = 'BUY';
  } else if (topRisks.length > topBuys.length) {
    consensus = 'SELL';
  }
  const reasoning = stdout.forecast || stdout.context || 'Le jugement de marché est en cours de calcul.';
  const modelName = payload.model_used || 'EconomicAnalyst';
  return {
    question: "Quel est mon meilleur plan de marché aujourd'hui ?",
    consensus,
    confidence: Math.max(0, Math.min(100, confidence)),
    models: [
      {
        name: modelName,
        verdict: consensus,
        confidence: Math.max(0, Math.min(100, confidence)),
        icon: '🤖'
      }
    ],
    reasoning,
    dataSources: ['Forecasts', 'LLM Judge', 'Model ensemble'],
    suggestedActions: [
      { icon: '📈', title: 'Allouer', detail: 'Renforcer la couverture des zones fortes', action: 'reviewRisk' },
      { icon: '⚖️', title: 'Sécuriser', detail: 'Vérifier les risques de concentration', action: 'reviewRisk' },
      { icon: '🔔', title: 'Alerte', detail: 'Alerter au franchissement de seuil', action: 'setAlert' }
    ]
  };
}

function buildLiveFreshnessContract(ingestionHealth, apiHealth, extraSources) {
  const sourceEntries = ingestionHealth && Array.isArray(ingestionHealth.sources) ? ingestionHealth.sources : [];
  const supplementalSources = Array.isArray(extraSources)
    ? extraSources
    : (extraSources && typeof extraSources === 'object' ? [extraSources] : []);
  const healthStatus = String(ingestionHealth && ingestionHealth.status ? ingestionHealth.status : '').toLowerCase();
  const timestamps = [];
  const ttlCandidates = [];
  const statuses = [];

  [...sourceEntries, ...supplementalSources].forEach((entry) => {
    const normalizedStatus = normalizeFreshnessStatus(entry && entry.status);
    if (normalizedStatus) {
      statuses.push(normalizedStatus);
    }

    const freshness = entry && Object.prototype.hasOwnProperty.call(entry, 'freshness')
      ? entry.freshness
      : entry;
    const timestamp = resolveFreshnessTimestamp(freshness);
    if (timestamp !== null) {
      timestamps.push(timestamp);
    }
    const ttlSeconds = normalizeNumber(
      freshness && typeof freshness === 'object' ? freshness.ttl_seconds : 0,
      0,
    );
    if (ttlSeconds > 0) {
      ttlCandidates.push(ttlSeconds * 1000);
    }
  });

  if (apiHealth && apiHealth.last_updates && typeof apiHealth.last_updates === 'object') {
    Object.values(apiHealth.last_updates).forEach((value) => {
      const timestamp = resolveFreshnessTimestamp(value);
      if (timestamp !== null) {
        timestamps.push(timestamp);
      }
    });
  }

  let contractState = 'unknown';
  if (statuses.length > 0) {
    if (statuses.every((status) => status === 'fresh')) {
      contractState = 'ok';
    } else if (statuses.some((status) => status === 'stale')) {
      contractState = 'stale';
    } else {
      contractState = 'degraded';
    }
  }

  if (contractState !== 'stale' && (
    healthStatus === 'degraded'
    || (ingestionHealth && normalizeNumber(ingestionHealth.degraded_count, 0) > 0)
  )) {
    contractState = 'degraded';
  } else if (
    contractState === 'unknown'
    && (healthStatus === 'ok' || healthStatus === 'healthy' || (ingestionHealth && ingestionHealth.all_fresh === true))
  ) {
    contractState = 'ok';
  }

  return {
    contractState,
    freshness: {
      lastFetchedAt: timestamps.length ? Math.min(...timestamps) : Date.now(),
      ttlMs: ttlCandidates.length ? Math.min(...ttlCandidates) : cache.TTL
    }
  };
}

// ─── Populate window globals used by app.js ──────────────────────────────────

async function populateWindowGlobals() {
  console.log('[API] Loading live data...');

  try {
    const contractWarnings = [];

    // News
    const rawNews = await getNewsFeed(20);
    if (rawNews.length > 0) {
      window.newsItems = rawNews.map(transformNewsItem);
      console.log("[API] ✅ " + window.newsItems.length + " news chargées depuis l'API");
    } else {
      contractWarnings.push('newsItems-unavailable');
    }

    // Alerts
    const alertsPayload = await getAlerts();
    const rawAlerts = Array.isArray(alertsPayload?.alerts) ? alertsPayload.alerts : [];
    window.alertTimelineMeta = {
      generatedAt: String(alertsPayload?.generatedAt || ''),
      suppressedCount: normalizeNumber(alertsPayload?.suppressedCount, 0),
      topPriorityBand: String(alertsPayload?.queue?.top_priority_band || alertsPayload?.queue?.topPriorityBand || '').toLowerCase(),
      priorityBands: extractObject(alertsPayload?.stats, ['priority_bands', 'priorityBands']) || {},
      suppressionReasons: extractObject(alertsPayload?.stats, ['suppression_reasons', 'suppressionReasons']) || {},
      suppressionWindowMinutes: normalizeNumber(
        alertsPayload?.pipeline?.suppression_window_minutes
          ?? alertsPayload?.pipeline?.suppressionWindowMinutes,
        0
      ),
    };
    window.alertTimeline = rawAlerts.map(transformAlert);
    if (window.alertTimeline.length > 0) {
      console.log('[API] ✅ ' + window.alertTimeline.length + ' alerts chargées depuis l\'API');
    }

    const policyImpact = await getPolicyImpact({ limit: 5 });
    window.policyImpact = policyImpact;
    const policyEvents = extractArray(policyImpact, ['events']).map(transformPolicyImpactEvent);
    if (policyEvents.length > 0) {
      window.alertTimeline = [...policyEvents, ...window.alertTimeline];
      console.log('[API] ✅ ' + policyEvents.length + ' policy impact alerts hydrated');
    }

    // Forecasts
    const rawForecasts = await getForecasts(20);
    if (rawForecasts.length > 0) {
      window.liveForecasts = rawForecasts.map(transformForecast);
      window.tradeIdeas = buildTradeIdeasFromForecasts(window.liveForecasts);
      // Also expose in v11Data format used by some widgets
      if (!window.v11Data) window.v11Data = {};
      window.v11Data.forecasts = window.liveForecasts;
      console.log('[API] ✅ ' + window.liveForecasts.length + ' forecasts loaded');
    } else {
      contractWarnings.push('tradeIdeas-unavailable');
    }

    const recommendationsPayload = await getDailyRecommendations(3);
    if (Array.isArray(recommendationsPayload.recommendations) && recommendationsPayload.recommendations.length > 0) {
      window.liveRecommendations = recommendationsPayload.recommendations;
      window.tradeIdeas = buildTradeIdeasFromForecasts(
        window.liveForecasts || [],
        window.liveRecommendations
      );
    } else {
      window.liveRecommendations = [];
    }

    const scoreboard = await getWalkForwardScoreboard();
    if (scoreboard && typeof scoreboard === 'object' && Array.isArray(scoreboard.rows)) {
      window.liveForecastScoreboard = scoreboard;
    } else {
      window.liveForecastScoreboard = null;
    }

    const geopoliticalRiskGraph = await getGeopoliticalRiskGraph({ limit: 4 });
    window.geopoliticalRiskGraph = geopoliticalRiskGraph && typeof geopoliticalRiskGraph === 'object'
      ? geopoliticalRiskGraph
      : null;
    const eventImpactHorizonMatrix = await getEventImpactHorizonMatrix({ limit: 3 });
    window.eventImpactHorizonMatrix = eventImpactHorizonMatrix && typeof eventImpactHorizonMatrix === 'object'
      ? eventImpactHorizonMatrix
      : null;

    // Stocks - build top movers with real % change from price history
    const rawStocks = await getStockPrices();
    const tickers = Object.keys(rawStocks);
    if (tickers.length > 0) {
      window.liveStocks = rawStocks;
      const movers = tickers.map(ticker => {
        const stockData = rawStocks[ticker];
        const points = (stockData && stockData.points) ? stockData.points : (Array.isArray(stockData) ? stockData : []);
        const first = points.length > 1 ? (Array.isArray(points[0]) ? points[0][1] : points[0]) : 0;
        const last = points.length > 0 ? (Array.isArray(points[points.length-1]) ? points[points.length-1][1] : points[points.length-1]) : 0;
        const change30d = first > 0 ? parseFloat(((last - first) / first * 100).toFixed(2)) : 0;
        const prev = points.length > 1 ? (Array.isArray(points[points.length-2]) ? points[points.length-2][1] : points[points.length-2]) : last;
        const change1d = prev > 0 ? parseFloat(((last - prev) / prev * 100).toFixed(2)) : 0;
        return { ticker, price: parseFloat(last.toFixed(2)), change: change1d, change30d, sparkline: points.slice(-20).map(p => Array.isArray(p) ? p[1] : p) };
      }).sort((a, b) => Math.abs(b.change30d) - Math.abs(a.change30d)).slice(0, 8);
      window.topMovers = movers;
      console.log('[API] ✅ ' + tickers.length + ' stocks, top movers: ' + movers.slice(0,3).map(m => m.ticker + ' (' + (m.change30d > 0 ? '+' : '') + m.change30d + '% 30d)').join(', '));
    }

    // Dashboard performance -> topStocks + opportunities
    const performance = await getDashboardPerformance();
    if (performance) {
      const topStocks = transformTopStocks(performance);
      const opportunities = transformOpportunities(performance);
      if (topStocks.length > 0) {
        window.topStocks = topStocks;
      }
      if (opportunities.length > 0) {
        window.liveOpportunities = opportunities;
      }
    }

    // Copilot bootstrap context -> story panel + starter prompts
    let brief = null;
    window.copilotStart = null;
    const copilotStartPayload = await getCopilotStart();
    const copilotStart = transformCopilotStart(
      copilotStartPayload.copilot_start || copilotStartPayload.copilotStart || copilotStartPayload,
      copilotStartPayload
    );
    if (copilotStart.brief_of_day || copilotStart.ask.length || copilotStart.open.length) {
      window.copilotStart = copilotStart;
    }
    const copilotContextAlerts = buildCopilotContextAlerts(copilotStartPayload);
    if (copilotContextAlerts.length > 0) {
      window.alertTimeline = [...copilotContextAlerts, ...window.alertTimeline];
      console.log('[API] ✅ ' + copilotContextAlerts.length + ' copilot regime/drift alerts hydrated');
    }

    if (window.copilotStart && window.copilotStart.brief_of_day) {
      brief = window.copilotStart.brief_of_day;
      window.storyData = transformBrief(brief);
    } else {
      brief = await getDailyBrief();
      if (brief && typeof brief === 'object') {
        window.storyData = transformBrief(brief);
      } else {
        contractWarnings.push('story-unavailable');
      }
    }

    // Sector performance -> Sector widget
    const sectorPayload = await getSectorPerformanceData();
    if (sectorPayload && typeof sectorPayload === 'object') {
      window.sectorPerformance = transformSectorPerformance(sectorPayload);
    }

    const marketDriversPayload = await getMarketDriversSnapshot();
    const transformedMarketDrivers = marketDriversPayload ? transformMarketDrivers(marketDriversPayload.data || marketDriversPayload) : [];
    const mergedMarketDrivers = mergeGeopoliticalDriver(transformedMarketDrivers, window.geopoliticalRiskGraph);
    if (mergedMarketDrivers.length > 0) {
      window.marketDrivers = mergedMarketDrivers;
    } else {
      contractWarnings.push('marketDrivers-unavailable');
    }

    const insiderBehavior = await getInsiderBehavior({ limit: 3 });
    window.insiderBehavior = insiderBehavior && typeof insiderBehavior === 'object'
      ? insiderBehavior
      : null;
    if (!window.insiderBehavior || !Array.isArray(window.insiderBehavior.signals) || window.insiderBehavior.signals.length === 0) {
      contractWarnings.push('insiderBehavior-unavailable');
    }

    const derivedCalendar = buildMarketCalendar(brief, rawNews, window.alertTimeline || []);
    if (hasCalendarEntries(derivedCalendar)) {
      window.marketCalendar = derivedCalendar;
    } else {
      contractWarnings.push('marketCalendar-unavailable');
    }
    window.liveContractWarnings = contractWarnings;

    // LLM Judge snapshot
    const judgePayload = await getLlmJudgeSnapshot();
    if (judgePayload) {
      const judgeData = transformJudgeData(judgePayload);
      if (judgeData) {
        window.llmJudgeData = judgeData;
      }
    }

    const copilotDecisionJournalPayload = await getCopilotDecisionJournal({ limit: 20 });
    window.copilotDecisionJournal = copilotDecisionJournalPayload && typeof copilotDecisionJournalPayload === 'object'
      ? copilotDecisionJournalPayload
      : null;

    // Judge decision journal for outcome feedback loop visibility
    const judgeAnalysis = await getJudgeAnalysis(5);
    const normalizedJudgeDecisionJournal = isObject(judgeAnalysis) || Array.isArray(judgeAnalysis)
      ? (judgeAnalysis.decision_journal || judgeAnalysis)
      : null;
    window.judgeDecisionJournal = isObject(normalizedJudgeDecisionJournal) || Array.isArray(normalizedJudgeDecisionJournal)
      ? normalizedJudgeDecisionJournal
      : null;

    // Portfolio KPIs
    const kpiPayload = await getDashboardKPIs();
    if (kpiPayload) {
      window.liveKpis = kpiPayload.data;
      window.liveKpisFreshness = kpiPayload.freshness;
    }

    // Portfolio summary (fallback source for portfolio value + deltas)
    const portfolioSummary = await getPortfolioSummary();
    if (portfolioSummary && portfolioSummary.data) {
      window.livePortfolioSummary = portfolioSummary.data;
      window.livePortfolioSummaryFreshness = portfolioSummary.freshness;
    }

    window.livePortfolioRiskProfile = null;
    window.livePortfolioRiskProfileFreshness = null;
    window.livePortfolioRiskProfileStatus = null;
    window.livePortfolioHealth = null;
    const portfolioRiskProfile = await getPortfolioRiskProfile();
    if (portfolioRiskProfile && portfolioRiskProfile.data) {
      window.livePortfolioRiskProfile = portfolioRiskProfile.data;
      window.livePortfolioRiskProfileFreshness = portfolioRiskProfile.freshness;
      window.livePortfolioRiskProfileStatus = toString(
        portfolioRiskProfile.status || portfolioRiskProfile.data.status,
        '',
      ).trim() || null;
      window.livePortfolioHealth = transformPortfolioHealth(portfolioRiskProfile);
      if (portfolioRiskProfile.status === 'degraded') {
        contractWarnings.push('portfolio-risk-profile-degraded');
      }
    }

    const ingestionHealth = await getIngestionHealth();
    if (ingestionHealth) {
      window.ingestionHealth = ingestionHealth;
    }

    const globalSignalMesh = await getGlobalSignalMesh();
    if (globalSignalMesh) {
      window.globalSignalMesh = globalSignalMesh;
    }

    const finalGlobalForecastGate = await getFinalGlobalForecastGate({ country: 'US', horizon: '3m' });
    window.finalGlobalForecastGate = finalGlobalForecastGate && typeof finalGlobalForecastGate === 'object'
      ? finalGlobalForecastGate
      : null;
    if (window.finalGlobalForecastGate && window.finalGlobalForecastGate.status && window.finalGlobalForecastGate.status !== 'fresh') {
      contractWarnings.push(`final-global-gate-${window.finalGlobalForecastGate.status}`);
    }

    const macroRegimeHierarchy = await getMacroRegimeHierarchy();
    window.macroRegimeHierarchy = macroRegimeHierarchy && typeof macroRegimeHierarchy === 'object'
      ? macroRegimeHierarchy
      : null;

    // Health
    const status = await getStatus();
    if (status) {
      window.apiStatus = status;
      window.apiHealth = status;
      const lastUpdate = status.last_updates && status.last_updates.news;
      if (lastUpdate) {
        const diff = Date.now() - new Date(lastUpdate).getTime();
        const mins = Math.floor(diff / 60000);
        console.log('[API] Data freshness: news updated ' + mins + ' min ago');
      }
    }

    const portfolioRiskFreshnessSource = portfolioRiskProfile && (
      portfolioRiskProfile.status
      || portfolioRiskProfile.freshness
      || (portfolioRiskProfile.data && portfolioRiskProfile.data.generated_at)
    )
      ? {
          status: String(
            portfolioRiskProfile.status
              || (portfolioRiskProfile.data && portfolioRiskProfile.data.status)
              || '',
          ).trim().toLowerCase(),
          freshness: portfolioRiskProfile.freshness
            || (portfolioRiskProfile.data && (portfolioRiskProfile.data.freshness || portfolioRiskProfile.data.generated_at))
            || null,
        }
      : null;
    const liveFreshnessContract = buildLiveFreshnessContract(
      window.ingestionHealth || null,
      window.apiHealth || null,
      [portfolioRiskFreshnessSource, window.globalSignalMesh].filter(Boolean),
    );
    window.liveFreshnessContract = liveFreshnessContract;
    if (liveFreshnessContract.contractState === 'stale') {
      contractWarnings.push('ingestion-contract-stale');
    } else if (liveFreshnessContract.contractState === 'degraded') {
      contractWarnings.push('ingestion-contract-degraded');
    } else if (liveFreshnessContract.contractState === 'unknown') {
      contractWarnings.push('ingestion-contract-unknown');
    }

    // Show LIVE badge
    const badge = document.createElement('span');
    badge.id = 'live-badge';
    badge.style.cssText = 'position:fixed;bottom:12px;right:12px;background:#10b981;color:white;font-size:11px;padding:4px 10px;border-radius:20px;z-index:9999;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.3)';
    badge.textContent = '● LIVE';
    document.body.appendChild(badge);

    // Refresh app.js widgets if already loaded
    if (typeof window.renderNewsFeed === 'function' && window.newsItems) {
      window.renderNewsFeed();
      console.log('[API] ✅ News feed refreshed');
    }

    // Dispatch event to trigger app.js applyLiveDashboardData
    const liveEvent = new CustomEvent('financecopilot:live-dashboard-updated', {
      detail: {
        data: {
          newsItems: window.newsItems || [],
          forecasts: window.liveForecasts || [],
          forecastScoreboard: window.liveForecastScoreboard || null,
          geopoliticalRiskGraph: window.geopoliticalRiskGraph || null,
          eventImpactHorizonMatrix: window.eventImpactHorizonMatrix || null,
          tradeIdeas: window.tradeIdeas || [],
          alerts: window.alertTimeline || [],
          topMovers: window.topMovers || [],
          stocks: window.liveStocks || {},
          topStocks: window.topStocks || [],
          opportunities: window.liveOpportunities || [],
          copilotStart: window.copilotStart || null,
          sectorPerformance: window.sectorPerformance || [],
          story: window.storyData || null,
          marketCalendar: window.marketCalendar || null,
          marketDrivers: window.marketDrivers || [],
          insiderBehavior: window.insiderBehavior || null,
          llmJudgeData: window.llmJudgeData || null,
          judgeDecisionJournal: window.judgeDecisionJournal || null,
          finalGlobalForecastGate: window.finalGlobalForecastGate || null,
          kpis: window.liveKpis || null,
          portfolioSummary: window.livePortfolioSummary || null,
          portfolioRiskProfile: window.livePortfolioRiskProfile || null,
          portfolioRiskProfileStatus: window.livePortfolioRiskProfileStatus || null,
          portfolioHealth: window.livePortfolioHealth || null,
          stockSummaryFreshness: window.livePortfolioSummaryFreshness || null,
          portfolioRiskProfileFreshness: window.livePortfolioRiskProfileFreshness || null,
          kpiFreshness: window.liveKpisFreshness || null
        },
        generatedAt: new Date().toISOString(),
        sources: collectLiveDashboardSources(),
        modelVersions: ['live'],
        warnings: contractWarnings,
        freshness: liveFreshnessContract.freshness,
        cache: liveFreshnessContract.freshness,
        contractState: liveFreshnessContract.contractState,
        ingestionHealth: window.ingestionHealth || null,
        globalSignalMesh: window.globalSignalMesh || null,
        finalGlobalForecastGate: window.finalGlobalForecastGate || null,
        macroRegimeHierarchy: window.macroRegimeHierarchy || null
      }
    });
    window.dispatchEvent(liveEvent);

    console.log('[API] ✅ All live data loaded successfully');
  } catch (err) {
    console.error('[API] Failed to load live data:', err);
  }
}

// Auto-refresh
function startAutoRefresh(intervalMs) {
  if (!intervalMs) intervalMs = 120000;
  setInterval(async () => {
    // Clear cache keys to force refresh
    [
      'news',
      'forecasts',
      'stocks',
      'dashboard_performance',
      'alerts',
      'copilot_context',
      'copilot_start',
      'brief_daily',
      'dashboard_allocation',
      'movers',
      'portfolios',
      'final-global-forecast-gate:country=US&horizon=3m',
    ].forEach((key) => clearCacheEntry(key));
    clearCacheEntriesWithPrefix('copilot_context:');
    clearCacheEntriesWithPrefix('copilot_start:');
    clearCacheEntriesWithPrefix('forecasts_scoreboard:');
    clearCacheEntriesWithPrefix('portfolio-risk-profile-');
    await populateWindowGlobals();
  }, intervalMs);
}

// ─── Public API ───────────────────────────────────────────────────────────────

window.FinanceAPI = {
  getNewsFeed,
  getForecasts,
  getWalkForwardScoreboard,
  getGeopoliticalRiskGraph,
  getEventImpactHorizonMatrix,
  getStockPrices,
  getTopMovers,
  getAlerts,
  getStatus,
  getHealth,
  getGlobalSignalMesh,
  getFinalGlobalForecastGate,
  getMacroRegimeHierarchy,
  getPolicyImpact,
  getInsiderBehavior,
  getJudgeAnalysis,
  getCopilotDecisionJournal,
  getCopilotStart,
  getCopilotContext,
  getDailyBrief,
  getPortfolios,
  getPortfolioRiskProfile,
  getPortfolioHealth,
  transformPortfolioRiskProfileToHealth: transformPortfolioHealth,
  askCopilot,
  executePaperTrade,
  searchUniverse,
  startAutoRefresh,
  getStrategyPlaybooks,
  getCacheStats: () => ({ keys: Object.keys(cache.data), TTL: cache.TTL })
};

window.getLiveDashboardData = () => ({
  data: {
    newsItems: window.newsItems || [],
    forecasts: window.liveForecasts || [],
    forecastScoreboard: window.liveForecastScoreboard || null,
    geopoliticalRiskGraph: window.geopoliticalRiskGraph || null,
    eventImpactHorizonMatrix: window.eventImpactHorizonMatrix || null,
    tradeIdeas: window.tradeIdeas || [],
    alerts: window.alertTimeline || [],
    topMovers: window.topMovers || [],
    stocks: window.liveStocks || {},
    topStocks: window.topStocks || [],
    opportunities: window.liveOpportunities || [],
    copilotStart: window.copilotStart || null,
    sectorPerformance: window.sectorPerformance || [],
    story: window.storyData || null,
    marketCalendar: window.marketCalendar || null,
    marketDrivers: window.marketDrivers || [],
    insiderBehavior: window.insiderBehavior || null,
    kpis: window.liveKpis || null,
    portfolioSummary: window.livePortfolioSummary || null,
    portfolioRiskProfile: window.livePortfolioRiskProfile || null,
    portfolioRiskProfileStatus: window.livePortfolioRiskProfileStatus || null,
    portfolioRiskProfileFreshness: window.livePortfolioRiskProfileFreshness || null,
    portfolioHealth: window.livePortfolioHealth || null,
    llmJudgeData: window.llmJudgeData || null,
    judgeDecisionJournal: window.judgeDecisionJournal || null,
    copilotDecisionJournal: window.copilotDecisionJournal || null,
    finalGlobalForecastGate: window.finalGlobalForecastGate || null,
    macroRegimeHierarchy: window.macroRegimeHierarchy || null
  },
  generatedAt: window.FinanceAPI && window.FinanceAPI.getCacheStats ? new Date().toISOString() : new Date().toISOString(),
  sources: collectLiveDashboardSources(),
  modelVersions: ['live'],
  warnings: window.liveContractWarnings || ['live-connector'],
  freshness: window.liveFreshnessContract && window.liveFreshnessContract.freshness
    ? window.liveFreshnessContract.freshness
    : { lastFetchedAt: Date.now(), ttlMs: cache.TTL },
  cache: window.liveFreshnessContract && window.liveFreshnessContract.freshness
    ? window.liveFreshnessContract.freshness
    : { lastFetchedAt: Date.now(), ttlMs: cache.TTL },
  contractState: window.liveFreshnessContract ? window.liveFreshnessContract.contractState : 'unknown',
  ingestionHealth: window.ingestionHealth || null,
  globalSignalMesh: window.globalSignalMesh || null,
  finalGlobalForecastGate: window.finalGlobalForecastGate || null,
  macroRegimeHierarchy: window.macroRegimeHierarchy || null
});

async function getStrategyPlaybooks(params = {}) {
  const {
    limit = 10,
    min_confidence = 0.5,
    ticker = '',
    portfolio_id = '',
    profile = 'equity_1w',
    sort_by = 'confidence',
    sort_order = 'desc',
    debug = false
  } = params;
  const queryParams = new URLSearchParams({
    limit: String(limit),
    min_confidence: String(min_confidence),
    profile,
    sort_by,
    sort_order
  });
  if (ticker) queryParams.append('ticker', ticker);
  if (portfolio_id) queryParams.append('portfolio_id', portfolio_id);
  if (debug) queryParams.append('debug', 'true');
  
  try {
    const response = await fetch(API_BASE + '/judge/strategy-playbooks?' + queryParams.toString(), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) return null;
    const payload = await response.json();
    const data = payload.data || payload;
    return {
      ok: payload.ok ?? true,
      status: payload.status || data.status || 'ok',
      data,
      freshness: payload.freshness || payload.data?.generated_at || new Date().toISOString(),
      source: data.source || payload.source || ['judge_strategy_playbooks'],
      error: payload.error || data.error || null,
      warnings: extractArray(data, ['warnings'], extractArray(payload, ['warnings']))
    };
  } catch (error) {
    console.warn('[API] Error fetching strategy playbooks:', error.message);
    return null;
  }
}

window.refreshLiveData = async () => {
  await populateWindowGlobals();
  return window.getLiveDashboardData();
};

window.initLiveData = async () => {
  await populateWindowGlobals();
};

// Run on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    populateWindowGlobals();
    startAutoRefresh(120000);
  });
} else {
  populateWindowGlobals();
  startAutoRefresh(120000);
}

console.log('[API] FinanceAPI connector loaded');

// Export strategy playbooks API
window.getStrategyPlaybooks = getStrategyPlaybooks;
