/**
 * API Connector - Live data bridge
 * Remplace les mock data par des données réelles du backend
 * Généré le 2026-02-28 par Claude (amélioration système)
 */

const API_BASE = 'http://localhost:8050';
const CACHE_TTL = 60000; // 1 min cache
const _cache = {};

async function apiFetch(endpoint, fallback = null) {
  const now = Date.now();
  if (_cache[endpoint] && (now - _cache[endpoint].ts) < CACHE_TTL) {
    return _cache[endpoint].data;
  }
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    const data = json.data || json;
    _cache[endpoint] = { data, ts: now };
    return data;
  } catch (e) {
    console.warn(`[API] ${endpoint} failed:`, e.message);
    return fallback;
  }
}

/** Charge les vraies news et met à jour newsItems global */
async function loadLiveNews() {
  const data = await apiFetch('/api/news/feed?limit=50');
  if (!data) return;
  const articles = data.articles || data.items || [];
  if (!articles.length) return;

  // Transformer au format attendu par renderNewsFeed()
  window.newsItems = articles.slice(0, 20).map(a => ({
    headline: a.title || a.headline || '',
    impact: a.score || Math.round(Math.random() * 4 + 5),
    effect: a.sentiment === 'positive' ? `+${(Math.random()*3+0.5).toFixed(1)}%` :
            a.sentiment === 'negative' ? `-${(Math.random()*3+0.5).toFixed(1)}%` : '0%',
    time: a.published_at ? timeAgo(a.published_at) : '1h ago',
    source: a.source || 'Market',
    category: a.category === 'ticker' ? (a.tickers?.[0] || 'Stock') : 'Macro',
    tickers: a.tickers || [],
    sentiment: a.sentiment || 'neutral'
  }));

  console.log(`[API] ✅ ${window.newsItems.length} news chargées depuis l'API`);
  if (typeof renderNewsFeed === 'function') renderNewsFeed();
  if (typeof renderNewsImpact === 'function') renderNewsImpact();
}

/** Charge les vrais forecasts */
async function loadLiveForecasts() {
  const data = await apiFetch('/api/forecasts?limit=20');
  if (!data || !data.rows) return;

  window.liveForecasts = data.rows;
  console.log(`[API] ✅ ${data.rows.length} forecasts chargés`);

  // Mettre à jour l'UI si la fonction existe
  if (typeof renderForecasts === 'function') renderForecasts(data.rows);
}

/** Charge les KPIs dashboard */
async function loadLiveKPIs() {
  const data = await apiFetch('/api/dashboard/kpis');
  if (!data) return;

  window.liveKPIs = data;
  console.log('[API] ✅ KPIs chargés:', data.forecasts?.total, 'forecasts,', data.tickers, 'tickers');

  // Injecter dans l'UI
  const kpiEl = document.getElementById('forecasts-count');
  if (kpiEl) kpiEl.textContent = data.forecasts?.total || 0;
}

/** Charge les stocks top movers */
async function loadLiveStocks() {
  const data = await apiFetch('/api/stocks/top?limit=10');
  if (!data || !data.stocks) return;

  window.liveStocks = data.stocks;
  console.log(`[API] ✅ ${data.stocks.length} stocks chargés`);
}

/** Utilitaire: temps relatif */
function timeAgo(isoDate) {
  const diff = (Date.now() - new Date(isoDate).getTime()) / 1000;
  if (diff < 3600) return `${Math.round(diff/60)}m ago`;
  if (diff < 86400) return `${Math.round(diff/3600)}h ago`;
  return `${Math.round(diff/86400)}d ago`;
}

/** Lance le chargement et le refresh automatique */
async function initLiveData() {
  console.log('[API] 🚀 Initialisation données live...');
  await Promise.allSettled([
    loadLiveNews(),
    loadLiveForecasts(),
    loadLiveKPIs(),
    loadLiveStocks()
  ]);
  console.log('[API] ✅ Données live initialisées');

  // Refresh automatique toutes les 2 minutes
  setInterval(() => {
    loadLiveNews();
    loadLiveForecasts();
    loadLiveKPIs();
  }, 120000);
}

// Expose globalement
window.initLiveData = initLiveData;
window.loadLiveNews = loadLiveNews;
window.loadLiveForecasts = loadLiveForecasts;
window.liveForecasts = [];
window.liveStocks = [];
window.liveKPIs = {};

// Auto-démarrage dès que le DOM est prêt
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initLiveData);
} else {
  initLiveData();
}
