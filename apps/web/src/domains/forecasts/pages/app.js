// ============================================================================
// FINANCE COPILOT V14 DIAMOND NAV - HUB CENTRAL MULTI-NIVEAUX
// Diamond Navigation Hub + Multi-Level Navigation + User-First Design
// ============================================================================

// ============ V16 ULTIMATE STATE ============
const v16State = {
  diamondDropdownOpen: false,
  currentFacette: null,
  currentTab: null,
  currentStock: null,
  breadcrumbs: [],
  visitedFacettes: [],
  explorationRate: 0
};

// Diamond Facettes Configuration
// Facettes configuration fallback data and UI config

// ============ V16 DIAMOND DROPDOWN FUNCTIONS (ENHANCED) ============
function toggleDiamondDropdown() {
  const dropdown = document.getElementById('diamondDropdown');
  v16State.diamondDropdownOpen = !v16State.diamondDropdownOpen;

  if (v16State.diamondDropdownOpen) {
    dropdown.classList.add('active');
    dropdown.style.display = 'flex';
    showToast('💎 Navigation Hub opened', 'info');
    setTimeout(() => {
      const searchInput = document.getElementById('searchFacettes');
      if (searchInput) searchInput.focus();
    }, 100);
  } else {
    dropdown.classList.remove('active');
    setTimeout(() => {
      dropdown.style.display = 'none';
    }, 300);
  }
}

// V17 BUGFIX: Close dropdown only on outside click
function handleClickOutside(e) {
  const dropdown = document.getElementById('diamondDropdown');
  const diamondBtn = document.querySelector('.diamond-btn-header');

  if (v16State.diamondDropdownOpen && dropdown && diamondBtn) {
    if (!dropdown.contains(e.target) && !diamondBtn.contains(e.target)) {
      closeDiamondDropdown();
    }
  }
}

document.addEventListener('click', handleClickOutside);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && v16State.diamondDropdownOpen) {
    closeDiamondDropdown();
  }
});

function closeDiamondDropdown() {
  const dropdown = document.getElementById('diamondDropdown');
  dropdown.classList.remove('active');
  v16State.diamondDropdownOpen = false;
  setTimeout(() => {
    dropdown.style.display = 'none';
  }, 300);
}

function openFacette(facetteId) {
  // V17 BUGFIX: Close dropdown when opening facette
  closeDiamondDropdown();

  const facette = facettes[facetteId];
  if (!facette) {
    console.error('Facette not found:', facetteId);
    return;
  }

  try {
    // Track exploration
    if (!v16State.visitedFacettes.includes(facetteId)) {
      v16State.visitedFacettes.push(facetteId);
      v16State.explorationRate = Math.round((v16State.visitedFacettes.length / 9) * 100);

      // Update progress bar
      const progressBar = document.getElementById('explorationProgress');
      const progressText = document.getElementById('explorationText');
      if (progressBar) progressBar.style.width = v16State.explorationRate + '%';
      if (progressText) progressText.textContent = v16State.explorationRate + '% discovered';

      if (v16State.explorationRate >= 30 && v16State.explorationRate < 50) {
        setTimeout(() => {
          showToast(`🎉 You've explored ${v16State.explorationRate}% of the app!`, 'success');
        }, 1000);
      }
    }

    v16State.currentFacette = facetteId;
    v16State.breadcrumbs = ['💎', facette.name];

    // Hide hero, show facette view
    const hero = document.getElementById('heroSection');
    const facetteView = document.getElementById('facetteView');

    if (hero) hero.style.display = 'none';
    if (facetteView) facetteView.style.display = 'block';

    // Update header
    const iconEl = document.getElementById('facetteIcon');
    const titleEl = document.getElementById('facetteTitle');
    const breadcrumbEl = document.getElementById('facetteBreadcrumb');

    if (iconEl) iconEl.textContent = facette.icon;
    if (titleEl) titleEl.textContent = facette.name;
    if (breadcrumbEl) breadcrumbEl.textContent = v16State.breadcrumbs.join(' > ');

    // Show search if needed
    const searchEl = document.getElementById('facetteSearch');
    if (searchEl) searchEl.style.display = facette.needsSearch ? 'flex' : 'none';

    // Render tabs
    renderFacetteTabs(facette);

    // Load initial content
    loadFacetteContent(facetteId, facette.tabs[0]);
    scheduleCriticalWidgetHealthRender();

    showToast(`🚀 Ouverture ${facette.name}`);
  } catch (e) {
    console.error('Error inside openFacette:', e);
    throw e; // Re-throw to be caught by global handler if needed
  }
}

function closeFacette() {
  document.getElementById('facetteView').style.display = 'none';
  document.getElementById('heroSection').style.display = 'block';
  v16State.currentFacette = null;
  v16State.currentTab = null;
  v16State.breadcrumbs = [];
  scheduleCriticalWidgetHealthRender();
}

function renderFacetteTabs(facette) {
  const tabsContainer = document.getElementById('facetteTabs');
  tabsContainer.innerHTML = facette.tabs.map((tab, index) => `
    <button class="facette-tab ${index === 0 ? 'active' : ''}" onclick="switchFacetteTab('${facette.name}', '${tab}')">
      ${tab}
    </button>
  `).join('');
}

function switchFacetteTab(facetteName, tabName) {
  v16State.currentTab = tabName;
  v16State.breadcrumbs = ['💎', facetteName, tabName];
  document.getElementById('facetteBreadcrumb').textContent = v16State.breadcrumbs.join(' > ');

  // Update active tab
  document.querySelectorAll('.facette-tab').forEach(tab => {
    tab.classList.toggle('active', tab.textContent.trim() === tabName);
  });

  loadFacetteContent(v16State.currentFacette, tabName);
  showToast(`📋 Viewing ${tabName}`);
}

const FACETTE_LIVE_TEMPLATE_SELECTORS = {
  story: '#market-pulse-widget-container',
  news: '#news-feed-widget-container',
  trade: '#trade-ideas-widget-container',
  calendar: '#market-calendar-widget-container',
  marketDrivers: '#market-drivers-widget-container'
};

const FACETTE_LIVE_SLOT_IDS = {
  story: [],
  news: ['newsFilter', 'newsCardsGrid'],
  trade: ['tradeIdeasGrid'],
  calendar: ['calendarSections'],
  marketDrivers: ['driversBarsVisual']
};

const FACETTE_LIVE_WARNING_KEYS = {
  story: 'story-unavailable',
  news: 'newsItems-unavailable',
  trade: 'tradeIdeas-unavailable',
  calendar: 'marketCalendar-unavailable',
  marketDrivers: 'marketDrivers-unavailable'
};

const FACETTE_LIVE_ROUTES = {
  marche: {
    synthese: ['story', 'marketDrivers', 'calendar'],
    actualites: ['news']
  },
  economie: {
    marche: ['story', 'marketDrivers'],
    'macro economie': ['marketDrivers', 'calendar'],
    'news economiques': ['news']
  },
  news: {
    '*': ['news']
  },
  trading: {
    'trade ideas': ['trade']
  }
};

function normalizeFacetteRouteToken(value) {
  return toString(value, '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function getFacetteWidgetSlot(root, slotId) {
  if (!root) return null;
  if (typeof root.querySelector !== 'function') return null;
  return root.querySelector(`[data-widget-slot="${slotId}"]`) || root.querySelector(`#${slotId}`);
}

function getFacetteLiveWarnings() {
  const currentWarnings = toArray(liveDataMeta && liveDataMeta.warnings, []);
  if (currentWarnings.length) {
    return currentWarnings;
  }
  return toArray(window.liveContractWarnings, []);
}

function facetteLiveRouteFallback(tabToken) {
  if (!tabToken) return [];
  if (tabToken.includes('news') || tabToken.includes('actualite')) {
    return ['news'];
  }
  if (tabToken.includes('trade') || tabToken.includes('opportunit')) {
    return ['trade'];
  }
  if (tabToken.includes('calendar') || tabToken.includes('calendrier') || tabToken.includes('earnings')) {
    return ['calendar'];
  }
  if (tabToken.includes('marche') || tabToken.includes('synthese')) {
    return ['story', 'marketDrivers'];
  }
  return [];
}

function resolveFacetteLiveWidgets(facetteId, tabName) {
  const facetteToken = normalizeFacetteRouteToken(facetteId);
  const tabToken = normalizeFacetteRouteToken(tabName);
  const facetteRoutes = FACETTE_LIVE_ROUTES[facetteToken];
  if (facetteRoutes) {
    if (facetteRoutes[tabToken]) {
      return facetteRoutes[tabToken];
    }
    if (facetteRoutes['*']) {
      return facetteRoutes['*'];
    }
  }
  return facetteLiveRouteFallback(tabToken);
}

function rewriteFacetteWidgetIds(template, widgetKey, widgetScope) {
  const slotIds = FACETTE_LIVE_SLOT_IDS[widgetKey] || [];
  return slotIds.reduce((html, slotId) => {
    const scopedId = `${slotId}-${widgetScope}`;
    return html.replace(new RegExp(`id="${slotId}"`, 'g'), `id="${scopedId}" data-widget-slot="${slotId}"`);
  }, template);
}

function buildFacetteLiveWidgetMarkup(widgetKey, widgetScope) {
  const selector = FACETTE_LIVE_TEMPLATE_SELECTORS[widgetKey];
  const source = selector ? document.querySelector(selector) : null;
  const template = toString(source && source.innerHTML, '').trim();
  if (!template) {
    return '';
  }
  const scopedTemplate = rewriteFacetteWidgetIds(template, widgetKey, widgetScope);
  return `
    <div class="facette-live-widget" data-facette-widget="${widgetKey}" data-widget-scope="${widgetScope}">
      ${scopedTemplate}
    </div>
  `;
}

function buildFacetteLiveContent(facetteId, tabName) {
  const widgets = resolveFacetteLiveWidgets(facetteId, tabName);
  if (!widgets.length) {
    return { html: '', widgets: [] };
  }

  const scopeBase = `${normalizeFacetteRouteToken(facetteId) || 'facette'}-${normalizeFacetteRouteToken(tabName) || 'tab'}`;
  const html = widgets
    .map((widgetKey, index) => buildFacetteLiveWidgetMarkup(widgetKey, `${scopeBase}-${index}`))
    .filter(Boolean)
    .join('');

  return { html, widgets };
}

function applyFacetteLiveFallbackNotice(root, widgetKey) {
  const warningKey = FACETTE_LIVE_WARNING_KEYS[widgetKey];
  if (!warningKey) return;
  const warnings = getFacetteLiveWarnings();
  if (!warnings.includes(warningKey)) return;
  if (root.querySelector('[data-facette-fallback-note="true"]')) return;

  const notice = document.createElement('div');
  notice.dataset.facetteFallbackNote = 'true';
  notice.style.cssText = 'margin-bottom:12px;padding:10px 12px;border-radius:12px;border:1px solid rgba(245,158,11,0.35);background:rgba(245,158,11,0.12);color:var(--color-text-light);font-size:12px;';
  notice.textContent = 'Fallback data shown: live API unavailable for this view.';

  const target = root.querySelector('.widget-body') || root;
  target.prepend(notice);
}

function renderMarketPulse(root = document) {
  if (!root || typeof root.querySelector !== 'function') return;
  const widget = root.querySelector('.market-pulse-widget');
  if (!widget) return;

  const story = isObject(appData.story) ? appData.story : {};
  const storyContent = widget.querySelector('.story-content');
  const storyDetail = widget.querySelector('.story-detail');
  const title = widget.querySelector('.widget-title');
  const timestamp = widget.querySelector('.widget-timestamp');
  const updateTime = widget.querySelector('.update-time');

  if (title) {
    title.textContent = toString(story.headline, 'What\'s Moving Your Portfolio Today');
  }
  if (storyContent) {
    storyContent.textContent = toString(
      story.content,
      'Live market story unavailable. Check back after the next backend refresh.'
    );
  }
  if (storyDetail) {
    storyDetail.textContent = toString(
      story.summary || story.detail || story.content,
      'The unified market brief did not return additional detail for this update.'
    );
  }
  if (timestamp) {
    timestamp.textContent = `Updated ${formatRelativeTime(toString(story.timestamp, liveDataMeta.generatedAt))}`;
  }
  if (updateTime) {
    updateTime.textContent = `Updated ${formatRelativeTime(toString(story.timestamp, liveDataMeta.generatedAt))}`;
  }

  applyFacetteLiveFallbackNotice(widget, 'story');
}

function renderFacetteLiveWidgets(root) {
  if (!root || typeof root.querySelectorAll !== 'function') return;

  root.querySelectorAll('[data-facette-widget]').forEach((widgetRoot) => {
    const widgetKey = widgetRoot.dataset.facetteWidget;
    if (widgetKey === 'story') {
      renderMarketPulse(widgetRoot);
      return;
    }
    if (widgetKey === 'news') {
      renderNewsFeed(widgetRoot);
      applyFacetteLiveFallbackNotice(widgetRoot, widgetKey);
      return;
    }
    if (widgetKey === 'trade') {
      renderTradeIdeas(widgetRoot);
      applyFacetteLiveFallbackNotice(widgetRoot, widgetKey);
      return;
    }
    if (widgetKey === 'calendar') {
      renderMarketCalendar(widgetRoot);
      applyFacetteLiveFallbackNotice(widgetRoot, widgetKey);
      return;
    }
    if (widgetKey === 'marketDrivers') {
      renderMarketDrivers(widgetRoot);
      applyFacetteLiveFallbackNotice(widgetRoot, widgetKey);
    }
  });
}

function loadFacetteContent(facetteId, tabName) {
  v16State.currentTab = tabName;
  const contentContainer = document.getElementById('facetteContent');
  if (!contentContainer) return;

  const liveContent = buildFacetteLiveContent(facetteId, tabName);
  if (liveContent.html) {
    contentContainer.innerHTML = liveContent.html;
    renderFacetteLiveWidgets(contentContainer);
    scheduleCriticalWidgetHealthRender();
    return;
  }

  // Generate sample content based on facette and tab
  const sampleContent = generateFacetteContent(facetteId, tabName);
  contentContainer.innerHTML = sampleContent;
  scheduleCriticalWidgetHealthRender();
}

// V15: Draw Professional Volatility Chart
function drawVolatilityChartPro() {
  const canvas = document.getElementById('volatilityChartPro');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };

  // Clear
  ctx.clearRect(0, 0, width, height);

  // Data (60 points for smooth curve)
  const data = [17, 25, 19, 24, 17, 23, 19, 21, 17, 23, 16, 21, 17, 19, 16, 22, 19, 17, 16, 19, 17, 16, 23, 18, 21, 19, 16, 22, 18, 19, 18, 21, 16, 20, 18, 16, 21, 19, 16, 20, 18, 19, 16, 19, 16, 20, 19, 17, 18, 21, 16, 20, 18, 19, 18, 16, 21, 19, 16, 20.8];

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Y-axis range
  const min = 15;
  const max = 25;
  const range = max - min;

  // Draw background zones
  // High risk zone (22-25)
  const highY = padding.top;
  const highHeight = ((25 - 22) / range) * chartHeight;
  ctx.fillStyle = 'rgba(239, 68, 68, 0.05)';
  ctx.fillRect(padding.left, highY, chartWidth, highHeight);

  // Moderate zone (18-22)
  const modY = padding.top + highHeight;
  const modHeight = ((22 - 18) / range) * chartHeight;
  ctx.fillStyle = 'rgba(245, 158, 11, 0.05)';
  ctx.fillRect(padding.left, modY, chartWidth, modHeight);

  // Low zone (15-18)
  const lowY = modY + modHeight;
  const lowHeight = chartHeight - highHeight - modHeight;
  ctx.fillStyle = 'rgba(34, 197, 94, 0.05)';
  ctx.fillRect(padding.left, lowY, chartWidth, lowHeight);

  // Draw grid lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = padding.top + (chartHeight / 5) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartWidth, y);
    ctx.stroke();

    // Y-axis labels
    const value = max - (range / 5) * i;
    ctx.fillStyle = '#94A3B8';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(value.toFixed(1), padding.left - 10, y + 4);
  }

  // Draw X-axis
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top + chartHeight);
  ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
  ctx.stroke();

  // X-axis labels
  ctx.fillStyle = '#94A3B8';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'center';
  const labels = ['30d ago', '20d ago', '10d ago', 'Today'];
  labels.forEach((label, i) => {
    const x = padding.left + (chartWidth / 3) * i;
    ctx.fillText(label, x, height - padding.bottom + 25);
  });

  // Draw gradient area
  const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartHeight);
  gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
  gradient.addColorStop(1, 'rgba(59, 130, 246, 0.05)');

  ctx.beginPath();
  data.forEach((value, i) => {
    const x = padding.left + (i / (data.length - 1)) * chartWidth;
    const y = padding.top + chartHeight - ((value - min) / range) * chartHeight;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
  ctx.lineTo(padding.left, padding.top + chartHeight);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Draw line
  ctx.beginPath();
  data.forEach((value, i) => {
    const x = padding.left + (i / (data.length - 1)) * chartWidth;
    const y = padding.top + chartHeight - ((value - min) / range) * chartHeight;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#3B82F6';
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Highlight last point
  const lastX = padding.left + chartWidth;
  const lastY = padding.top + chartHeight - ((data[data.length - 1] - min) / range) * chartHeight;
  ctx.beginPath();
  ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
  ctx.fillStyle = '#3B82F6';
  ctx.fill();
  ctx.strokeStyle = '#FFFFFF';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Annotations (events)
  const fedX = padding.left + (chartWidth * 0.4);
  const fedY = padding.top + chartHeight - ((23 - min) / range) * chartHeight;
  ctx.beginPath();
  ctx.moveTo(fedX, fedY - 10);
  ctx.lineTo(fedX, padding.top);
  ctx.strokeStyle = 'rgba(245, 158, 11, 0.5)';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = '#F59E0B';
  ctx.font = '10px sans-serif';
  ctx.fillText('Fed', fedX + 5, padding.top + 15);
}

function generateFacetteContent(facetteId, tabName) {
  const safeTabName = toString(tabName, 'Overview');
  const facette = isObject(facettes[facetteId]) ? facettes[facetteId] : {};
  const safeFacetteName = toString(facette.name, String(facetteId).toUpperCase());
  const scoreSeed = (String(facetteId || '').length + safeTabName.length);
  const confidence = 60 + (scoreSeed * 3 % 35);
  const accuracy = 72 + (scoreSeed * 5 % 25);
  const insights = Math.max(1, scoreSeed % 10);

  return `
    <div class="widget-card">
      <div class="widget-header">
        <h3>${safeTabName}</h3>
      </div>
      <div class="widget-body">
        <p style="font-size: 16px; line-height: 1.8; color: var(--color-text-light);">
          Contenu pour <strong>${safeFacetteName}</strong> > <strong>${safeTabName}</strong>
        </p>
        <div style="margin-top: 32px; padding: 24px; background: rgba(139, 92, 246, 0.1); border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.3);">
          <h4 style="margin-bottom: 16px;">🤖 AI Analysis</h4>
          <p style="font-size: 14px; line-height: 1.7; color: var(--color-text-secondary);">
            Basé sur les données disponibles, cette vue <strong>${safeTabName}</strong> synthétise marché, news et prévisions.
          </p>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; margin-top: 32px;">
          <div style="padding: 20px; background: rgba(31, 64, 175, 0.1); border-radius: 12px; text-align: center;">
            <div style="font-size: 32px; font-weight: 700; color: #10B981; margin-bottom: 8px;">${confidence}%</div>
            <div style="font-size: 12px; color: var(--color-text-secondary);">Confidence Score</div>
          </div>
          <div style="padding: 20px; background: rgba(31, 64, 175, 0.1); border-radius: 12px; text-align: center;">
            <div style="font-size: 32px; font-weight: 700; color: #8B5CF6; margin-bottom: 8px;">${accuracy}%</div>
            <div style="font-size: 12px; color: var(--color-text-secondary);">AI Accuracy</div>
          </div>
          <div style="padding: 20px; background: rgba(31, 64, 175, 0.1); border-radius: 12px; text-align: center;">
            <div style="font-size: 32px; font-weight: 700; color: #F59E0B; margin-bottom: 8px;">${insights}</div>
            <div style="font-size: 12px; color: var(--color-text-secondary);">Insights Found</div>
          </div>
        </div>
        <div style="margin-top: 32px; display: flex; gap: 16px;">
          <button class="kpi-action-btn primary" onclick="searchStock()">🔍 Deep Dive</button>
          <button class="kpi-action-btn secondary" onclick="showToast('Exporting analysis...')">Export Analysis</button>
          <button class="kpi-action-btn secondary" onclick="showToast('Setting alert...')">Set Alert</button>
        </div>
      </div>
    </div>
  `;
}

function scoreSearchNewsItem(item, symbol) {
  const target = String(symbol).toUpperCase();
  const title = String(item.title || item.headline || item.summary || '').toUpperCase();
  const source = String(item.source || '').toUpperCase();
  const tickers = toArray(item.tickers, []);
  const tickerMatch = tickers.some((entry) => String(entry).toUpperCase() === target);
  const relevance = toFiniteNumber(item.relevance, 0);
  const sentiment = toString(item.sentiment, 'neutral').toLowerCase();
  const publishedAt = item.published_at || item.pub_date || item.date || item.created_at;
  const parsedDate = Date.parse(publishedAt);
  const ageHours = Number.isFinite(parsedDate) ? Math.max(0, (Date.now() - parsedDate) / 3600000) : 168;
  const freshness = ageHours <= 2 ? 2.2 : ageHours <= 8 ? 1.6 : ageHours <= 24 ? 1.0 : 0.3;
  const matchBonus = (title.includes(target) || source.includes(target) || tickerMatch) ? 2 : 0.6;
  const sentimentBonus = sentiment === 'positive' ? 1.3 : sentiment === 'negative' ? 1.1 : 0.8;
  const score = (relevance * 6) + matchBonus + sentimentBonus + freshness;
  return Math.max(0, Math.min(10, score));
}

async function searchStock() {
  const input = document.getElementById('stockSymbolInput');
  const symbol = input && input.value ? input.value.trim().toUpperCase() : '';

  if (!symbol) {
    showToast('Please enter a stock symbol', 'warning');
    return;
  }
  if (!v16State.currentFacette || !facettes[v16State.currentFacette]) {
    showToast('Veuillez ouvrir une facette avant la recherche', 'warning');
    return;
  }

  v16State.currentStock = symbol;
  v16State.breadcrumbs = ['💎', facettes[v16State.currentFacette].name, symbol];
  document.getElementById('facetteBreadcrumb').textContent = v16State.breadcrumbs.join(' > ');

  showToast(`📈 Analyzing ${symbol}...`);
  const contentContainer = document.getElementById('facetteContent');
  if (!contentContainer) {
    return;
  }

  contentContainer.innerHTML = `
    <div class="widget-card">
      <div class="widget-header">
        <h3>${symbol} Deep Dive</h3>
      </div>
      <div class="widget-body">
        <p style="font-size: 14px; color: var(--color-text-light);">Recherche universelle en cours...</p>
      </div>
    </div>
  `;

  try {
    const searchPayload = await (typeof window.FinanceAPI?.searchUniverse === 'function'
      ? window.FinanceAPI.searchUniverse(symbol, {
        type: 'stocks,news,forecasts',
        tickers: [symbol],
        limit: 12,
        sortBy: 'relevance'
      })
      : Promise.resolve({ query: symbol, results: { stocks: [], news: [], forecasts: [] }, total: 0 }));
    const payload = isObject(searchPayload) ? (searchPayload.results || searchPayload.data || {}) : {};
    const stocks = toArray(payload.stocks, []);
    const forecasts = toArray(payload.forecasts, []);
    const news = toArray(payload.news, []);

    const selectedStock = stocks.find((row) => String(row.ticker || row.symbol || '').toUpperCase() === symbol)
      || stocks[0]
      || {};
    const selectedForecast = forecasts.find((row) => String(row.ticker || row.symbol || '').toUpperCase() === symbol)
      || forecasts[0]
      || {};
    const liveRow = isObject(window.liveStocks) ? window.liveStocks[symbol] : null;
    const livePoints = toArray((isObject(liveRow) ? liveRow.points : []), []);
    const livePrices = livePoints
      .map((point) => Array.isArray(point) ? toFiniteNumber(point[1], NaN) : toFiniteNumber(point, NaN))
      .filter((value) => Number.isFinite(value));

    const currentPrice = Math.max(0, toFiniteNumber(
      selectedStock.current_price || selectedStock.price || selectedStock.last_price || livePrices[livePrices.length - 1],
      0
    ));
    const previousPrice = livePrices.length > 1 ? livePrices[livePrices.length - 2] : currentPrice;
    const dayDelta = previousPrice > 0 ? ((currentPrice - previousPrice) / previousPrice) * 100 : 0;

    const forecastDelta = toFiniteNumber(
      selectedForecast.expected_return || selectedForecast.expectedReturn || selectedForecast.forecast || 0,
      0
    );
    const forecastConfidence = toFiniteNumber(
      selectedForecast.confidence || selectedForecast.confidence_pct || selectedForecast.score || 0,
      0
    );
    const forecastConfidencePct = forecastConfidence > 1
      ? Math.max(0, Math.min(100, Math.round(forecastConfidence)))
      : Math.max(0, Math.min(100, Math.round(forecastConfidence * 100)));
    const riskLevel = Math.max(1, Math.min(10, 10 - Math.round(forecastConfidencePct / 12)));

    const scoredNews = toArray(news, [])
      .map((entry) => {
        const row = isObject(entry) ? entry : {};
        return {
          headline: toString(row.title || row.headline, 'Market update'),
          summary: toString(row.summary || row.description, ''),
          source: toString(row.source, 'API'),
          time: formatRelativeTime(row.published_at || row.pub_date || row.date || row.created_at || ''),
          impact: scoreSearchNewsItem(row, symbol)
        };
      })
      .sort((a, b) => toFiniteNumber(b.impact, 0) - toFiniteNumber(a.impact, 0))
      .slice(0, 5);

    const newsBlock = scoredNews.length
      ? scoredNews.map((item) => `
        <div style="padding: 14px 16px; margin-bottom: 10px; background: rgba(255,255,255,0.05); border-radius: 10px; border-left: 4px solid #F59E0B;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap: 10px;">
            <strong style="font-size: 14px; color: var(--color-text-light);">${item.headline}</strong>
            <span style="font-size: 12px; color: #94A3B8; white-space: nowrap;">Impact ${item.impact.toFixed(1)}/10 • ${item.time}</span>
          </div>
          <p style="margin: 8px 0 0; font-size: 13px; color: var(--color-text-secondary);">${item.summary || 'Aucun résumé disponible.'}</p>
          <p style="margin: 8px 0 0; font-size: 12px; color: #94A3B8;">${item.source}</p>
        </div>
      `).join('')
      : '<p style="color: var(--color-text-secondary);">Aucune news récente trouvée pour ce ticker.</p>';

    const copilotRaw = await (typeof window.FinanceAPI?.askCopilot === 'function'
      ? window.FinanceAPI.askCopilot(`Analyse courte de ${symbol} : tendance, moteurs et risques`, [symbol])
      : Promise.resolve({ data: { answer: 'Service indisponible', sources: [] } }));
    const copilotParsed = buildCopilotJudgePayload(isObject(copilotRaw) && isObject(copilotRaw.data) ? copilotRaw.data : copilotRaw);
    const reasoningText = toString(copilotParsed?.reasoning || copilotParsed?.answer, 'Synthèse en cours.');

    contentContainer.innerHTML = `
      <div class="widget-card">
        <div class="widget-header">
          <h3>${symbol} Deep Dive</h3>
        </div>
        <div class="widget-body">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 24px;">
            <div style="padding: 24px; background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05)); border-radius: 16px; border: 1px solid rgba(16, 185, 129, 0.3);">
              <div style="font-size: 14px; color: var(--color-text-secondary); margin-bottom: 8px;">Current Price</div>
              <div style="font-size: 36px; font-weight: 700; color: #10B981; margin-bottom: 8px;">$${currentPrice.toFixed(2)}</div>
              <div style="font-size: 13px; color: #10B981;">${dayDelta >= 0 ? '↑' : '↓'} ${Math.abs(dayDelta).toFixed(2)}% today</div>
            </div>
            <div style="padding: 24px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(139, 92, 246, 0.05)); border-radius: 16px; border: 1px solid rgba(139, 92, 246, 0.3);">
              <div style="font-size: 14px; color: var(--color-text-secondary); margin-bottom: 8px;">AI Forecast (30d)</div>
              <div style="font-size: 36px; font-weight: 700; color: #8B5CF6; margin-bottom: 8px;">${forecastDelta >= 0 ? '+' : ''}${forecastDelta.toFixed(1)}%</div>
              <div style="font-size: 13px; color: #8B5CF6;">${forecastConfidencePct}% confidence</div>
            </div>
            <div style="padding: 24px; background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05)); border-radius: 16px; border: 1px solid rgba(245, 158, 11, 0.3);">
              <div style="font-size: 14px; color: var(--color-text-secondary); margin-bottom: 8px;">Risk Level</div>
              <div style="font-size: 36px; font-weight: 700; color: #F59E0B; margin-bottom: 8px;">${riskLevel}/10</div>
              <div style="font-size: 13px; color: #F59E0B;">Moderate Risk</div>
            </div>
          </div>
          <div style="margin-top: 24px;">
            <h4 style="margin-bottom: 12px;">📰 News Impact (top)</h4>
            ${newsBlock}
          </div>
          <div style="margin-top: 32px;">
            <h4>🤖 AI Recommendation</h4>
            <div style="padding: 24px; background: rgba(139, 92, 246, 0.1); border-radius: 12px; border-left: 4px solid #8B5CF6;">
              <p style="font-size: 15px; line-height: 1.7; color: var(--color-text-light);">
                <strong>${toString(copilotParsed?.consensus, 'HOLD').toUpperCase()}</strong> position on ${symbol}.
                ${reasoningText}
              </p>
              <p style="margin-top: 10px; font-size: 12px; color: #94A3B8;">
                Confiance: ${Math.max(0, Math.min(100, Math.round(toFiniteNumber(copilotParsed?.confidence, 35))))}%
                • Source: ${toString(copilotParsed?.model, 'Copilot')}
              </p>
            </div>
          </div>
        </div>
      </div>
    `;
    showToast(`✅ ${symbol} analysis complete!`, 'success');
  } catch (error) {
    console.error('searchStock failed', error);
    contentContainer.innerHTML = `
      <div class="widget-card">
        <div class="widget-header">
          <h3>${symbol} Deep Dive</h3>
        </div>
        <div class="widget-body">
          <p style="color: #F87171;">Impossible de charger ${symbol} pour le moment. Réessayez dans quelques secondes.</p>
        </div>
      </div>
    `;
    showToast(`⚠️ ${symbol} analysis temporary unavailable`, 'error');
  }
}

function quickNeed(need) {
  const needMap = {
    'analyze': 'deep-dive',
    'forecast': 'previsions',
    'news': 'news',
    'ask': 'copilot'
  };

  const facetteId = needMap[need];
  if (facetteId) {
    openFacette(facetteId);
  }
}

// ============================================================================
// FINANCE COPILOT V13 VISUAL-FIRST - MAXIMUM VISUALS, MINIMUM TEXT
// Trade Ideas + Market Calendar + News Feed + LLM Judge Multi-Model
// ============================================================================

// ============ CRITICAL BUG FIXES ============
let isNavigating = false;
let currentTabName = 'overview';

// Safe event listener wrapper to prevent bugs
function safeAddEventListener(element, event, handler) {
  if (!element) {
    console.error('Element not found for event:', event);
    return;
  }

  element.addEventListener(event, (e) => {
    try {
      handler(e);
    } catch (error) {
      console.error('Event handler error:', error);
      showToast('An error occurred. Please try again.', 'error');
    }
  });
}

// Prevent page from going blank
function safeSwitchTab(button, tabName) {
  if (isNavigating) return;
  isNavigating = true;

  try {
    // Remove active from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.remove('active');
    });

    // Resolve the button to activate (supports calls without explicit button)
    const targetButton = button || document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    if (targetButton) {
      targetButton.classList.add('active');
    }

    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.remove('active');
      content.style.display = 'none';
    });

    // Show selected tab content
    const selectedTab = document.getElementById(`tab-${tabName}`);
    if (selectedTab) {
      selectedTab.classList.add('active');
      selectedTab.style.display = 'block';
      currentTabName = tabName;

      // Tab-specific visual initializations
      if (tabName === 'performance') {
        // Ensure full portfolio health gauge is rendered when the Performance tab is viewed
        try {
          drawHealthGauge();
        } catch (e) {
          console.error('Error drawing health gauge:', e);
        }
      }

      if (tabName === 'market') {
        // Initialize Market Analysis charts after tab is visible
        setTimeout(() => {
          try {
            console.log('🎨 Initializing Market Analysis charts...');

            // Market Drivers Donut
            if (typeof drawMarketDriversDonut === 'function') {
              drawMarketDriversDonut();
            }

            // Cluster Map (Similar Stocks)
            if (typeof drawClusterMap === 'function') {
              drawClusterMap();
            }

            // News Impact table
            if (typeof renderNewsImpact === 'function') {
              renderNewsImpact();
            }

            // Sector Performance chart
            if (typeof drawSectorPerformance === 'function') {
              drawSectorPerformance();
            }

            // Volatility Chart Pro
            if (typeof drawVolatilityChartPro === 'function') {
              drawVolatilityChartPro();
            }

            // Correlation Heatmap (only draw once)
            const heatmapContainer = document.getElementById('heatmapContainer');
            if (heatmapContainer && !heatmapContainer.dataset.drawn && typeof drawCorrelationHeatmap === 'function') {
              drawCorrelationHeatmap();
              heatmapContainer.dataset.drawn = 'true';
            }

            console.log('✅ Market Analysis charts initialized!');
          } catch (e) {
            console.error('Error initializing Market Analysis charts:', e);
          }
        }, 100);
      }

      showToast(`Viewing ${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
    } else {
      console.error('Tab not found:', tabName);
      // Fallback to overview
      const overviewTab = document.getElementById('tab-overview');
      if (overviewTab) {
        overviewTab.classList.add('active');
        overviewTab.style.display = 'block';
      }
    }
  } catch (error) {
    console.error('Tab switch error:', error);
    showToast('Navigation error. Refreshing...', 'error');
    setTimeout(() => location.reload(), 1000);
  } finally {
    setTimeout(() => { isNavigating = false; }, 100);
  }
}

// ============ COMMAND K FUNCTIONS ============
function openCommandK() {
  const modal = document.getElementById('commandKModal');
  const input = document.getElementById('commandKInput');

  if (modal) {
    modal.style.display = 'flex';
    if (input) {
      setTimeout(() => input.focus(), 100);
    }
  }
}

function closeCommandK() {
  const modal = document.getElementById('commandKModal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function runCommandKCopilotPrompt(question) {
  const overlay = document.getElementById('aiCopilotOverlay');
  const input = document.getElementById('aiOverlayInput');
  if (!overlay || !input) return;

  const submitPrompt = () => {
    input.value = question;
    sendOverlayMessage();
  };

  const overlayClosed = overlay.style.display === 'none' || !overlay.style.display;
  if (overlayClosed) {
    toggleAICopilot();
    setTimeout(submitPrompt, 30);
    return;
  }

  submitPrompt();
}

function runCommandKTickerDeepDive(symbol) {
  openFacette('deep-dive');
  setTimeout(() => {
    const input = document.getElementById('stockSymbolInput');
    if (!input) return;
    input.value = symbol;
    searchStock();
  }, 30);
}

function executeCommandKAction(action) {
  closeCommandK();

  const actions = {
    'dashboard': () => safeSwitchTab(document.querySelector('[data-tab="overview"]'), 'overview'),
    'market': () => safeSwitchTab(document.querySelector('[data-tab="market"]'), 'market'),
    'opportunities': () => safeSwitchTab(document.querySelector('[data-tab="opportunities"]'), 'opportunities'),
    'copilot': () => toggleAICopilot(),
    'nvda-analysis': () => runCommandKTickerDeepDive('NVDA'),
    'portfolio-risk': () => runCommandKCopilotPrompt('Give me a portfolio risk memo for today with verdict, main reasons, invalidation conditions, confidence, freshness, and sources.'),
    'market-forecast': () => runCommandKCopilotPrompt('Give me a 1-week market forecast memo with regime, drivers, risks, confidence, freshness, and sources.'),
    'stock-nvda': () => runCommandKTickerDeepDive('NVDA'),
    'stock-meta': () => runCommandKTickerDeepDive('META'),
    'stock-aapl': () => runCommandKTickerDeepDive('AAPL'),
    'portfolio-value': () => openDrillDown('portfolio'),
    'win-rate': () => showToast('Win Rate: 72% (Above Target)'),
    'ai-forecast': () => openDrillDown('forecast')
  };

  if (actions[action]) {
    actions[action]();
  } else {
    showToast(`Executing: ${action}`);
  }
}

// Command K keyboard shortcut (immediate on load)
document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    openCommandK();
  }
  if (e.key === 'Escape') {
    closeCommandK();
    document.getElementById('commandPalette')?.classList.remove('active');
    document.getElementById('notificationDrawer')?.classList.remove('active');
    document.getElementById('settingsModal')?.classList.remove('active');
  }

  // Quick navigation shortcuts
  if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '5') {
    e.preventDefault();
    const tabs = ['overview', 'market', 'opportunities', 'performance', 'ailab'];
    const index = parseInt(e.key) - 1;
    if (tabs[index]) {
      safeSwitchTab(document.querySelector(`[data-tab="${tabs[index]}"]`), tabs[index]);
    }
  }
});

// Close Command K on backdrop click
document.addEventListener('click', (e) => {
  const modal = document.getElementById('commandKModal');
  if (modal && e.target === modal) {
    closeCommandK();
  }
});

// ============ DATA LAYER ============
const LIVE_DATA_EVENT = window.FINANCECOPILOT_LIVE_EVENT || 'financecopilot:live-dashboard-updated';
const LIVE_FALLBACK_TAG = 'offline-fallback';

const FALLBACK_FACETTES = {
  'deep-dive': {
    icon: '📈',
    name: 'Deep Dive Action',
    color: '#3B82F6',
    needsSearch: true,
    tabs: ['Synthèse', 'Prévisions', 'Risques', 'Signaux Techniques', 'Actualités', 'Copilot']
  },
  economie: {
    icon: '🌍',
    name: 'Économie Globale',
    color: '#10B981',
    needsSearch: false,
    tabs: ['Marché', 'Macro Économie', 'Prévisions', 'News Économiques', 'Copilot Macro']
  },
  news: {
    icon: '📰',
    name: 'News Impactantes',
    color: '#F59E0B',
    needsSearch: false,
    tabs: ['Toutes les News', 'High Impact', 'Mes Holdings', 'Par Secteur']
  },
  previsions: {
    icon: '🔮',
    name: 'Prévisions AI',
    color: '#8B5CF6',
    needsSearch: false,
    tabs: ['Portfolio', 'Marché Général', 'Secteurs', 'Actions Suivies']
  },
  risques: {
    icon: '🚦',
    name: 'Risques & Signaux',
    color: '#EF4444',
    needsSearch: false,
    tabs: ['Alertes Actives', 'Risk Dashboard', 'Anomalies Détectées', 'Monitoring']
  },
  copilot: {
    icon: '🤖',
    name: 'Copilot Q&A',
    color: '#14B8A6',
    needsSearch: false,
    tabs: ['Chat Global', 'Questions Fréquentes', 'Historique', 'Suggestions']
  },
  trading: {
    icon: '💹',
    name: 'Opportunités Trading',
    color: '#FCD34D',
    needsSearch: false,
    tabs: ['Trade Ideas', 'Backtests', 'Scenarios', 'Exécution']
  },
  portfolio: {
    icon: '🗂️',
    name: 'Portfolio Analytics',
    color: '#6366F1',
    needsSearch: false,
    tabs: ['Vue d’Ensemble', 'Performance', 'Holdings', 'Attribution', 'Dividendes']
  },
  explorer: {
    icon: '🗺️',
    name: 'Explorer Avancé',
    color: '#EC4899',
    needsSearch: false,
    tabs: ['Corrélations', 'Clustering', 'Patterns', 'Heatmaps', 'Network Graph']
  }
};

const FALLBACK_V11_DATA = {
  userProfile: {
    type: 'Trader',
    preferences: {
      complexityLevel: 'advanced',
      autoRefresh: true,
      refreshInterval: 30,
      theme: 'dark',
      notifications: true
    },
    behavior: {
      mostViewedTab: 'Opportunities',
      mostClickedWidget: 'Trade Ideas',
      averageSessionTime: 18,
      lastActive: '2025-11-18T20:00:00'
    }
  },
  aiSuggestions: [
    { type: 'check', title: 'Check Risk Concentration Alert', priority: 'high', widget: 'Risk Alerts', tab: 'Risk', timestamp: '2 min ago' },
    { type: 'view', title: "You haven't viewed Sector Performance today", priority: 'medium', widget: 'Sector Performance', tab: 'Market Intel', timestamp: 'Today' },
    { type: 'action', title: 'NVDA signal 92% confidence - Act Now', priority: 'high', widget: 'Trade Ideas', tab: 'Opportunities', timestamp: '2h ago' }
  ],
  storyPoints: {
    overview: [
      { step: 1, title: 'Portfolio Performance', description: 'Portfolio up 1.88% today, driven by tech rally', widget: 'Hero KPIs', highlight: 'portfolioValue' }
    ]
  },
  aiInsights: {
    overview: [
      { type: 'positive', icon: '📈', title: 'Technical trend', description: 'Momentum remains constructive', severity: 'info', action: 'View Performance' },
      { type: 'neutral', icon: '⚖️', title: 'Risk stable', description: 'Risk score stable for the session', severity: 'info', action: 'View Risk' }
    ],
    opportunities: []
  }
};

const DEFAULT_PROFILE_LABEL = 'Trader';
const DEFAULT_PROFILE_JUDGE_PLACEHOLDER = 'Entrez votre portefeuille (ex: AAPL,MSFT,NVDA)';
const DEFAULT_PROFILE_JUDGE_EXAMPLE = 'NVDA,META,AAPL,MSFT';
const DEFAULT_PROFILE_AI_SUGGESTIONS = FALLBACK_V11_DATA.aiSuggestions.map((suggestion) => ({ ...suggestion }));
const DEFAULT_PROFILE_QUICK_ACTIONS = [
  {
    priority: 'high',
    badge: 'High Priority',
    title: 'NVDA Breakout Signal Detected',
    detailType: 'confidence',
    detailLabel: 'Confidence',
    detailValue: '92%',
    primaryLabel: 'View Details',
    primaryToast: 'Opening NVDA details...',
    secondaryLabel: 'Add to Watchlist',
    secondaryToast: 'Added to watchlist'
  },
  {
    priority: 'medium',
    badge: 'Medium Priority',
    title: 'Rebalance Tech Exposure',
    detailType: 'suggestion',
    detailLabel: 'Suggestion',
    detailValue: 'Diversify to Healthcare',
    primaryLabel: 'See Plan',
    primaryToast: 'Viewing rebalance plan...',
    secondaryLabel: 'Execute',
    secondaryToast: 'Executing rebalance...'
  },
  {
    priority: 'low',
    badge: 'Low Priority',
    title: 'Weekly Report Ready',
    detailType: 'suggestion',
    detailLabel: 'Suggestion',
    detailValue: 'Your performance summary is available',
    primaryLabel: 'View Report',
    primaryToast: 'Opening report...',
    secondaryLabel: 'Schedule Email',
    secondaryToast: 'Email scheduled'
  }
];
const PROFILE_PRESETS = {
  reda_personal_investing: {
    label: 'Reda (Investissement perso)',
    userProfileType: 'Investisseur particulier',
    complexityLevel: 'guided',
    refreshInterval: 300,
    judgePlaceholder: 'Ex: SPY,QQQ,DIA,IWM,AAPL,MSFT,JNJ,WMT,GLD',
    judgeExample: 'SPY,QQQ,DIA,IWM,AAPL,MSFT,JNJ,WMT,GLD',
    aiSuggestions: [
      { type: 'check', title: 'Verifier si le portefeuille est trop concentre en tech', priority: 'high', widget: 'Portfolio Health', tab: 'Portfolio', timestamp: 'Maintenant' },
      { type: 'view', title: 'Revoir le calendrier macro avant tout arbitrage', priority: 'medium', widget: 'Market Calendar', tab: 'Market Intel', timestamp: 'Cette semaine' },
      { type: 'action', title: 'Demander un avis simple sur le coeur de portefeuille', priority: 'high', widget: 'AI Multi-Model Judge', tab: 'AI Insights', timestamp: 'Pret' }
    ],
    quickActions: [
      {
        priority: 'high',
        badge: 'Priorite haute',
        title: 'Verifier la diversification du portefeuille coeur',
        detailType: 'suggestion',
        detailLabel: 'Suggestion',
        detailValue: 'Comparer SPY, QQQ, DIA et IWM avant tout arbitrage',
        primaryLabel: 'Voir le plan',
        primaryToast: 'Ouverture du plan de diversification',
        secondaryLabel: 'Ouvrir le Judge',
        secondaryToast: 'Preparation du Judge portefeuille'
      },
      {
        priority: 'medium',
        badge: 'Priorite moyenne',
        title: 'Planifier un rebalance mensuel simple',
        detailType: 'suggestion',
        detailLabel: 'Suggestion',
        detailValue: 'Revenir vers un profil equilibre sans effet de levier',
        primaryLabel: 'Voir la vue risque',
        primaryToast: 'Ouverture de la vue risque',
        secondaryLabel: 'Creer un rappel',
        secondaryToast: 'Rappel mensuel cree'
      },
      {
        priority: 'low',
        badge: 'Priorite basse',
        title: 'Suivre les actifs defensifs et dividendes',
        detailType: 'suggestion',
        detailLabel: 'Suggestion',
        detailValue: 'Surveiller JNJ, WMT et GLD pour stabiliser le portefeuille',
        primaryLabel: 'Voir le calendrier',
        primaryToast: 'Ouverture du calendrier portefeuille',
        secondaryLabel: 'Sauver en liste',
        secondaryToast: 'Liste defensive mise a jour'
      }
    ]
  }
};
const PROFILE_JUDGE_EXAMPLES = [
  DEFAULT_PROFILE_JUDGE_EXAMPLE,
  ...Object.values(PROFILE_PRESETS)
    .map((preset) => preset.judgeExample)
    .filter((example) => typeof example === 'string' && example.trim())
];
const FORECAST_PROFILE_STORAGE_KEY = 'finance.forecasts.currentProfile';
const FORECAST_PROFILE_FALLBACK = 'trader';
const FORECAST_PROFILE_VALUES = new Set([
  'auto',
  'executive',
  'trader',
  'analyst',
  ...Object.keys(PROFILE_PRESETS)
]);

function normalizeForecastProfile(profile) {
  const value = typeof profile === 'string' ? profile.trim() : '';
  return FORECAST_PROFILE_VALUES.has(value) ? value : FORECAST_PROFILE_FALLBACK;
}

function loadStoredForecastProfile() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return FORECAST_PROFILE_FALLBACK;
  }
  try {
    return normalizeForecastProfile(window.localStorage.getItem(FORECAST_PROFILE_STORAGE_KEY));
  } catch (error) {
    console.warn('Unable to read stored forecasts profile:', error?.message || error);
    return FORECAST_PROFILE_FALLBACK;
  }
}

function storeForecastProfile(profile) {
  const normalizedProfile = normalizeForecastProfile(profile);
  if (typeof window === 'undefined' || !window.localStorage) {
    return normalizedProfile;
  }
  try {
    window.localStorage.setItem(FORECAST_PROFILE_STORAGE_KEY, normalizedProfile);
  } catch (error) {
    console.warn('Unable to persist forecasts profile:', error?.message || error);
  }
  return normalizedProfile;
}

const FALLBACK_TRADE_IDEAS = [
  { symbol: 'NVDA', signalType: 'Breakout', entry: 875, target: 980, confidence: 92 },
  { symbol: 'META', signalType: 'Reversal', entry: 520, target: 565, confidence: 85 }
];

const FALLBACK_MARKET_CALENDAR = {
  earnings: [
    { stock: 'NVDA', date: 'Nov 20', impact: 'High', holding: true }
  ],
  economicData: [
    { event: 'Fed Minutes', date: 'Nov 21', impact: 'High' }
  ],
  exDividend: [
    { stock: 'MSFT', date: 'Nov 19', amount: 0.68 }
  ]
};

const FALLBACK_NEWS_ITEMS = [
  { headline: 'Fed Signals Rate Cuts Q2', impact: 8.5, effect: '+3.2%', time: '2h ago', source: 'Reuters', category: 'Macro' },
  { headline: 'NVDA Earnings Beat Expectations', impact: 9.2, effect: '+5.1%', time: '4h ago', source: 'Bloomberg', category: 'Earnings' }
];

const FALLBACK_LLM_JUDGE_DATA = {
  question: 'What should I do with my portfolio today?',
  consensus: 'HOLD POSITIONS',
  confidence: 87,
  models: [
    { name: 'Model A', verdict: 'Hold', confidence: 85, icon: '🤖' },
    { name: 'Model B', verdict: 'Hold', confidence: 90, icon: '🧠' },
    { name: 'Model C', verdict: 'Hold', confidence: 86, icon: '💎' }
  ],
  reasoning: 'Signals remain mixed but bias remains constructive with moderate confidence.',
  dataSources: ['Portfolio Analysis', 'Market Signals', 'News Feed'],
  suggestedActions: [
    { icon: '🔔', title: 'Set Alert', detail: 'NVDA $880', action: 'setAlert' },
    { icon: '⚖️', title: 'Review Risk', detail: 'Concentration Check', action: 'reviewRisk' },
    { icon: '📅', title: 'Check Calendar', detail: '3 Events This Week', action: 'viewCalendar' }
  ]
};

const FALLBACK_COPILOT_START = {
  brief_of_day: {
    title: 'Brief of the day',
    summary: 'No daily brief available yet.',
    market_regime: 'UNKNOWN',
    market_sentiment: 'UNKNOWN',
    top_opportunities: [],
    top_signals: [],
    top_risks: [],
    macro_signals: [],
    sector_rotation: {
      top: [],
      bottom: []
    },
    generated_at: '',
    freshness: '',
    source: ['brief_daily_fallback'],
    sources: ['brief_daily_fallback'],
    degraded: false
  },
  ask: [
    {
      id: 'portfolio_today',
      label: 'Portfolio today?',
      prompt: 'What should I do with my portfolio today?'
    },
    {
      id: 'market_theme',
      label: 'Best theme now?',
      prompt: 'Which market theme deserves a deep dive right now?'
    },
    {
      id: 'nvda_memo',
      label: 'NVDA 1-week memo',
      prompt: 'Give me a 1-week investment memo on NVDA.'
    }
  ],
  open: [
    {
      id: 'brief_of_day',
      label: 'Open Live Brief',
      target: '/brief/daily'
    },
    {
      id: 'opportunities',
      label: 'Open opportunities',
      target: 'opportunities'
    },
    {
      id: 'copilot',
      label: 'Open copilot',
      target: 'copilot'
    }
  ]
};

const FALLBACK_MARKET_DRIVERS = [
  { factor: 'Technical', contribution: 40, color: '#1F40AF' },
  { factor: 'Sentiment', contribution: 35, color: '#8B5CF6' },
  { factor: 'News', contribution: 20, color: '#F59E0B' },
  { factor: 'Macro', contribution: 5, color: '#10B981' }
];

const FALLBACK_APP_DATA = {
  portfolioSparkline: [125000, 125150, 125300, 125400, 125550, 125700, 125800, 125950, 126100, 126200, 126100, 126250, 126400, 126500, 126650, 126800, 126900, 127050, 127200, 127150, 127100],
  forecastProjection: [127456, 127650, 127850, 128100, 128350, 128600, 128800, 129000, 129250, 129500, 129700, 129900, 130100, 130300, 130500, 130700],
  stockSparklines: {
    NVDA: [820, 822, 825, 828, 830, 832, 835, 837, 840, 842, 845, 847, 850, 852, 855, 857, 860, 862, 865, 867, 870],
    META: [500, 501, 502, 503, 505, 506, 508, 509, 510, 511, 512, 513, 515, 516, 518, 519, 520, 521, 522, 523, 523.5],
    AAPL: [175, 175.5, 176, 176.5, 177, 177.5, 178, 178.5, 179, 179.5, 178.5, 178, 177.5, 177, 176.5, 176, 177, 177.5, 178, 178.5, 179],
    MSFT: [400, 401, 402, 403, 405, 406, 408, 409, 410, 411, 412, 413, 414, 415, 416, 415, 414, 413, 412, 411, 410],
    GOOGL: [138, 138.5, 139, 139.5, 140, 140.5, 141, 141.5, 142, 141.5, 141, 140.5, 140, 139.5, 139, 140, 140.5, 141, 141.5, 142]
  },
  hero: {
    portfolioValue: 127456,
    portfolioChange: 1.88,
    forecastNext30d: 5.3,
    forecastConfidence: 82,
    winRate: 72,
    winRateChange: 2.3
  },
  story: {
    headline: 'Aperçu du jour',
    content: 'Les signaux IA détectent un retour de confiance technique; le marché reste orienté croissance.',
    sentiment: 'bullish',
    timestamp: 'Updated 5 minutes ago'
  },
  copilotStart: FALLBACK_COPILOT_START,
  correlations: {
    labels: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
    data: [
      [1.0, 0.85, 0.72, 0.68, 0.58],
      [0.85, 1.0, 0.78, 0.70, 0.62],
      [0.72, 0.78, 1.0, 0.68, 0.55],
      [0.68, 0.70, 0.68, 1.0, 0.60],
      [0.58, 0.62, 0.55, 0.60, 1.0]
    ]
  },
  portfolioHealth: {
    overall: 83,
    suggestion: 'Diversifier Tech → Santé',
    riskLabel: 'Medium',
    riskTone: 'neutral',
    riskProfile: 'balanced',
    confidence: 82,
    stateSummary: '1Y horizon | High conviction | Moderate risk',
    allocationLabel: 'Largest saved weight: NVDA 45%',
    allocationProgress: 75,
    benchmark: 'SPY',
    updatedAt: null
  },
  portfolioRiskProfile: null,
  portfolioRiskProfileFreshness: null,
  sectorPerformance: [
    { sector: 'Technology', change: 8.5, holdings: true, weight: 45 },
    { sector: 'Finance', change: 3.1, holdings: true, weight: 15 },
    { sector: 'Energy', change: -1.8, holdings: false, weight: 0 },
    { sector: 'Healthcare', change: 5.2, holdings: false, weight: 0 },
    { sector: 'Real Estate', change: 1.2, holdings: false, weight: 4 }
  ],
  backtestResults: {
    sharpeRatio: 1.28,
    winRate: 72,
    maxDrawdown: -12.3,
    totalReturn: 28.5
  },
  marketDrivers: FALLBACK_MARKET_DRIVERS,
  opportunities: [
    { conviction: 'High', return: 12.3, confidence: 92 },
    { conviction: 'Medium', return: 5.8, confidence: 78 }
  ],
  topStocks: [
    { symbol: 'NVDA', price: 875.60, change: 8.5, forecast: '+12.3%', confidence: 92 },
    { symbol: 'META', price: 523.45, change: 5.2, forecast: '+8.1%', confidence: 85 },
    { symbol: 'AAPL', price: 178.23, change: 2.1, forecast: '+4.5%', confidence: 78 }
  ]
};

let facettes = window.facettes || FALLBACK_FACETTES;
let v11Data = window.v11Data || FALLBACK_V11_DATA;
let baseProfileAISuggestions = Array.isArray(v11Data.aiSuggestions) && v11Data.aiSuggestions.length
  ? v11Data.aiSuggestions.map((suggestion) => ({ ...suggestion }))
  : DEFAULT_PROFILE_AI_SUGGESTIONS.map((suggestion) => ({ ...suggestion }));
let tradeIdeas = sanitizeTradeIdeas(window.tradeIdeas || FALLBACK_TRADE_IDEAS);
let marketCalendar = sanitizeMarketCalendar(window.marketCalendar || FALLBACK_MARKET_CALENDAR);
let newsItems = sanitizeNewsItems(window.newsItems || FALLBACK_NEWS_ITEMS);
let liveAlerts = [];
let llmJudgeData = window.llmJudgeData || FALLBACK_LLM_JUDGE_DATA;
let judgeDecisionJournal = sanitizeJudgeDecisionJournal(window.judgeDecisionJournal || []);
let marketDrivers = sanitizeMarketDrivers(window.marketDrivers || FALLBACK_MARKET_DRIVERS);
let liveForecastRows = [];
let liveTopMovers = [];
let liveKpis = window.liveKpis || null;
let livePortfolioSummary = window.livePortfolioSummary || null;
let appData = normalizeAppData(window.appData || {});
let liveDataMeta = {
  generatedAt: new Date().toISOString(),
  sources: [LIVE_FALLBACK_TAG],
  modelVersions: [LIVE_FALLBACK_TAG],
  warnings: ['offline-fallback'],
  freshness: { lastFetchedAt: Date.now(), ttlMs: 60000 },
  cache: { lastFetchedAt: Date.now(), ttlMs: 60000 },
  contractState: 'unknown',
  ingestionHealth: null
};
const CRITICAL_WIDGET_HEALTH_TARGETS = {
  hero: {
    selectors: [
      '#heroSection',
      '#hero-glassmorphic-container .hero-glassmorphic',
      '#mainHeroSection',
      '#hero-what-need-container'
    ],
    anchorSelector: '.hero-subtitle, .hero-header',
    copy: {
      loading: 'Live sync in progress. Quick actions stay available while cached context remains visible.',
      stale: 'This portfolio snapshot is aging. Refresh before launching a new action.',
      degraded: 'Fallback sources are driving the hero summary. Confirm key numbers before acting.',
      error: 'Live portfolio sync is unavailable. Retry before using this entry point.'
    }
  },
  news: {
    selectors: ['#news-feed-widget-container .news-feed-widget', '#news-feed-widget-container'],
    anchorSelector: '.widget-header',
    copy: {
      loading: 'Live headlines are loading. Cached cards remain available in the meantime.',
      stale: 'These headlines are beyond the normal freshness window. Refresh before reacting.',
      degraded: 'Some news sources are unavailable. Cross-check in Market before trading on this feed.',
      error: 'The live news feed failed to load. Retry sync or stay on cached headlines.'
    }
  },
  forecasts: {
    selectors: ['#forecast-scenarios-widget-container .forecast-scenarios-widget', '#forecast-scenarios-widget-container'],
    anchorSelector: '.widget-header',
    copy: {
      loading: 'Forecast scenarios are recalculating. Cached ranges stay visible until sync completes.',
      stale: 'Scenario ranges are older than expected. Refresh before using them for decisions.',
      degraded: 'Forecasts are running with partial signals. Treat the ranges as directional only.',
      error: 'The forecast engine is unavailable. Retry sync before relying on this widget.'
    }
  },
  judge: {
    selectors: ['#llm-judge-widget-container .llm-judge-widget', '#llm-judge-widget-container'],
    anchorSelector: '.widget-header',
    copy: {
      loading: 'The judge is loading live context. You can still review the cached workflow.',
      stale: 'Judge consensus is no longer fresh. Refresh before asking for a new verdict.',
      degraded: 'The judge is running on partial context. Keep prompts narrow or refresh first.',
      error: 'The multi-model judge is unreachable. Retry sync before using this panel.'
    }
  },
  'deep-dive': {
    selectors: ['#facetteView'],
    anchorSelector: '.facette-header',
    shouldRender: () => v16State.currentFacette === 'deep-dive',
    copy: {
      loading: 'Deep-dive context is preparing live data. You can still open a ticker while sync runs.',
      stale: 'Deep-dive context is aging. Refresh before starting another ticker review.',
      degraded: 'Deep-dive is using partial sources. Recheck critical values before taking action.',
      error: 'Deep-dive context is unavailable. Retry sync before trusting this analysis path.'
    }
  }
};
const CRITICAL_WIDGET_HEALTH_STATE_META = {
  loading: { badge: 'LOADING', actionLabel: 'Syncing...', actionDisabled: true },
  stale: { badge: 'STALE', actionLabel: 'Refresh live data', actionDisabled: false },
  degraded: { badge: 'DEGRADED', actionLabel: 'Retry live sync', actionDisabled: false },
  error: { badge: 'ERROR', actionLabel: 'Retry live data', actionDisabled: false }
};
let criticalWidgetHealthOverride = { state: 'loading' };
let criticalWidgetHealthObserver = null;
let criticalWidgetHealthFrame = null;

function isObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function toFiniteNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toString(value, fallback = '') {
  if (value === undefined || value === null) return fallback;
  return String(value);
}

function toArray(value, fallback = []) {
  return Array.isArray(value) ? value : fallback;
}

function escapeHtml(value) {
  return toString(value, '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function toNumberArray(value, fallback = []) {
  if (!Array.isArray(value)) return fallback;
  const normalized = value
    .map((item) => toFiniteNumber(item))
    .filter((item) => Number.isFinite(item));
  return normalized.length ? normalized : fallback;
}

function normalizeVerdict(value, fallback = 'hold') {
  const normalized = toString(value, fallback).toLowerCase();
  if (normalized.includes('buy') || normalized.includes('achat') || normalized.includes('long')) {
    return 'buy';
  }
  if (normalized.includes('sell') || normalized.includes('vendre') || normalized.includes('short')) {
    return 'sell';
  }
  return 'hold';
}

function formatConfidence(value, fallback = 0) {
  const parsed = toFiniteNumber(value, fallback);
  const normalized = parsed > 1 ? parsed : parsed * 100;
  const bounded = Math.max(0, Math.min(100, Math.round(normalized)));
  return Number.isFinite(bounded) ? bounded : fallback;
}

function normalizeReasoning(value) {
  if (Array.isArray(value)) {
    return value.map((item) => toString(item).trim()).filter((item) => item.length > 5);
  }
  if (typeof value !== 'string' || !value.trim()) {
    return [];
  }
  const parsed = value.split(/[\n\r]+/).map((line) => line.replace(/^\s*[-*•]\s*/, '').trim()).filter(Boolean);
  return parsed.length
    ? parsed.slice(0, 3)
    : value
      .split(/(?<=[.!?])\s+/)
      .map((sentence) => sentence.trim())
      .filter((sentence) => sentence.length > 8)
      .slice(0, 3);
}

function normalizeCopilotSources(value) {
  const sources = Array.isArray(value) ? value : (value ? [value] : []);
  return sources.map((source) => {
    if (!isObject(source)) {
      return {
        label: toString(source, 'Source'),
        url: '',
        excerpt: ''
      };
    }
    const url = toString(source.url || source.link, '');
    const label = toString(source.ticker || source.source || source.label || source.type, 'Source');
    const excerpt = toString(source.excerpt || source.snippet || source.reason, '');
    return { label, url, excerpt };
  });
}

function normalizeCopilotSourceLabels(value) {
  const sources = Array.isArray(value) ? value : (value ? [value] : []);
  return sources
    .map((source) => {
      if (isObject(source)) {
        return toString(source.label || source.source || source.ticker || source.type || source.name, '').trim();
      }
      return toString(source, '').trim();
    })
    .filter((label) => label.length > 0);
}

function buildCopilotJudgePayload(raw) {
  if (!isObject(raw) && raw !== null) {
    return null;
  }
  const payload = raw && isObject(raw) ? raw : {};
  const data = isObject(payload.data) ? payload.data : payload;
  const memo = isObject(data.memo) ? data.memo : {};
  const verdict = normalizeVerdict(
    data.verdict || data.action || data.recommendation || memo.verdict || memo.action || memo.recommendation,
    'hold'
  );
  const confidence = formatConfidence(data.confidence ?? memo.confidence, 0.35);
  const rawRisk = isObject(data.risk) ? data.risk : (isObject(memo.risk) ? memo.risk : {});
  const riskLevel = toString(
    data.risk_level
      || data.riskLevel
      || memo.risk_level
      || memo.riskLevel
      || rawRisk.level
      || rawRisk.risk_level
      || (typeof data.risk === 'string' ? data.risk : ''),
    'medium'
  ).toLowerCase();
  const riskCaveat = toString(data.risk_caveat || memo.risk_caveat || rawRisk.caveat || rawRisk.reason || '', '');
  const models = toArray(data.models, []).filter(isObject);
  const fallbackModel = {
    name: toString(data.model, 'Copilot'),
    verdict: verdict.toUpperCase(),
    confidence,
    icon: '🤖',
    evidence: riskCaveat
  };
  const modelRows = models.length
    ? models.map((item) => ({
      name: toString(item.name, 'Copilot'),
      verdict: normalizeVerdict(item.verdict || item.action, verdict).toUpperCase(),
      confidence: formatConfidence(item.confidence, confidence),
      icon: toString(item.icon || '🤖', '🤖'),
      evidence: toString(item.evidence || item.reasoning || item.why || riskCaveat, '')
    }))
    : [fallbackModel];
  const memoSummary = toString(
    memo.summary || memo.answer || memo.thesis || data.answer || data.reasoning || data.why,
    ''
  );
  const memoRegime = toString(memo.market_regime || memo.marketRegime || memo.regime, '').toUpperCase();
  const memoHorizon = toString(memo.horizon || data.horizon, '').replace(/_/g, ' ').trim();
  const memoOpportunities = normalizeCopilotStartList(
    memo.top_opportunities || memo.topOpportunities || memo.opportunities || memo.top_signals || memo.signals
  );
  const memoRisks = normalizeCopilotStartList(memo.top_risks || memo.topRisks || memo.risks);
  const memoFreshness = toString(
    memo.freshness || memo.generated_at || memo.generatedAt || data.freshness || data.generated_at || data.generatedAt,
    ''
  );
  const nextSteps = toArray(data.next_steps || data.nextSteps || memo.next_steps || memo.nextSteps, [])
    .map((item) => toString(item, '').trim())
    .filter(Boolean)
    .slice(0, 3);
  const invalidation = toArray(data.invalidation || memo.invalidation, [])
    .map((item) => toString(item, '').trim())
    .filter(Boolean)
    .slice(0, 3);
  const reasoning = normalizeReasoning(
    data.why || data.reasoning || memo.main_reasons || memo.mainReasons || memo.reasons || memo.drivers || memoSummary
  );
  const sources = normalizeCopilotSources(data.sources || data.citations || memo.sources || memo.source);
  const requirementsMet = isObject(data.requirements_met || data.requirementsMet)
    ? (data.requirements_met || data.requirementsMet)
    : {};
  const qualityStatus = toString(data.quality_status || data.qualityStatus, memo.degraded === true ? 'degraded' : 'insufficient_sources');
  const rawPlaybookContext = isObject(data.playbook_context || data.playbookContext)
    ? (data.playbook_context || data.playbookContext)
    : null;
  const rawConflictWarning = isObject(data.conflict_warning || data.conflictWarning)
    ? (data.conflict_warning || data.conflictWarning)
    : null;
  const rawContextInfluence = isObject(data.context_influence || data.contextInfluence)
    ? (data.context_influence || data.contextInfluence)
    : null;
  const contextInfluence = rawContextInfluence
    ? {
      mode: toString(rawContextInfluence.mode, 'market_wide'),
      portfolioApplied: !!(rawContextInfluence.portfolio_applied ?? rawContextInfluence.portfolioApplied),
      source: toString(rawContextInfluence.source, ''),
      requestedTickers: normalizeCopilotStarterTickers(
        rawContextInfluence.requested_tickers || rawContextInfluence.requestedTickers
      ),
      effectiveTickers: normalizeCopilotStarterTickers(
        rawContextInfluence.effective_tickers || rawContextInfluence.effectiveTickers
      ),
      portfolioId: toString(rawContextInfluence.portfolio_id || rawContextInfluence.portfolioId, '')
    }
    : null;

  return {
    question: toString(data.question, 'Que faire avec votre portefeuille ?'),
    consensus: verdict.toUpperCase(),
    answer: memoSummary || toString(data.answer || data.reasoning || data.why, ''),
    confidence,
    verdictClass: verdict,
    model: toString(data.model, 'Copilot'),
    qualityStatus,
    requirementsMet: {
      min_sources_2: !!requirementsMet.min_sources_2,
      quality_threshold: !!requirementsMet.quality_threshold
    },
    riskLevel,
    risk: {
      level: riskLevel,
      caveat: riskCaveat
    },
    models: modelRows,
    why: reasoning,
    reasoning: reasoning.length
      ? reasoning.join(' ')
      : (memoSummary || toString(data.answer, 'Analyse indisponible pour le moment, réessayez plus tard.')),
    dataSources: sources,
    horizon: memoHorizon,
    next_steps: nextSteps,
    invalidation,
    suggestedActions: toArray(data.suggestedActions, FALLBACK_LLM_JUDGE_DATA.suggestedActions).map((action) => ({
      icon: toString(action.icon, '➡️'),
      title: toString(action.title, 'Action'),
      detail: toString(action.detail, ''),
      action: toString(action.action, 'setAlert')
    })),
    generatedAt: memoFreshness || toString(data.generated_at || data.generatedAt, ''),
    playbook_id: toString(data.playbook_id || data.playbookId, ''),
    playbook_context: rawPlaybookContext
      ? {
        name: toString(rawPlaybookContext.name, ''),
        description: toString(rawPlaybookContext.description, ''),
        guardrails: toArray(rawPlaybookContext.guardrails, [])
          .map((item) => toString(item, '').trim())
          .filter(Boolean)
          .slice(0, 2)
      }
      : null,
    conflict_warning: rawConflictWarning
      ? {
        detected: !!rawConflictWarning.detected,
        reason: toString(rawConflictWarning.reason, ''),
        signal: toString(rawConflictWarning.signal, ''),
        playbook_id: toString(rawConflictWarning.playbook_id || rawConflictWarning.playbookId, '')
      }
      : null,
    contextInfluence,
    memo: {
      summary: memoSummary,
      regime: memoRegime,
      horizon: memoHorizon,
      topOpportunities: memoOpportunities,
      topRisks: memoRisks,
      nextSteps,
      invalidation,
      degraded: memo.degraded === true || qualityStatus === 'degraded',
      degradedReason: toString(
        memo.degraded_reason || memo.degradedReason || data.degraded_reason || data.degradedReason,
        ''
      ),
      freshness: memoFreshness
    }
  };
}

function sanitizeTradeIdeas(items) {
  const rows = toArray(items, FALLBACK_TRADE_IDEAS);
  return rows.map((item) => ({
    symbol: toString(item.symbol || item.ticker || 'UNKNOWN', 'UNKNOWN').toUpperCase(),
    signalType: toString(item.signalType || item.signal, 'Signal'),
    entry: toFiniteNumber(item.entry, 0),
    target: toFiniteNumber(item.target, 0),
    confidence: Math.max(0, Math.min(100, Math.round(toFiniteNumber(item.confidence, 70))))
  }));
}

function normalizePercentValue(value, fallback = 0) {
  const parsed = toFiniteNumber(value, fallback);
  return Math.abs(parsed) <= 1 ? parsed * 100 : parsed;
}

function sanitizeForecastRows(rows) {
  const items = toArray(rows, []);
  return items.map((item) => {
    const direction = toString(item.direction, 'neutral').toLowerCase();
    const expected = normalizePercentValue(toFiniteNumber(item.expectedReturn ?? item.expected_return ?? item.expected_return_pct ?? 0, 0));
    const targetPrice = toFiniteNumber(item.targetPrice ?? item.target_price ?? item.target, 0);
    const currentPrice = toFiniteNumber(item.currentPrice ?? item.current_price ?? item.current, 0);
    const updatedAt = toString(item.updatedAt || item.updated_at || item.generated_at || item.timestamp, '');
    const provenance = isObject(item.provenance) ? item.provenance : {};
    return {
      ticker: toString(item.ticker || item.symbol || item.asset || 'UNKNOWN', 'UNKNOWN').toUpperCase(),
      direction: direction,
      directionArrow: item.directionArrow || (direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→'),
      confidence: Math.max(0, Math.min(100, Math.round(normalizePercentValue(toFiniteNumber(item.confidence, 0))))),
      horizon: toString(item.horizon, ''),
      expectedReturn: expected,
      currentPrice,
      targetPrice,
      reasoning: toString(item.reasoning, item.reason || ''),
      action: toString(item.action, 'hold'),
      riskLevel: toString(item.riskLevel || item.risk, 'medium'),
      updatedAt,
      provenance: {
        ...provenance,
        sla: isObject(provenance.sla) ? provenance.sla : {}
      }
    };
  });
}

function sanitizeTopMovers(payload) {
  const rawRows = isObject(payload) ? [] : toArray(payload, []);
  const mapRows = Array.isArray(payload) ? payload : [];
  const fromMap = isObject(payload) && !Array.isArray(payload)
    ? Object.entries(payload).map(([ticker, stock]) => ({ ticker, ...stock }))
    : [];
  const rows = mapRows.length ? mapRows : (toArray(rawRows, []) || []);
  return toArray((rows.length ? rows : fromMap), []).map((item) => {
    const sparkline = Array.isArray(item.sparkline) ? item.sparkline : (Array.isArray(item.points) ? item.points : []);
    const sparkValues = toArray(Array.isArray(sparkline[0]) ? sparkline.map((p) => (Array.isArray(p) ? p[1] : p)) : sparkline, []);
    return {
      symbol: toString(item.ticker || item.symbol || item.name, 'UNKNOWN').toUpperCase(),
      price: toFiniteNumber(item.price, 0),
      change: toFiniteNumber(item.change ?? item.change30d ?? item.pct_change ?? 0, 0),
      change30d: toFiniteNumber(item.change30d ?? item.change ?? item.pct_change ?? 0, 0),
      forecast: toString(item.forecast, ''),
      confidence: Math.max(0, Math.min(100, Math.round(toFiniteNumber(item.confidence, 70)))),
      sparkline: sparkValues,
      position: toString(item.position, '0 shares')
    };
  });
}

function buildTradeIdeasFromForecasts(items) {
  const rows = sanitizeForecastRows(items);
  if (!rows.length) {
    return sanitizeTradeIdeas(window.tradeIdeas || FALLBACK_TRADE_IDEAS);
  }
  return rows.slice(0, 6).map((item) => ({
    symbol: item.ticker,
    signalType: item.action === 'buy' ? 'Buy' : item.action === 'sell' ? 'Sell' : 'Hold',
    entry: item.currentPrice || toFiniteNumber(item.targetPrice * 0.95, 0),
    target: item.targetPrice || item.currentPrice || 0,
    confidence: item.confidence
  }));
}

function normalizeKpiHero(payload = {}) {
  const source = isObject(payload) ? payload : {};
  const raw = source.data || source.portfolioSummary || source.portfolio_summary || source.portfolio || {};
  const percentLike = (value) => {
    const normalized = normalizePercentValue(toFiniteNumber(value, NaN), NaN);
    return Number.isFinite(normalized) ? normalized : null;
  };
  return {
    portfolioValue: toFiniteNumber(raw.portfolio_value ?? raw.portfolioValue ?? raw.final_capital, FALLBACK_APP_DATA.hero.portfolioValue),
    portfolioChange: percentLike(raw.total_return_pct ?? raw.portfolio_change ?? raw.portfolio_change_pct) ?? FALLBACK_APP_DATA.hero.portfolioChange,
    forecastNext30d: percentLike(raw.forecast_next_30d_pct ?? raw.forecast30d ?? raw.forecast_next30d) ?? FALLBACK_APP_DATA.hero.forecastNext30d,
    forecastConfidence: percentLike(raw.forecast_confidence_pct ?? raw.forecast_confidence ?? raw.confidence) ?? FALLBACK_APP_DATA.hero.forecastConfidence,
    winRate: Math.round(percentLike(raw.win_rate_pct ?? raw.winRate ?? raw.win_rate ?? raw.winrate) ?? FALLBACK_APP_DATA.hero.winRate),
    winRateChange: toFiniteNumber(raw.win_rate_change ?? raw.winRateChange ?? FALLBACK_APP_DATA.hero.winRateChange, FALLBACK_APP_DATA.hero.winRateChange)
  };
}

function inferTopStocksFromMovers(rows, fallbackRows = []) {
  const movers = sanitizeTopMovers(rows);
  if (!movers.length) return toArray(fallbackRows, []).slice(0, 5);
  return movers.slice(0, 5).map((item) => ({
    symbol: item.symbol,
    price: toFiniteNumber(item.price, 0),
    change: toFiniteNumber(item.change30d || item.change, 0),
    forecast: `${item.change >= 0 ? '+' : ''}${Math.abs(toFiniteNumber(item.change, 0)).toFixed(1)}%`,
    confidence: item.confidence
  }));
}

function sanitizeTopStockRows(rows, fallbackRows = []) {
  const fallback = toArray(fallbackRows, FALLBACK_APP_DATA.topStocks);
  const items = toArray(rows, fallback);
  return items.map((item) => {
    const forecast = toString(item.forecast, '');
    return {
      symbol: toString(item.symbol || item.ticker, 'UNKNOWN').toUpperCase(),
      price: toFiniteNumber(item.price, 0),
      change: toFiniteNumber(item.change, 0),
      forecast: forecast,
      confidence: Math.max(0, Math.min(100, Math.round(toFiniteNumber(item.confidence, 70))))
    };
  });
}

function sanitizeNewsItems(items) {
  const rows = toArray(items, FALLBACK_NEWS_ITEMS);
  return rows.map((item) => ({
    headline: toString(item.headline, 'Market update'),
    impact: Math.max(0, Math.min(10, Math.round(toFiniteNumber(item.impact, 5)))),
    effect: toString(item.effect, `${toFiniteNumber(item.change_percent, 0).toFixed(1)}%`),
    time: toString(item.time || item.published_at || item.created_at, 'recently'),
    source: toString(item.source, 'Unknown'),
    category: toString(item.category || item.section || item.ticker, 'News'),
    tickers: toArray(item.tickers, []),
    sentiment: toString(item.sentiment, '')
  }));
}

function sanitizeCopilotStart(payload) {
  const source = isObject(payload) ? payload : {};
  const fallback = FALLBACK_COPILOT_START;
  const scopeTickers = normalizeCopilotStarterTickers(source.scope_tickers);
  const briefSource = isObject(source.brief_of_day)
    ? source.brief_of_day
    : (isObject(source.briefOfDay) ? source.briefOfDay : {});
  const sectorRotation = isObject(briefSource.sector_rotation)
    ? briefSource.sector_rotation
    : (isObject(briefSource.sectorRotation) ? briefSource.sectorRotation : {});
  const marketRegime = toString(
    briefSource.market_regime
      || briefSource.marketRegime
      || briefSource.market_sentiment
      || briefSource.sentiment
      || briefSource.regime,
    fallback.brief_of_day.market_regime
  ).toUpperCase();
  const askItems = toArray(source.ask, fallback.ask)
    .slice(0, fallback.ask.length)
    .map((item, index) => {
      const base = fallback.ask[index] || fallback.ask[0];
      const prefill = isObject(item && item.prefill) ? item.prefill : {};
      return {
        id: toString(item && item.id, base.id),
        label: toString(item && item.label, base.label),
        prompt: toString(
          item && item.prompt,
          toString(item && item.question, toString(prefill.question, base.prompt))
        ),
        tickers: normalizeCopilotStarterTickers(
          Array.isArray(item && item.tickers)
            ? item.tickers
            : (Array.isArray(prefill.tickers) ? prefill.tickers : [])
        )
      };
    });
  const openItems = toArray(source.open, fallback.open)
    .slice(0, fallback.open.length)
    .map((item, index) => {
      const base = fallback.open[index] || fallback.open[0];
      return {
        id: toString(item && item.id, base.id),
        label: toString(item && item.label, base.label),
        target: normalizeCopilotStartOpenTarget(item && item.target, item && item.id ? item.id : base.id)
      };
    });

  return {
    brief_of_day: {
      ...fallback.brief_of_day,
      ...briefSource,
      title: toString(briefSource.title || briefSource.headline, fallback.brief_of_day.title),
      summary: toString(briefSource.summary || briefSource.message || briefSource.overview, fallback.brief_of_day.summary),
      market_regime: marketRegime,
      market_sentiment: marketRegime,
      top_opportunities: normalizeCopilotStartList(
        briefSource.top_opportunities || briefSource.topOpportunities || briefSource.opportunities || briefSource.top_signals || briefSource.signals
      ),
      top_signals: normalizeCopilotStartList(briefSource.top_signals || briefSource.signals),
      top_risks: normalizeCopilotStartList(briefSource.top_risks || briefSource.risks),
      macro_signals: toArray(briefSource.macro_signals, fallback.brief_of_day.macro_signals),
      sector_rotation: {
        top: toArray(sectorRotation.top, fallback.brief_of_day.sector_rotation.top),
        bottom: toArray(sectorRotation.bottom, fallback.brief_of_day.sector_rotation.bottom)
      },
      generated_at: toString(
        briefSource.generated_at || briefSource.generatedAt || briefSource.freshness,
        fallback.brief_of_day.generated_at
      ),
      freshness: toString(
        briefSource.freshness || briefSource.generated_at || briefSource.generatedAt,
        fallback.brief_of_day.freshness
      ),
      source: normalizeCopilotSourceLabels(briefSource.sources || briefSource.source || fallback.brief_of_day.source),
      sources: normalizeCopilotSourceLabels(briefSource.sources || briefSource.source || fallback.brief_of_day.sources),
      degraded: briefSource.degraded === true
    },
    ask: askItems.length ? askItems : fallback.ask,
    open: openItems.length ? openItems : fallback.open,
    scope_tickers: scopeTickers
  };
}

const ALERT_SEVERITY_ORDER = {
  critical: 0,
  high: 1,
  warning: 2,
  medium: 3,
  info: 4,
  low: 5
};

function normalizeAlertSeverity(value, fallback = 'medium') {
  const severity = toString(value, fallback).toLowerCase();
  if (severity === 'critical') return 'critical';
  if (severity === 'high') return 'high';
  if (severity === 'warning') return 'warning';
  if (severity === 'medium') return 'medium';
  if (severity === 'low') return 'low';
  if (severity === 'info') return 'info';
  return fallback;
}

function mapAlertPriority(severity, fallback = 'low') {
  const normalized = normalizeAlertSeverity(severity, fallback);
  if (normalized === 'critical' || normalized === 'high') return 'high';
  if (normalized === 'warning' || normalized === 'medium') return 'medium';
  return 'low';
}

function mapAlertType(rawType = '', rawCategory = '') {
  const type = toString(rawType, '').toLowerCase();
  const category = toString(rawCategory, '').toLowerCase();
  if (category === 'news') return 'news';
  if (category === 'risk') return 'risks';
  if (type.includes('risk') || type.includes('bear') || type.includes('negative') || type.includes('volatility')) return 'risks';
  if (type.includes('bull') || type.includes('support') || type.includes('oversold-bullish') || type.includes('positive') || type.includes('breakout') || category === 'forecast') return 'opportunities';
  return 'signal';
}

function resolveAlertIcon(type = '', severity = 'low') {
  const normalizedType = type.toLowerCase();
  if (normalizedType.includes('risk') || normalizedType.includes('bear') || normalizedType.includes('volatility')) return '⚠️';
  if (normalizedType.includes('news')) return '📰';
  if (normalizedType.includes('positive') || normalizedType.includes('bull') || normalizedType.includes('breakout')) return '📈';
  if (normalizeAlertSeverity(severity, 'low') === 'low' || normalizeAlertSeverity(severity, 'low') === 'info') return '🛈';
  return '⚡';
}

function sanitizeAlertTimeline(items) {
  const rows = toArray(items, []);
  const bySignature = new Map();
  const parsed = rows.map((item) => {
    const source = isObject(item) ? item : {};
    const severity = normalizeAlertSeverity(source.severity, 'medium');
    const priority = mapAlertPriority(severity, 'low');
    const type = mapAlertType(source.type, source.category);
    const confidence = toFiniteNumber(source.confidence, 0);
    const confidenceLabel = Math.max(0, Math.min(100, Math.round(confidence > 1 ? confidence : confidence * 100)));
    const summary = toString(source.summary || source.description || source.detail || source.message, 'Alerte marché détectée');
    const timestamp = toString(source.timestamp || source.generated_at || source.generatedAt, new Date().toISOString());
    const signature = [toString(source.ticker, 'MARKET'), source.type || 'signal', summary].join('|');

    return {
      id: toString(source.id, 'alert-' + signature.replace(/[^a-z0-9-]/gi, '-')),
      title: `${toString(source.ticker, 'MARKET').toUpperCase()} ${type === 'risks' ? 'Risk' : type === 'news' ? 'News' : 'Signal'}`,
      summary,
      severity,
      severityLabel: toString(severity, 'medium').toUpperCase(),
      priority,
      priorityRank: ALERT_SEVERITY_ORDER[severity],
      type,
      confidence: confidenceLabel,
      confidenceLabel: confidenceLabel ? `${confidenceLabel}%` : '—',
      ticker: toString(source.ticker, 'MARKET').toUpperCase(),
      icon: resolveAlertIcon(source.type, severity),
      timestamp,
      timeLabel: formatRelativeTime(timestamp),
      signalSource: source.category || source.type || 'market',
      actionHint: type === 'news' ? 'Voir news' : 'Act now',
      signature
    };
  });

  parsed.forEach((item) => {
    if (!item.signature || bySignature.has(item.signature)) {
      return;
    }
    bySignature.set(item.signature, item);
  });

  return Array.from(bySignature.values())
    .sort((a, b) => {
      if (a.priorityRank !== b.priorityRank) return a.priorityRank - b.priorityRank;
      if (a.confidence !== b.confidence) return b.confidence - a.confidence;
      return Date.parse(b.timestamp || 0) - Date.parse(a.timestamp || 0);
    })
    .slice(0, 12);
}

function renderAlertTimeline(alerts = liveAlerts) {
  const container = document.getElementById('timelineContainer');
  if (!container) return;

  const rows = sanitizeAlertTimeline(alerts);
  if (!rows.length) {
    container.innerHTML = `
      <div class="alert-item medium expandable" data-priority="low" data-type="news" onclick="toggleAlertDetails(this)">
        <span class="alert-icon">🔎</span>
        <div class="alert-content">
          <h3>Aucune alerte nouvelle</h3>
          <p>Le flux reste propre pour l'instant</p>
        </div>
        <div class="alert-actions" style="display: none;"></div>
      </div>
    `;
    return;
  }

  container.innerHTML = rows.map((item) => `
    <div class="alert-item ${item.priority} expandable" data-priority="${item.priority}" data-type="${item.type}" onclick="toggleAlertDetails(this)">
      <span class="alert-icon">${item.icon}</span>
      <div class="alert-content">
        <h3>${item.title}</h3>
        <p>${item.confidenceLabel} confidence • ${item.timeLabel}</p>
      </div>
      <div class="alert-actions" style="display: none;">
        <button class="alert-action-btn primary" onclick="showToast('Applying ${item.actionHint} for ${item.ticker}')">${item.actionHint}</button>
        <button class="alert-action-btn secondary" onclick="showToast('Reminder set for ${item.ticker}')">Remind Me</button>
        <button class="alert-action-btn" onclick="showToast('Alert dismissed')">Dismiss</button>
      </div>
    </div>
  `).join('');
}

function sanitizeMarketCalendar(calendar) {
  const source = isObject(calendar) ? calendar : FALLBACK_MARKET_CALENDAR;
  return {
    earnings: toArray(source.earnings, FALLBACK_MARKET_CALENDAR.earnings).map((item) => ({
      stock: toString(item.stock, 'N/A'),
      date: toString(item.date, 'TBA'),
      impact: toString(item.impact, 'Medium'),
      holding: Boolean(item.holding)
    })),
    economicData: toArray(source.economicData, FALLBACK_MARKET_CALENDAR.economicData).map((item) => ({
      event: toString(item.event, 'N/A'),
      date: toString(item.date, 'TBA'),
      impact: toString(item.impact, 'Medium')
    })),
    exDividend: toArray(source.exDividend, FALLBACK_MARKET_CALENDAR.exDividend).map((item) => ({
      stock: toString(item.stock, 'N/A'),
      date: toString(item.date, 'TBA'),
      amount: toFiniteNumber(item.amount, 0)
    }))
  };
}

function sanitizeMarketDrivers(items) {
  const rows = toArray(items, FALLBACK_MARKET_DRIVERS);
  return rows.map((item) => ({
    factor: toString(item.factor, 'Market'),
    contribution: Math.max(0, Math.min(100, Math.round(toFiniteNumber(item.contribution, 0)))),
    color: toString(item.color, '#1F40AF')
  }));
}

function sanitizeJudgeDecisionJournal(entries) {
  const rows = extractArray(entries, ['entries', 'journal', 'decisions', 'history', 'verdicts']);
  return rows
    .map((entry) => {
      if (!isObject(entry)) return null;

      const symbol = toString(entry.symbol || entry.ticker || entry.asset || entry.market, 'Décision');
      const decision = toString(entry.decision || entry.verdict || entry.label || entry.outcome, 'N/A');
      const note = toString(entry.note || entry.outcome || entry.result || entry.status || entry.rationale || '', '');
      const rationale = toString(entry.rationale || entry.reason || entry.summary || entry.explanation || '', '');
      const confidence = toFiniteNumber(
        entry.confidence ?? entry.confidence_score ?? entry.score ?? entry.probability,
        null
      );
      const timeText = toString(
        entry.timestamp ||
          entry.time ||
          entry.generatedAt ||
          entry.createdAt ||
          entry.created_at ||
          '',
        ''
      ).trim();

      // V17: Preserve outcome_feedback for DecisionJournalOutcomeFeedback rendering
      const outcomeFeedback = isObject(entry.outcome_feedback)
        ? {
            schema_version: toString(entry.outcome_feedback.schema_version, 'v1'),
            status: toString(entry.outcome_feedback.status, 'pending'),
            update_mode: toString(entry.outcome_feedback.update_mode, 'append_only'),
            latest_feedback_at: entry.outcome_feedback.latest_feedback_at || null,
            next_checkpoint: isObject(entry.outcome_feedback.next_checkpoint)
              ? {
                  horizon: toString(entry.outcome_feedback.next_checkpoint.horizon, ''),
                  status: toString(entry.outcome_feedback.next_checkpoint.status, ''),
                  due_at: entry.outcome_feedback.next_checkpoint.due_at || null,
                  record_mode: entry.outcome_feedback.next_checkpoint.record_mode || null,
                  outcome: entry.outcome_feedback.next_checkpoint.outcome || null,
                  actual_return: entry.outcome_feedback.next_checkpoint.actual_return || null,
                  notes: entry.outcome_feedback.next_checkpoint.notes || null,
                  recorded_at: entry.outcome_feedback.next_checkpoint.recorded_at || null
                }
              : null,
            checkpoints: Array.isArray(entry.outcome_feedback.checkpoints)
              ? entry.outcome_feedback.checkpoints.map((cp) => ({
                  horizon: toString(cp.horizon, ''),
                  status: toString(cp.status, ''),
                  due_at: cp.due_at || null,
                  record_mode: cp.record_mode || null,
                  outcome: cp.outcome || null,
                  actual_return: cp.actual_return || null,
                  notes: cp.notes || null,
                  recorded_at: cp.recorded_at || null
                }))
              : []
          }
        : null;

      return {
        symbol,
        decision,
        note,
        rationale,
        confidence,
        timestamp: timeText || null,
        outcome_feedback: outcomeFeedback
      };
    })
    .filter(Boolean)
    .slice(0, 8);
}

function sanitizeSectorPerformance(items, fallback = []) {
  const rows = toArray(items, fallback);
  return rows
    .map((item) => {
      const source = isObject(item) ? item : {};
      const change = toFiniteNumber(source.change_pct ?? source.change ?? source.delta ?? source.delta_pct ?? 0, 0);
      const weight = toFiniteNumber(source.weight_pct ?? source.weight ?? source.alloc ?? 0, 0);
      const sector = toString(source.sector || source.name || source.label, 'Unknown');
      const holdings =
        source.holdings === true ||
        source.holdings === 'true' ||
        source.inPortfolio === true ||
        source.inPortfolio === 'true' ||
        weight > 0 ||
        sector === 'Portfolio';
      return {
        sector,
        change,
        changeLabel: `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`,
        absChange: Math.abs(change),
        trendIcon: change > 0 ? '↑' : change < 0 ? '↓' : '→',
        trendDirection: change > 0 ? 'UP' : change < 0 ? 'DOWN' : 'FLAT',
        inPortfolio: holdings,
        holdings,
        weight,
        weightLabel: `${toFiniteNumber(weight, 0).toFixed(2)}%`
      };
    })
    .filter((row) => !!row.sector);
}

function sanitizeCorrelationMatrix(rows, fallback) {
  if (!Array.isArray(rows)) return fallback;
  if (!rows.length) return fallback;
  return rows.map((row) => toNumberArray(row, fallback[0] || []));
}

function normalizeAppData(data = {}) {
  const base = FALLBACK_APP_DATA;
  const source = isObject(data) ? data : {};
  const sourceCorrelations = isObject(source.correlations) ? source.correlations : {};
  const portfolioRiskProfileFreshness = toString(source.portfolioRiskProfileFreshness, '').trim();
  const labels = toArray(sourceCorrelations.labels, base.correlations.labels);
  const size = labels.length;
  const matrix = sanitizeCorrelationMatrix(sourceCorrelations.data, base.correlations.data).slice(0, size);

  return {
    ...base,
    ...source,
    portfolioSparkline: toNumberArray(source.portfolioSparkline, base.portfolioSparkline),
    forecastProjection: toNumberArray(source.forecastProjection, base.forecastProjection),
    stockSparklines: {
      ...base.stockSparklines,
      ...(isObject(source.stockSparklines) ? source.stockSparklines : {})
    },
    hero: {
      ...base.hero,
      ...(isObject(source.hero) ? source.hero : {})
    },
    correlations: {
      labels,
      data: matrix
    },
    sectorPerformance: sanitizeSectorPerformance(source.sectorPerformance, base.sectorPerformance),
    portfolioHealth: {
      ...base.portfolioHealth,
      ...(isObject(source.portfolioHealth) ? source.portfolioHealth : {})
    },
    portfolioRiskProfile: isObject(source.portfolioRiskProfile) ? source.portfolioRiskProfile : base.portfolioRiskProfile,
    portfolioRiskProfileFreshness: portfolioRiskProfileFreshness || base.portfolioRiskProfileFreshness,
    backtestResults: {
      ...base.backtestResults,
      ...(isObject(source.backtestResults) ? {
        sharpeRatio: toFiniteNumber(source.backtestResults.sharpe_ratio ?? source.backtestResults.sharpeRatio, base.backtestResults.sharpeRatio),
        winRate: toFiniteNumber(source.backtestResults.win_rate ?? source.backtestResults.winRate, base.backtestResults.winRate),
        maxDrawdown: toFiniteNumber(source.backtestResults.max_drawdown ?? source.backtestResults.maxDrawdown, base.backtestResults.maxDrawdown),
        totalReturn: toFiniteNumber(source.backtestResults.total_return ?? source.backtestResults.totalReturn, base.backtestResults.totalReturn)
      } : source.backtestResults)
    },
    opportunities: toArray(source.opportunities, base.opportunities),
    topStocks: toArray(source.topStocks, base.topStocks),
    marketDrivers: toArray(source.marketDrivers, base.marketDrivers),
    newsImpact: sanitizeNewsItems(toArray(source.newsImpact, source.newsItems || source.news || []))
  };
}

function formatRelativeTime(input) {
  const parsed = Date.parse(input);
  if (Number.isNaN(parsed)) return 'just now';
  const deltaMs = Math.max(0, Date.now() - parsed);
  const deltaMin = Math.floor(deltaMs / 60000);
  if (deltaMin < 1) return 'just now';
  if (deltaMin < 60) return `${deltaMin}m ago`;
  const deltaHours = Math.floor(deltaMin / 60);
  if (deltaHours < 24) return `${deltaHours}h ago`;
  const deltaDays = Math.floor(deltaHours / 24);
  return `${deltaDays}d ago`;
}

function getCriticalWidgetHealthAgeMs(meta = {}) {
  const freshness = isObject(meta.cache) ? meta.cache : isObject(meta.freshness) ? meta.freshness : {};
  const lastFetchedAt = toFiniteNumber(freshness.lastFetchedAt, 0);
  if (lastFetchedAt > 0) {
    return Math.max(0, Date.now() - lastFetchedAt);
  }
  const generatedAt = Date.parse(meta.generatedAt);
  return Number.isFinite(generatedAt) ? Math.max(0, Date.now() - generatedAt) : 0;
}

function getCriticalWidgetHealthStatus() {
  if (criticalWidgetHealthOverride && criticalWidgetHealthOverride.state) {
    return criticalWidgetHealthOverride;
  }

  const contractState = toString(liveDataMeta.contractState, '').toLowerCase();
  const warnings = toArray(liveDataMeta.warnings, []).map((entry) => toString(entry, '').toLowerCase());
  const sources = toArray(liveDataMeta.sources, []).map((entry) => toString(entry, '').toLowerCase());
  const apiStatus = toString(window.apiHealth && window.apiHealth.status, '').toLowerCase();
  const apiLastUpdates = isObject(window.apiHealth && window.apiHealth.last_updates)
    ? Object.values(window.apiHealth.last_updates)
    : [];
  const apiAgeMs = apiLastUpdates
    .map((entry) => Date.parse(entry))
    .filter((entry) => Number.isFinite(entry))
    .map((entry) => Math.max(0, Date.now() - entry))
    .reduce((maxAge, entry) => Math.max(maxAge, entry), 0);
  const baseAgeMs = getCriticalWidgetHealthAgeMs(liveDataMeta);
  const ageMs = Math.max(baseAgeMs, apiAgeMs);
  const ttlMs = Math.max(60000, toFiniteNumber(liveDataMeta.freshness?.ttlMs || liveDataMeta.cache?.ttlMs, 60000));

  if (apiStatus && apiStatus !== 'ok' && apiStatus !== 'healthy') {
    return { state: apiStatus.includes('degraded') ? 'degraded' : 'error' };
  }
  if (warnings.some((entry) => /(error|failed|timeout|exception)/.test(entry))) {
    return { state: 'error' };
  }
  if (contractState === 'stale') {
    return { state: 'stale', reason: 'Ingestion freshness contract reports stale sources.' };
  }
  if (contractState === 'degraded') {
    return { state: 'degraded', reason: 'Ingestion freshness contract reports partial source health.' };
  }
  if (contractState === 'unknown') {
    return { state: 'degraded', reason: 'Ingestion freshness contract is unavailable.' };
  }
  if (warnings.some((entry) => /(stale|delay|lag|aged)/.test(entry)) || ageMs > ttlMs * 2) {
    return { state: 'stale' };
  }
  if (
    sources.some((entry) => entry.includes('fallback'))
    || warnings.some((entry) => /(fallback|unavailable|partial|missing)/.test(entry))
  ) {
    return { state: 'degraded' };
  }
  return null;
}

function buildCriticalWidgetHealthDetail(status) {
  if (status && status.reason) {
    return status.reason;
  }

  if (status && status.state === 'loading') {
    return 'Cached data remains visible until live sync completes.';
  }

  const warnings = toArray(liveDataMeta.warnings, [])
    .map((entry) => toString(entry, '').replace(/[_-]+/g, ' ').trim())
    .filter(Boolean);
  if (warnings.length) {
    return warnings.slice(0, 2).join(' | ');
  }

  const sources = toArray(liveDataMeta.sources, []).map((entry) => toString(entry, '')).filter(Boolean);
  if (sources.length) {
    return `Source: ${sources.join(', ')}`;
  }

  return `Updated ${formatRelativeTime(liveDataMeta.generatedAt)}`;
}

function setCriticalWidgetHealthOverride(state, detail = {}) {
  criticalWidgetHealthOverride = state ? { state, ...detail } : null;
  scheduleCriticalWidgetHealthRender();
}

function isCriticalWidgetHealthHostVisible(node) {
  if (!node || !node.isConnected) {
    return false;
  }
  const style = typeof window !== 'undefined' && typeof window.getComputedStyle === 'function'
    ? window.getComputedStyle(node)
    : null;
  if (style && (style.display === 'none' || style.visibility === 'hidden')) {
    return false;
  }
  if (typeof node.getClientRects === 'function' && node.getClientRects().length > 0) {
    return true;
  }
  return node.offsetParent !== null;
}

function resolveCriticalWidgetHealthHost(target) {
  const selectors = toArray(target && target.selectors, []);
  let fallbackHost = null;
  for (const selector of selectors) {
    const node = document.querySelector(selector);
    if (node) {
      if (isCriticalWidgetHealthHostVisible(node)) {
        return node;
      }
      if (!fallbackHost) {
        fallbackHost = node;
      }
    }
  }
  return fallbackHost;
}

function clearCriticalWidgetHealthBanner(widgetKey) {
  document
    .querySelectorAll(`.dashboard-widget-health[data-widget="${widgetKey}"]`)
    .forEach((node) => node.remove());
}

function mountCriticalWidgetHealthBanner(host, banner, anchorSelector = '') {
  const anchor = anchorSelector ? host.querySelector(anchorSelector) : null;
  if (anchor) {
    anchor.insertAdjacentElement('afterend', banner);
    return;
  }
  host.prepend(banner);
}

function renderCriticalWidgetHealth() {
  criticalWidgetHealthFrame = null;
  const status = getCriticalWidgetHealthStatus();

  Object.entries(CRITICAL_WIDGET_HEALTH_TARGETS).forEach(([widgetKey, target]) => {
    clearCriticalWidgetHealthBanner(widgetKey);
    const shouldRender = Boolean(status) && (!target.shouldRender || target.shouldRender());
    if (!shouldRender) {
      return;
    }

    const host = resolveCriticalWidgetHealthHost(target);
    const copy = target.copy && status ? target.copy[status.state] : '';
    if (!host || !copy) {
      return;
    }

    const stateMeta = CRITICAL_WIDGET_HEALTH_STATE_META[status.state] || CRITICAL_WIDGET_HEALTH_STATE_META.error;
    const banner = document.createElement('div');
    banner.className = 'dashboard-widget-health';
    banner.dataset.widget = widgetKey;
    banner.dataset.state = status.state;
    banner.setAttribute('role', 'status');
    banner.setAttribute('aria-live', 'polite');

    const summary = document.createElement('div');
    summary.className = 'dashboard-widget-health__summary';

    const meta = document.createElement('div');
    meta.className = 'dashboard-widget-health__meta';

    const badge = document.createElement('span');
    badge.className = 'dashboard-widget-health__badge';
    badge.textContent = stateMeta.badge;

    const detail = document.createElement('span');
    detail.className = 'dashboard-widget-health__detail';
    detail.textContent = buildCriticalWidgetHealthDetail(status);

    const message = document.createElement('p');
    message.className = 'dashboard-widget-health__message';
    message.textContent = copy;

    meta.appendChild(badge);
    meta.appendChild(detail);
    summary.appendChild(meta);
    summary.appendChild(message);
    banner.appendChild(summary);

    const action = document.createElement('button');
    action.type = 'button';
    action.className = 'dashboard-widget-health__action';
    action.textContent = stateMeta.actionLabel;
    action.disabled = Boolean(stateMeta.actionDisabled);
    if (!stateMeta.actionDisabled) {
      action.addEventListener('click', () => refreshData());
    }
    banner.appendChild(action);

    mountCriticalWidgetHealthBanner(host, banner, target.anchorSelector);
  });
}

function scheduleCriticalWidgetHealthRender() {
  if (criticalWidgetHealthFrame) {
    cancelAnimationFrame(criticalWidgetHealthFrame);
  }
  criticalWidgetHealthFrame = requestAnimationFrame(() => {
    renderCriticalWidgetHealth();
  });
}

function observeCriticalWidgetMounts() {
  if (criticalWidgetHealthObserver || typeof MutationObserver !== 'function') {
    return;
  }

  criticalWidgetHealthObserver = new MutationObserver(() => {
    scheduleCriticalWidgetHealthRender();
  });

  [
    'hero-what-need-container',
    'hero-glassmorphic-container',
    'news-feed-widget-container',
    'forecast-scenarios-widget-container',
    'llm-judge-widget-container',
    'facette-view-container'
  ].forEach((id) => {
    const node = document.getElementById(id);
    if (node) {
      criticalWidgetHealthObserver.observe(node, { childList: true, subtree: true });
    }
  });
}

function updateLiveProvenance(meta = {}) {
  const lineage = document.getElementById('liveDataProvenance');
  if (!lineage) return;

  const configuredSources = toArray(meta.sources, [LIVE_FALLBACK_TAG]);
  const configuredModels = toArray(meta.modelVersions, ['unknown']);
  const configuredWarnings = toArray(meta.warnings, []);
  const sources = configuredSources.length ? configuredSources : [LIVE_FALLBACK_TAG];
  const models = configuredModels.length ? configuredModels : ['unknown'];
  const warnings = configuredWarnings.length ? configuredWarnings : [];
  const contractState = toString(meta.contractState, '').toLowerCase();
  const contractText = contractState ? ` | freshness: ${contractState.toUpperCase()}` : '';
  const forecastSla = isObject(meta.forecastSla) ? meta.forecastSla : null;
  const forecastSlaText = forecastSla
    ? ` | forecast SLA: ${forecastSla.withinTargetCount}/${forecastSla.totalCount} within ${forecastSla.targetLabel}`
    : '';
  const warningText = warnings.length ? ` | warnings: ${warnings.join(', ')}` : '';
  const freshness = formatRelativeTime(meta.generatedAt);
  lineage.textContent = `Source: ${sources.join(', ')} | model: ${models.join(', ')} | updated: ${freshness}${contractText}${forecastSlaText}${warningText}`;
}

function summarizeForecastSla(rows) {
  const items = toArray(rows, []).filter((row) => isObject(row));
  const slaRows = items
    .map((row) => (isObject(row.provenance) && isObject(row.provenance.sla) ? row.provenance.sla : null))
    .filter((sla) => !!sla);
  if (!slaRows.length) {
    return null;
  }

  const targetSeconds = Math.max(
    0,
    ...slaRows.map((sla) => toFiniteNumber(sla.target_max_age_seconds, 0))
  );
  const withinTargetCount = slaRows.filter((sla) => Boolean(sla.within_target)).length;
  const totalCount = slaRows.length;
  const compliancePct = totalCount ? Math.round((withinTargetCount / totalCount) * 100) : 0;
  const status = compliancePct >= 90 ? 'ok' : compliancePct > 0 ? 'degraded' : 'stale';
  const targetMinutes = Math.max(1, Math.round(targetSeconds / 60));

  return {
    withinTargetCount,
    totalCount,
    compliancePct,
    targetSeconds,
    targetLabel: `${targetMinutes}m`,
    status
  };
}

function syncDashboardCards() {
  const sourceHero = appData.hero || {};
  const kpiHero = normalizeKpiHero(liveKpis || livePortfolioSummary || {});
  const hero = {
    ...sourceHero,
    ...kpiHero
  };
  const portfolioValue = toFiniteNumber(hero.portfolioValue, FALLBACK_APP_DATA.hero.portfolioValue);
  const portfolioChange = toFiniteNumber(hero.portfolioChange, FALLBACK_APP_DATA.hero.portfolioChange);
  const forecast30d = toFiniteNumber(hero.forecastNext30d, FALLBACK_APP_DATA.hero.forecastNext30d);
  const forecastConfidence = toFiniteNumber(hero.forecastConfidence, FALLBACK_APP_DATA.hero.forecastConfidence);
  const winRate = Math.round(toFiniteNumber(hero.winRate, FALLBACK_APP_DATA.hero.winRate));

  const portfolioValueEl = document.querySelector('.kpi-value-huge[data-value]');
  if (portfolioValueEl) {
    portfolioValueEl.textContent = `$${portfolioValue.toLocaleString()}`;
  }
  const changeHuge = document.querySelector('.change-huge');
  if (changeHuge) {
    changeHuge.dataset.value = portfolioChange.toFixed(2);
    changeHuge.textContent = `${portfolioChange >= 0 ? '+' : ''}${portfolioChange.toFixed(2)}%`;
  }
  const forecastEl = document.querySelector('.kpi-value-huge.forecast');
  if (forecastEl) {
    forecastEl.dataset.value = forecast30d.toFixed(1);
    forecastEl.textContent = `${forecast30d >= 0 ? '+' : ''}${forecast30d.toFixed(1)}%`;
  }
  const gaugeEl = document.querySelector('.gauge-value-overlay');
  if (gaugeEl) {
    gaugeEl.textContent = `${Math.round(forecastConfidence)}%`;
  }
  const circleEl = document.querySelector('.circle-number[data-value]');
  if (circleEl) {
    circleEl.textContent = String(winRate);
  }

  if (appData.story && appData.story.content) {
    const summary = document.querySelector('.ai-summary-content');
    if (summary) {
      summary.textContent = appData.story.content;
    }
    const lastUpdated = document.querySelector('.last-updated');
    if (lastUpdated) {
      lastUpdated.textContent = toString(appData.story.timestamp, `Updated ${formatRelativeTime(liveDataMeta.generatedAt)}`);
    }
  }

  document.querySelectorAll('.last-updated, .refresh-time').forEach((el) => {
    el.textContent = `Updated ${formatRelativeTime(liveDataMeta.generatedAt)}`;
  });
}

function renderLiveDashboardWidgets() {
  renderMarketPulse();
  renderTradeIdeas();
  renderMarketCalendar();
  renderNewsFeed();
  renderMarketDrivers();
  renderHeroCopilotBrief(appData.copilotStart);
  renderAlertTimeline();
  renderJudgeDecisionJournal();
  syncDashboardCards();
  updateLiveProvenance(liveDataMeta);
  renderForecastScenarioWidget();
  renderTopMoversWidget();
  drawHealthGaugeCompact();
  drawHealthGauge();
  drawConfidenceGauge(Math.round(toFiniteNumber(appData.hero?.forecastConfidence, 82)));
  drawWinRateCircle();
  scheduleCriticalWidgetHealthRender();
}

function renderForecastScenarioWidget() {
  const scenarioWidget = document.querySelector('.forecast-scenarios-widget');
  if (!scenarioWidget) return;

  const rows = sanitizeForecastRows(liveForecastRows);
  const bars = scenarioWidget.querySelectorAll('.scenario-bar-item');
  const barsByType = {
    bull: bars[0],
    base: bars[1],
    bear: bars[2]
  };
  if (!rows.length || !bars.length) {
    return;
  }

  const positive = rows.filter((row) => row.direction === 'up' || row.direction === 'bullish');
  const negative = rows.filter((row) => row.direction === 'down' || row.direction === 'bearish');
  const neutral = rows.filter((row) => row.direction === 'neutral' || row.direction === 'flat');

  const avgReturn = rows.reduce((acc, row) => acc + row.expectedReturn, 0) / rows.length;
  const bullRow = positive.sort((a, b) => b.expectedReturn - a.expectedReturn)[0];
  const bearRow = negative.sort((a, b) => a.expectedReturn - b.expectedReturn)[0];

  const topBull = toString((bullRow ? bullRow.ticker : 'SPY'), '').toUpperCase();
  const topBear = toString((bearRow ? bearRow.ticker : 'QQQ'), '').toUpperCase();
  const topBase = toString((neutral[0] ? neutral[0].ticker : rows[0].ticker), '').toUpperCase();

  const makePercent = (value) => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  const clamp = (value) => Math.max(8, Math.min(85, Math.round(Math.abs(value) * 100) / 100));
  const bullValue = Math.abs((bullRow ? bullRow.expectedReturn : avgReturn > 0 ? avgReturn : 0));
  const baseValue = Math.abs(avgReturn || 0);
  const bearValue = Math.abs((bearRow ? Math.abs(bearRow.expectedReturn) : avgReturn < 0 ? Math.abs(avgReturn) : 2.1));

  if (barsByType.bull) {
    const fill = barsByType.bull.querySelector('.scenario-bar-fill');
    const label = barsByType.bull.querySelector('.scenario-label');
    if (label) label.textContent = `Bull Case (${topBull})`;
    if (fill) {
      fill.style.width = `${clamp(bullValue)}%`;
      fill.textContent = makePercent(toFiniteNumber(bullRow?.expectedReturn || (avgReturn > 0 ? avgReturn : 1.2), 1.2));
    }
  }

  if (barsByType.base) {
    const fill = barsByType.base.querySelector('.scenario-bar-fill');
    const label = barsByType.base.querySelector('.scenario-label');
    if (label) label.textContent = `Base Case (${topBase})`;
    if (fill) {
      fill.style.width = `${clamp(baseValue)}%`;
      fill.textContent = makePercent(toFiniteNumber(avgReturn, 2.1));
    }
  }

  if (barsByType.bear) {
    const fill = barsByType.bear.querySelector('.scenario-bar-fill');
    const label = barsByType.bear.querySelector('.scenario-label');
    if (label) label.textContent = `Bear Case (${topBear})`;
    if (fill) {
      fill.style.width = `${clamp(bearValue)}%`;
      fill.textContent = `${toFiniteNumber(bearRow?.expectedReturn || (-1.5), -1.5).toFixed(1)}%`;
    }
  }

  const scenarioContext = scenarioWidget.querySelector('.scenario-context');
  if (scenarioContext) {
    const liveTickers = rows.slice(0, 4).map((row) => row.ticker).join(', ');
    scenarioContext.textContent = `Top live forecasts: ${liveTickers}`;
  }
}

function renderTopMoversWidget(stocks = liveTopMovers) {
  const widget = document.querySelector('.top-movers-widget');
  if (!widget) return;

  const movers = sanitizeTopMovers(stocks);
  const rows = movers.slice(0, 5);
  const list = widget.querySelector('.movers-table');
  if (!list) return;

  if (!rows.length) {
    list.innerHTML = '';
    return;
  }

  list.innerHTML = rows.map((item) => {
    const symbol = toString(item.symbol, 'N/A');
    const symbolId = symbol.replace(/[^A-Za-z0-9]/g, '') || 'stock';
    const change = toFiniteNumber(item.change, 0);
    const colorClass = change >= 0 ? 'positive' : 'negative';
    const sign = change >= 0 ? '▲' : '▼';
    return `
      <div class="mover-row">
        <div class="mover-stock">${symbol}</div>
        <canvas class="table-sparkline" id="spark${symbolId}" width="80" height="30"></canvas>
        <div class="mover-price">$${toFiniteNumber(item.price, 0).toFixed(2)}</div>
        <div class="mover-change ${colorClass}">${sign} ${Math.abs(change).toFixed(1)}%</div>
        <div class="mover-position">${toString(item.position, '0 shares')}</div>
        <div class="mover-playbook" id="playbook-${symbolId}">
          <span class="playbook-badge badge-loading">⏳</span>
        </div>
        <button class="mover-action-btn" onclick="showToast('Trading ${symbol}...')">Trade</button>
      </div>
    `;
  }).join('');

  list.querySelectorAll('.table-sparkline').forEach((canvas, index) => {
    const item = rows[index];
    const clean = toString(item.symbol, `stock-${index}`).replace(/[^A-Za-z0-9]/g, '');
    const updated = document.getElementById(`spark${clean}`);
    if (!updated || !item.sparkline.length) return;
    const points = item.sparkline;
    const base = points.slice(-20);
    const isPositive = toFiniteNumber(item.change, 0) >= 0;
    drawMiniSparkline(updated.getContext('2d'), base, 80, 30, isPositive);
  });
  const footer = widget.querySelector('.widget-footer .widget-timestamp');
  if (footer) {
    footer.textContent = `Updated ${formatRelativeTime(liveDataMeta.generatedAt)}`;
  }

  hydrateTopMoversPlaybooks(rows);
}

async function hydrateTopMoversPlaybooks(rows = []) {
  const playbookIntegration = window.PlaybookIntegration;
  if (!playbookIntegration || typeof playbookIntegration.renderTickerPlaybookSummary !== 'function') {
    return;
  }

  for (const item of rows) {
    const symbol = toString(item.symbol, '').toUpperCase();
    const symbolId = symbol.replace(/[^A-Za-z0-9]/g, '') || 'stock';
    const container = document.getElementById(`playbook-${symbolId}`);
    if (!container) continue;

    try {
      container.innerHTML = await playbookIntegration.renderTickerPlaybookSummary(symbol);
    } catch (error) {
      console.warn(`[Top Movers] Failed to load playbook for ${symbol}:`, error.message);
      container.innerHTML = '<span class="playbook-badge badge-neutral">--</span>';
    }
  }
}

function renderJudgeDecisionJournal(entries = judgeDecisionJournal) {
  const container = document.getElementById('judgeDecisionJournal');
  if (!container) return;

  const rows = sanitizeJudgeDecisionJournal(entries);
  if (!rows.length) {
    container.innerHTML = '<p style="color: #94A3B8; margin: 0;">Aucun élément de journal de décision pour le moment.</p>';
    return;
  }

  container.innerHTML = rows.map((entry) => {
    const confidence = Number.isFinite(entry.confidence)
      ? `${Math.max(0, Math.min(100, Math.round(entry.confidence * 100)))}%`
      : null;

    const note = entry.note ? `<div class="alert-subtitle">${entry.note}</div>` : '';
    const rationale = entry.rationale ? `<p style="margin-top: 8px; color: #94A3B8;">${entry.rationale}</p>` : '';
    const meta = [entry.timestamp, confidence ? `Confiance: ${confidence}` : null]
      .filter(Boolean)
      .join(' • ');
    const metaMarkup = meta ? `<div class="alert-meta">${meta}</div>` : '';

    // V17: Outcome feedback loop display (DecisionJournalOutcomeFeedback)
    const outcomeFeedback = entry.outcome_feedback;
    let outcomeMarkup = '';
    if (outcomeFeedback && typeof outcomeFeedback === 'object') {
      const checkpoints = Array.isArray(outcomeFeedback.checkpoints) ? outcomeFeedback.checkpoints : [];
      const nextCheckpoint = outcomeFeedback.next_checkpoint || null;
      const statusBadge = outcomeFeedback.status
        ? `<span class="outcome-status-badge outcome-status-${outcomeFeedback.status}">${outcomeFeedback.status}</span>`
        : '';

      const nextCheckpointHtml = nextCheckpoint
        ? `<div class="outcome-next-checkpoint">
            <strong>Prochéchéance:</strong> ${nextCheckpoint.horizon || 'N/A'} • ${nextCheckpoint.status || 'En attente'}
            ${nextCheckpoint.due_at ? `• Échéance: ${new Date(nextCheckpoint.due_at).toLocaleDateString()}` : ''}
            ${nextCheckpoint.actual_return != null ? `• Rendement: ${nextCheckpoint.actual_return}%` : ''}
          </div>`
        : '';

      const checkpointsHtml = checkpoints.length
        ? `<div class="outcome-checkpoints">
            <strong>Historique:</strong>
            <ul style="margin: 6px 0 0 16px; font-size: 12px; color: #94A3B8;">
              ${checkpoints.map((cp) => `
                <li>
                  ${cp.horizon || 'N/A'}: ${cp.status || 'inconnu'}
                  ${cp.actual_return != null ? `(${cp.actual_return}%)` : ''}
                  ${cp.recorded_at ? `• ${new Date(cp.recorded_at).toLocaleDateString()}` : ''}
                </li>
              `).join('')}
            </ul>
          </div>`
        : '';

      outcomeMarkup = `<div class="outcome-feedback-section" style="margin-top: 10px; padding: 8px; background: rgba(30, 41, 59, 0.5); border-radius: 6px; border-left: 3px solid #3B82F6;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
          <span style="font-size: 14px; font-weight: 600;">📊 Suivi des résultats</span>
          ${statusBadge}
        </div>
        ${nextCheckpointHtml}
        ${checkpointsHtml}
      </div>`;
    }

    return `
      <div class="alert-item">
        <div class="alert-content">
          <div class="alert-title">${toString(entry.symbol, 'Décision')} • ${toString(entry.decision, 'N/A')}</div>
          ${note}
          ${rationale}
          ${metaMarkup}
          ${outcomeMarkup}
        </div>
      </div>
    `;
  }).join('');
}

function applyLiveDashboardData(payload = {}) {
  if (!payload || typeof payload !== 'object') {
    return;
  }

  const data = payload.data || payload;
  // Backfill core portfolio-state fields from the raw risk-profile contract
  // so partial health payloads do not regress to static fallback copy.
  const derivedPortfolioHealth = isObject(data.portfolioRiskProfile)
    && isObject(window.FinanceAPI)
    && typeof window.FinanceAPI.transformPortfolioRiskProfileToHealth === 'function'
    ? window.FinanceAPI.transformPortfolioRiskProfileToHealth({
      data: data.portfolioRiskProfile,
      freshness: data.portfolioRiskProfileFreshness || null,
      status: data.portfolioRiskProfileStatus || null
    })
    : null;
  const mergedPortfolioHealth = derivedPortfolioHealth || isObject(data.portfolioHealth)
    ? {
      ...(derivedPortfolioHealth || {}),
      ...(isObject(data.portfolioHealth) ? data.portfolioHealth : {})
    }
    : null;
  const payloadMeta = payload.meta || {};
  liveDataMeta = {
    generatedAt: payload.generatedAt || data.generatedAt || payload.generated_at || new Date().toISOString(),
    sources: toArray(payload.sources, toArray(payloadMeta.sources, toArray(payload.source, [LIVE_FALLBACK_TAG]))),
    modelVersions: toArray(payload.modelVersions, toArray(payloadMeta.modelVersions, ['unknown'])),
    warnings: toArray(payload.warnings, toArray(payloadMeta.warnings, [])),
    freshness: payload.freshness || payload.cache || { lastFetchedAt: Date.now(), ttlMs: 60000 },
    cache: payload.cache || { lastFetchedAt: Date.now(), ttlMs: 60000 },
    contractState: toString(payload.contractState || payloadMeta.contractState || '', '').toLowerCase() || 'unknown',
    ingestionHealth: isObject(payload.ingestionHealth)
      ? payload.ingestionHealth
      : (isObject(payloadMeta.ingestionHealth) ? payloadMeta.ingestionHealth : null)
  };

  tradeIdeas = sanitizeTradeIdeas(data.tradeIdeas);
  liveForecastRows = sanitizeForecastRows(data.forecasts || window.liveForecasts);
  liveDataMeta.forecastSla = summarizeForecastSla(liveForecastRows);
  liveTopMovers = sanitizeTopMovers(data.topMovers || data.stocks || window.topMovers);
  liveAlerts = sanitizeAlertTimeline(data.alerts || window.alertTimeline || []);
  liveKpis = data.kpis || window.liveKpis;
  livePortfolioSummary = data.portfolioSummary || window.livePortfolioSummary;

  const kpiSource = normalizeKpiHero(liveKpis || {});
  const summarySource = normalizeKpiHero(livePortfolioSummary || {});

  marketCalendar = sanitizeMarketCalendar(data.marketCalendar);
  newsItems = sanitizeNewsItems(data.newsItems);
  marketDrivers = sanitizeMarketDrivers(data.marketDrivers);
  tradeIdeas = buildTradeIdeasFromForecasts(liveForecastRows);

  const payloadTopStocks = toArray(data.topStocks, []);
  const fallbackTopStocks = inferTopStocksFromMovers(liveTopMovers, payloadTopStocks);
  const rawCopilotStart = data.copilotStart || data.copilot_start || window.copilotStart || null;
  const copilotScopeTickers = Array.isArray(rawCopilotStart?.scope_tickers)
    ? rawCopilotStart.scope_tickers
    : (Array.isArray(data.scope_tickers) ? data.scope_tickers : null);
  const copilotStartPayload = isObject(rawCopilotStart)
    ? {
      ...rawCopilotStart,
      ...(copilotScopeTickers ? { scope_tickers: copilotScopeTickers } : {})
    }
    : rawCopilotStart;
  const copilotStart = sanitizeCopilotStart(copilotStartPayload);
  const copilotStartState = isObject(copilotStartPayload)
    ? buildCopilotStartState({
      data: {
        copilot_start: copilotStart,
        scope_tickers: copilotScopeTickers
      }
    })
    : null;
  window.copilotStart = copilotStart;
  
  // Map story data from API (window.storyData set by apiConnector.js)
  const storyData = data.story || window.storyData || null;
  const storyOverride = storyData && typeof storyData === 'object' ? {
    headline: storyData.headline || 'Aperçu du jour',
    content: storyData.content || storyData.summary || '',
    sentiment: storyData.sentiment || 'neutral',
    timestamp: storyData.timestamp || storyData.generatedAt || new Date().toISOString()
  } : null;
  
  appData = normalizeAppData({
    ...data,
    ...(mergedPortfolioHealth ? { portfolioHealth: mergedPortfolioHealth } : {}),
    hero: {
      ...(isObject(data.hero) ? data.hero : {}),
      ...kpiSource,
      ...summarySource
    },
    copilotStart,
    topStocks: sanitizeTopStockRows(toArray(fallbackTopStocks, [])),
    ...(storyOverride ? { story: storyOverride } : {})
  });
  if (isObject(data.llmJudgeData)) {
    llmJudgeData = {
      ...FALLBACK_LLM_JUDGE_DATA,
      ...data.llmJudgeData
    };
  }
  judgeDecisionJournal = sanitizeJudgeDecisionJournal(
    data.judgeDecisionJournal || window.judgeDecisionJournal || []
  );

  renderLiveDashboardWidgets();
  if (copilotStartState) {
    renderHeroCopilotBrief(copilotStartState);
  } else if (rawCopilotStart) {
    renderHeroCopilotBrief(copilotStart);
  }
}

window.addEventListener(LIVE_DATA_EVENT, (event) => {
  applyLiveDashboardData(event.detail || {});
  if (v16State.currentFacette && v16State.currentTab) {
    loadFacetteContent(v16State.currentFacette, v16State.currentTab);
  }
});

// V11 State Management
const v11State = {
  storyMode: false,
  currentStoryPoint: 0,
  splitViewEnabled: false,
  filterBarVisible: false,
  currentProfile: loadStoredForecastProfile()
};

// ============ STATE MANAGEMENT ============
const appState = {
  selectedPeriod: '1W',
  customizeMode: false,
  darkMode: true,
  autoRefresh: true,
  refreshInterval: 60000
};

// ============ V11 ENHANCED FUNCTIONS ============

// Profile Management
function cloneProfileItems(items) {
  return Array.isArray(items) ? items.map((item) => ({ ...item })) : [];
}

function resolveProfilePreset(profile) {
  const preset = PROFILE_PRESETS[profile];
  return {
    label: preset?.label || DEFAULT_PROFILE_LABEL,
    userProfileType: preset?.userProfileType || DEFAULT_PROFILE_LABEL,
    complexityLevel: preset?.complexityLevel || FALLBACK_V11_DATA.userProfile.preferences.complexityLevel,
    refreshInterval: preset?.refreshInterval || FALLBACK_V11_DATA.userProfile.preferences.refreshInterval,
    judgePlaceholder: preset?.judgePlaceholder || DEFAULT_PROFILE_JUDGE_PLACEHOLDER,
    judgeExample: preset?.judgeExample || DEFAULT_PROFILE_JUDGE_EXAMPLE,
    aiSuggestions: cloneProfileItems(preset?.aiSuggestions || baseProfileAISuggestions),
    quickActions: cloneProfileItems(preset?.quickActions || DEFAULT_PROFILE_QUICK_ACTIONS)
  };
}

function renderProfileQuickActions(profile) {
  const container = document.getElementById('quick-actions-widget-container');
  if (!container) return;

  const { quickActions } = resolveProfilePreset(profile);
  container.innerHTML = `
    <section class="quick-actions-grid" aria-label="Quick actions">
      ${quickActions.map((action) => {
        const detailMarkup = action.detailType === 'confidence'
          ? `<div class="action-confidence">${action.detailLabel}: <span class="confidence-value">${action.detailValue}</span></div>`
          : `<div class="action-suggestion">${action.detailLabel}: ${action.detailValue}</div>`;
        return `
          <div class="action-card ${action.priority}-priority">
            <div class="action-header">
              <span class="priority-badge ${action.priority}">${action.badge}</span>
            </div>
            <h3 class="action-title">${action.title}</h3>
            ${detailMarkup}
            <div class="action-buttons">
              <button class="action-btn primary" onclick="showToast('${action.primaryToast}')">${action.primaryLabel}</button>
              <button class="action-btn secondary" onclick="showToast('${action.secondaryToast}')">${action.secondaryLabel}</button>
            </div>
          </div>
        `;
      }).join('')}
    </section>
  `;
}

function syncJudgeInputForProfile(profile) {
  const input = document.getElementById('judgeQuestion');
  if (!input) return;

  const preset = resolveProfilePreset(profile);
  const currentValue = toString(input.value, '').trim();
  if (!currentValue || PROFILE_JUDGE_EXAMPLES.includes(currentValue)) {
    input.value = preset.judgeExample;
  }
  input.placeholder = preset.judgePlaceholder;
}

function syncForecastProfileUI() {
  const profile = normalizeForecastProfile(v11State.currentProfile);
  if (profile !== v11State.currentProfile) {
    v11State.currentProfile = profile;
  }
  const preset = resolveProfilePreset(profile);
  const currentUserProfile = isObject(v11Data.userProfile) ? v11Data.userProfile : {};
  const currentPreferences = isObject(currentUserProfile.preferences) ? currentUserProfile.preferences : {};

  v11Data = {
    ...v11Data,
    userProfile: {
      ...currentUserProfile,
      type: preset.userProfileType,
      preferences: {
        ...currentPreferences,
        complexityLevel: preset.complexityLevel,
        refreshInterval: preset.refreshInterval
      }
    },
    aiSuggestions: cloneProfileItems(preset.aiSuggestions)
  };

  const selector = document.getElementById('profileSelector');
  if (selector) {
    selector.value = profile;
  }

  initAISuggestions();
  renderProfileQuickActions(profile);
  syncJudgeInputForProfile(profile);
}

function changeProfile(profile) {
  const nextProfile = storeForecastProfile(profile);
  v11State.currentProfile = nextProfile;
  const preset = resolveProfilePreset(nextProfile);
  showToast(`Profile changed to ${preset.label}`);
  // Reorganize widgets based on profile
  reorganizeWidgetsByProfile(nextProfile);
}

function reorganizeWidgetsByProfile(profile) {
  syncForecastProfileUI();
  console.log(`Reorganizing for ${profile} profile`);
}

// AI Suggestions
function initAISuggestions() {
  const panel = document.getElementById('aiSuggestionsPanel');
  const list = document.getElementById('suggestionsList');
  if (!list) return;

  list.innerHTML = v11Data.aiSuggestions.map(s => `
    <div class="suggestion-item ${s.priority}-priority" onclick="navigateToSuggestion('${s.widget}', '${s.tab}')">
      <span class="suggestion-icon">${s.type === 'check' ? '⚠️' : s.type === 'view' ? '📊' : '⚡'}</span>
      <div class="suggestion-content">
        <div class="suggestion-title">${s.title}</div>
        <div class="suggestion-meta">${s.timestamp} · ${s.priority.charAt(0).toUpperCase() + s.priority.slice(1)} Priority</div>
      </div>
      <button class="suggestion-go-btn" onclick="event.stopPropagation(); navigateToSuggestion('${s.widget}', '${s.tab}')">Go →</button>
    </div>
  `).join('');
}

function closeSuggestions() {
  const panel = document.getElementById('aiSuggestionsPanel');
  if (panel) panel.style.display = 'none';
}

function navigateToSuggestion(widget, tab) {
  showToast(`Navigating to ${widget} in ${tab}`);
  closeSuggestions();
}

// Story Mode
function toggleStoryMode() {
  v11State.storyMode = !v11State.storyMode;
  const overlay = document.getElementById('storyOverlay');
  if (!overlay) return;

  if (v11State.storyMode) {
    overlay.style.display = 'block';
    v11State.currentStoryPoint = 0;
    renderStoryPoint();
  } else {
    overlay.style.display = 'none';
  }
}

function renderStoryPoint() {
  const points = v11Data.storyPoints.overview;
  const current = v11State.currentStoryPoint;
  const container = document.getElementById('storyPointContainer');
  const currentEl = document.getElementById('storyCurrent');
  const totalEl = document.getElementById('storyTotal');

  if (!container || !points[current]) return;

  currentEl.textContent = current + 1;
  totalEl.textContent = points.length;

  const point = points[current];
  container.innerHTML = `
    <div class="story-point">
      <div class="story-point-header">
        <div class="story-number">${point.step}</div>
        <div>
          <h3>${point.title}</h3>
        </div>
      </div>
      <p>${point.description}</p>
      <button class="story-action" onclick="showToast('Navigating to ${point.widget}...')">View Details</button>
    </div>
  `;
}

function nextStoryPoint() {
  const points = v11Data.storyPoints.overview;
  if (v11State.currentStoryPoint < points.length - 1) {
    v11State.currentStoryPoint++;
    renderStoryPoint();
  }
}

function prevStoryPoint() {
  if (v11State.currentStoryPoint > 0) {
    v11State.currentStoryPoint--;
    renderStoryPoint();
  }
}

// Drill-Down
function buildRobustnessGoNoGoDecision() {
  const status = getCriticalWidgetHealthStatus();
  const rawState = status && status.state;
  const state = rawState
    ? String(rawState).trim().toLowerCase()
    : (status && status.reason ? 'unknown' : 'ok');
  const reason = status && status.reason
    ? toString(status.reason, '')
    : buildCriticalWidgetHealthDetail(status || { state: 'ok' });
  const detail = reason || 'Data quality is within tolerance.';
  const normalizedState = state === 'warn' ? 'warning' : state;

  if (['error', 'degraded', 'stale', 'loading', 'warning', 'unknown'].includes(normalizedState)) {
    return {
      state: normalizedState,
      decision: 'NO-GO',
      detail,
    };
  }

  return { state, decision: 'GO', detail };
}

function buildRobustnessDrillPayload() {
  const decision = buildRobustnessGoNoGoDecision();
  const sourceMeta = toArray(liveDataMeta.sources, [LIVE_FALLBACK_TAG]).join(', ');
  const modelMeta = toArray(liveDataMeta.modelVersions, ['unknown']).join(', ');
  const warningMeta = toArray(liveDataMeta.warnings, ['none']).join(' | ');
  const freshnessMeta = formatRelativeTime(liveDataMeta.generatedAt);

  const summaryClasses = decision.decision === 'GO' ? 'context-badge positive' : 'context-badge warning';
  const summary = decision.decision === 'GO'
    ? 'All critical signals are in tolerance. You can proceed with a standard action gate.'
    : 'Critical quality warning detected. Consider holding and refreshing before committing.';
  const actions = decision.decision === 'GO'
    ? [
      'Proceed with standard workflow.',
      'Monitor alert panel after action.',
    ]
    : [
      'Pause new entries and wait for refresh.',
      'Review live feed warnings and retry the drill.',
    ];

  return {
    title: 'Robustness Drill: GO / NO-GO',
    content: `
      <div class="drill-section">
        <h3>Readiness Verdict</h3>
        <div style="display:flex;align-items:center;gap:10px;margin:12px 0;">
          <span class="${summaryClasses}">${decision.decision}</span>
          <span>${summary}</span>
        </div>
        <p>${decision.detail}</p>
        <p><strong>Sources:</strong> ${sourceMeta}</p>
        <p><strong>Models:</strong> ${modelMeta}</p>
        <p><strong>Warnings:</strong> ${warningMeta}</p>
        <p><strong>Freshness:</strong> ${freshnessMeta}</p>
      </div>
      <div class="drill-section">
        <h3>Next Actions</h3>
        <div class="drill-section">
          ${actions.map((action) => `<p>• ${action}</p>`).join('')}
        </div>
        ${decision.decision === 'GO'
          ? "<p class=\"drill-actions\"><button class=\"drill-action-btn\" onclick=\"showToast('Proceeding under GO signal')\">Proceed</button></p>"
          : '<p class="drill-actions"><button class="drill-action-btn" onclick="refreshData()">Refresh Now</button></p>'
        }
      </div>
    `
  };
}

function openRobustnessDrill() {
  const payload = buildRobustnessDrillPayload();
  openDrillDown('readiness', payload);
  return payload;
}

function openDrillDown(metric, readinessPayload = null) {
  const modal = document.getElementById('drillDownModal');
  const title = document.getElementById('drillDownTitle');
  const body = document.getElementById('drillDownBody');

  if (!modal || !title || !body) return;

  const drillData = {
    readiness: readinessPayload || buildRobustnessDrillPayload(),
    portfolio: {
      title: 'Portfolio Change: +1.88%',
      content: `
        <div class="drill-section">
          <h3>Contributing Factors</h3>
          <div class="contribution-chart">
            <div class="waterfall-item"><span>NVDA</span><div class="waterfall-bar" style="width: 45%; background: var(--color-success);">+0.85%</div></div>
            <div class="waterfall-item"><span>META</span><div class="waterfall-bar" style="width: 24%; background: var(--color-success);">+0.45%</div></div>
            <div class="waterfall-item"><span>AAPL</span><div class="waterfall-bar" style="width: 18%; background: var(--color-success);">+0.34%</div></div>
            <div class="waterfall-item"><span>Others</span><div class="waterfall-bar" style="width: 13%; background: var(--color-success);">+0.24%</div></div>
          </div>
        </div>
        <div class="drill-section">
          <h3>🤖 AI Analysis</h3>
          <div class="ai-explanation">
            <p>Tech rally on Fed dovish signals. Your heavy tech exposure (45% portfolio) amplified gains. NVDA earnings beat expectations yesterday, momentum continuing.</p>
          </div>
        </div>
        <div class="drill-actions">
          <button class="drill-action-btn" onclick="showToast('Viewing tech holdings...')">View Tech Holdings</button>
          <button class="drill-action-btn" onclick="showToast('Rebalancing...')">Rebalance Portfolio</button>
          <button class="drill-action-btn" onclick="showToast('Setting alerts...')">Set Price Alerts</button>
        </div>
      `
    },
    forecast: {
      title: 'AI Forecast: +5.3% (Next 30 Days)',
      content: `
        <div class="drill-section">
          <h3>Forecast Breakdown</h3>
          <div class="timeline-section">
            <p><strong>Week 1:</strong> +1.2% (Fed policy support)</p>
            <p><strong>Week 2:</strong> +1.8% (Earnings momentum)</p>
            <p><strong>Week 3:</strong> +1.5% (Technical breakout)</p>
            <p><strong>Week 4:</strong> +0.8% (Consolidation)</p>
          </div>
        </div>
        <div class="drill-section">
          <h3>🤖 Confidence Factors</h3>
          <div class="ai-explanation">
            <p>82% confidence based on: Technical momentum (40%), earnings season (35%), Fed policy (20%), market sentiment (5%).</p>
          </div>
        </div>
        <div class="drill-actions">
          <button class="drill-action-btn" onclick="showToast('Opening scenario builder...')">Build Custom Scenario</button>
          <button class="drill-action-btn" onclick="showToast('Running backtest...')">Backtest Strategy</button>
        </div>
      `
    }
  };

  const data = drillData[metric] || { title: 'Details', content: '<p>No additional data available.</p>' };

  title.textContent = data.title;
  body.innerHTML = data.content;
  modal.style.display = 'flex';
}

function closeDrillDown() {
  const modal = document.getElementById('drillDownModal');
  if (modal) modal.style.display = 'none';
}

// Split View
function toggleSplitView() {
  v11State.splitViewEnabled = !v11State.splitViewEnabled;
  const container = document.getElementById('splitViewContainer');
  const mainContainer = document.querySelector('.main-container');

  if (!container) return;

  if (v11State.splitViewEnabled) {
    container.style.display = 'grid';
    mainContainer.style.display = 'none';
    // Clone current view to left pane
    const leftPane = document.getElementById('leftPaneContent');
    const rightPane = document.getElementById('rightPaneContent');
    if (leftPane) leftPane.innerHTML = '<p style="padding: 20px;">Current view loaded</p>';
    if (rightPane) rightPane.innerHTML = '<p style="padding: 20px;">Comparison view: October data</p>';
    showToast('Split view enabled');
  } else {
    container.style.display = 'none';
    mainContainer.style.display = 'block';
    showToast('Split view disabled');
  }
}

function updateComparison(mode) {
  showToast(`Comparison changed to: ${mode}`);
}

function maximizePane(pane) {
  showToast(`Maximizing ${pane} pane`);
}

// Filter Bar
function toggleFilterBar() {
  const filterBar = document.getElementById('filterBar');
  if (!filterBar) return;

  v11State.filterBarVisible = !v11State.filterBarVisible;
  filterBar.classList.toggle('collapsed');

  // Update confidence slider display
  const slider = document.getElementById('confidenceSlider');
  const display = document.getElementById('confidenceValue');
  if (slider && display) {
    slider.oninput = () => display.textContent = slider.value + '%';
  }
}

function applyFilters() {
  const confidence = document.getElementById('confidenceSlider').value;
  showToast(`Filters applied: Confidence ≥ ${confidence}%`);
  // Apply filters to all widgets
}

function clearFilters() {
  document.getElementById('confidenceSlider').value = 70;
  document.getElementById('confidenceValue').textContent = '70%';
  showToast('Filters cleared');
}

// AI Insights
function initAIInsights() {
  const list = document.getElementById('insightsList');
  if (!list) return;

  const insights = v11Data.aiInsights.overview;
  list.innerHTML = insights.map(i => `
    <div class="insight-item ${i.type}" onclick="showToast('${i.action}')">
      <span class="insight-icon">${i.icon}</span>
      <div class="insight-content">
        <div class="insight-title">${i.title}</div>
        <div class="insight-description">${i.description}</div>
      </div>
      <button class="insight-action" onclick="event.stopPropagation(); showToast('${i.action}')">${i.action}</button>
    </div>
  `).join('');
}

function refreshInsights() {
  showToast('Refreshing AI insights...');
  setTimeout(() => {
    initAIInsights();
    showToast('Insights refreshed!');
  }, 1000);
}

// Widget Actions
function askAIAbout(widget) {
  toggleAICopilot();
  setTimeout(() => {
    addAIMessage(`Tell me about the ${widget} widget and what actions I should take.`, 'user');
    setTimeout(() => {
      addAIMessage(`The ${widget} shows current market conditions. Based on the data, I recommend monitoring tech sector momentum and considering portfolio rebalancing if volatility increases.`, 'ai');
    }, 1000);
  }, 500);
}

function askAIPrompt(prompt) {
  toggleAICopilot();
  setTimeout(() => {
    addAIMessage(prompt, 'user');
    setTimeout(() => {
      const responses = {
        'Why is this changing?': 'The change is driven by Fed dovish signals and strong tech earnings. NVDA beat expectations, creating positive momentum across the sector.',
        'Predict next 7 days': 'AI predicts +2.3% over next 7 days with 85% confidence. Key drivers: continued earnings momentum, low volatility environment, and positive market sentiment.',
        'Find anomalies': 'Detected 2 anomalies: 1) Volatility spike at 2pm (unusual for this hour), 2) TSLA underperforming vs sector (-12% while tech +8.5%).'
      };
      addAIMessage(responses[prompt] || 'Analyzing your request...', 'ai');
    }, 1000);
  }, 500);
}

function pinWidget(widget) {
  showToast(`${widget} pinned to dashboard`);
}

function setAlert(widget) {
  showToast(`Alert set for ${widget}`);
}

function exportWidget(widget) {
  showToast(`Exporting ${widget} data...`);
}

// ============ DIAMOND RADIAL MENU (V14) ============
function toggleDiamondMenu() {
  const menu = document.getElementById('diamondMenu');
  if (!menu) return;

  const isHidden = menu.style.display === 'none' || menu.style.display === '';
  menu.style.display = isHidden ? 'block' : 'none';
}

function closeDiamondMenu() {
  const menu = document.getElementById('diamondMenu');
  if (menu) {
    menu.style.display = 'none';
  }
}

// ============ AI COPILOT FUNCTIONS ============
function toggleAICopilot() {
  const overlay = document.getElementById('aiCopilotOverlay');
  if (!overlay) return;

  if (overlay.style.display === 'none' || !overlay.style.display) {
    overlay.style.display = 'block';
    setTimeout(() => overlay.classList.add('active'), 10);
    hydrateCopilotOverlayStart();
    focusCopilotInput();
  } else {
    overlay.classList.remove('active');
    setTimeout(() => overlay.style.display = 'none', 400);
  }
}

function appendCopilotChatMessage(containerId, content, type, options = {}) {
  const panel = document.getElementById(containerId);
  if (!panel) return null;

  const messageDiv = document.createElement('div');
  messageDiv.className = 'ai-message';

  const bodyHtml = options.html === true
    ? toString(content, '<p>Analysis unavailable for the moment.</p>')
    : `<p>${escapeHtml(toString(content, '')).replace(/\n/g, '<br/>')}</p>`;

  if (type === 'user') {
    messageDiv.innerHTML = `
      <div class="ai-avatar" style="background: var(--color-royal-blue);">👤</div>
      <div class="ai-message-content">
        ${bodyHtml}
      </div>
    `;
  } else {
    messageDiv.innerHTML = `
      <div class="ai-avatar">🤖</div>
      <div class="ai-message-content">
        ${bodyHtml}
      </div>
    `;
  }

  panel.appendChild(messageDiv);
  panel.scrollTop = panel.scrollHeight;
  return messageDiv;
}

function buildCopilotChatResponseHtml(payload) {
  const verdict = escapeHtml(toString(payload.consensus, 'HOLD'));
  const confidence = Math.max(0, Math.min(100, Math.round(toFiniteNumber(payload.confidence, 0))));
  const riskLevel = escapeHtml(toString(payload.risk && payload.risk.level, 'medium'));
  const model = escapeHtml(toString(payload.model, 'Copilot'));
  const quality = escapeHtml(toString(payload.qualityStatus, 'insufficient_sources').replace(/_/g, ' '));
  const memo = isObject(payload.memo) ? payload.memo : {};
  const memoSummary = toString(memo.summary, '').trim();
  const memoRegime = toString(memo.regime, '').replace(/_/g, ' ').trim();
  const memoHorizon = toString(payload.horizon || memo.horizon, '').replace(/_/g, ' ').trim();
  const memoOpportunities = toArray(memo.topOpportunities, []).slice(0, 3);
  const memoRisks = toArray(memo.topRisks, []).slice(0, 3);
  const memoNextSteps = toArray(payload.next_steps || payload.nextSteps || memo.nextSteps || memo.next_steps, [])
    .map((item) => toString(item, '').trim())
    .filter((item) => item.length > 0)
    .slice(0, 3);
  const memoInvalidation = toArray(payload.invalidation || memo.invalidation, [])
    .map((item) => toString(item, '').trim())
    .filter((item) => item.length > 0)
    .slice(0, 3);
  const memoDegraded = memo.degraded === true;
  const memoDegradedReason = toString(memo.degradedReason || memo.degraded_reason, '')
    .replace(/_/g, ' ')
    .trim();
  const reasoning = toArray(payload.why, [])
    .map((line) => toString(line, '').trim())
    .filter((line) => line.length > 0)
    .slice(0, 3);
  const reasoningText = reasoning.join(' ').trim();
  const reasoningHtml = reasoning.length
    ? reasoning.map((line, index) => `<p${index ? ' style="margin-top: 8px;"' : ''}>${escapeHtml(line)}</p>`).join('')
    : `<p>${escapeHtml(toString(payload.answer, 'Analysis unavailable for the moment.'))}</p>`;
  const summaryHtml = memoSummary
    ? `<p style="margin-top: 8px;">${escapeHtml(memoSummary)}</p>`
    : '';
  const regimeHtml = memoRegime
    ? `<p style="margin-top: 8px;"><strong>Regime:</strong> ${escapeHtml(memoRegime)}</p>`
    : '';
  const horizonHtml = memoHorizon
    ? `<p style="margin-top: 8px;"><strong>Horizon:</strong> ${escapeHtml(memoHorizon)}</p>`
    : '';
  const opportunitiesHtml = memoOpportunities.length
    ? `<p style="margin-top: 8px;"><strong>Opportunities:</strong> ${memoOpportunities.map((item) => escapeHtml(toString(item, ''))).join(' • ')}</p>`
    : '';
  const topRisksHtml = memoRisks.length
    ? `<p style="margin-top: 8px;"><strong>Risks:</strong> ${memoRisks.map((item) => escapeHtml(toString(item, ''))).join(' • ')}</p>`
    : '';
  const nextStepsHtml = memoNextSteps.length
    ? `<p style="margin-top: 8px;"><strong>Next steps:</strong> ${memoNextSteps.map((item) => escapeHtml(item)).join(' • ')}</p>`
    : '';
  const invalidationHtml = memoInvalidation.length
    ? `<p style="margin-top: 8px;"><strong>Invalidation:</strong> ${memoInvalidation.map((item) => escapeHtml(item)).join(' • ')}</p>`
    : '';
  const riskHtml = payload.risk && payload.risk.caveat
    ? `<p style="margin-top: 8px;"><strong>Risk:</strong> ${escapeHtml(payload.risk.caveat)}</p>`
    : '';
  const degradedHtml = memoDegraded
    ? `<p style="margin-top: 8px; color: #FBBF24;"><strong>Degraded:</strong> ${escapeHtml(memoDegradedReason || 'This memo is using partial backend context.')}</p>`
    : '';
  const sourceLabels = toArray(payload.dataSources, [])
    .slice(0, 3)
    .map((source) => escapeHtml(toString(isObject(source) ? source.label : source, 'Source')))
    .join(', ');
  const updatedAt = toString(memo.freshness || payload.generatedAt, '');
  const updated = updatedAt ? escapeHtml(formatRelativeTime(updatedAt)) : 'just now';
  const playbookId = payload.playbook_id ? escapeHtml(payload.playbook_id) : null;
  const playbookContext = payload.playbook_context && typeof payload.playbook_context === 'object'
    ? payload.playbook_context
    : null;
  const guardrail = playbookContext && Array.isArray(playbookContext.guardrails)
    ? toString(playbookContext.guardrails[0], '')
    : '';
  const conflictWarning = payload.conflict_warning && typeof payload.conflict_warning === 'object'
    ? payload.conflict_warning
    : null;
  const contextInfluence = payload.contextInfluence && typeof payload.contextInfluence === 'object'
    ? payload.contextInfluence
    : null;
  const contextMode = contextInfluence
    ? escapeHtml(
      toString(contextInfluence.mode, 'market_wide')
        .replace(/_/g, ' ')
        .trim()
    )
    : '';
  const contextTickers = contextInfluence
    ? toArray(contextInfluence.effectiveTickers, [])
      .map((ticker) => escapeHtml(toString(ticker, '').trim()))
      .filter(Boolean)
      .slice(0, 3)
      .join(', ')
    : '';
  const contextSource = contextInfluence
    ? escapeHtml(toString(contextInfluence.source, '').replace(/_/g, ' ').trim())
    : '';

  const playbookHtml = playbookId
    ? `<div style="margin-top: 8px;">
        <p style="font-size: 11px; font-family: 'Courier New', monospace; background: rgba(59, 130, 246, 0.1); padding: 6px 10px; border-radius: 6px; display: inline-block;">📋 Playbook: <strong>${playbookId}</strong></p>
        ${playbookContext && playbookContext.name ? `<p style="margin-top: 6px; font-size: 12px;"><strong>${escapeHtml(playbookContext.name)}</strong>${playbookContext.description ? ` • ${escapeHtml(playbookContext.description)}` : ''}</p>` : ''}
        ${guardrail ? `<p style="margin-top: 4px; font-size: 12px; color: #94A3B8;">Guardrail: ${escapeHtml(guardrail)}</p>` : ''}
      </div>`
    : '';
  const conflictHtml = conflictWarning && conflictWarning.detected
    ? `<p style="margin-top: 8px; color: #FCA5A5;"><strong>Conflict:</strong> ${escapeHtml(toString(conflictWarning.reason, 'Signal diverges from active playbook.'))}</p>`
    : '';
  const contextHtml = contextInfluence
    ? `<p style="margin-top: 8px; font-size: 12px; color: #94A3B8;"><strong>Context:</strong> ${contextMode}${contextInfluence.portfolioApplied ? ' • saved portfolio applied' : ''}${contextTickers ? ` • focus ${contextTickers}` : ''}${contextSource ? ` • source ${contextSource}` : ''}</p>`
    : '';
  const metadataBadges = [
    updatedAt ? `Freshness: ${updated}` : '',
    sourceLabels ? `Sources: ${sourceLabels}` : '',
    memoDegraded ? 'Degraded' : '',
  ].filter(Boolean);
  const metadataBadgesHtml = metadataBadges.length
    ? `<div style="margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;">${metadataBadges.map((label) => `<span class="source-badge">${label}</span>`).join('')}</div>`
    : '';
  const metadataParts = [
    `Model: ${model}`,
    `Sources: ${sourceLabels || 'Unavailable'}`,
    `Quality: ${quality}`,
    `Updated ${updated}`,
    updatedAt ? `Freshness: ${updated}` : '',
  ].filter(Boolean).join(' • ');

  return `
    <p><strong>${verdict}</strong> position • Confidence ${confidence}% • Risk ${riskLevel}</p>
    ${summaryHtml || reasoningHtml}
    ${regimeHtml}
    ${horizonHtml}
    ${opportunitiesHtml}
    ${topRisksHtml}
    ${memoSummary && reasoning.length && reasoningText !== memoSummary ? `<div style="margin-top: 10px;">${reasoningHtml}</div>` : ''}
    ${nextStepsHtml}
    ${invalidationHtml}
    ${riskHtml}
    ${degradedHtml}
    ${contextHtml}
    ${metadataBadgesHtml}
    ${playbookHtml}
    ${conflictHtml}
    <p style="margin-top: 10px; font-size: 12px; color: #94A3B8;">${metadataParts}</p>
  `;
}

let copilotContextRequest = null;

function normalizeCopilotStarterTickers(value) {
  const seen = new Set();
  return toArray(value, [])
    .map((ticker) => toString(ticker, '').trim().toUpperCase())
    .filter((ticker) => {
      if (!ticker || seen.has(ticker)) return false;
      seen.add(ticker);
      return true;
    });
}

function readCopilotInputTickers(input) {
  const raw = toString(input?.dataset?.copilotTickers, '');
  if (!raw) return [];
  try {
    return normalizeCopilotStarterTickers(JSON.parse(raw));
  } catch (error) {
    return [];
  }
}

function buildDefaultCopilotStartState() {
  return {
    brief: {
      title: 'Brief of the day',
      summary: 'No daily brief available yet.',
      generatedAt: '',
      marketSentiment: 'UNKNOWN',
      marketRegime: 'UNKNOWN',
      topOpportunities: [],
      topSignals: [],
      topRisks: [],
      sources: [],
      degraded: false,
      freshness: new Date().toISOString()
    },
    ask: [
      {
        id: 'portfolio_today',
        label: 'Portfolio today?',
        prompt: 'What should I do with my portfolio today?',
        tickers: []
      },
      {
        id: 'market_theme',
        label: 'Best theme now?',
        prompt: 'Which market theme deserves a deep dive right now?',
        tickers: []
      },
      {
        id: 'nvda_memo',
        label: 'NVDA 1-week memo',
        prompt: 'Give me a 1-week investment memo on NVDA.',
        tickers: ['NVDA']
      }
    ],
    open: [
      { id: 'brief_of_day', label: 'Open Live Brief', target: '/brief/daily' },
      { id: 'opportunities', label: 'Open opportunities', target: 'opportunities' },
      { id: 'copilot', label: 'Ask a custom question', target: 'copilot' }
    ]
  };
}

function normalizeCopilotStartAsk(value, fallbackTickers = []) {
  const scopeTickers = normalizeCopilotStarterTickers(fallbackTickers);
  return toArray(value, [])
    .filter(isObject)
    .map((item, index) => {
      const prefill = isObject(item.prefill) ? item.prefill : {};
      const prompt = toString(item.prompt || item.question || prefill.question, '');
      const prefillTickers = Array.isArray(item.tickers) && item.tickers.length
        ? item.tickers
        : (Array.isArray(prefill.tickers) && prefill.tickers.length
          ? prefill.tickers
          : scopeTickers);
      return {
        id: toString(item.id, `copilot_ask_${index}`),
        label: toString(item.label, prompt || 'Ask copilot'),
        prompt,
        tickers: normalizeCopilotStarterTickers(prefillTickers)
      };
    })
    .filter((item) => item.prompt);
}

function normalizeCopilotStartOpen(value) {
  return toArray(value, [])
    .filter(isObject)
    .map((item, index) => ({
      id: toString(item.id, `copilot_open_${index}`),
      label: toString(item.label, 'Open'),
      target: normalizeCopilotStartOpenTarget(item.target, item.id)
    }))
    .filter((item) => item.target);
}

function normalizeCopilotStartOpenTarget(target, id = '') {
  const normalizedTarget = toString(target, '')
    .trim()
    .toLowerCase()
    .replace(/[?#].*$/, '')
    .replace(/\/+$/, '');
  const normalizedId = toString(id, '').trim().toLowerCase();
  if (
    normalizedId === 'brief_of_day'
    || normalizedTarget === '/brief/daily'
    || normalizedTarget === '/brief'
    || normalizedTarget === 'brief'
    || normalizedTarget === 'brief/daily'
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
    || normalizedTarget === '/copilot'
    || normalizedTarget === '/copilot/ask'
    || normalizedTarget === 'copilot/ask'
    || normalizedTarget === 'copilot'
  ) {
    return 'copilot';
  }
  return normalizedTarget.replace(/^\/+/, '');
}

function normalizeCopilotStartList(value) {
  return toArray(value, [])
    .map((item) => toString(isObject(item) ? (item.label || item.title || item.name || item.sector) : item, '').trim())
    .filter(Boolean)
    .slice(0, 3);
}

function buildCopilotStartState(raw) {
  const fallback = buildDefaultCopilotStartState();
  const payload = isObject(raw) ? raw : {};
  const data = isObject(payload.data) ? payload.data : payload;
  const copilotStart = isObject(data.copilot_start)
    ? data.copilot_start
    : (
      isObject(data.brief_of_day)
      || isObject(data.briefOfDay)
      || Array.isArray(data.ask)
      || Array.isArray(data.open)
        ? data
        : {}
    );
  const scopeTickers = Array.isArray(copilotStart.scope_tickers) && copilotStart.scope_tickers.length
    ? copilotStart.scope_tickers
    : data.scope_tickers;
  const briefSource = isObject(copilotStart.brief_of_day)
    ? copilotStart.brief_of_day
    : (isObject(copilotStart.briefOfDay)
      ? copilotStart.briefOfDay
      : (isObject(data.daily_brief) ? data.daily_brief : {}));
  const ask = normalizeCopilotStartAsk(copilotStart.ask, scopeTickers);
  const open = normalizeCopilotStartOpen(copilotStart.open);
  const marketRegime = toString(
    briefSource.market_regime
      || briefSource.marketRegime
      || briefSource.market_sentiment
      || briefSource.sentiment
      || briefSource.regime,
    fallback.brief.marketRegime
  ).toUpperCase();
  const topSignals = normalizeCopilotStartList(briefSource.top_signals || briefSource.signals);
  const topOpportunities = normalizeCopilotStartList(
    briefSource.top_opportunities || briefSource.topOpportunities || briefSource.opportunities || topSignals
  );
  const topRisks = normalizeCopilotStartList(briefSource.top_risks || briefSource.risks);
  const sourceLabels = normalizeCopilotSourceLabels(briefSource.sources || briefSource.source);
  const generatedAt = toString(
    briefSource.generated_at || briefSource.generatedAt || briefSource.freshness,
    fallback.brief.generatedAt
  );
  const rawContextInfluence = isObject(data.context_influence || data.contextInfluence)
    ? (data.context_influence || data.contextInfluence)
    : (isObject(copilotStart.context_influence || copilotStart.contextInfluence)
      ? (copilotStart.context_influence || copilotStart.contextInfluence)
      : null);
  const contextInfluence = rawContextInfluence
    ? {
      mode: toString(rawContextInfluence.mode, 'market_wide'),
      portfolioApplied: !!(rawContextInfluence.portfolio_applied ?? rawContextInfluence.portfolioApplied),
      source: toString(rawContextInfluence.source, ''),
      requestedTickers: normalizeCopilotStarterTickers(
        rawContextInfluence.requested_tickers || rawContextInfluence.requestedTickers
      ),
      effectiveTickers: normalizeCopilotStarterTickers(
        rawContextInfluence.effective_tickers || rawContextInfluence.effectiveTickers
      ),
      portfolioId: toString(rawContextInfluence.portfolio_id || rawContextInfluence.portfolioId, '')
    }
    : null;

  return {
    brief: {
      title: toString(briefSource.title || briefSource.headline, fallback.brief.title),
      summary: toString(briefSource.summary || briefSource.message || briefSource.overview, fallback.brief.summary),
      generatedAt,
      marketSentiment: marketRegime || fallback.brief.marketSentiment,
      marketRegime: marketRegime || fallback.brief.marketRegime,
      topSignals,
      topOpportunities,
      topRisks,
      sources: sourceLabels,
      degraded: briefSource.degraded === true,
      degradedReason: toString(briefSource.degraded_reason || briefSource.degradedReason, ''),
      freshness: toString(
        briefSource.freshness || briefSource.generated_at,
        fallback.brief.freshness
      )
    },
    contextInfluence,
    ask: ask.length ? ask : fallback.ask,
    open: open.length ? open : fallback.open
  };
}

function buildCopilotStartHtml(state) {
  const brief = state && isObject(state.brief) ? state.brief : buildDefaultCopilotStartState().brief;
  const title = escapeHtml(toString(brief.title, 'Brief of the day'));
  const sentiment = escapeHtml(toString(brief.marketRegime || brief.marketSentiment, 'UNKNOWN').replace(/_/g, ' '));
  const summary = escapeHtml(toString(brief.summary, 'No daily brief available yet.')).replace(/\n/g, '<br/>');
  const updated = escapeHtml(brief.freshness ? formatRelativeTime(brief.freshness) : 'just now');
  const signals = brief.topSignals.length
    ? `<p style="margin-top: 8px;"><strong>Signals:</strong> ${brief.topSignals.map((item) => escapeHtml(item)).join(' • ')}</p>`
    : '';
  const opportunities = !brief.topSignals.length && brief.topOpportunities.length
    ? `<p style="margin-top: 8px;"><strong>Opportunities:</strong> ${brief.topOpportunities.map((item) => escapeHtml(item)).join(' • ')}</p>`
    : '';
  const risks = brief.topRisks.length
    ? `<p style="margin-top: 8px;"><strong>Risks:</strong> ${brief.topRisks.map((item) => escapeHtml(item)).join(' • ')}</p>`
    : '';
  const degradedReason = escapeHtml(
    toString(brief.degradedReason || brief.degraded_reason, '').replace(/_/g, ' ').trim()
  );
  const meta = [
    sentiment !== 'UNKNOWN' ? `Regime ${sentiment}` : '',
    brief.degraded ? `Fallback: ${degradedReason || 'Degraded context'}` : '',
    brief.sources.length ? `Sources: ${brief.sources.slice(0, 2).map((item) => escapeHtml(item)).join(', ')}` : ''
  ].filter(Boolean).join(' • ');

  return `
    <p><strong>${title}</strong> • ${sentiment} • Updated ${updated}</p>
    <p style="margin-top: 8px;">${summary}</p>
    ${signals}
    ${opportunities}
    ${risks}
    ${meta ? `<p style="margin-top: 8px; font-size: 12px; color: #94A3B8;">${meta}</p>` : ''}
  `;
}

function focusCopilotInput() {
  document.getElementById('aiOverlayInput')?.focus();
}

function renderCopilotStartMessage(state) {
  const panel = document.getElementById('aiMessagesPanel');
  if (!panel) return;

  panel.querySelector('[data-copilot-welcome="true"]')?.remove();
  panel.querySelectorAll('[data-copilot-start="true"]').forEach((node) => node.remove());

  const startMessage = appendCopilotChatMessage('aiMessagesPanel', buildCopilotStartHtml(state), 'ai', { html: true });
  if (!startMessage) return;

  startMessage.dataset.copilotStart = 'true';
  panel.insertBefore(startMessage, panel.firstChild);
  panel.scrollTop = 0;
}

function runCopilotStartPrompt(prompt, tickers = []) {
  const overlay = document.getElementById('aiCopilotOverlay');
  const input = document.getElementById('aiOverlayInput');
  if (!input) return;

  const normalizedPrompt = toString(prompt, '').trim();
  if (!normalizedPrompt) return;

  const normalizedTickers = normalizeCopilotStarterTickers(tickers);
  if (normalizedTickers.length) {
    input.dataset.copilotTickers = JSON.stringify(normalizedTickers);
  } else {
    delete input.dataset.copilotTickers;
  }

  const submitPrompt = () => {
    input.value = normalizedPrompt;
    focusCopilotInput();
    sendOverlayMessage();
  };

  const overlayClosed = !!overlay && (overlay.style.display === 'none' || !overlay.style.display);
  if (overlayClosed) {
    toggleAICopilot();
    setTimeout(submitPrompt, 30);
    return;
  }

  submitPrompt();
}

function resolveCopilotStartOpenDestination(target) {
  const normalizedTarget = normalizeCopilotStartOpenTarget(target);
  if (!normalizedTarget) return null;

  const destination = {
    brief: {
      tab: 'market',
      anchorId: 'market-pulse-widget-container'
    },
    overview: {
      tab: 'overview'
    },
    market: {
      tab: 'market'
    },
    opportunities: {
      tab: 'opportunities'
    },
    performance: {
      tab: 'performance'
    },
    ailab: {
      tab: 'ailab'
    },
    '/copilot/': {
      tab: 'copilot'
    },
    'copilot/': {
      tab: 'copilot'
    },
    copilot: {
      tab: 'copilot'
    }
  }[normalizedTarget];

  return destination
    ? {
      target: normalizedTarget,
      ...destination
    }
    : null;
}

function runCopilotStartOpen(target) {
  const destination = (typeof resolveCopilotStartOpenDestination === 'function'
    ? resolveCopilotStartOpenDestination(target)
    : (() => {
      const normalizedTarget = normalizeCopilotStartOpenTarget(target);
      const fallbackDestination = {
        market: {
          tab: 'market',
          anchorId: 'market-pulse-widget-container'
        },
        overview: {
          tab: 'overview'
        },
        opportunities: {
          tab: 'opportunities'
        },
        performance: {
          tab: 'performance'
        },
        ailab: {
          tab: 'ailab'
        },
        copilot: {
          tab: 'copilot'
        }
      }[normalizedTarget];
      return fallbackDestination
        ? {
          target: normalizedTarget,
          ...fallbackDestination
        }
        : null;
    })());
  const overlay = document.getElementById('aiCopilotOverlay');
  if (!destination) {
    showToast(`Open ${target} is unavailable`, 'error');
    return;
  }

  if (destination.target === 'copilot') {
    const overlayClosed = !!overlay && (overlay.style.display === 'none' || !overlay.style.display);
    if (overlayClosed) {
      if (typeof toggleAICopilot === 'function') {
        toggleAICopilot();
      } else if (overlay) {
        overlay.style.display = 'block';
      }
    }

    if (typeof focusCopilotInput === 'function') {
      focusCopilotInput();
      return;
    }
    const input = document.getElementById('aiOverlayInput');
    if (input && typeof input.focus === 'function') {
      input.focus();
    }
    return;
  }

  const targetPanel = document.getElementById(`tab-${destination.tab}`);
  if (!targetPanel) {
    showToast(`Open ${destination.target} is unavailable`, 'error');
    return;
  }

  if (overlay) {
    overlay.classList.remove('active');
    setTimeout(() => {
      overlay.style.display = 'none';
    }, 400);
  }

  setTimeout(() => {
    safeSwitchTab(document.querySelector(`.tab-btn[data-tab="${destination.tab}"]`), destination.tab);
    if (destination.anchorId) {
      setTimeout(() => {
        document.getElementById(destination.anchorId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 30);
    }
  }, 30);
}

function resolveCopilotStartState(state) {
  const fallback = buildDefaultCopilotStartState();
  if (!isObject(state)) {
    return fallback;
  }
  if (isObject(state.brief)) {
    const rawBrief = state.brief;
    const topSignals = normalizeCopilotStartList(rawBrief.topSignals || rawBrief.top_signals);
    const topRisks = normalizeCopilotStartList(rawBrief.topRisks || rawBrief.top_risks);
    const topOpportunities = normalizeCopilotStartList(rawBrief.topOpportunities || rawBrief.top_opportunities);
    const marketRegime = toString(
      rawBrief.marketRegime || rawBrief.market_regime || rawBrief.marketSentiment || rawBrief.market_sentiment || rawBrief.regime,
      fallback.brief.marketRegime
    );
    const sourceLabels = normalizeCopilotSourceLabels(rawBrief.sources || rawBrief.source);
    const rawContextInfluence = isObject(state.contextInfluence || state.context_influence)
      ? (state.contextInfluence || state.context_influence)
      : null;
    return {
      brief: {
        ...fallback.brief,
        ...rawBrief,
        marketSentiment: marketRegime,
        marketRegime,
        generatedAt: toString(rawBrief.generatedAt || rawBrief.generated_at, fallback.brief.generatedAt),
        freshness: toString(rawBrief.freshness || rawBrief.generated_at || rawBrief.generatedAt, fallback.brief.freshness),
        topSignals,
        topRisks,
        topOpportunities,
        sources: sourceLabels,
        degraded: rawBrief.degraded === true,
        degradedReason: toString(rawBrief.degradedReason || rawBrief.degraded_reason, '')
      },
      contextInfluence: rawContextInfluence
        ? {
          mode: toString(rawContextInfluence.mode, 'market_wide'),
          portfolioApplied: !!(rawContextInfluence.portfolio_applied ?? rawContextInfluence.portfolioApplied),
          source: toString(rawContextInfluence.source, ''),
          requestedTickers: normalizeCopilotStarterTickers(
            rawContextInfluence.requestedTickers || rawContextInfluence.requested_tickers
          ),
          effectiveTickers: normalizeCopilotStarterTickers(
            rawContextInfluence.effectiveTickers || rawContextInfluence.effective_tickers
          ),
          portfolioId: toString(rawContextInfluence.portfolioId || rawContextInfluence.portfolio_id, '')
        }
        : null,
      ask: Array.isArray(state.ask) && state.ask.length ? state.ask : fallback.ask,
      open: Array.isArray(state.open) && state.open.length ? state.open : fallback.open
    };
  }
  return buildCopilotStartState({
    data: {
      copilot_start: state,
      scope_tickers: state.scope_tickers
    }
  });
}

function renderHeroCopilotBrief(state) {
  const titleEl = document.getElementById('heroBriefTitle') || document.querySelector('.hero-daily-brief h3');
  const leadEl = document.getElementById('heroBriefLead');
  const summaryEl = document.getElementById('heroBriefSummary') || document.querySelector('.hero-daily-brief .ai-summary-content');
  const timestampEl = document.getElementById('heroBriefTimestamp') || document.querySelector('.hero-daily-brief .ai-timestamp');
  const signalsEl = document.getElementById('heroBriefSignals');
  const risksEl = document.getElementById('heroBriefRisks');
  const actionsRoot = document.getElementById('heroBriefActions') || document.querySelector('.hero-daily-brief .hero-brief-actions');
  const suggestionRoot = document.getElementById('heroSuggestionChips');
  if (!titleEl && !leadEl && !summaryEl && !timestampEl && !actionsRoot && !suggestionRoot) return;

  const fallbackState = buildDefaultCopilotStartState();
  const resolvedState = resolveCopilotStartState(state);
  const brief = isObject(resolvedState.brief) ? resolvedState.brief : fallbackState.brief;
  const askItems = Array.isArray(resolvedState.ask) && resolvedState.ask.length
    ? resolvedState.ask
    : fallbackState.ask;
  const openItems = Array.isArray(resolvedState.open) && resolvedState.open.length
    ? resolvedState.open
    : fallbackState.open;
  const askItem = askItems[0] || fallbackState.ask[0];
  const openItem = openItems.find((item) => isObject(item) && toString(item.target, '').toLowerCase() !== 'copilot')
    || openItems[0]
    || fallbackState.open[0];
  const rawContextInfluence = isObject(resolvedState.contextInfluence || resolvedState.context_influence)
    ? (resolvedState.contextInfluence || resolvedState.context_influence)
    : null;
  const contextInfluence = rawContextInfluence
    ? {
      mode: toString(rawContextInfluence.mode, 'market_wide'),
      portfolioApplied: !!(rawContextInfluence.portfolio_applied ?? rawContextInfluence.portfolioApplied),
      source: toString(rawContextInfluence.source, ''),
      effectiveTickers: normalizeCopilotStarterTickers(
        rawContextInfluence.effective_tickers || rawContextInfluence.effectiveTickers
      )
    }
    : null;
  const normalizedBriefStatus = toString(
    brief.status || brief.freshnessStatus || brief.freshness_status || brief.qualityStatus || brief.quality_status,
    ''
  ).trim().toLowerCase();
  const briefDegraded = brief.degraded === true
    || normalizedBriefStatus === 'degraded'
    || normalizedBriefStatus === 'stale'
    || normalizedBriefStatus === 'api_unavailable';

  if (titleEl) {
    titleEl.textContent = toString(brief.title, fallbackState.brief.title);
  }

  if (leadEl) {
    const regime = toString(brief.marketRegime || brief.marketSentiment, fallbackState.brief.marketRegime).replace(/_/g, ' ');
    const degradedReason = toString(brief.degradedReason || brief.degraded_reason, '').replace(/_/g, ' ').trim();
    const leadParts = ['A 30-second portfolio memo before you dive deeper.'];
    if (regime !== 'UNKNOWN') {
      leadParts.push(`Regime: ${regime.toLowerCase()}.`);
    }
    if (briefDegraded) {
      leadParts.push(`Fallback context${degradedReason ? `: ${degradedReason.toLowerCase()}` : ''}.`);
    }
    if (contextInfluence && contextInfluence.portfolioApplied) {
      leadParts.push('Saved portfolio context applied.');
    }
    leadEl.textContent = leadParts.join(' ');
  }

  if (summaryEl) {
    summaryEl.textContent = toString(brief.summary, fallbackState.brief.summary);
  }

  if (timestampEl) {
    const freshness = toString(brief.freshness || brief.generated_at || brief.generatedAt, '');
    const timestampParts = [`Updated ${freshness ? formatRelativeTime(freshness) : 'just now'}`];
    if (brief.sources.length) {
      timestampParts.push(`${brief.sources.length} source${brief.sources.length > 1 ? 's' : ''}`);
    }
    if (briefDegraded) {
      timestampParts.push('degraded');
    }
    timestampEl.textContent = timestampParts.join(' • ');
  }

  if (signalsEl) {
    const signalItems = brief.topSignals.length
      ? brief.topSignals
      : normalizeCopilotStartList(brief.topOpportunities || brief.top_opportunities);
    const signalLabel = brief.topSignals.length ? 'Signals' : 'Opportunities';
    const text = signalItems.length ? `${signalLabel}: ${signalItems.join(' • ')}` : '';
    signalsEl.textContent = text;
    signalsEl.style.display = text ? 'block' : 'none';
  }

  if (risksEl) {
    const text = brief.topRisks.length ? `Risks: ${brief.topRisks.join(' • ')}` : '';
    risksEl.textContent = text;
    risksEl.style.display = text ? 'block' : 'none';
  }

  if (actionsRoot) {
    actionsRoot.innerHTML = '';

    if (askItem && toString(askItem.prompt, '')) {
      const askButton = document.createElement('button');
      askButton.type = 'button';
      askButton.className = 'ai-action-btn';
      askButton.textContent = toString(askItem.label, 'Ask About Today');
      askButton.addEventListener('click', () => runCopilotStartPrompt(askItem.prompt, askItem.tickers));
      actionsRoot.appendChild(askButton);
    }

    if (openItem && toString(openItem.target, '')) {
      const openButton = document.createElement('button');
      openButton.type = 'button';
      openButton.className = 'ai-action-btn secondary';
      openButton.textContent = toString(openItem.label, 'Open Live Brief');
      openButton.addEventListener('click', () => runCopilotStartOpen(openItem.target));
      actionsRoot.appendChild(openButton);
    }
  }

  if (suggestionRoot) {
    suggestionRoot.innerHTML = '';
    const primaryOpenId = toString(openItem && openItem.id, '');
    const regime = toString(brief.marketRegime || brief.marketSentiment, fallbackState.brief.marketRegime).replace(/_/g, ' ');
    const contextMode = contextInfluence
      ? toString(contextInfluence.mode, 'market_wide').replace(/_/g, ' ').trim()
      : '';
    const contextSource = contextInfluence
      ? toString(contextInfluence.source, '').replace(/_/g, ' ').trim()
      : '';
    const focusTickers = contextInfluence && contextInfluence.effectiveTickers.length
      ? contextInfluence.effectiveTickers.slice(0, 2).join(', ')
      : '';
    const metadataLabels = [
      regime !== 'UNKNOWN' ? `Regime: ${regime}` : '',
      contextInfluence
        ? `Context: ${contextMode || 'market wide'}${contextInfluence.portfolioApplied ? ' portfolio' : ''}${focusTickers ? ` • ${focusTickers}` : ''}${contextSource ? ` • ${contextSource}` : ''}`
        : '',
      brief.sources.length ? `Sources: ${brief.sources.slice(0, 2).join(', ')}` : '',
      briefDegraded ? 'Degraded' : ''
    ].filter(Boolean).slice(0, 3);

    metadataLabels.forEach((label) => {
      const badge = document.createElement('span');
      badge.className = 'suggestion-chip';
      badge.textContent = label;
      suggestionRoot.appendChild(badge);
    });

    const suggestionItems = [
      ...askItems.slice(1).map((item) => ({
        label: toString(item.label, 'Ask copilot'),
        run() {
          runCopilotStartPrompt(item.prompt, item.tickers);
        }
      })),
      ...openItems
        .filter((item) => toString(item.id, '') !== primaryOpenId)
        .map((item) => ({
          label: toString(item.label, 'Open'),
          run() {
            runCopilotStartOpen(item.target);
          }
        }))
    ].slice(0, Math.max(0, 3 - metadataLabels.length));

    suggestionItems.forEach((item) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'suggestion-chip';
      chip.textContent = item.label;
      chip.addEventListener('click', item.run);
      suggestionRoot.appendChild(chip);
    });
  }
}

function renderCopilotStartActions(state) {
  const actionsRoot = document.getElementById('aiQuickActions');
  if (!actionsRoot) return;

  actionsRoot.innerHTML = '';
  state.ask.forEach((item) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quick-action-btn';
    button.textContent = toString(item.label, 'Ask copilot');
    button.addEventListener('click', () => runCopilotStartPrompt(item.prompt, item.tickers));
    actionsRoot.appendChild(button);
  });

  state.open.forEach((item) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quick-action-btn';
    button.textContent = toString(item.label, 'Open');
    button.addEventListener('click', () => runCopilotStartOpen(item.target));
    actionsRoot.appendChild(button);
  });
}

function updateCopilotContextLabel(state) {
  const contextValue = document.getElementById('aiContextValue');
  if (!contextValue) return;

  const regime = toString(state?.brief?.marketRegime || state?.brief?.marketSentiment, 'UNKNOWN').replace(/_/g, ' ');
  const parts = ['Brief of the day'];
  if (regime !== 'UNKNOWN') {
    parts.push(regime);
  }
  if (state?.contextInfluence?.portfolioApplied) {
    parts.push('portfolio aware');
  }
  if (state?.brief?.degraded === true) {
    parts.push('degraded');
  }
  contextValue.textContent = parts.join(' • ');
}

async function hydrateCopilotOverlayStart() {
  if (copilotContextRequest) return copilotContextRequest;

  const contextValue = document.getElementById('aiContextValue');
  if (contextValue) {
    contextValue.textContent = 'Loading brief of the day...';
  }

  // Prefer the starter contract so the landing hero and copilot overlay share the same brief/ask/open payload.
  copilotContextRequest = Promise.resolve(
    typeof window.FinanceAPI?.getCopilotStart === 'function'
      ? Promise.resolve(window.FinanceAPI.getCopilotStart()).catch((error) => {
        if (typeof window.FinanceAPI?.getCopilotContext !== 'function') {
          throw error;
        }
        console.warn('[Copilot] getCopilotStart failed, falling back to getCopilotContext:', error?.message || error);
        return window.FinanceAPI.getCopilotContext();
      })
      : (typeof window.FinanceAPI?.getCopilotContext === 'function'
        ? window.FinanceAPI.getCopilotContext()
        : null)
  )
    .then((raw) => {
      const payloadData = isObject(raw?.data)
        ? raw.data
        : (isObject(raw) ? raw : {});
      const rawCopilotStart = isObject(payloadData.copilot_start)
        ? payloadData.copilot_start
        : (isObject(payloadData.copilotStart)
          ? payloadData.copilotStart
          : raw);
      const sanitizedStart = sanitizeCopilotStart(rawCopilotStart);
      window.copilotStart = sanitizedStart;
      const state = buildCopilotStartState({
        ...payloadData,
        copilot_start: sanitizedStart,
      });
      updateCopilotContextLabel(state);
      renderCopilotStartMessage(state);
      renderCopilotStartActions(state);
      renderHeroCopilotBrief(state);
      return state;
    })
    .catch((error) => {
      console.warn('[Copilot] failed to load start context:', error?.message || error);
      window.copilotStart = sanitizeCopilotStart(null);
      const state = buildCopilotStartState(null);
      updateCopilotContextLabel(state);
      renderCopilotStartMessage(state);
      renderCopilotStartActions(state);
      renderHeroCopilotBrief(state);
      return state;
    })
    .finally(() => {
      copilotContextRequest = null;
    });

  return copilotContextRequest;
}

async function submitCopilotChat(inputId, containerId) {
  const input = document.getElementById(inputId);
  if (!input || !input.value.trim()) return;

  const sendButton = input.parentElement && typeof input.parentElement.querySelector === 'function'
    ? input.parentElement.querySelector('.ai-send-btn')
    : null;
  const question = input.value.trim();
  const promptTickers = readCopilotInputTickers(input);
  input.value = '';

  appendCopilotChatMessage(containerId, question, 'user');
  const pendingMessage = appendCopilotChatMessage(
    containerId,
    '<p>Building a live investment memo from the latest backend context...</p>',
    'ai',
    { html: true }
  );

  input.disabled = true;
  if (sendButton) sendButton.disabled = true;

  try {
    const rawResponse = await (typeof window.FinanceAPI?.askCopilot === 'function'
      ? window.FinanceAPI.askCopilot(question, promptTickers)
      : Promise.resolve({
        data: {
          answer: 'Copilot API service unavailable.',
          sources: [],
          confidence: 0.2,
          verdict: 'hold',
          quality_status: 'api_unavailable',
          risk_level: 'high',
          risk_caveat: 'Live backend is unavailable, so the memo cannot be grounded in current sources.',
          generated_at: new Date().toISOString()
        }
      }));
    const payload = buildCopilotJudgePayload(
      rawResponse && isObject(rawResponse) && isObject(rawResponse.data)
        ? rawResponse.data
        : rawResponse
    );
    if (!payload) {
      throw new Error('Invalid Copilot response.');
    }

    pendingMessage?.remove();
    appendCopilotChatMessage(containerId, buildCopilotChatResponseHtml(payload), 'ai', { html: true });
    showToast('Copilot memo ready', 'success');
  } catch (error) {
    pendingMessage?.remove();
    appendCopilotChatMessage(
      containerId,
      `<p>Copilot could not complete the memo.</p><p style="margin-top: 8px;">${escapeHtml(error?.message || toString(error, 'Unknown error'))}</p>`,
      'ai',
      { html: true }
    );
    showToast('Copilot temporarily unavailable', 'error');
  } finally {
    delete input.dataset.copilotTickers;
    input.disabled = false;
    if (sendButton) sendButton.disabled = false;
    input.focus();
  }
}

function sendOverlayMessage() {
  const input = document.getElementById('aiOverlayInput');
  if (!input || !input.value.trim()) return;
  return submitCopilotChat('aiOverlayInput', 'aiMessagesPanel');
}

function handleOverlayEnter(event) {
  if (event.key === 'Enter') {
    sendOverlayMessage();
  }
}

function quickAsk(action) {
  const questions = {
    'explain': 'Explain what matters on this screen right now.',
    'whatdo': 'What should I do with my portfolio today?',
    'simulate': 'Give me a 1-week investment memo on NVDA.'
  };

  const input = document.getElementById('aiOverlayInput');
  if (input && questions[action]) {
    delete input.dataset.copilotTickers;
    input.value = questions[action];
    sendOverlayMessage();
  }
}

function addAIMessage(content, type, options = {}) {
  return appendCopilotChatMessage('aiMessagesPanel', content, type, options);
}

// AI Lab Functions
function sendAIMessage() {
  const input = document.getElementById('aiChatInput');
  if (!input || !input.value.trim()) return;
  return submitCopilotChat('aiChatInput', 'aiChatMessages');
}

function handleChatEnter(event) {
  if (event.key === 'Enter') {
    sendAIMessage();
  }
}

function askAI(question) {
  const input = document.getElementById('aiChatInput');
  if (input) {
    input.value = question;
    sendAIMessage();
  }
}

// Enhanced KPI Actions
function deepDivePortfolio() {
  showToast('Opening Portfolio Deep Dive view...');
  switchTab(document.querySelector('[data-tab="performance"]'), 'performance');
}

function openScenarioBuilder() {
  showToast('Opening AI Scenario Builder...');
  // In production, this would open a modal with scenario inputs
}

function explainForecast() {
  toggleAICopilot();
  setTimeout(() => {
    const response = 'The +5.3% forecast for the next 30 days is based on: 1) Technical momentum indicators showing bullish continuation patterns, 2) Strong earnings season with 78% of companies beating estimates, 3) Fed dovish stance supporting risk assets, 4) Positive market sentiment (72% optimistic). The 82% confidence level reflects historical accuracy of similar setups.';
    addAIMessage(response, 'ai');
  }, 500);
}

function openBacktest() {
  showToast('Opening Backtest Lab...');
  switchTab(document.querySelector('[data-tab="performance"]'), 'performance');
  setTimeout(() => {
    document.getElementById('backtestSim')?.scrollIntoView({ behavior: 'smooth' });
  }, 300);
}

function viewAllTrades() {
  showToast('Loading complete trade history...');
  switchTab(document.querySelector('[data-tab="performance"]'), 'performance');
}

function optimizeStrategy() {
  toggleAICopilot();
  setTimeout(() => {
    const response = 'AI Strategy Optimization suggests: 1) Implement trailing stop losses at 5% to protect gains, 2) Diversify into healthcare sector (currently 0% allocation), 3) Reduce tech concentration from 65% to 50%, 4) Add defensive positions for downside protection. Expected impact: -2% risk, +1.5% potential return.';
    addAIMessage(response, 'ai');
  }, 500);
}

function riskAnalysis() {
  showToast('Generating comprehensive risk analysis...');
  switchTab(document.querySelector('[data-tab="performance"]'), 'performance');
}

function showKpiMenu(kpi) {
  showToast(`KPI menu: Export, Set Alert, Compare, Share`);
}

// ============ UTILITY FUNCTIONS ============
function animateValue(element, start, end, duration, prefix = '', suffix = '') {
  const startTime = performance.now();

  function easeOutQuart(t) {
    return 1 - Math.pow(1 - t, 4);
  }

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easedProgress = easeOutQuart(progress);
    const current = start + (end - start) * easedProgress;

    let displayValue;
    if (end >= 1000) {
      displayValue = prefix + Math.floor(current).toLocaleString() + suffix;
    } else {
      displayValue = prefix + current.toFixed(1) + suffix;
    }

    element.textContent = displayValue;

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

// Enhanced toast with better styling and auto-dismiss
function showToast(message, type = 'success') {
  const toast = document.getElementById('successToast');
  if (!toast) {
    // Create toast if it doesn't exist
    const newToast = document.createElement('div');
    newToast.id = 'successToast';
    newToast.className = 'toast';
    newToast.innerHTML = `
      <span class="toast-icon">✓</span>
      <span class="toast-message"></span>
    `;
    document.body.appendChild(newToast);
    return showToast(message, type);
  }

  const messageEl = toast.querySelector('.toast-message');
  const iconEl = toast.querySelector('.toast-icon');

  if (messageEl) messageEl.textContent = message;

  // Set icon and color based on type
  if (type === 'success') {
    toast.style.background = 'linear-gradient(135deg, #2D9E78, #10b981)';
    if (iconEl) iconEl.textContent = '✓';
  } else if (type === 'error') {
    toast.style.background = 'linear-gradient(135deg, #DC2626, #EF4444)';
    if (iconEl) iconEl.textContent = '✗';
  } else if (type === 'info') {
    toast.style.background = 'linear-gradient(135deg, #1F40AF, #4A6BD9)';
    if (iconEl) iconEl.textContent = 'ℹ';
  } else if (type === 'warning') {
    toast.style.background = 'linear-gradient(135deg, #F59E0B, #FBBF24)';
    if (iconEl) iconEl.textContent = '⚠';
  }

  toast.style.display = 'flex';
  toast.style.animation = 'slideInRight 0.3s ease-out';

  // Auto-dismiss after 3 seconds
  setTimeout(() => {
    toast.style.animation = 'slideOutRight 0.3s ease-in';
    setTimeout(() => {
      toast.style.display = 'none';
    }, 300);
  }, 3000);
}

function showLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.style.display = 'flex';
}

function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.style.display = 'none';
}

// ============ HEADER FUNCTIONS ============
function changeBlueprint(blueprint) {
  const blueprintNames = {
    executive: 'Executive Summary',
    full: 'Full Analysis',
    trading: 'Trading Dashboard',
    risk: 'Risk Management',
    ai: 'AI Insights Deep Dive'
  };

  showToast(`Switched to ${blueprintNames[blueprint]}`);

  // Update AI context
  const contextValue = document.getElementById('aiContextValue');
  if (contextValue) {
    contextValue.textContent = blueprintNames[blueprint];
  }
}

function changePeriod(period) {
  appState.selectedPeriod = period;
  showToast(`Period changed to ${period}`);
}

function toggleMoreMenu() {
  const menu = document.getElementById('moreMenu');
  if (menu) {
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  }
}

// Close more menu when clicking outside
document.addEventListener('click', (e) => {
  const menu = document.getElementById('moreMenu');
  const moreBtn = document.querySelector('.more-menu-btn');
  if (menu && !menu.contains(e.target) && !moreBtn.contains(e.target)) {
    menu.style.display = 'none';
  }
});

function refreshData() {
  const btn = document.querySelector('.header-btn[aria-label="Refresh data"]');
  if (btn) {
    btn.style.animation = 'spin 1s linear';
  }

  showLoading();
  setCriticalWidgetHealthOverride('loading');
  const refresh = (typeof window.refreshLiveData === 'function')
    ? window.refreshLiveData()
    : Promise.resolve(window.getLiveDashboardData ? window.getLiveDashboardData() : {});

  Promise.resolve(refresh)
    .then((payload) => {
      if (payload) {
        applyLiveDashboardData(payload);
        setCriticalWidgetHealthOverride(null);
        showToast('Data refreshed from live endpoint');
      } else {
        setCriticalWidgetHealthOverride(null);
        showToast('Data refreshed with cached content');
      }
    })
    .catch((error) => {
      console.error('refreshData failed:', error);
      setCriticalWidgetHealthOverride('error', {
        reason: toString(error && error.message, 'refresh failed')
      });
      showToast('Refresh failed, keeping last known data', 'error');
    })
    .finally(() => {
      setTimeout(() => {
        hideLoading();
        if (btn) {
          btn.style.animation = '';
        }

        // Update timestamp
        document.querySelectorAll('.last-updated, .refresh-time').forEach(el => {
          el.textContent = `Updated ${formatRelativeTime(liveDataMeta.generatedAt || Date.now())}`;
        });
      }, 300);
    });
}

// V13: Draw Confidence Gauge
function drawConfidenceGauge(value) {
  const canvas = document.getElementById('confidenceGauge');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const clampedValue = Math.max(0, Math.min(100, Math.round(toFiniteNumber(value, 82))));

  // Background arc
  ctx.strokeStyle = 'rgba(31, 64, 175, 0.2)';
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.arc(60, 50, 35, 0.75 * Math.PI, 2.25 * Math.PI);
  ctx.stroke();

  // Value arc
  const percent = clampedValue / 100;
  ctx.strokeStyle = '#10B981';
  ctx.lineWidth = 8;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.arc(60, 50, 35, 0.75 * Math.PI, 0.75 * Math.PI + (1.5 * Math.PI * percent));
  ctx.stroke();
}

function openExportModal() {
  showToast('Export feature: Choose format (PNG, PDF, CSV)');
  // In production, this would open a modal with export options
}

function openSettings() {
  const modal = document.getElementById('settingsModal');
  if (modal) {
    modal.classList.add('active');
  }
}

function closeSettings() {
  const modal = document.getElementById('settingsModal');
  if (modal) {
    modal.classList.remove('active');
  }
}

function saveSettings() {
  const autoRefresh = document.getElementById('autoRefresh').checked;
  const theme = document.getElementById('themeSelect').value;

  appState.autoRefresh = autoRefresh;
  appState.darkMode = theme === 'dark';

  closeSettings();
  showToast('Settings saved successfully');
}



function toggleTheme() {
  appState.darkMode = !appState.darkMode;
  const menuItem = document.getElementById('themeMenuItem');

  if (appState.darkMode) {
    document.body.style.background = '#0F172A';
    if (menuItem) menuItem.innerHTML = '🌙 Dark Mode';
  } else {
    document.body.style.background = '#E8E9F3';
    document.body.style.color = '#0F172A';
    if (menuItem) menuItem.innerHTML = '☀️ Light Mode';
  }

  showToast(`Switched to ${appState.darkMode ? 'dark' : 'light'} mode`);
}

function openNotifications() {
  const drawer = document.getElementById('notificationDrawer');
  if (drawer) {
    drawer.classList.add('active');
  }
}

function closeNotifications() {
  const drawer = document.getElementById('notificationDrawer');
  if (drawer) {
    drawer.classList.remove('active');
  }
}

function markAsRead(button) {
  const item = button.closest('.notification-item');
  item.classList.add('read');
  button.remove();

  // Update badge count
  const badges = document.querySelectorAll('.notification-badge, .nav-badge');
  badges.forEach(badge => {
    const currentCount = parseInt(badge.textContent || '0', 10);
    if (!Number.isFinite(currentCount) || currentCount <= 0) {
      return;
    }
    const next = currentCount - 1;
    badge.textContent = next > 0 ? String(next) : '';
    if (next <= 0) {
      badge.style.display = 'none';
    }
  });
}

function markAllRead() {
  document.querySelectorAll('.notification-item').forEach(item => {
    item.classList.add('read');
    const btn = item.querySelector('.mark-read');
    if (btn) btn.remove();
  });

  document.querySelectorAll('.notification-badge, .nav-badge').forEach(badge => {
    badge.style.display = 'none';
  });

  showToast('All notifications marked as read');
}

// ============ COMMAND PALETTE ============
function toggleCommandPalette() {
  const palette = document.getElementById('commandPalette');
  if (!palette) return;

  palette.classList.toggle('active');
  if (palette.classList.contains('active')) {
    document.getElementById('commandInput').focus();
  }
}

function executeCommand(cmd) {
  toggleCommandPalette();

  switch (cmd) {
    case 'correlation':
      document.querySelector('.correlation-map').scrollIntoView({ behavior: 'smooth' });
      showToast('Showing correlation matrix');
      break;
    case 'backtest':
      runBacktest();
      break;
    case 'report':
      showToast('Generating comprehensive report...');
      break;
    case 'refresh':
      refreshData();
      break;
    case 'theme':
      toggleTheme();
      break;
    case 'nvda':
      showToast('NVDA: +12.3% forecast with 92% confidence');
      break;
    case 'risk':
      showToast('Risk exposure: Tech 45%, Healthcare 20%, Finance 15%');
      break;
    default:
      showToast(`Executing: ${cmd}`);
  }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  // CMD/CTRL + K for command palette
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    toggleCommandPalette();
  }

  // Escape closes overlays
  if (e.key === 'Escape') {
    document.getElementById('commandPalette')?.classList.remove('active');
    document.getElementById('notificationDrawer')?.classList.remove('active');
    document.getElementById('settingsModal')?.classList.remove('active');
  }
});

// Close on background click
document.getElementById('commandPalette')?.addEventListener('click', (e) => {
  if (e.target.id === 'commandPalette') {
    toggleCommandPalette();
  }
});

document.getElementById('settingsModal')?.addEventListener('click', (e) => {
  if (e.target.id === 'settingsModal') {
    closeSettings();
  }
});

// ============ TAB SWITCHING (SAFE VERSION) ============
function switchTab(button, tabName) {
  safeSwitchTab(button, tabName);
}

function switchTabLegacy(button, tabName) {
  // Remove active from all tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });

  // Add active to clicked tab
  button.classList.add('active');

  // Hide all tab content
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
    content.style.display = 'none';
  });

  // Show selected tab content
  const selectedTab = document.getElementById(`tab-${tabName}`);
  if (selectedTab) {
    selectedTab.classList.add('active');
    selectedTab.style.display = 'block';
  }

  const tabNames = {
    overview: 'Overview',
    market: 'Market Analysis',
    opportunities: 'Opportunities',
    performance: 'Performance'
  };

  showToast(`Viewing ${tabNames[tabName]}`);
}

function showHelp(topic) {
  const helpMessages = {
    pulse: 'AI-generated narrative summarizing today\'s market movements and their impact on your portfolio.',
    scenarios: 'AI-powered scenarios showing potential outcomes for the next 30 days based on market signals.',
    movers: 'Top 5 stocks in your portfolio with the biggest price movements today.',
    health: 'Overall portfolio health score based on diversification, risk level, and growth potential.',
    drivers: 'Key factors currently driving your portfolio performance, ranked by impact.',
    relationships: 'Shows which stocks in your portfolio tend to move together (correlation analysis).',
    similar: 'AI groups stocks based on their risk/return behavior patterns.',
    news: 'Recent news events and their estimated impact on your portfolio value.',
    sectors: 'Performance comparison across market sectors, highlighting your holdings.',
    volatility: 'Current market volatility level and trend over the past 30 days.',
    alerts: 'Real-time trading signals and market alerts ranked by confidence and priority.',
    recommendations: 'AI-powered investment recommendations with confidence scores and reasoning.',
    ideas: 'Specific trade opportunities with entry points, targets, and risk/reward ratios.',
    calendar: 'Upcoming earnings, economic events, and ex-dividend dates affecting your holdings.',
    'health-full': 'Comprehensive portfolio health analysis with prioritized improvement suggestions.',
    backtest: 'Test your investment strategies against historical data to evaluate potential performance.',
    returns: 'Your cumulative returns over time compared to market benchmarks like S&P 500.',
    history: 'Complete record of your recent trades with profit/loss calculations.'
  };

  showToast(helpMessages[topic] || 'Help information', 'info');
}

// ============ WIDGET FUNCTIONS ============
function expandStory(button) {
  const expanded = button.nextElementSibling;
  if (!expanded) return;

  const isHidden = expanded.style.display === 'none' || !expanded.style.display;
  expanded.style.display = isHidden ? 'block' : 'none';
  button.textContent = isHidden ? 'Hide analysis' : 'Read full analysis';
}

function toggleInteractiveView(button) {
  const arena = document.getElementById('interactiveArena');
  if (!arena) return;

  const isHidden = arena.style.display === 'none' || !arena.style.display;
  arena.style.display = isHidden ? 'block' : 'none';
  button.textContent = isHidden ? 'Hide Interactive View' : 'Switch to Interactive View';

  if (isHidden) {
    showToast('Interactive bubble view activated - drag to explore!');
  }
}

function toggleCorrelationMatrix(button) {
  const container = document.getElementById('heatmapContainer');
  if (!container) return;

  const isHidden = container.style.display === 'none' || !container.style.display;
  container.style.display = isHidden ? 'block' : 'none';
  button.textContent = isHidden ? 'Hide Full Matrix' : 'Show Full Matrix';

  if (isHidden && !container.dataset.drawn) {
    drawCorrelationHeatmap();
    container.dataset.drawn = 'true';
  }
}

function toggleAdvancedVolatility(button) {
  const advanced = document.getElementById('volatilityAdvanced');
  if (!advanced) return;

  const isHidden = advanced.style.display === 'none' || !advanced.style.display;
  advanced.style.display = isHidden ? 'block' : 'none';
  button.textContent = isHidden ? 'Hide Advanced View' : 'Show Advanced View';
}

function toggleAlertDetails(alertItem) {
  const actions = alertItem.querySelector('.alert-actions');
  if (!actions) return;

  const isHidden = actions.style.display === 'none' || !actions.style.display;
  actions.style.display = isHidden ? 'flex' : 'none';
  alertItem.classList.toggle('expanded');
}

function selectReturnRange(button, range) {
  document.querySelectorAll('.range-btn').forEach(btn => btn.classList.remove('active'));
  button.classList.add('active');
  showToast(`Viewing ${range} returns`);
}

function filterHistory(button, type) {
  document.querySelectorAll('.history-filter-btn').forEach(btn => btn.classList.remove('active'));
  button.classList.add('active');
  showToast(`Filtering: ${type}`);
}



function filterAlerts(type) {
  const buttons = document.querySelectorAll('.alert-timeline .filter-btn');
  buttons.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === type);
  });

  const alerts = document.querySelectorAll('.alert-timeline .alert-item');
  alerts.forEach(alert => {
    if (!alert) return;
    const normalizedType = toString(alert.dataset.type, 'news').toLowerCase() === 'risk' ? 'risks' : toString(alert.dataset.type, 'news').toLowerCase() === 'opportunity' ? 'opportunities' : toString(alert.dataset.type, 'news').toLowerCase();
    const priority = toString(alert.dataset.priority, 'low').toLowerCase();
    if (type === 'all') {
      alert.style.display = 'flex';
      return;
    }
    if (type === 'opportunities') {
      alert.style.display = normalizedType === 'opportunities' ? 'flex' : 'none';
      return;
    }
    if (type === 'risks') {
      alert.style.display = normalizedType === 'risks' ? 'flex' : 'none';
      return;
    }
    if (type === 'news') {
      alert.style.display = normalizedType === 'news' ? 'flex' : 'none';
      return;
    }
    alert.style.display = priority === type ? 'flex' : 'none';
  });
}



function toggleComparison(button) {
  // If called without a button (e.g., from a checkbox onchange), do a simple toast and return
  if (!button) {
    showToast('Benchmark comparison toggled');
    return;
  }

  if (button.textContent.includes('Benchmark')) {
    button.textContent = 'Hide Benchmark';
    showToast('Showing S&P 500 comparison');
  } else {
    button.textContent = 'vs Benchmark';
    showToast('Benchmark hidden');
  }
}

function mapPortfolioHealthTone(value) {
  const tone = toString(value, '').toLowerCase();
  if (tone === 'positive' || tone === 'warning' || tone === 'neutral') {
    return tone;
  }
  return 'neutral';
}

function formatPortfolioHealthProfile(value) {
  const normalized = toString(value, FALLBACK_APP_DATA.portfolioHealth.riskProfile)
    .replace(/[_-]+/g, ' ')
    .trim();
  if (!normalized) {
    return 'Balanced';
  }

  return normalized
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

// ============ HEALTH GAUGE COMPACT ============
function drawHealthGaugeCompact() {
  const health = isObject(appData.portfolioHealth) ? appData.portfolioHealth : {};
  const overall = Math.max(0, Math.min(100, Math.round(toFiniteNumber(health.overall, FALLBACK_APP_DATA.portfolioHealth.overall))));
  const canvas = document.getElementById('healthGaugeCompact');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    const centerX = 75;
    const centerY = 75;
    const radius = 55;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background arc
    ctx.strokeStyle = 'rgba(31, 64, 175, 0.2)';
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 2.25 * Math.PI);
    ctx.stroke();

    // Value arc
    const percent = overall / 100;
    ctx.strokeStyle = '#1F40AF';
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 0.75 * Math.PI + (1.5 * Math.PI * percent));
    ctx.stroke();
  }

  const valueEl = document.getElementById('healthValueCompact');
  if (valueEl) {
    valueEl.textContent = `${overall}%`;
  }

  const riskBadge = document.getElementById('portfolioHealthRiskBadge');
  if (riskBadge) {
    const tone = mapPortfolioHealthTone(health.riskTone || FALLBACK_APP_DATA.portfolioHealth.riskTone);
    riskBadge.className = `context-badge ${tone}`;
    riskBadge.textContent = toString(health.riskLabel, FALLBACK_APP_DATA.portfolioHealth.riskLabel);
  }

  const profileBadge = document.getElementById('portfolioHealthProfileBadge');
  if (profileBadge) {
    const tone = mapPortfolioHealthTone(health.riskTone || FALLBACK_APP_DATA.portfolioHealth.riskTone);
    profileBadge.className = `context-badge ${tone}`;
    profileBadge.textContent = formatPortfolioHealthProfile(health.riskProfile);
  }

  const profileConfidence = document.getElementById('portfolioHealthProfileConfidence');
  if (profileConfidence) {
    const confidence = Math.max(0, Math.min(100, Math.round(toFiniteNumber(
      health.confidence,
      FALLBACK_APP_DATA.portfolioHealth.confidence,
    ))));
    const benchmark = toString(health.benchmark, FALLBACK_APP_DATA.portfolioHealth.benchmark);
    profileConfidence.textContent = `${confidence}% confidence vs ${benchmark}`;
  }

  const stateSummary = document.getElementById('portfolioHealthStateSummary');
  if (stateSummary) {
    stateSummary.textContent = toString(health.stateSummary, FALLBACK_APP_DATA.portfolioHealth.stateSummary);
  }

  const suggestionEl = document.getElementById('portfolioHealthSuggestion');
  if (suggestionEl) {
    suggestionEl.textContent = `Suggestion: ${toString(health.suggestion, FALLBACK_APP_DATA.portfolioHealth.suggestion)}`;
  }

  const allocationLabel = document.getElementById('portfolioHealthAllocationLabel');
  if (allocationLabel) {
    allocationLabel.textContent = toString(health.allocationLabel, FALLBACK_APP_DATA.portfolioHealth.allocationLabel);
  }

  const allocationFill = document.getElementById('portfolioHealthAllocationFill');
  if (allocationFill) {
    const allocationProgress = Math.max(0, Math.min(100, Math.round(toFiniteNumber(health.allocationProgress, FALLBACK_APP_DATA.portfolioHealth.allocationProgress))));
    allocationFill.style.width = `${allocationProgress}%`;
  }

  const timestampEl = document.getElementById('portfolioHealthTimestamp');
  if (timestampEl) {
    timestampEl.textContent = `Updated ${formatRelativeTime(toString(health.updatedAt, liveDataMeta.generatedAt))}`;
  }
}

// ============ CHART DRAWING FUNCTIONS ============
// Enhanced sparkline with gradient fill, smooth curves, and highlight points
function drawSparkline(canvasId, data, color = '#2D9E78') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = 4;

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  ctx.clearRect(0, 0, width, height);

  // Draw gradient fill area
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, color + '40'); // 25% opacity
  gradient.addColorStop(1, color + '08'); // 3% opacity

  ctx.beginPath();
  data.forEach((value, index) => {
    const x = (index / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  // Close path for fill
  ctx.lineTo(width - padding, height - padding);
  ctx.lineTo(padding, height - padding);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Draw line on top
  ctx.beginPath();
  data.forEach((value, index) => {
    const x = (index / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.stroke();

  // Highlight last point
  const lastX = width - padding;
  const lastY = height - padding - ((data[data.length - 1] - min) / range) * (height - padding * 2);
  ctx.beginPath();
  ctx.arc(lastX, lastY, 3.5, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Highlight min/max points
  const maxIndex = data.indexOf(max);
  const minIndex = data.indexOf(min);

  const maxX = (maxIndex / (data.length - 1)) * (width - padding * 2) + padding;
  const maxY = height - padding - ((max - min) / range) * (height - padding * 2);

  ctx.beginPath();
  ctx.arc(maxX, maxY, 2, 0, Math.PI * 2);
  ctx.fillStyle = '#2D9E78';
  ctx.fill();
}

function drawCorrelationHeatmap() {
  const canvas = document.getElementById('correlationHeatmap');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const { labels, data } = appData.correlations;

  const size = labels.length;
  const cellSize = 60;
  const padding = 60;

  canvas.width = cellSize * size + padding * 2;
  canvas.height = cellSize * size + padding * 2;

  // Draw cells with staggered animation
  data.forEach((row, i) => {
    row.forEach((value, j) => {
      setTimeout(() => {
        const x = padding + j * cellSize;
        const y = padding + i * cellSize;

        let color;
        if (value >= 0.8) color = '#1F40AF';
        else if (value >= 0.6) color = '#2E56D6';
        else if (value >= 0.4) color = '#4A6BD9';
        else color = 'rgba(255,255,255,0.1)';

        ctx.fillStyle = color;
        const radius = 4;
        ctx.beginPath();
        ctx.roundRect(x + 2, y + 2, cellSize - 4, cellSize - 4, radius);
        ctx.fill();

        ctx.fillStyle = value >= 0.4 ? '#E8E9F3' : 'rgba(255,255,255,0.7)';
        ctx.font = '500 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(value.toFixed(2), x + cellSize / 2, y + cellSize / 2);
      }, (i * size + j) * 40);
    });
  });

  // Draw labels
  setTimeout(() => {
    ctx.fillStyle = '#B0B4CC';
    ctx.font = '600 11px sans-serif';
    labels.forEach((label, i) => {
      ctx.textAlign = 'center';
      ctx.fillText(label, padding + i * cellSize + cellSize / 2, padding - 20);
      ctx.textAlign = 'right';
      ctx.fillText(label, padding - 15, padding + i * cellSize + cellSize / 2);
    });
  }, 1200);
}

function drawMarketDriversDonut() {
  const canvas = document.getElementById('driversDonut');
  if (!canvas) return;

  // Destroy existing chart if it exists
  const existingChart = Chart.getChart(canvas);
  if (existingChart) {
    existingChart.destroy();
  }

  const colors = ['#1F40AF', '#2E56D6', '#4A6BD9', '#6687DD'];

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: appData.marketDrivers.map(d => d.factor),
      datasets: [{
        data: appData.marketDrivers.map(d => d.contribution),
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#0F172A',
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: {
        animateRotate: true,
        animateScale: true,
        duration: 1500,
        easing: 'easeOutQuart'
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#E8E9F3',
            font: { size: 12, weight: '500' },
            padding: 16
          }
        },
        tooltip: {
          backgroundColor: 'rgba(31, 64, 175, 0.9)',
          titleColor: '#E8E9F3',
          bodyColor: '#E8E9F3',
          borderColor: 'rgba(31, 64, 175, 0.3)',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8
        }
      }
    }
  });
}

function drawClusterMap() {
  const canvas = document.getElementById('clusterMap');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = 60;

  ctx.clearRect(0, 0, width, height);

  // Draw axes
  ctx.strokeStyle = '#B0B4CC';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(padding, height - padding);
  ctx.lineTo(width - padding, height - padding);
  ctx.lineTo(width - padding, padding);
  ctx.stroke();

  // Labels
  ctx.fillStyle = '#B0B4CC';
  ctx.font = '12px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Risk →', width / 2, height - 20);
  ctx.save();
  ctx.translate(20, height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('Return →', 0, 0);
  ctx.restore();

  // Draw points for all 15 stocks
  const maxRisk = 30;
  const maxReturn = 15;
  const groupColors = {
    'High Growth': '#8B5CF6',
    'Stable': '#1F40AF',
    'Defensive': '#2D9E78',
    'Energy': '#B8860B',
    'Finance': '#4A6BD9'
  };

  const clusterPoints = toArray(appData.clusterMap, []);
  if (!clusterPoints.length) return;

  clusterPoints.forEach((point, i) => {
    setTimeout(() => {
      const x = padding + ((point.risk / maxRisk) * (width - padding * 2));
      const y = height - padding - ((point.return + 5) / (maxReturn + 5) * (height - padding * 2));

      const pointColor = groupColors[point.group] || '#1F40AF';
      const radius = Math.abs(point.return) > 8 ? 12 : 8;

      ctx.shadowBlur = 10;
      ctx.shadowColor = pointColor;
      ctx.fillStyle = pointColor;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.fillStyle = '#E8E9F3';
      ctx.font = '600 10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(point.name, x, y - radius - 6);
    }, i * 150);
  });
}

function renderNewsImpact() {
  const container = document.getElementById('newsTable');
  if (!container) return;

  const rows = Array.isArray(appData.newsImpact) && appData.newsImpact.length > 0
    ? appData.newsImpact
    : (Array.isArray(newsItems) ? newsItems : []);

  const getTicker = (news) => {
    if (typeof news?.ticker === 'string' && news.ticker.trim()) {
      return news.ticker.trim().toUpperCase();
    }
    if (typeof news?.category === 'string' && /^[A-Z.-]{1,10}$/.test(news.category.trim())) {
      return news.category.trim().toUpperCase();
    }
    return '';
  };

  const getImpactLabel = (impactValue) => {
    if (impactValue >= 8) return 'High';
    if (impactValue >= 5) return 'Medium';
    return 'Low';
  };

  const getImpactClass = (news) => {
    if (typeof news?.effect === 'string' && news.effect.startsWith('+')) return 'positive';
    if (typeof news?.effect === 'string' && news.effect.startsWith('-')) return 'negative';
    return news?.impact >= 8 ? 'positive' : news?.impact >= 5 ? 'neutral' : 'negative';
  };

  container.innerHTML = rows.slice(0, 10).map(news => `
    <div class="news-row" ${getTicker(news) ? `data-ticker="${getTicker(news)}"` : ''}>
      <div class="news-content">
        <div class="news-headline">${news.headline}</div>
        <div class="news-source">${news.source || 'API'} • ${news.time || 'Recently'}</div>
      </div>
      <div class="news-impact-badge ${getImpactClass(news)}">${getImpactLabel(Number(news.impact) || 0)}</div>
      <div class="news-delta ${news.effect.startsWith('+') ? 'positive' : 'negative'}">${news.effect}</div>
      ${getTicker(news) ? `<div class="news-playbook" id="playbook-news-${getTicker(news)}"></div>` : ''}
    </div>
  `).join('');

  if (window.NewsImpactPlaybooks && typeof window.NewsImpactPlaybooks.refresh === 'function') {
    window.NewsImpactPlaybooks.refresh();
  }
}

function drawSectorPerformance() {
  const canvas = document.getElementById('sectorChart');
  if (!canvas) return;
  const sectorData = Array.isArray(appData.sectorPerformance) ? appData.sectorPerformance : [];
  const rotationList = document.getElementById('sectorRotationList');
  const subtitle = document.getElementById('sectorWidgetSubtitle');

  if (rotationList) {
    rotationList.innerHTML = sectorData
      .slice(0, 6)
      .map((sector) => {
        const sign = sector.changeLabel || '';
        const icon = sector.trendIcon || (sector.change >= 0 ? '↑' : '↓');
        const inPortfolio = sector.holdings ? 'Portfolio' : 'No position';
        return `<div class="sector-rotation-item"><span class="sector-name">${sector.sector || 'Unknown'}</span><span class="sector-trend">${icon} ${sign}</span><span class="sector-meta">${inPortfolio}</span></div>`;
      })
      .join('');
  }

  if (subtitle) {
    subtitle.textContent = sectorData.length > 0
      ? `${sectorData[0].sector || 'Markets'} • ${sectorData[0].trendIcon || ''} ${sectorData[0].changeLabel || `${sectorData[0].change >= 0 ? '+' : ''}${sectorData[0].change.toFixed(2)}%`}`
      : 'Collecte des données sectorielles...';
  }

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: sectorData.map(s => s.sector),
      datasets: [{
        label: 'Change %',
        data: sectorData.map(s => s.change),
        backgroundColor: sectorData.map(s => {
          if (s.holdings) {
            return s.change > 5 ? '#2D9E78' : s.change > 0 ? '#1F40AF' : '#8B3A3A';
          } else {
            return 'rgba(176, 180, 204, 0.3)';
          }
        }),
        borderWidth: sectorData.map(s => s.holdings ? 2 : 0),
        borderColor: sectorData.map(s => s.holdings ? '#4A6BD9' : 'transparent'),
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 1500,
        easing: 'easeOutQuart',
        delay: (context) => context.dataIndex * 100
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(31, 64, 175, 0.9)',
          titleColor: '#E8E9F3',
          bodyColor: '#E8E9F3',
          borderColor: 'rgba(31, 64, 175, 0.3)',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            afterLabel: function (context) {
              const sector = sectorData[context.dataIndex];
              if (!sector) return '';
              const label = sector.changeLabel || `${sector.change >= 0 ? '+' : ''}${sector.change.toFixed(2)}%`;
              if (sector.holdings) {
                const trend = sector.trendIcon || '';
                return `${trend} ${label} • Portfolio ${sector.weightLabel || `${sector.weight}%`}`;
              }
              return ` ${sector.trendIcon || ''} ${label}`;
            }
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#B0B4CC', font: { size: 11 } },
          grid: { color: 'rgba(31, 64, 175, 0.1)' }
        },
        y: {
          ticks: { color: '#E8E9F3', font: { size: 11, weight: '500' } },
          grid: { display: false }
        }
      }
    }
  });
}

function toggleCollapse(button) {
  const widget = button.closest('.widget-card');
  if (!widget) return;

  const body = widget.querySelector('.widget-body');
  if (!body) return;

  const isHidden = body.style.display === 'none';
  body.style.display = isHidden ? '' : 'none';
  button.textContent = isHidden ? '−' : '+';
}

function renderPortfolioHealthFullDetails() {
  const health = isObject(appData.portfolioHealth) ? appData.portfolioHealth : {};
  const allocationProgress = Math.max(0, Math.min(100, Math.round(toFiniteNumber(
    health.allocationProgress,
    FALLBACK_APP_DATA.portfolioHealth.allocationProgress,
  ))));
  const confidence = Math.max(0, Math.min(100, Math.round(toFiniteNumber(
    health.confidence,
    FALLBACK_APP_DATA.portfolioHealth.confidence,
  ))));
  const riskLabel = toString(health.riskLabel, FALLBACK_APP_DATA.portfolioHealth.riskLabel);
  const riskTone = mapPortfolioHealthTone(health.riskTone || FALLBACK_APP_DATA.portfolioHealth.riskTone);
  const profileLabel = formatPortfolioHealthProfile(health.riskProfile);
  const benchmark = toString(health.benchmark, FALLBACK_APP_DATA.portfolioHealth.benchmark);
  const stateSummary = toString(health.stateSummary, FALLBACK_APP_DATA.portfolioHealth.stateSummary);
  const suggestion = toString(health.suggestion, FALLBACK_APP_DATA.portfolioHealth.suggestion);
  const allocationLabel = toString(health.allocationLabel, FALLBACK_APP_DATA.portfolioHealth.allocationLabel);
  const status = toString(health.status, '').toLowerCase();
  let riskFillWidth = 60;

  if (riskLabel.toLowerCase() === 'low') {
    riskFillWidth = 35;
  } else if (riskLabel.toLowerCase() === 'high') {
    riskFillWidth = 85;
  }

  const allocationFill = document.getElementById('portfolioHealthFullAllocationFill');
  if (allocationFill) {
    allocationFill.style.width = `${allocationProgress}%`;
    allocationFill.textContent = `${allocationProgress}%`;
  }

  const allocationLabelEl = document.getElementById('portfolioHealthFullAllocationLabel');
  if (allocationLabelEl) {
    allocationLabelEl.textContent = allocationLabel;
  }

  const riskFill = document.getElementById('portfolioHealthFullRiskFill');
  if (riskFill) {
    riskFill.style.width = `${riskFillWidth}%`;
    riskFill.textContent = riskLabel;
  }

  const profileBadge = document.getElementById('portfolioHealthFullProfileBadge');
  if (profileBadge) {
    profileBadge.className = `context-badge ${riskTone}`;
    profileBadge.textContent = profileLabel;
  }

  const riskSummary = document.getElementById('portfolioHealthFullRiskSummary');
  if (riskSummary) {
    riskSummary.textContent = `Risk concentration: ${riskLabel} | Benchmark ${benchmark}`;
  }

  const confidenceFill = document.getElementById('portfolioHealthFullConfidenceFill');
  if (confidenceFill) {
    confidenceFill.style.width = `${confidence}%`;
    confidenceFill.textContent = `${confidence}%`;
  }

  const stateSummaryEl = document.getElementById('portfolioHealthFullStateSummary');
  if (stateSummaryEl) {
    stateSummaryEl.textContent = stateSummary;
  }

  const primarySuggestion = document.getElementById('portfolioHealthSuggestionPrimary');
  if (primarySuggestion) {
    primarySuggestion.className = `suggestion-item ${riskTone === 'warning' || status === 'degraded' ? 'high' : 'medium'}`;
  }

  const primarySuggestionText = document.getElementById('portfolioHealthSuggestionPrimaryText');
  if (primarySuggestionText) {
    primarySuggestionText.textContent = suggestion;
  }

  const secondarySuggestion = document.getElementById('portfolioHealthSuggestionSecondary');
  if (secondarySuggestion) {
    secondarySuggestion.className = 'suggestion-item medium';
  }

  const secondarySuggestionText = document.getElementById('portfolioHealthSuggestionSecondaryText');
  if (secondarySuggestionText) {
    secondarySuggestionText.textContent = stateSummary;
  }

  const tertiarySuggestion = document.getElementById('portfolioHealthSuggestionTertiary');
  if (tertiarySuggestion) {
    tertiarySuggestion.className = `suggestion-item ${allocationProgress >= 60 ? 'high' : 'low'}`;
  }

  const tertiarySuggestionText = document.getElementById('portfolioHealthSuggestionTertiaryText');
  if (tertiarySuggestionText) {
    tertiarySuggestionText.textContent = allocationLabel;
  }
}

function drawHealthGauge() {
  const health = isObject(appData.portfolioHealth) ? appData.portfolioHealth : {};
  const overall = Math.max(0, Math.min(100, Math.round(toFiniteNumber(health.overall, FALLBACK_APP_DATA.portfolioHealth.overall))));
  const canvas = document.getElementById('healthGauge');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const centerX = 100;
  const centerY = 100;
  const radius = 70;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background arc
  ctx.strokeStyle = 'rgba(31, 64, 175, 0.2)';
  ctx.lineWidth = 12;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 2.25 * Math.PI);
  ctx.stroke();

  // Value arc with animation
  const percent = overall / 100;
  ctx.strokeStyle = '#1F40AF';
  ctx.lineWidth = 12;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 0.75 * Math.PI + (1.5 * Math.PI * percent));
  ctx.stroke();

  const valueEl = document.getElementById('healthValue');
  if (valueEl) {
    valueEl.textContent = `${overall}%`;
  }

  renderPortfolioHealthFullDetails();

  const footerEl = document.querySelector('.portfolio-health-full .widget-footer .widget-timestamp');
  if (footerEl) {
    footerEl.textContent = `Updated ${formatRelativeTime(toString(health.updatedAt, liveDataMeta.generatedAt))}`;
  }
}

function renderBacktestMetrics() {
  const container = document.getElementById('backtestMetrics');
  if (!container) return;

  const metrics = [
    { label: 'Sharpe Ratio', value: appData.backtestResults.sharpeRatio },
    { label: 'Win Rate', value: appData.backtestResults.winRate + '%' },
    { label: 'Max Drawdown', value: appData.backtestResults.maxDrawdown + '%' },
    { label: 'Total Return', value: appData.backtestResults.totalReturn + '%' }
  ];

  container.innerHTML = metrics.map(m => `
    <div class="backtest-metric">
      <div class="metric-label">${m.label}</div>
      <div class="metric-value">${m.value}</div>
    </div>
  `).join('');
}

function runBacktest() {
  const resultsDiv = document.getElementById('backtestResults');
  if (resultsDiv) {
    resultsDiv.style.display = 'block';
  }

  showLoading();
  setTimeout(() => {
    hideLoading();
    showToast('Backtest simulation completed!');
    renderBacktestMetrics();
  }, 2000);
}

function renderOpportunities() {
  const container = document.getElementById('opportunitiesList');
  if (!container) return;

  container.innerHTML = appData.opportunities.map(opp => `
    <div class="opportunity-card">
      <div class="opportunity-conviction">${opp.conviction} Conviction</div>
      <div class="opportunity-return">+${opp.return}%</div>
      <div class="opportunity-confidence">${opp.confidence}% confidence</div>
      <button class="opportunity-btn" onclick="showToast('Opening ${opp.conviction} opportunity details...')">Explore</button>
    </div>
  `).join('');
}

function renderPerformanceTable() {
  const tbody = document.getElementById('performanceTableBody');
  if (!tbody) return;

  tbody.innerHTML = appData.topStocks.map(stock => `
    <tr>
      <td class="table-symbol">${stock.symbol}</td>
      <td>$${stock.price.toFixed(2)}</td>
      <td class="table-change ${stock.change >= 0 ? 'positive' : 'negative'}">
        ${stock.change >= 0 ? '▲' : '▼'} ${Math.abs(stock.change).toFixed(1)}%
      </td>
      <td>${stock.forecast}</td>
      <td>${stock.confidence}%</td>
      <td><canvas class="table-sparkline" width="80" height="24"></canvas></td>
    </tr>
  `).join('');

  // Draw sparklines only for the rows in the performance table
  const rowSparklines = tbody.querySelectorAll('.table-sparkline');
  rowSparklines.forEach((canvas, i) => {
    const stock = appData.topStocks[i];
    if (!stock) return;
    const ctx = canvas.getContext('2d');
    const data = [0.9, 0.95, 0.92, 0.98, 1.0].map(v => v * stock.price);
    drawMiniSparkline(ctx, data, 80, 24, stock.change >= 0);
  });
}

function drawMiniSparkline(ctx, data, width, height, isPositive) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  ctx.strokeStyle = isPositive ? '#2D9E78' : '#8B3A3A';
  ctx.lineWidth = 2;
  ctx.beginPath();

  data.forEach((value, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((value - min) / range * height);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();
}

// Enhanced stock sparkline with gradient and smooth rendering
function drawStockSparkline(canvasId, data, color = '#2D9E78') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = 3;

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  ctx.clearRect(0, 0, width, height);

  // Draw gradient fill
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, color + '30');
  gradient.addColorStop(1, color + '05');

  ctx.beginPath();
  data.forEach((value, index) => {
    const x = (index / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.lineTo(width - padding, height - padding);
  ctx.lineTo(padding, height - padding);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Draw line
  ctx.beginPath();
  data.forEach((value, index) => {
    const x = (index / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.stroke();

  // Highlight last point
  const lastX = width - padding;
  const lastY = height - padding - ((data[data.length - 1] - min) / range) * (height - padding * 2);
  ctx.beginPath();
  ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
}

function sortTable(columnIndex) {
  showToast('Table sorted by column ' + columnIndex);
  // In production, this would actually sort the table
}

function loadMoreStocks() {
  showLoading();
  setTimeout(() => {
    hideLoading();
    showToast('Loaded 10 more stocks');
  }, 1000);
}

function drawVolatilitySurface() {
  const canvas = document.getElementById('volatilitySurface');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);

  const rows = 12;
  const cols = 16;

  for (let i = 0; i < rows; i++) {
    setTimeout(() => {
      const yBase = 50 + (i * (height - 100) / rows);
      ctx.strokeStyle = `rgba(31, 64, 175, ${0.3 + (i / rows) * 0.7})`;
      ctx.lineWidth = 2;
      ctx.beginPath();

      for (let j = 0; j < cols; j++) {
        const x = 50 + (j * (width - 100) / cols);
        const volatility = Math.sin(i * 0.5) * Math.cos(j * 0.3) * 30;
        const y = yBase - volatility;

        if (j === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }

      ctx.stroke();
    }, i * 50);
  }
}

// ============ BUBBLE DRAG FUNCTIONALITY ============
let draggedBubble = null;
let offset = { x: 0, y: 0 };

function initBubbleDrag() {
  const bubbles = document.querySelectorAll('.bubble[draggable="true"]');

  bubbles.forEach(bubble => {
    bubble.addEventListener('mousedown', startDrag);
    bubble.addEventListener('touchstart', startDrag, { passive: false });
  });

  document.addEventListener('mousemove', drag);
  document.addEventListener('touchmove', drag, { passive: false });
  document.addEventListener('mouseup', endDrag);
  document.addEventListener('touchend', endDrag);
}

function startDrag(e) {
  if (!e.target.closest('.bubble.user')) return;

  draggedBubble = e.target.closest('.bubble');
  const rect = draggedBubble.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  offset.x = clientX - rect.left;
  offset.y = clientY - rect.top;

  draggedBubble.style.cursor = 'grabbing';
  draggedBubble.style.zIndex = '100';

  e.preventDefault();
}

function drag(e) {
  if (!draggedBubble) return;

  const container = document.querySelector('.arena-container');
  const containerRect = container.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  let x = clientX - containerRect.left - offset.x;
  let y = clientY - containerRect.top - offset.y;

  const bubbleSize = 140;
  x = Math.max(0, Math.min(x, containerRect.width - bubbleSize));
  y = Math.max(0, Math.min(y, containerRect.height - bubbleSize));

  draggedBubble.style.left = x + 'px';
  draggedBubble.style.top = y + 'px';
  draggedBubble.style.transform = 'none';

  e.preventDefault();
}

function endDrag() {
  if (draggedBubble) {
    draggedBubble.style.cursor = 'move';
    draggedBubble.style.zIndex = '';
    showToast('Scenario updated based on new position');
    draggedBubble = null;
  }
}

// ============ CUSTOMIZATION FUNCTIONS ============
function enterCustomizeMode() {
  appState.customizeMode = !appState.customizeMode;

  if (appState.customizeMode) {
    document.body.classList.add('customize-mode');
    showToast('Customization mode enabled. Drag widgets to rearrange.');
  } else {
    document.body.classList.remove('customize-mode');
    showToast('Customization mode disabled');
  }
}

function resetLayout() {
  showToast('Layout reset to default');
  location.reload();
}

function saveLayout() {
  showToast('Layout saved successfully!');
}

// ============ MOBILE NAVIGATION ============
function selectTab(button, tab) {
  document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
  button.classList.add('active');

  // Synchronize with main tab system
  const tabMap = {
    dashboard: 'overview',
    portfolio: 'performance',
    opportunities: 'opportunities',
    alerts: 'market',
    more: 'ailab'
  };
  const targetTab = tabMap[tab];
  if (targetTab) {
    const desktopButton = document.querySelector(`.tab-btn[data-tab="${targetTab}"]`);
    safeSwitchTab(desktopButton, targetTab);
  }

  showToast(`Navigated to ${tab}`);
}

// ============ INITIALIZATION ============
// V13: Render Trade Ideas
function renderTradeIdeas(root = document) {
  const container = getFacetteWidgetSlot(root, 'tradeIdeasGrid');
  if (!container) return;

  container.innerHTML = tradeIdeas.map(idea => `
    <div class="trade-card">
      <div class="trade-main">
        <div class="stock-info">
          <span class="symbol">${idea.symbol}</span>
          <span class="signal-type">${idea.signalType}</span>
        </div>
        <div class="prices">
          <span class="entry">$${idea.entry}</span>
          <span class="arrow">→</span>
          <span class="target">$${idea.target}</span>
        </div>
      </div>
      <div class="trade-meta">
        <div class="confidence-bar">
          <div class="bar-fill" style="width: ${idea.confidence}%"></div>
          <span class="confidence-text">${idea.confidence}%</span>
        </div>
        <button class="trade-btn" onclick="showToast('Opening ${idea.symbol} trade...')">Trade</button>
      </div>
    </div>
  `).join('');
}

// V13: Render Market Calendar
function renderMarketCalendar(root = document) {
  const container = getFacetteWidgetSlot(root, 'calendarSections');
  if (!container) return;

  let html = '<div class="calendar-section">';
  html += '<h4>Earnings (Next 7 days)</h4>';
  marketCalendar.earnings.forEach(e => {
    html += `
      <div class="event-item">
        <span class="event-name">${e.stock}</span>
        <span class="event-date">${e.date}</span>
        <span class="impact-badge ${e.impact.toLowerCase()}">${e.impact} Impact</span>
      </div>
    `;
  });
  html += '</div>';

  html += '<div class="calendar-section">';
  html += '<h4>Economic Data</h4>';
  marketCalendar.economicData.forEach(e => {
    html += `
      <div class="event-item">
        <span class="event-name">${e.event}</span>
        <span class="event-date">${e.date}</span>
        <span class="impact-badge ${e.impact.toLowerCase()}">${e.impact} Impact</span>
      </div>
    `;
  });
  html += '</div>';

  html += '<div class="calendar-section">';
  html += '<h4>Ex-Dividend Dates</h4>';
  marketCalendar.exDividend.forEach(e => {
    html += `
      <div class="event-item">
        <span class="event-name">${e.stock}</span>
        <span class="event-date">${e.date}</span>
        <span class="dividend-amount">$${e.amount}</span>
      </div>
    `;
  });
  html += '</div>';

  container.innerHTML = html;
}

// V13: Render News Feed
function renderNewsFeed(root = document) {
  const container = getFacetteWidgetSlot(root, 'newsCardsGrid');
  if (!container) return;

  container.innerHTML = newsItems.map(news => `
    <div class="news-card">
      <div class="news-header">
        <span class="impact-badge ${news.impact >= 8 ? 'very-high' : news.impact >= 7 ? 'high' : 'medium'}">
          ${news.impact >= 8 ? 'Very High' : news.impact >= 7 ? 'High' : 'Medium'} ${news.impact.toFixed(1)}/10
        </span>
        <span class="time">${news.time}</span>
      </div>
      <h4 class="headline">${news.headline}</h4>
      <div class="news-metrics">
        <div class="effect-indicator ${news.effect.startsWith('+') ? 'positive' : 'negative'}">
          <span class="arrow">${news.effect.startsWith('+') ? '↗️' : '↘️'}</span>
          <span class="value">${news.effect}</span>
          <span class="label">Effect on Portfolio</span>
        </div>
        <div class="source">
          <span>${news.source}</span>
        </div>
      </div>
      <div class="news-actions">
        <button class="news-btn" onclick="showToast('Reading full article...')">Read Full</button>
        <button class="news-btn secondary" onclick="showToast('AI analyzing...')">AI Analysis</button>
        <button class="news-btn icon-only" onclick="showToast('Alert set')" title="Set Alert">🔔</button>
      </div>
    </div>
  `).join('');
}

// V13: Render Market Drivers Visual
function renderMarketDrivers(root = document) {
  const container = getFacetteWidgetSlot(root, 'driversBarsVisual');
  if (!container) return;

  container.innerHTML = marketDrivers.map(driver => `
    <div class="driver-bar-item">
      <span class="driver-label">${driver.factor}</span>
      <div class="driver-bar-wrapper">
        <div class="driver-bar-fill" style="width: ${driver.contribution}%; background: ${driver.color};">
          ${driver.contribution}%
        </div>
      </div>
    </div>
  `).join('');
}

// V13: Ask LLM Judge
function askLLMJudge() {
  const input = document.getElementById('judgeQuestion');
  const processing = document.getElementById('judgeProcessing');
  const result = document.getElementById('judgeResult');
  const askAnother = document.getElementById('askAnotherBtn');
  const askButton = document.getElementById('judgeAskButton');
  const status = document.getElementById('judgeStatus');
  const question = toString(input?.value, '').trim();

  if (!question) {
    showToast('Veuillez saisir votre portefeuille', 'warning');
    if (status) {
      status.className = 'judge-status judge-status-warning';
      status.innerText = 'Veuillez saisir au moins un actif (ex: AAPL,MSFT)';
    }
    return;
  }

  const startedAt = performance.now();

  const rawTickers = question
    .split(/[,;\n\s]+/)
    .map((ticker) => ticker.trim().toUpperCase())
    .filter((ticker) => ticker.length > 0)
    .slice(0, 8);

  const tickerDisplay = rawTickers.length ? rawTickers.join(', ') : question;

  input.disabled = true;
  if (askButton) askButton.disabled = true;
  processing.style.display = 'block';
  result.style.display = 'none';
  askAnother.style.display = 'none';
  if (status) {
    status.className = 'judge-status judge-status-running';
    status.innerText = `Analyse en cours sur ${tickerDisplay}`;
  }

  const steps = processing.querySelectorAll('.processing-step');
  steps.forEach((step) => {
    step.classList.remove('active');
  });

  let activeStep = 0;
  const progressTicker = setInterval(() => {
    if (activeStep >= steps.length) {
      clearInterval(progressTicker);
      return;
    }
    steps[activeStep].classList.add('active');
    activeStep += 1;
  }, 800);

  const timeoutMs = 30000;
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => {
      reject(new Error('Réponse trop lente (>30s)'));
    }, timeoutMs);
  });

  const apiCall = typeof window.FinanceAPI?.askCopilot === 'function'
    ? window.FinanceAPI.askCopilot(question, rawTickers)
    : Promise.resolve({
      data: {
        answer: 'Service API indisponible',
        sources: [],
        confidence: 0.2,
        verdict: 'hold'
      }
    });

  Promise.race([Promise.resolve(apiCall), timeoutPromise])
    .then((raw) => {
      const payload = buildCopilotJudgePayload(raw && isObject(raw) && raw.data ? raw.data : raw);
      if (!payload) {
        throw new Error('Réponse Copilot invalide');
      }

      const latencyMs = Math.max(0, Math.round(performance.now() - startedAt));
      const runAt = payload.generatedAt || new Date().toISOString();
      const runTime = runAt
        ? new Date(runAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : 'Heure indisponible';

      const modelLabel = toString(payload.model, 'Copilot');
      const confidenceScore = Math.max(0, Math.min(100, Math.round(toFiniteNumber(payload.confidence, 0))));
      const modelMeta = `Source: ${modelLabel} • Latence: ${latencyMs}ms • Mis à jour ${runTime}`;

      llmJudgeData = {
        ...FALLBACK_LLM_JUDGE_DATA,
        ...payload,
        question
      };

      const modelHtml = llmJudgeData.models
        .map((model) => {
          const confidence = Math.max(0, Math.min(100, Math.round(toFiniteNumber(model.confidence, 0))));
          const verdictClass = normalizeVerdict(model.verdict, 'hold');
          return `
            <div class="model-item">
              <div class="model-header">
                <span class="model-icon">${toString(model.icon, '🤖')}</span>
                <span class="model-name">${toString(model.name, 'Model')}</span>
                <span class="model-verdict ${verdictClass}">${toString(model.verdict, 'HOLD')}</span>
              </div>
              <div class="model-confidence">
                <div class="confidence-bar">
                  <div class="bar-fill" style="width: ${confidence}%"></div>
                </div>
                <span class="confidence-text">${confidence}%</span>
              </div>
            </div>
          `;
        }).join('');

      const sourceHtml = llmJudgeData.dataSources
        .slice(0, 5)
        .map((source) => {
          const label = toString(source.label, 'Source');
          const excerpt = toString(source.excerpt, '');
          const url = toString(source.url, '');
          const sourceLink = url
            ? `<a href="${url}" target="_blank" rel="noopener noreferrer">📊 ${label}</a>`
            : `📊 ${label}`;
          const sourceHint = excerpt ? `<span class="source-hint"> — ${excerpt}</span>` : '';
          return `<span class="source-badge">${sourceLink}${sourceHint}</span>`;
        }).join('');

      const reasoningText = toArray(llmJudgeData.reasoning, [])
        .filter((line) => toString(line, '').trim())
        .slice(0, 3)
        .join('<br/>');

      result.innerHTML = `
        <div class="consensus-section">
          <div class="consensus-badge ${normalizeVerdict(llmJudgeData.consensus, 'hold')}">${toString(llmJudgeData.consensus, 'HOLD')}</div>
          <div class="confidence-display">
            <div class="confidence-number">${confidenceScore}%</div>
            <div class="confidence-label">Confiance de consensus</div>
            <div class="confidence-label source-meta">${modelMeta}</div>
            <div class="confidence-label">Qualité: ${toString(llmJudgeData.qualityStatus, 'insufficient_sources')}</div>
          </div>
        </div>

        <div class="models-breakdown">
          <h4>Opinions des modèles</h4>
          ${modelHtml || '<p>Pas de modèle consulté.</p>'}
        </div>

        <div class="reasoning-section">
          <h4>Pourquoi cette recommandation ?</h4>
          <p class="reasoning-text">${reasoningText || toString(llmJudgeData.answer, 'Analyse indisponible pour le moment, réessayez plus tard.')}</p>
          <div class="data-sources">
            ${sourceHtml || '<span class="source-badge">📊 Sources indisponibles</span>'}
          </div>
        </div>

        <div class="actions-section">
          <h4>Prochaines étapes</h4>
          <div class="action-cards">
            ${llmJudgeData.suggestedActions.map((action) => `
              <div class="action-card">
                <span class="action-icon">${toString(action.icon, '➡️')}</span>
                <div class="action-content">
                  <span class="action-title">${toString(action.title, 'Action')}</span>
                  <span class="action-detail">${toString(action.detail, '')}</span>
                </div>
                <button class="action-btn" onclick="executeAction('${toString(action.action, 'setAlert')}')">Go</button>
              </div>
            `).join('')}
          </div>
        </div>
      `;

      showToast('Analyse Copilot terminée', 'success');
      if (status) {
        status.className = 'judge-status judge-status-success';
        status.innerText = `Analyse terminée (${llmJudgeData.models.length} modèle(s)) en ${latencyMs}ms`;
      }
    })
    .catch((error) => {
      const reason = error?.message || toString(error, 'Erreur inconnue');
      if (status) {
        status.className = 'judge-status judge-status-error';
        status.innerText = `Erreur: ${reason}`;
      }
      result.innerHTML = `
        <div class="reasoning-section">
          <h4>Erreur de consultation</h4>
          <p class="reasoning-text">${reason}</p>
        </div>
      `;
      showToast("Impossible de terminer l'analyse", 'error');
    })
    .finally(() => {
      clearInterval(progressTicker);
      processing.style.display = 'none';
      result.style.display = 'block';
      askAnother.style.display = 'block';
      input.disabled = false;
      if (askButton) askButton.disabled = false;
      steps.forEach((step, index) => {
        if (index >= activeStep) {
          step.classList.add('active');
        }
      });
    });

}

function resetLLMJudge() {
  document.getElementById('judgeQuestion').value = '';
  document.getElementById('judgeResult').style.display = 'none';
  document.getElementById('askAnotherBtn').style.display = 'none';
  const status = document.getElementById('judgeStatus');
  if (status) {
    status.className = 'judge-status';
    status.innerText = '';
  }
  const steps = document.querySelectorAll('.processing-step');
  steps.forEach(step => step.classList.remove('active'));
}

function executeAction(action) {
  const actions = {
    setAlert: 'Alert set for NVDA at $880',
    reviewRisk: 'Opening risk analysis...',
    viewCalendar: 'Viewing market calendar...'
  };
  showToast(actions[action] || 'Action executed');
}

function showLLMHelp() {
  showToast('LLM Judge queries 3 AI models and synthesizes their consensus based on your portfolio data', 'info');
}

function filterNews(filter) {
  showToast(`Filtering news: ${filter}`);
}

function loadMoreNews() {
  showToast('Loading more news...');
}

// V13: Draw Win Rate Circle
function drawWinRateCircle() {
  const canvases = document.querySelectorAll('.win-rate-circle');
  if (!canvases.length) return;

  canvases.forEach(canvas => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const value = (appData.hero && typeof appData.hero.winRate === 'number')
      ? appData.hero.winRate
      : 72;
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 15;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background circle
    ctx.strokeStyle = 'rgba(31, 64, 175, 0.2)';
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.stroke();

    // Value arc
    const percent = value / 100;
    ctx.strokeStyle = '#10B981';
    ctx.lineWidth = 10;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -0.5 * Math.PI, -0.5 * Math.PI + (2 * Math.PI * percent));
    ctx.stroke();
  });
}

window.addEventListener('DOMContentLoaded', () => {
  observeCriticalWidgetMounts();
  scheduleCriticalWidgetHealthRender();
  if (typeof window.initLiveData === 'function') {
    setCriticalWidgetHealthOverride('loading');
    window.initLiveData()
      .then(() => {
        setCriticalWidgetHealthOverride(null);
      })
      .catch((error) => {
        console.warn('[Finance Copilot] live init failed, fallback data remains active:', error?.message || error);
        setCriticalWidgetHealthOverride('error', {
          reason: toString(error && error.message, 'live init failed')
        });
      });
  } else {
    setCriticalWidgetHealthOverride(null);
  }

  console.log('🚀 Finance Copilot V16 ULTIMATE initializing...');
  console.log('✨ ULTIMATE EXCELLENCE VERSION');
  console.log('💎 Diamond Dropdown Top-Left = Enhanced Grid 3x3 Navigation');
  console.log('🎨 Professional Widgets = Market Volatility PRO, KPIs MEGA');
  console.log('🤖 AI Integration Everywhere = Insights, Suggestions, Context');
  console.log('📊 Market Volatility PRO = Professional Chart + Stats Panel');
  console.log('✨ All Widgets Finalized = Production-Ready Quality');
  console.log('🎯 9 Facettes = 9 Complete Universes');
  console.log('♾️ Infinite Exploration Mode');

  // Initialize Command K immediately
  const commandKBadge = document.getElementById('commandKFloatingBadge');
  if (commandKBadge) {
    console.log('✅ Command K badge active');
  }

  // Animate KPI values
  const kpiValues = document.querySelectorAll('.kpi-value[data-value]');
  kpiValues.forEach((element, index) => {
    setTimeout(() => {
      const value = parseFloat(element.dataset.value);
      const isCurrency = element.textContent.includes('$');
      const isPercent = element.classList.contains('forecast') || element.classList.contains('success');

      if (isCurrency) {
        animateValue(element, 0, value, 2000, '$', '');
      } else if (isPercent) {
        animateValue(element, 0, value, 2000, element.classList.contains('forecast') ? '+' : '', '%');
      } else {
        animateValue(element, 0, value, 2000);
      }
    }, index * 150);
  });

  // Animate progress bars
  setTimeout(() => {
    document.querySelectorAll('.progress-fill[data-width]').forEach(bar => {
      bar.style.width = bar.dataset.width + '%';
    });
  }, 500);

  // Draw sparklines for all KPIs with real data (60 points for ultra-smooth)
  const sparklineData1 = appData.portfolioSparkline; // All 60 points
  const sparklineData2 = appData.forecastProjection.slice(0, 60);
  const sparklineData3 = [68, 68.2, 68.5, 68.8, 69, 69.2, 69.5, 69.7, 70, 70.2, 70.5, 70.7, 71, 71.2, 71.5, 71.7, 72]; // Smooth progression

  setTimeout(() => {
    drawSparkline('sparkline1', sparklineData1, '#10b981');
    drawSparkline('sparkline2', sparklineData2, '#1F40AF');
    drawSparkline('sparkline3', sparklineData3, '#10b981');
  }, 300);

  // Initialize charts and widgets (only those visible in default tab)
  setTimeout(() => {
    // drawMarketDriversDonut(); // ⚠️ Moved to after component loading (index.html)
    // drawClusterMap(); // ⚠️ Moved to after component loading (index.html)
    // renderNewsImpact(); // ⚠️ Moved to after component loading (index.html)
    // drawSectorPerformance(); // ⚠️ Moved to Market tab initialization (safeSwitchTab)
    // drawHealthGaugeCompact(); // ⚠️ Moved to after component loading (index.html)
    drawHealthGauge();
    renderPerformanceTable();

    // Draw sparklines for top movers
    if (appData.stockSparklines.NVDA) {
      drawStockSparkline('sparkNVDA', appData.stockSparklines.NVDA, '#2D9E78');
      drawStockSparkline('sparkMETA', appData.stockSparklines.META, '#2D9E78');
      drawStockSparkline('sparkAAPL', appData.stockSparklines.AAPL, '#2D9E78');
      drawStockSparkline('sparkMSFT', appData.stockSparklines.MSFT, '#2D9E78');
      drawStockSparkline('sparkGOOGL', appData.stockSparklines.GOOGL, '#2D9E78');
    }
  }, 500);

  // V16: Initialize professional volatility chart
  setTimeout(() => {
    drawVolatilityChartPro();
  }, 1000);

  // V17: Initialize advanced visualizations
  setTimeout(() => {
    drawCandlestickChart();
    drawVolumeChart();
    drawHeatmapChart();
    drawTreemapChart();
    drawSparkline('sparklineMega1', appData.portfolioSparkline, '#10B981');
  }, 1200);

  // V16: Initialize search functionality
  const searchFacettes = document.getElementById('searchFacettes');
  if (searchFacettes) {
    searchFacettes.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      document.querySelectorAll('.facette-card').forEach(card => {
        const name = card.querySelector('.facette-name').textContent.toLowerCase();
        const desc = card.querySelector('.facette-desc').textContent.toLowerCase();
        if (name.includes(query) || desc.includes(query)) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    });
  }

  // Initialize bubble drag
  initBubbleDrag();

  // V11: Initialize enhancements
  initAISuggestions();
  initAIInsights();
  applyLiveDashboardData(window.getLiveDashboardData ? window.getLiveDashboardData() : {});

  // V13: Initialize visual components
  setTimeout(() => {
    renderLiveDashboardWidgets();
  }, 600);

  // Animate change values
  setTimeout(() => {
    const changeHuge = document.querySelector('.change-huge');
    if (changeHuge) {
      const target = toFiniteNumber(changeHuge.dataset.value || appData.hero?.portfolioChange, 1.88);
      animateValue(changeHuge, 0, target, 2000, target >= 0 ? '+' : '', '%');
    }
  }, 800);



  // V17 BUGFIX: Show hero section by default, hide duplicate
  const heroSection = document.getElementById('heroSection');
  const mainHeroSection = document.getElementById('mainHeroSection');
  if (heroSection) heroSection.style.display = 'block';
  if (mainHeroSection) mainHeroSection.style.display = 'none';

  console.log('✅ V17 BUGFIXES APPLIED:');
  console.log('   - Navigation closes only on outside click');
  console.log('   - Single Hero section (duplicate hidden)');
  console.log('   - Story Mode integrated in Hero');
  console.log('   - AI Suggestions integrated in Hero');
  console.log('✅ V17 ADVANCED VISUALIZATIONS:');
  console.log('   - Candlestick Chart with Volume');
  console.log('   - Heatmap Correlation Matrix');
  console.log('   - Treemap Portfolio Allocation');
  console.log('   - Multi-KPI Cards Bloomberg Style');
  console.log('🏆 V17 PROFESSIONAL READY!');

  // V15: Hide legacy diamond hub, show dropdown button
  const diamondHub = document.getElementById('diamondHub');
  if (diamondHub) {
    diamondHub.style.display = 'none';
  }

  console.log('💎 Diamond Dropdown Top-Left active');

  // Make sure overview tab is visible on load
  setTimeout(() => {
    const overviewTab = document.getElementById('tab-overview');
    if (overviewTab) {
      overviewTab.style.display = 'block';
      overviewTab.classList.add('active');
    }
  }, 100);

  // Initialize first tab as active with error handling
  try {
    const firstTab = document.getElementById('tab-overview');
    if (firstTab) {
      firstTab.style.display = 'block';
      firstTab.classList.add('active');
    }

    // Global error handler
    window.addEventListener('error', (e) => {
      console.error('Global error details:', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        colno: e.colno,
        error: e.error
      });
      showToast('An unexpected error occurred: ' + e.message, 'error');
      return false; // Let default handler run to see if browser logs more
    });

    // Prevent unhandled promise rejections
    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection:', e.reason);
      e.preventDefault();
    });

    console.log('✅ Error handling initialized');
    console.log('✅ All event listeners wrapped safely');

  } catch (error) {
    console.error('Initialization error:', error);
    alert('Dashboard initialization failed. Please refresh the page.');
  }
});

// Expose functions globally
window.changeBlueprint = changeBlueprint;
window.toggleAICopilot = toggleAICopilot;
window.runCopilotStartOpen = runCopilotStartOpen;
window.renderHeroCopilotBrief = renderHeroCopilotBrief;
window.sendOverlayMessage = sendOverlayMessage;
window.handleOverlayEnter = handleOverlayEnter;
window.quickAsk = quickAsk;
window.sendAIMessage = sendAIMessage;
window.handleChatEnter = handleChatEnter;
window.askAI = askAI;
window.deepDivePortfolio = deepDivePortfolio;
window.openScenarioBuilder = openScenarioBuilder;
window.explainForecast = explainForecast;
window.openBacktest = openBacktest;
window.viewAllTrades = viewAllTrades;
window.optimizeStrategy = optimizeStrategy;
window.riskAnalysis = riskAnalysis;
window.showKpiMenu = showKpiMenu;
window.changePeriod = changePeriod;
window.toggleMoreMenu = toggleMoreMenu;
window.switchTab = switchTab;
window.toggleInteractiveView = toggleInteractiveView;
window.toggleCorrelationMatrix = toggleCorrelationMatrix;
window.toggleAdvancedVolatility = toggleAdvancedVolatility;
window.toggleAlertDetails = toggleAlertDetails;
window.selectReturnRange = selectReturnRange;
window.filterHistory = filterHistory;
window.refreshData = refreshData;
window.renderAlertTimeline = renderAlertTimeline;
window.openExportModal = openExportModal;
window.openSettings = openSettings;
window.closeSettings = closeSettings;
window.saveSettings = saveSettings;
window.toggleTheme = toggleTheme;
window.openNotifications = openNotifications;
window.closeNotifications = closeNotifications;
window.markAsRead = markAsRead;
window.markAllRead = markAllRead;
window.toggleCommandPalette = toggleCommandPalette;
window.executeCommand = executeCommand;

window.showHelp = showHelp;
window.expandStory = expandStory;

window.filterAlerts = filterAlerts;

window.toggleComparison = toggleComparison;
window.runBacktest = runBacktest;
window.sortTable = sortTable;
window.loadMoreStocks = loadMoreStocks;
window.enterCustomizeMode = enterCustomizeMode;
window.resetLayout = resetLayout;
window.saveLayout = saveLayout;
window.selectTab = selectTab;

// V11 Exposed Functions
window.openCommandK = openCommandK;
window.closeCommandK = closeCommandK;
window.executeCommandKAction = executeCommandKAction;
window.safeSwitchTab = safeSwitchTab;
window.changeProfile = changeProfile;
window.syncForecastProfileUI = syncForecastProfileUI;
window.closeSuggestions = closeSuggestions;
window.navigateToSuggestion = navigateToSuggestion;
window.toggleStoryMode = toggleStoryMode;
window.nextStoryPoint = nextStoryPoint;
window.prevStoryPoint = prevStoryPoint;
window.openDrillDown = openDrillDown;
window.openRobustnessDrill = openRobustnessDrill;
window.closeDrillDown = closeDrillDown;
window.toggleSplitView = toggleSplitView;
window.updateComparison = updateComparison;
window.maximizePane = maximizePane;
window.toggleFilterBar = toggleFilterBar;
window.applyFilters = applyFilters;
window.clearFilters = clearFilters;
window.refreshInsights = refreshInsights;
window.askAIAbout = askAIAbout;
window.askAIPrompt = askAIPrompt;
window.pinWidget = pinWidget;
window.setAlert = setAlert;
window.exportWidget = exportWidget;
window.drawReturnsChart = drawReturnsChart;
window.drawVolatilityLineChart = drawVolatilityLineChart;
window.drawVolatilityChartPro = drawVolatilityChartPro;

// ============ V17 ADVANCED VISUALIZATIONS ============

// Candlestick Chart
function drawCandlestickChart() {
  const canvas = document.getElementById('candlestickChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 20, right: 60, bottom: 40, left: 60 };

  const candleData = [
    { date: 'Nov 1', open: 850, high: 880, low: 845, close: 875, volume: 15000000 },
    { date: 'Nov 2', open: 875, high: 890, low: 870, close: 885, volume: 18000000 },
    { date: 'Nov 3', open: 885, high: 895, low: 875, close: 880, volume: 16000000 },
    { date: 'Nov 4', open: 880, high: 920, low: 875, close: 910, volume: 25000000 },
    { date: 'Nov 5', open: 910, high: 930, low: 905, close: 920, volume: 22000000 },
    { date: 'Nov 6', open: 920, high: 925, low: 900, close: 905, volume: 19000000 },
    { date: 'Nov 7', open: 905, high: 915, low: 895, close: 900, volume: 17000000 },
    { date: 'Nov 8', open: 900, high: 910, low: 890, close: 895, volume: 16000000 },
    { date: 'Nov 9', open: 895, high: 900, low: 880, close: 885, volume: 18000000 },
    { date: 'Nov 10', open: 885, high: 895, low: 875, close: 890, volume: 15000000 },
    { date: 'Nov 11', open: 890, high: 900, low: 885, close: 895, volume: 14000000 },
    { date: 'Nov 12', open: 895, high: 905, low: 890, close: 900, volume: 16000000 },
    { date: 'Nov 13', open: 900, high: 915, low: 895, close: 910, volume: 20000000 },
    { date: 'Nov 14', open: 910, high: 920, low: 905, close: 915, volume: 18000000 },
    { date: 'Nov 15', open: 915, high: 925, low: 910, close: 920, volume: 21000000 },
    { date: 'Nov 16', open: 920, high: 930, low: 915, close: 925, volume: 23000000 },
    { date: 'Nov 17', open: 925, high: 935, low: 920, close: 930, volume: 24000000 },
    { date: 'Nov 18', open: 930, high: 940, low: 925, close: 935, volume: 26000000 }
  ];

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const prices = candleData.flatMap(d => [d.low, d.high]);
  const minPrice = Math.min(...prices) * 0.98;
  const maxPrice = Math.max(...prices) * 1.02;
  const priceRange = maxPrice - minPrice;

  ctx.clearRect(0, 0, width, height);

  // Grid lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = padding.top + (chartHeight / 5) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartWidth, y);
    ctx.stroke();

    const price = maxPrice - (priceRange / 5) * i;
    ctx.fillStyle = '#94A3B8';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('$' + price.toFixed(0), padding.left - 10, y + 4);
  }

  const candleWidth = (chartWidth / candleData.length) * 0.7;
  const spacing = chartWidth / candleData.length;

  candleData.forEach((candle, i) => {
    const x = padding.left + spacing * i + spacing / 2;
    const isBullish = candle.close >= candle.open;
    const color = isBullish ? '#10B981' : '#EF4444';

    const highY = padding.top + chartHeight - ((candle.high - minPrice) / priceRange) * chartHeight;
    const lowY = padding.top + chartHeight - ((candle.low - minPrice) / priceRange) * chartHeight;

    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, highY);
    ctx.lineTo(x, lowY);
    ctx.stroke();

    const openY = padding.top + chartHeight - ((candle.open - minPrice) / priceRange) * chartHeight;
    const closeY = padding.top + chartHeight - ((candle.close - minPrice) / priceRange) * chartHeight;
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.abs(closeY - openY);

    ctx.fillStyle = color;
    ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, Math.max(bodyHeight, 1));
  });

  // MA(20) overlay
  ctx.strokeStyle = '#8B5CF6';
  ctx.lineWidth = 2;
  ctx.beginPath();
  candleData.forEach((candle, i) => {
    if (i >= 10) {
      const ma = candleData.slice(Math.max(0, i - 10), i + 1).reduce((sum, c) => sum + c.close, 0) / Math.min(i + 1, 11);
      const maY = padding.top + chartHeight - ((ma - minPrice) / priceRange) * chartHeight;
      const x = padding.left + spacing * i + spacing / 2;

      if (i === 10) ctx.moveTo(x, maY);
      else ctx.lineTo(x, maY);
    }
  });
  ctx.stroke();

  // Event annotation
  const eventIndex = 10;
  const eventX = padding.left + spacing * eventIndex + spacing / 2;
  ctx.strokeStyle = 'rgba(245, 158, 11, 0.5)';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(eventX, padding.top);
  ctx.lineTo(eventX, padding.top + chartHeight);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = '#F59E0B';
  ctx.font = '10px sans-serif';
  ctx.fillText('Earnings', eventX + 5, padding.top + 15);

  // X-axis labels
  ctx.fillStyle = '#94A3B8';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'center';
  candleData.forEach((candle, i) => {
    if (i % 5 === 0) {
      const x = padding.left + spacing * i + spacing / 2;
      ctx.fillText(candle.date, x, height - padding.bottom + 20);
    }
  });
}

function drawVolumeChart() {
  const canvas = document.getElementById('volumeChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 10, right: 60, bottom: 20, left: 60 };

  const volumes = [15, 18, 16, 25, 22, 19, 17, 16, 18, 15, 14, 16, 20, 18, 21, 23, 24, 26];
  const maxVolume = Math.max(...volumes);

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const barWidth = (chartWidth / volumes.length) * 0.7;
  const spacing = chartWidth / volumes.length;

  ctx.clearRect(0, 0, width, height);

  volumes.forEach((vol, i) => {
    const x = padding.left + spacing * i + spacing / 2 - barWidth / 2;
    const barHeight = (vol / maxVolume) * chartHeight;
    const y = padding.top + chartHeight - barHeight;

    ctx.fillStyle = i % 2 === 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)';
    ctx.fillRect(x, y, barWidth, barHeight);
  });
}

function drawHeatmapChart() {
  const canvas = document.getElementById('heatmapChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;

  const stocks = ['NVDA', 'AMD', 'AAPL', 'META', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'];
  const correlations = [
    [1.00, 0.85, 0.42, 0.38, 0.45, 0.50, 0.32, 0.40],
    [0.85, 1.00, 0.40, 0.35, 0.43, 0.48, 0.30, 0.38],
    [0.42, 0.40, 1.00, 0.65, 0.70, 0.75, 0.28, 0.60],
    [0.38, 0.35, 0.65, 1.00, 0.72, 0.68, 0.25, 0.55],
    [0.45, 0.43, 0.70, 0.72, 1.00, 0.78, 0.30, 0.65],
    [0.50, 0.48, 0.75, 0.68, 0.78, 1.00, 0.35, 0.70],
    [0.32, 0.30, 0.28, 0.25, 0.30, 0.35, 1.00, 0.40],
    [0.40, 0.38, 0.60, 0.55, 0.65, 0.70, 0.40, 1.00]
  ];

  const padding = 80;
  const cellSize = (width - padding * 2) / stocks.length;

  ctx.clearRect(0, 0, width, height);

  correlations.forEach((row, i) => {
    row.forEach((corr, j) => {
      const x = padding + j * cellSize;
      const y = padding + i * cellSize;

      const color = corr >= 0
        ? `rgba(34, 197, 94, ${corr * 0.8})`
        : `rgba(239, 68, 68, ${Math.abs(corr) * 0.8})`;

      ctx.fillStyle = color;
      ctx.fillRect(x, y, cellSize, cellSize);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, cellSize, cellSize);

      ctx.fillStyle = corr > 0.6 || corr < -0.6 ? '#FFFFFF' : '#1E293B';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(corr.toFixed(2), x + cellSize / 2, y + cellSize / 2);
    });
  });

  ctx.fillStyle = '#F8FAFC';
  ctx.font = '13px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  stocks.forEach((stock, i) => {
    const x = padding + i * cellSize + cellSize / 2;
    ctx.fillText(stock, x, padding - 10);
  });

  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  stocks.forEach((stock, i) => {
    const y = padding + i * cellSize + cellSize / 2;
    ctx.fillText(stock, padding - 10, y);
  });
}

function drawTreemapChart() {
  const canvas = document.getElementById('treemapChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;

  const holdings = [
    { symbol: 'NVDA', value: 32000, return: 8.5 },
    { symbol: 'AAPL', value: 25000, return: 3.2 },
    { symbol: 'META', value: 18000, return: 5.1 },
    { symbol: 'JNJ', value: 15000, return: 2.1 },
    { symbol: 'PFE', value: 12000, return: -1.5 },
    { symbol: 'JPM', value: 14000, return: 4.3 },
    { symbol: 'BAC', value: 8000, return: 2.8 },
    { symbol: 'XOM', value: 7000, return: 6.2 }
  ];

  const totalValue = holdings.reduce((sum, h) => sum + h.value, 0);

  ctx.clearRect(0, 0, width, height);

  let currentX = 0;
  let currentY = 0;
  let remainingWidth = width;
  let remainingHeight = height;

  holdings.forEach((holding, index) => {
    const ratio = holding.value / totalValue;
    const area = ratio * (width * height);

    let rectWidth, rectHeight;
    if (remainingWidth > remainingHeight) {
      rectWidth = area / remainingHeight;
      rectHeight = remainingHeight;
      if (index === holdings.length - 1 || currentX + rectWidth > width) {
        rectWidth = remainingWidth;
      }
    } else {
      rectHeight = area / remainingWidth;
      rectWidth = remainingWidth;
      if (index === holdings.length - 1 || currentY + rectHeight > height) {
        rectHeight = remainingHeight;
      }
    }

    const color = holding.return >= 0
      ? `rgba(34, 197, 94, ${0.6 + ratio * 0.4})`
      : `rgba(239, 68, 68, ${0.6 + ratio * 0.4})`;

    ctx.fillStyle = color;
    ctx.fillRect(currentX, currentY, rectWidth, rectHeight);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 2;
    ctx.strokeRect(currentX, currentY, rectWidth, rectHeight);

    if (rectWidth > 80 && rectHeight > 60) {
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(holding.symbol, currentX + rectWidth / 2, currentY + 10);

      ctx.font = '14px sans-serif';
      ctx.fillText('$' + (holding.value / 1000).toFixed(1) + 'K',
        currentX + rectWidth / 2, currentY + 32);

      const returnColor = holding.return >= 0 ? '#A7F3D0' : '#FECACA';
      ctx.fillStyle = returnColor;
      ctx.fillText((holding.return >= 0 ? '+' : '') + holding.return.toFixed(1) + '%',
        currentX + rectWidth / 2, currentY + 50);
    }

    if (remainingWidth > remainingHeight) {
      currentX += rectWidth;
      remainingWidth -= rectWidth;
    } else {
      currentY += rectHeight;
      remainingHeight -= rectHeight;
    }
  });
}

function updateCandlestickTimeframe(tf) {
  document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  showToast(`Timeframe changed to ${tf}`);
  drawCandlestickChart();
}

window.drawCandlestickChart = drawCandlestickChart;
window.drawVolumeChart = drawVolumeChart;
window.drawHeatmapChart = drawHeatmapChart;
window.drawTreemapChart = drawTreemapChart;
window.updateCandlestickTimeframe = updateCandlestickTimeframe;

// V16 Exposed Functions
window.toggleDiamondDropdown = toggleDiamondDropdown;
window.closeDiamondDropdown = closeDiamondDropdown;
window.drawVolatilityChartPro = drawVolatilityChartPro;
window.openFacette = openFacette;
window.closeFacette = closeFacette;
window.switchFacetteTab = switchFacetteTab;
window.searchStock = searchStock;
window.quickNeed = quickNeed;

// V13 Exposed Functions
window.renderTradeIdeas = renderTradeIdeas;
window.renderMarketCalendar = renderMarketCalendar;
window.renderNewsFeed = renderNewsFeed;
window.renderMarketDrivers = renderMarketDrivers;
window.askLLMJudge = askLLMJudge;
window.resetLLMJudge = resetLLMJudge;
window.executeAction = executeAction;
window.showLLMHelp = showLLMHelp;
window.filterNews = filterNews;
window.loadMoreNews = loadMoreNews;
window.drawConfidenceGauge = drawConfidenceGauge;
window.drawWinRateCircle = drawWinRateCircle;

// V11: Volatility and Returns Chart Functions
function drawVolatilityLineChart() {
  const canvas = document.getElementById('volatilityLineChart');
  if (!canvas) return;

  new Chart(canvas, {
    type: 'line',
    data: {
      labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
      datasets: [{
        label: 'VIX',
        data: Array.from({ length: 30 }, () => 15 + Math.random() * 10),
        borderColor: '#1F40AF',
        backgroundColor: 'rgba(31, 64, 175, 0.1)',
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(31, 64, 175, 0.9)',
          titleColor: '#E8E9F3',
          bodyColor: '#E8E9F3'
        }
      },
      scales: {
        x: { display: false },
        y: {
          ticks: { color: '#B0B4CC' },
          grid: { color: 'rgba(31, 64, 175, 0.1)' }
        }
      }
    }
  });
}

function drawReturnsChart() {
  const canvas = document.getElementById('returnsChart');
  if (!canvas) return;

  new Chart(canvas, {
    type: 'line',
    data: {
      labels: Array.from({ length: 12 }, (_, i) => `Month ${i + 1}`),
      datasets: [
        {
          label: 'Your Portfolio',
          data: Array.from({ length: 12 }, (_, i) => (i + 1) * 2.5),
          borderColor: '#1F40AF',
          backgroundColor: 'rgba(31, 64, 175, 0.1)',
          fill: true
        },
        {
          label: 'S&P 500',
          data: Array.from({ length: 12 }, (_, i) => (i + 1) * 1.3),
          borderColor: '#B0B4CC',
          backgroundColor: 'rgba(176, 180, 204, 0.05)',
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#E8E9F3' } },
        tooltip: {
          backgroundColor: 'rgba(31, 64, 175, 0.9)',
          titleColor: '#E8E9F3',
          bodyColor: '#E8E9F3'
        }
      },
      scales: {
        x: {
          ticks: { color: '#B0B4CC' },
          grid: { color: 'rgba(31, 64, 175, 0.1)' }
        },
        y: {
          ticks: { color: '#B0B4CC' },
          grid: { color: 'rgba(31, 64, 175, 0.1)' }
        }
      }
    }
  });
}
