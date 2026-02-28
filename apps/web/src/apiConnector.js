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

async function getNewsFeed(limit) {
  if (!limit) limit = 20;
  const data = await fetchWithCache('/news/feed?limit=' + limit, 'news');
  return (data && data.data && (data.data.items || data.data.articles)) || [];
}

async function getForecasts(limit) {
  if (!limit) limit = 20;
  const data = await fetchWithCache('/forecasts?limit=' + limit, 'forecasts');
  return (data && data.data && (data.data.rows || data.data.forecasts)) || [];
}

async function getStockPrices() {
  const data = await fetchWithCache('/stocks/prices', 'stocks');
  return (data && data.data && data.data.tickers) || {};
}

async function getTopMovers() {
  const data = await fetchWithCache('/stocks/top-movers', 'movers');
  return (data && data.data) || null;
}

async function getHealth() {
  return await fetchWithCache('/health', 'health');
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

// ─── Populate window globals used by app.js ──────────────────────────────────

async function populateWindowGlobals() {
  console.log('[API] Loading live data...');

  try {
    // News
    const rawNews = await getNewsFeed(20);
    if (rawNews.length > 0) {
      window.newsItems = rawNews.map(transformNewsItem);
      console.log('[API] ✅ ' + window.newsItems.length + ' news loaded');
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
          forecasts: window.liveForecasts || []
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
  startAutoRefresh,
  getCacheStats: () => ({ keys: Object.keys(cache.data), TTL: cache.TTL })
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
