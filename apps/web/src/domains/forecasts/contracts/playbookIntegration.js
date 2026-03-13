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

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function toFiniteNumber(value, fallback = NaN) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : fallback;
}

function normalizePercentValue(value, fallback = NaN) {
  const numericValue = toFiniteNumber(value, fallback);
  if (!Number.isFinite(numericValue)) {
    return fallback;
  }
  return Math.abs(numericValue) > 1 ? numericValue / 100 : numericValue;
}

function formatPercentValue(value) {
  const normalized = Math.round(toFiniteNumber(value, 0) * 10000) / 100;
  const sign = normalized >= 0 ? '+' : '';
  return `${sign}${normalized.toFixed(2)}%`;
}

function formatBpsValue(value) {
  const normalized = Math.round(toFiniteNumber(value, 0) * 10) / 10;
  return `${normalized.toFixed(Number.isInteger(normalized) ? 0 : 1)} bps`;
}

function describeCostAdjustedReturn(playbook) {
  const expectedReturn = normalizePercentValue(playbook.expected_return, NaN);
  const costAwareness = playbook && typeof playbook.cost_awareness === 'object'
    ? playbook.cost_awareness
    : null;

  if (!costAwareness) {
    return {
      color: Number.isFinite(expectedReturn) && expectedReturn < 0 ? 'negative' : 'positive',
      label: Number.isFinite(expectedReturn) ? formatPercentValue(expectedReturn) : '',
      title: 'Expected return',
    };
  }

  const grossExpectedReturnPct = normalizePercentValue(
    costAwareness.gross_expected_return_pct,
    expectedReturn,
  );
  const netExpectedReturnPct = normalizePercentValue(
    costAwareness.net_expected_return_pct,
    NaN,
  );
  const feeBps = toFiniteNumber(costAwareness.fee_bps, NaN);
  const slippageBps = toFiniteNumber(costAwareness.slippage_bps, NaN);
  const estimatedTaxDragBps = toFiniteNumber(costAwareness.estimated_tax_drag_bps, NaN);
  const hasLowNetEdge = Number.isFinite(grossExpectedReturnPct)
    && grossExpectedReturnPct > 0
    && Number.isFinite(netExpectedReturnPct)
    && (netExpectedReturnPct <= 0 || netExpectedReturnPct <= grossExpectedReturnPct * 0.25);

  if (!Number.isFinite(netExpectedReturnPct)) {
    return {
      color: Number.isFinite(expectedReturn) && expectedReturn < 0 ? 'negative' : 'positive',
      label: Number.isFinite(expectedReturn) ? formatPercentValue(expectedReturn) : '',
      title: 'Expected return',
    };
  }

  const titleParts = [
    Number.isFinite(grossExpectedReturnPct)
      ? `Gross edge ${formatPercentValue(grossExpectedReturnPct)} -> Net edge ${formatPercentValue(netExpectedReturnPct)}`
      : `Net edge ${formatPercentValue(netExpectedReturnPct)}`,
    Number.isFinite(feeBps) ? `Fees ${formatBpsValue(feeBps)}` : '',
    Number.isFinite(slippageBps) ? `Slippage ${formatBpsValue(slippageBps)}` : '',
    Number.isFinite(estimatedTaxDragBps) ? `Tax drag ${formatBpsValue(estimatedTaxDragBps)}` : '',
    hasLowNetEdge
      ? (netExpectedReturnPct <= 0 ? 'Costs overwhelm edge' : 'Low net edge after costs')
      : '',
  ].filter(Boolean);

  return {
    color: netExpectedReturnPct < 0 ? 'negative' : 'positive',
    label: `${hasLowNetEdge && netExpectedReturnPct > 0 ? 'Low Net ' : 'Net '}${formatPercentValue(netExpectedReturnPct)}`,
    title: titleParts.join(' | '),
  };
}

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

  const returnSummary = describeCostAdjustedReturn(playbook);
  if (!returnSummary.label) {
    return '';
  }

  return `<span class="playbook-return ${returnSummary.color}" title="${escapeHtml(returnSummary.title)}">${escapeHtml(returnSummary.label)}</span>`;
}

/**
 * Get policy guardrail indicator HTML for a ticker.
 * Reuses the playbook payload instead of introducing a separate UI contract.
 * @param {string} ticker - Stock ticker symbol
 * @returns {Promise<string>} HTML policy indicator
 */
async function getPolicyGuardrailBadge(ticker) {
  const playbook = await getPlaybookForTicker(ticker);

  if (!playbook || !playbook.policy_guardrails || typeof playbook.policy_guardrails !== 'object') {
    return '';
  }

  const guardrails = playbook.policy_guardrails;
  const status = String(guardrails.status || 'ok').trim().toLowerCase();
  const violationCount = Number.isFinite(guardrails.violation_count)
    ? guardrails.violation_count
    : 0;

  if (status !== 'violated' && status !== 'review') {
    return '';
  }

  const effectiveAction = String(guardrails.effective_action || playbook.decision || 'hold')
    .trim()
    .toUpperCase();
  const badgeClass = status === 'violated' ? 'badge-policy-violated' : 'badge-policy-review';
  const title = violationCount > 0
    ? `Policy guardrail active: ${violationCount} issue(s), effective action ${effectiveAction}`
    : `Policy guardrail active: effective action ${effectiveAction}`;

  return `
    <span class="playbook-badge ${badgeClass}" title="${title}">
      🛡 ${effectiveAction}
    </span>
  `;
}

/**
 * Render the standard playbook markup used in ticker-based widgets.
 * Keeps badge/risk/return assembly in one place to avoid duplicate helpers.
 * @param {string} ticker - Stock ticker symbol
 * @returns {Promise<string>} Combined playbook markup
 */
async function renderTickerPlaybookSummary(ticker) {
  const [badgeHtml, policyHtml, riskHtml, returnHtml] = await Promise.all([
    getDecisionBadge(ticker),
    getPolicyGuardrailBadge(ticker),
    getRiskIndicator(ticker),
    getExpectedReturn(ticker)
  ]);

  return `${badgeHtml}${policyHtml}${riskHtml}${returnHtml}`;
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
  getPolicyGuardrailBadge,
  getRiskIndicator,
  getExpectedReturn,
  renderTickerPlaybookSummary,
  clearPlaybookCache,
  initPlaybookIntegration
};

console.log('[PlaybookIntegration] Strategy playbooks integration helper loaded');
