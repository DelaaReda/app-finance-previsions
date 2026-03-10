/**
 * Strategy Playbooks Integration Helper
 * 
 * Provides utilities for integrating strategy playbook recommendations
 * into dashboard widgets (top-movers, news-impact, stock-relationships).
 * 
 * @module playbookIntegration
 */

// Cache for playbook data to avoid repeated API calls
let playbookCache = null;
let cacheTimestamp = null;
const CACHE_TTL_MS = 120000; // 2 minutes

/**
 * Fetch and cache strategy playbooks from the Judge API
 * @returns {Promise<Array>} Array of playbook objects
 */
async function fetchPlaybooks() {
  const now = Date.now();
  
  // Return cached data if still valid
  if (playbookCache && cacheTimestamp && (now - cacheTimestamp) < CACHE_TTL_MS) {
    return playbookCache;
  }
  
  try {
    const result = await window.getStrategyPlaybooks({
      limit: 50,
      min_confidence: 0.5,
      profile: 'equity_1w'
    });
    
    if (result && result.data && result.data.playbooks) {
      playbookCache = result.data.playbooks;
      cacheTimestamp = now;
      return playbookCache;
    }
  } catch (error) {
    console.warn('[PlaybookIntegration] Failed to fetch playbooks:', error.message);
  }
  
  return [];
}

/**
 * Get playbook recommendation for a specific ticker
 * @param {string} ticker - Stock ticker symbol
 * @returns {Promise<Object|null>} Playbook object or null if not found
 */
async function getPlaybookForTicker(ticker) {
  const playbooks = await fetchPlaybooks();
  const normalizedTicker = ticker.toUpperCase().trim();
  
  return playbooks.find(pb => 
    pb.ticker && pb.ticker.toUpperCase() === normalizedTicker
  ) || null;
}

/**
 * Get decision badge HTML for a ticker
 * @param {string} ticker - Stock ticker symbol
 * @returns {Promise<string>} HTML badge element
 */
async function getDecisionBadge(ticker) {
  const playbook = await getPlaybookForTicker(ticker);
  
  if (!playbook) {
    return '<span class="playbook-badge badge-neutral">No Data</span>';
  }
  
  const { decision, confidence } = playbook;
  const confidencePct = Math.round(confidence * 100);
  
  let badgeClass = 'badge-neutral';
  let badgeText = 'HOLD';
  let badgeIcon = '⏸';
  
  if (decision === 'go') {
    badgeClass = 'badge-go';
    badgeText = 'BUY';
    badgeIcon = '🟢';
  } else if (decision === 'no_go') {
    badgeClass = 'badge-no-go';
    badgeText = 'SELL';
    badgeIcon = '🔴';
  }
  
  return `
    <span class="playbook-badge ${badgeClass}" title="Confidence: ${confidencePct}%">
      ${badgeIcon} ${badgeText}
    </span>
  `;
}

/**
 * Get risk indicator HTML for a ticker
 * @param {string} ticker - Stock ticker symbol
 * @returns {Promise<string>} HTML risk indicator
 */
async function getRiskIndicator(ticker) {
  const playbook = await getPlaybookForTicker(ticker);
  
  if (!playbook) {
    return '';
  }
  
  const { risk_level } = playbook;
  let riskClass = 'risk-medium';
  let riskIcon = '⚠';
  
  if (risk_level === 'low') {
    riskClass = 'risk-low';
    riskIcon = '🟢';
  } else if (risk_level === 'medium') {
    riskClass = 'risk-medium';
    riskIcon = '⚠';
  } else if (risk_level === 'high') {
    riskClass = 'risk-high';
    riskIcon = '🔴';
  } else if (risk_level === 'critical') {
    riskClass = 'risk-critical';
    riskIcon = '⛔';
  }
  
  return `
    <span class="playbook-risk ${riskClass}" title="Risk: ${risk_level}">
      ${riskIcon}
    </span>
  `;
}

/**
 * Get expected return indicator for a ticker
 * @param {string} ticker - Stock ticker symbol
 * @returns {Promise<string>} Formatted expected return
 */
async function getExpectedReturn(ticker) {
  const playbook = await getPlaybookForTicker(ticker);
  
  if (!playbook) {
    return '';
  }
  
  const { expected_return } = playbook;
  const returnPct = (expected_return * 100).toFixed(2);
  const sign = expected_return >= 0 ? '+' : '';
  const color = expected_return >= 0 ? 'positive' : 'negative';
  
  return `<span class="playbook-return ${color}">${sign}${returnPct}%</span>`;
}

/**
 * Clear the playbook cache
 */
function clearPlaybookCache() {
  playbookCache = null;
  cacheTimestamp = null;
}

/**
 * Initialize playbook integration for a widget
 * @param {string} widgetId - Widget container ID
 * @param {Function} renderCallback - Callback to render playbook data
 */
async function initPlaybookIntegration(widgetId, renderCallback) {
  try {
    const playbooks = await fetchPlaybooks();
    renderCallback(playbooks);
  } catch (error) {
    console.error(`[PlaybookIntegration] Error initializing ${widgetId}:`, error.message);
  }
}

// Export to window for widget access
window.PlaybookIntegration = {
  fetchPlaybooks,
  getPlaybookForTicker,
  getDecisionBadge,
  getRiskIndicator,
  getExpectedReturn,
  clearPlaybookCache,
  initPlaybookIntegration
};

console.log('[PlaybookIntegration] Strategy playbooks integration helper loaded');
