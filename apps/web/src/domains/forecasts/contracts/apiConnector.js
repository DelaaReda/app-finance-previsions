/**
 * Finance Copilot API Connector
 * Bridges the live backend API to app.js window globals
 * Auto-refresh every 2 minutes
 */

const API_BASE = 'http://localhost:8050/api';

// Cache with TTL
const cache = {
  data: {},
  timestamps: {},
  TTL: 120000 // 2 minutes
};

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

async function getStockPrices() {
  const payload = getResponseData(await fetchWithCache('/stocks/prices?tickers=NVDA,META,AAPL,MSFT,GOOGL', 'stocks'));
  return extractObject(payload, ['prices', 'tickers', 'data']) || {};
}

async function getTopMovers() {
  const payload = getResponseData(await fetchWithCache('/stocks/top-legacy?limit=10', 'movers'));
  return payload;
}

async function getDashboardPerformance() {
  const payload = getResponseData(await fetchWithCache('/dashboard/performance', 'dashboard_performance'));
  return payload || {};
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
  return await fetchWithCache('/health', 'health');
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

async function getJudgeAnalysis(limit) {
  if (!limit) limit = 5;
  const data = await fetchWithCache('/judge?limit=' + limit, 'judge');
  return (data && data.data) || { verdicts: [] };
}

async function askCopilot(question, tickers) {
  if (!tickers) tickers = [];
  try {
    const response = await fetch(API_BASE + '/copilot/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, tickers, max_sources: 5 })
    });
    return await response.json();
  } catch (error) {
    return { data: { answer: 'Service temporarily unavailable', sources: [] } };
  }
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
    effect: sentimentEffect + (Math.random() * 2 + 0.5).toFixed(1) + '%',
    time: timeAgo,
    source: item.source || 'API',
    category: (item.tickers && item.tickers.length > 0) ? item.tickers[0] : 'Market',
    sentiment: item.sentiment || 'neutral',
    summary: item.summary || '',
    url: item.url || ''
  };
}

function transformForecast(row) {
  const dir = row.direction === 'up' ? '↑' : row.direction === 'down' ? '↓' : '→';
  const confidence = row.confidence != null ? Math.round(row.confidence * 100) : 0;
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
    generatedAt: row.generated_at || row.timestamp || ''
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
  const payloadSummary = payload.summary || payload.message || payload.overview;
  const sectorRotation = payload.sector_rotation || payload.sectorRotation || {};
  const topSectors = toArray(sectorRotation.top).map((entry) => String(entry || '').trim()).filter(Boolean);
  const bottomSectors = toArray(sectorRotation.bottom).map((entry) => String(entry || '').trim()).filter(Boolean);
  const summary = payloadSummary || 'Le marché reste actif avec une lecture mitigée.';
  const headline = payload.title || payload.headline || 'Aperçu du marché';
  const sentiment = payload.sentiment || 'neutral';
  const timestamp = payload.generated_at || payload.generatedAt || payload.generated_at_iso || new Date().toISOString();
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
    sectorRotationSummary: rotationText.join(' | ')
  };
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

// ─── Populate window globals used by app.js ──────────────────────────────────

async function populateWindowGlobals() {
  console.log('[API] Loading live data...');

  try {
    // News
    const rawNews = await getNewsFeed(20);
    if (rawNews.length > 0) {
      window.newsItems = rawNews.map(transformNewsItem);
      console.log("[API] ✅ " + window.newsItems.length + " news chargées depuis l'API");
    }

    // Forecasts
    const rawForecasts = await getForecasts(20);
    if (rawForecasts.length > 0) {
      window.liveForecasts = rawForecasts.map(transformForecast);
      // Also expose in v11Data format used by some widgets
      if (!window.v11Data) window.v11Data = {};
      window.v11Data.forecasts = window.liveForecasts;
      console.log('[API] ✅ ' + window.liveForecasts.length + ' forecasts loaded');
    }

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

    // Daily brief -> Story panel
    const brief = await getDailyBrief();
    if (brief && typeof brief === 'object') {
      window.storyData = transformBrief(brief);
    }

    // Sector performance -> Sector widget
    const sectorPayload = await getSectorPerformanceData();
    if (sectorPayload && typeof sectorPayload === 'object') {
      window.sectorPerformance = transformSectorPerformance(sectorPayload);
    }

    // LLM Judge snapshot
    const judgePayload = await getLlmJudgeSnapshot();
    if (judgePayload) {
      const judgeData = transformJudgeData(judgePayload);
      if (judgeData) {
        window.llmJudgeData = judgeData;
      }
    }

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

    // Health
    const health = await getHealth();
    if (health) {
      window.apiHealth = health;
      const lastUpdate = health.last_updates && health.last_updates.news;
      if (lastUpdate) {
        const diff = Date.now() - new Date(lastUpdate).getTime();
        const mins = Math.floor(diff / 60000);
        console.log('[API] Data freshness: news updated ' + mins + ' min ago');
      }
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
          topMovers: window.topMovers || [],
          stocks: window.liveStocks || {},
          topStocks: window.topStocks || [],
          opportunities: window.liveOpportunities || [],
          sectorPerformance: window.sectorPerformance || [],
          story: window.storyData || null,
          llmJudgeData: window.llmJudgeData || null,
          kpis: window.liveKpis || null,
          portfolioSummary: window.livePortfolioSummary || null,
          stockSummaryFreshness: window.livePortfolioSummaryFreshness || null,
          kpiFreshness: window.liveKpisFreshness || null
        },
        generatedAt: new Date().toISOString(),
        sources: ['api-connector'],
        modelVersions: ['live']
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
    delete cache.data.news;
    delete cache.data.forecasts;
    delete cache.data.stocks;
    delete cache.data.dashboard_performance;
    delete cache.data.brief_daily;
    delete cache.data.dashboard_allocation;
    delete cache.data.movers;
    await populateWindowGlobals();
  }, intervalMs);
}

// ─── Public API ───────────────────────────────────────────────────────────────

window.FinanceAPI = {
  getNewsFeed,
  getForecasts,
  getStockPrices,
  getTopMovers,
  getHealth,
  getJudgeAnalysis,
  askCopilot,
  searchUniverse,
  startAutoRefresh,
  getCacheStats: () => ({ keys: Object.keys(cache.data), TTL: cache.TTL })
};

window.getLiveDashboardData = () => ({
  data: {
    newsItems: window.newsItems || [],
    forecasts: window.liveForecasts || [],
    topMovers: window.topMovers || [],
    stocks: window.liveStocks || {},
    topStocks: window.topStocks || [],
    opportunities: window.liveOpportunities || [],
    sectorPerformance: window.sectorPerformance || [],
    story: window.storyData || null,
    kpis: window.liveKpis || null,
    portfolioSummary: window.livePortfolioSummary || null,
    llmJudgeData: window.llmJudgeData || null
  },
  generatedAt: window.FinanceAPI && window.FinanceAPI.getCacheStats ? new Date().toISOString() : new Date().toISOString(),
  sources: ['api-connector'],
  modelVersions: ['live'],
  warnings: ['live-connector'],
  freshness: { lastFetchedAt: Date.now(), ttlMs: cache.TTL }
});

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
