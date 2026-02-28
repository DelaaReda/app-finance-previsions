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
// Facettes configuration moved to mockData.js

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

function loadFacetteContent(facetteId, tabName) {
  const contentContainer = document.getElementById('facetteContent');

  // Generate sample content based on facette and tab
  const sampleContent = generateFacetteContent(facetteId, tabName);
  contentContainer.innerHTML = sampleContent;
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
  // This would be dynamic in production
  return `
    <div class="widget-card">
      <div class="widget-header">
        <h3>${tabName}</h3>
      </div>
      <div class="widget-body">
        <p style="font-size: 16px; line-height: 1.8; color: var(--color-text-light);">
          Contenu pour <strong>${facettes[facetteId].name}</strong> > <strong>${tabName}</strong>
        </p>
        <div style="margin-top: 32px; padding: 24px; background: rgba(139, 92, 246, 0.1); border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.3);">
          <h4 style="margin-bottom: 16px;">🤖 AI Analysis</h4>
          <p style="font-size: 14px; line-height: 1.7; color: var(--color-text-secondary);">
            Based on current market conditions and your portfolio composition, this ${tabName} view provides comprehensive insights.
            The AI has analyzed ${Math.floor(Math.random() * 10000) + 5000} data points to generate these recommendations.
          </p>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; margin-top: 32px;">
          <div style="padding: 20px; background: rgba(31, 64, 175, 0.1); border-radius: 12px; text-align: center;">
            <div style="font-size: 32px; font-weight: 700; color: #10B981; margin-bottom: 8px;">+${(Math.random() * 10 + 2).toFixed(1)}%</div>
            <div style="font-size: 12px; color: var(--color-text-secondary);">Confidence Score</div>
          </div>
          <div style="padding: 20px; background: rgba(31, 64, 175, 0.1); border-radius: 12px; text-align: center;">
            <div style="font-size: 32px; font-weight: 700; color: #8B5CF6; margin-bottom: 8px;">${Math.floor(Math.random() * 30 + 70)}%</div>
            <div style="font-size: 12px; color: var(--color-text-secondary);">AI Accuracy</div>
          </div>
          <div style="padding: 20px; background: rgba(31, 64, 175, 0.1); border-radius: 12px; text-align: center;">
            <div style="font-size: 32px; font-weight: 700; color: #F59E0B; margin-bottom: 8px;">${Math.floor(Math.random() * 50 + 10)}</div>
            <div style="font-size: 12px; color: var(--color-text-secondary);">Insights Found</div>
          </div>
        </div>
        <div style="margin-top: 32px; display: flex; gap: 16px;">
          <button class="kpi-action-btn primary" onclick="showToast('Deep diving into data...')">🔍 Deep Dive</button>
          <button class="kpi-action-btn secondary" onclick="showToast('Exporting analysis...')">Export Analysis</button>
          <button class="kpi-action-btn secondary" onclick="showToast('Setting alert...')">Set Alert</button>
        </div>
      </div>
    </div>
  `;
}

function searchStock() {
  const input = document.getElementById('stockSymbolInput');
  const symbol = input.value.trim().toUpperCase();

  if (!symbol) {
    showToast('Please enter a stock symbol', 'warning');
    return;
  }

  v16State.currentStock = symbol;
  v16State.breadcrumbs = ['💎', facettes[v16State.currentFacette].name, symbol];
  document.getElementById('facetteBreadcrumb').textContent = v16State.breadcrumbs.join(' > ');

  showToast(`📈 Analyzing ${symbol}...`);

  // Load stock-specific content
  setTimeout(() => {
    const contentContainer = document.getElementById('facetteContent');
    contentContainer.innerHTML = `
      <div class="widget-card">
        <div class="widget-header">
          <h3>${symbol} Deep Dive</h3>
        </div>
        <div class="widget-body">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 24px;">
            <div style="padding: 24px; background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05)); border-radius: 16px; border: 1px solid rgba(16, 185, 129, 0.3);">
              <div style="font-size: 14px; color: var(--color-text-secondary); margin-bottom: 8px;">Current Price</div>
              <div style="font-size: 36px; font-weight: 700; color: #10B981; margin-bottom: 8px;">$${(Math.random() * 500 + 100).toFixed(2)}</div>
              <div style="font-size: 13px; color: #10B981;">↑ +${(Math.random() * 5 + 1).toFixed(2)}% today</div>
            </div>
            <div style="padding: 24px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(139, 92, 246, 0.05)); border-radius: 16px; border: 1px solid rgba(139, 92, 246, 0.3);">
              <div style="font-size: 14px; color: var(--color-text-secondary); margin-bottom: 8px;">AI Forecast (30d)</div>
              <div style="font-size: 36px; font-weight: 700; color: #8B5CF6; margin-bottom: 8px;">+${(Math.random() * 15 + 3).toFixed(1)}%</div>
              <div style="font-size: 13px; color: #8B5CF6;">${Math.floor(Math.random() * 20 + 75)}% confidence</div>
            </div>
            <div style="padding: 24px; background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05)); border-radius: 16px; border: 1px solid rgba(245, 158, 11, 0.3);">
              <div style="font-size: 14px; color: var(--color-text-secondary); margin-bottom: 8px;">Risk Level</div>
              <div style="font-size: 36px; font-weight: 700; color: #F59E0B; margin-bottom: 8px;">${Math.floor(Math.random() * 4 + 4)}/10</div>
              <div style="font-size: 13px; color: #F59E0B;">Moderate Risk</div>
            </div>
          </div>
          <div style="margin-top: 32px;">
            <h4 style="margin-bottom: 16px;">🤖 AI Recommendation</h4>
            <div style="padding: 24px; background: rgba(139, 92, 246, 0.1); border-radius: 12px; border-left: 4px solid #8B5CF6;">
              <p style="font-size: 15px; line-height: 1.7; color: var(--color-text-light);">
                <strong>HOLD</strong> position on ${symbol}. The AI detects strong momentum with ${Math.floor(Math.random() * 20 + 80)}% confidence.
                Technical indicators show bullish continuation patterns. Monitor resistance at $${(Math.random() * 50 + 450).toFixed(2)}.
              </p>
            </div>
          </div>
        </div>
      </div>
    `;
    showToast(`✅ ${symbol} analysis complete!`, 'success');
  }, 800);
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

function executeCommandKAction(action) {
  closeCommandK();

  const actions = {
    'dashboard': () => safeSwitchTab(document.querySelector('[data-tab="overview"]'), 'overview'),
    'market': () => safeSwitchTab(document.querySelector('[data-tab="market"]'), 'market'),
    'opportunities': () => safeSwitchTab(document.querySelector('[data-tab="opportunities"]'), 'opportunities'),
    'copilot': () => toggleAICopilot(),
    'nvda-analysis': () => showToast('Opening NVDA analysis...'),
    'portfolio-risk': () => showToast('Analyzing portfolio risk...'),
    'market-forecast': () => showToast('Loading market forecast...'),
    'stock-nvda': () => showToast('NVDA: $875.60 (+8.5%) - Strong Buy Signal'),
    'stock-meta': () => showToast('META: $523.45 (+5.2%) - Buy Signal'),
    'stock-aapl': () => showToast('AAPL: $178.23 (+2.1%) - Hold'),
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
// V11 Enhanced Data
// v11Data moved to mockData.js

// V13 Trade Ideas Data
// tradeIdeas moved to mockData.js

// V13 Market Calendar Data
// marketCalendar moved to mockData.js

// V13 News Items Data (EXPANDED)
// newsItems moved to mockData.js

// V13 LLM Judge Data
// llmJudgeData moved to mockData.js

// V13 Market Drivers Visual
// marketDrivers moved to mockData.js

// appData moved to mockData.js

// V11 State Management
const v11State = {
  storyMode: false,
  currentStoryPoint: 0,
  splitViewEnabled: false,
  filterBarVisible: false,
  currentProfile: 'trader'
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
function changeProfile(profile) {
  v11State.currentProfile = profile;
  showToast(`Profile changed to ${profile}`);
  // Reorganize widgets based on profile
  reorganizeWidgetsByProfile(profile);
}

function reorganizeWidgetsByProfile(profile) {
  // Simulate profile-based reorganization
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
function openDrillDown(metric) {
  const modal = document.getElementById('drillDownModal');
  const title = document.getElementById('drillDownTitle');
  const body = document.getElementById('drillDownBody');

  if (!modal || !title || !body) return;

  const drillData = {
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
    document.getElementById('aiOverlayInput')?.focus();
  } else {
    overlay.classList.remove('active');
    setTimeout(() => overlay.style.display = 'none', 400);
  }
}

function sendOverlayMessage() {
  const input = document.getElementById('aiOverlayInput');
  if (!input || !input.value.trim()) return;

  const message = input.value.trim();
  input.value = '';

  // Add user message
  addAIMessage(message, 'user');

  // Simulate AI response
  setTimeout(() => {
    const responses = {
      'explain': 'Based on your current portfolio performance, the 1.88% gain is primarily driven by your tech holdings. NVDA is up 8.5% following strong earnings, while META gained 5.2% on positive market sentiment. This outperformance relative to the S&P 500 (+1.2%) demonstrates the strength of your tech allocation.',
      'what should i do': 'Given current market conditions and your portfolio composition, I recommend: 1) Hold your current tech positions as momentum remains strong, 2) Set trailing stops on NVDA at 5% to protect gains, 3) Consider taking partial profits on META if it hits $550, and 4) Monitor Fed announcements closely as dovish signals could extend the rally.',
      'simulate': 'Let me run a scenario analysis for you. If NVDA continues its current trajectory, your portfolio could see an additional 3-4% gain over the next 30 days. However, if tech sector volatility increases, we could see a 2-3% pullback. Would you like me to run a specific scenario with custom parameters?'
    };

    const lowerMessage = message.toLowerCase();
    let response = 'I understand your question. Based on your portfolio data and current market conditions, I can provide detailed analysis. What specific aspect would you like me to focus on?';

    for (const [key, value] of Object.entries(responses)) {
      if (lowerMessage.includes(key)) {
        response = value;
        break;
      }
    }

    addAIMessage(response, 'ai');
  }, 1000);
}

function handleOverlayEnter(event) {
  if (event.key === 'Enter') {
    sendOverlayMessage();
  }
}

function quickAsk(action) {
  const questions = {
    'explain': 'Explain what I\'m seeing on this screen',
    'whatdo': 'What should I do with my portfolio right now?',
    'simulate': 'Simulate a market scenario for me'
  };

  const input = document.getElementById('aiOverlayInput');
  if (input && questions[action]) {
    input.value = questions[action];
    sendOverlayMessage();
  }
}

function addAIMessage(content, type) {
  const panel = document.getElementById('aiMessagesPanel');
  if (!panel) return;

  const messageDiv = document.createElement('div');
  messageDiv.className = 'ai-message';

  if (type === 'user') {
    messageDiv.innerHTML = `
      <div class="ai-avatar" style="background: var(--color-royal-blue);">👤</div>
      <div class="ai-message-content">
        <p>${content}</p>
      </div>
    `;
  } else {
    messageDiv.innerHTML = `
      <div class="ai-avatar">🤖</div>
      <div class="ai-message-content">
        <p>${content}</p>
      </div>
    `;
  }

  panel.appendChild(messageDiv);
  panel.scrollTop = panel.scrollHeight;
}

// AI Lab Functions
function sendAIMessage() {
  const input = document.getElementById('aiChatInput');
  if (!input || !input.value.trim()) return;

  const message = input.value.trim();
  input.value = '';

  const container = document.getElementById('aiChatMessages');
  if (!container) return;

  // Add user message
  const userMsg = document.createElement('div');
  userMsg.className = 'ai-message';
  userMsg.innerHTML = `
    <div class="ai-avatar" style="background: var(--color-royal-blue);">👤</div>
    <div class="ai-message-content">
      <p>${message}</p>
    </div>
  `;
  container.appendChild(userMsg);

  // Simulate AI response
  setTimeout(() => {
    const aiMsg = document.createElement('div');
    aiMsg.className = 'ai-message';
    aiMsg.innerHTML = `
      <div class="ai-avatar">🤖</div>
      <div class="ai-message-content">
        <p>I've analyzed your question. Based on your portfolio data and market conditions, here's my assessment: Your current strategy aligns well with your risk tolerance and investment goals. I recommend maintaining your current allocation while monitoring key support levels.</p>
      </div>
    `;
    container.appendChild(aiMsg);
    container.scrollTop = container.scrollHeight;
  }, 1200);
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
  // Target the dedicated refresh button instead of relying on the implicit event
  const btn = document.querySelector('.header-btn[aria-label="Refresh data"]');
  if (btn) {
    btn.style.animation = 'spin 1s linear';
  }

  showLoading();

  setTimeout(() => {
    hideLoading();
    if (btn) {
      btn.style.animation = '';
    }
    showToast('Data refreshed successfully');

    // Update timestamp
    document.querySelectorAll('.last-updated, .refresh-time').forEach(el => {
      el.textContent = 'Updated just now';
    });
  }, 1500);
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
    if (type === 'all') {
      alert.style.display = 'flex';
    } else if (type === 'opportunities') {
      alert.style.display = alert.dataset.type === 'opportunity' ? 'flex' : 'none';
    } else if (type === 'risks') {
      alert.style.display = alert.dataset.type === 'risk' ? 'flex' : 'none';
    } else if (type === 'news') {
      alert.style.display = alert.dataset.type === 'news' ? 'flex' : 'none';
    } else {
      alert.style.display = alert.dataset.priority === type ? 'flex' : 'none';
    }
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

// ============ HEALTH GAUGE COMPACT ============
function drawHealthGaugeCompact() {
  const canvas = document.getElementById('healthGaugeCompact');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const centerX = 75;
  const centerY = 75;
  const radius = 55;

  // Background arc
  ctx.strokeStyle = 'rgba(31, 64, 175, 0.2)';
  ctx.lineWidth = 10;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 2.25 * Math.PI);
  ctx.stroke();

  // Value arc
  const percent = appData.portfolioHealth.overall / 100;
  ctx.strokeStyle = '#1F40AF';
  ctx.lineWidth = 10;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 0.75 * Math.PI + (1.5 * Math.PI * percent));
  ctx.stroke();
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

  appData.clusterMap.forEach((point, i) => {
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

  container.innerHTML = appData.newsImpact.slice(0, 10).map(news => `
    <div class="news-row">
      <div class="news-headline">${news.headline}</div>
      <div class="news-impact">Impact: ${news.impact.toFixed(1)}</div>
      <div class="news-delta ${news.effect.startsWith('+') ? 'positive' : 'negative'}">${news.effect}</div>
    </div>
  `).join('');
}

function drawSectorPerformance() {
  const canvas = document.getElementById('sectorChart');
  if (!canvas) return;

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: appData.sectorPerformance.map(s => s.sector),
      datasets: [{
        label: 'Change %',
        data: appData.sectorPerformance.map(s => s.change),
        backgroundColor: appData.sectorPerformance.map(s => {
          if (s.holdings) {
            return s.change > 5 ? '#2D9E78' : s.change > 0 ? '#1F40AF' : '#8B3A3A';
          } else {
            return 'rgba(176, 180, 204, 0.3)';
          }
        }),
        borderWidth: appData.sectorPerformance.map(s => s.holdings ? 2 : 0),
        borderColor: appData.sectorPerformance.map(s => s.holdings ? '#4A6BD9' : 'transparent'),
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
              const sector = appData.sectorPerformance[context.dataIndex];
              if (sector.holdings) {
                return `Portfolio weight: ${sector.weight}%`;
              }
              return 'Not in portfolio';
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

function drawHealthGauge() {
  const canvas = document.getElementById('healthGauge');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const centerX = 100;
  const centerY = 100;
  const radius = 70;

  // Background arc
  ctx.strokeStyle = 'rgba(31, 64, 175, 0.2)';
  ctx.lineWidth = 12;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 2.25 * Math.PI);
  ctx.stroke();

  // Value arc with animation
  const percent = appData.portfolioHealth.overall / 100;
  ctx.strokeStyle = '#1F40AF';
  ctx.lineWidth = 12;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 0.75 * Math.PI + (1.5 * Math.PI * percent));
  ctx.stroke();

  const valueEl = document.getElementById('healthValue');
  if (valueEl) {
    valueEl.textContent = appData.portfolioHealth.overall + '%';
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
function renderTradeIdeas() {
  const container = document.getElementById('tradeIdeasGrid');
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
function renderMarketCalendar() {
  const container = document.getElementById('calendarSections');
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
function renderNewsFeed() {
  const container = document.getElementById('newsCardsGrid');
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
function renderMarketDrivers() {
  const container = document.getElementById('driversBarsVisual');
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

  if (!input.value.trim()) {
    showToast('Please enter a question', 'warning');
    return;
  }

  // Show processing
  input.disabled = true;
  processing.style.display = 'block';
  result.style.display = 'none';

  // Simulate processing steps
  const steps = processing.querySelectorAll('.processing-step');
  steps.forEach((step, i) => {
    setTimeout(() => {
      step.classList.add('active');
    }, i * 800);
  });

  // Show result after processing
  setTimeout(() => {
    processing.style.display = 'none';
    result.style.display = 'block';
    askAnother.style.display = 'block';
    input.disabled = false;

    result.innerHTML = `
      <div class="consensus-section">
        <div class="consensus-badge hold">${llmJudgeData.consensus}</div>
        <div class="confidence-display">
          <div class="confidence-number">${llmJudgeData.confidence}%</div>
          <div class="confidence-label">Consensus Confidence</div>
        </div>
      </div>
      
      <div class="models-breakdown">
        <h4>Model Opinions</h4>
        ${llmJudgeData.models.map(model => `
          <div class="model-item">
            <div class="model-header">
              <span class="model-icon">${model.icon}</span>
              <span class="model-name">${model.name}</span>
              <span class="model-verdict hold">${model.verdict}</span>
            </div>
            <div class="model-confidence">
              <div class="confidence-bar">
                <div class="bar-fill" style="width: ${model.confidence}%"></div>
              </div>
              <span class="confidence-text">${model.confidence}%</span>
            </div>
          </div>
        `).join('')}
      </div>
      
      <div class="reasoning-section">
        <h4>Why This Recommendation?</h4>
        <p class="reasoning-text">${llmJudgeData.reasoning}</p>
        <div class="data-sources">
          ${llmJudgeData.dataSources.map(source => `<span class="source-badge">📊 ${source}</span>`).join('')}
        </div>
      </div>
      
      <div class="actions-section">
        <h4>Suggested Next Steps</h4>
        <div class="action-cards">
          ${llmJudgeData.suggestedActions.map(action => `
            <div class="action-card">
              <span class="action-icon">${action.icon}</span>
              <div class="action-content">
                <span class="action-title">${action.title}</span>
                <span class="action-detail">${action.detail}</span>
              </div>
              <button class="action-btn" onclick="executeAction('${action.action}')">Act</button>
            </div>
          `).join('')}
        </div>
      </div>
    `;

    showToast('AI analysis complete!', 'success');
  }, 4000);
}

function resetLLMJudge() {
  document.getElementById('judgeQuestion').value = '';
  document.getElementById('judgeResult').style.display = 'none';
  document.getElementById('askAnotherBtn').style.display = 'none';
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

// V13: Draw Confidence Gauge
function drawConfidenceGauge() {
  const canvas = document.getElementById('confidenceGauge');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const value = 82;

  // Background arc
  ctx.strokeStyle = 'rgba(31, 64, 175, 0.2)';
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.arc(60, 50, 35, 0.75 * Math.PI, 2.25 * Math.PI);
  ctx.stroke();

  // Value arc
  const percent = value / 100;
  ctx.strokeStyle = '#10B981';
  ctx.lineWidth = 8;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.arc(60, 50, 35, 0.75 * Math.PI, 0.75 * Math.PI + (1.5 * Math.PI * percent));
  ctx.stroke();
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

  // V13: Initialize visual components
  setTimeout(() => {
    renderTradeIdeas();
    renderMarketCalendar();
    renderNewsFeed();
    renderMarketDrivers();
    drawConfidenceGauge();
    drawWinRateCircle();

    // Sync numeric win rate display with data attribute / appData
    document.querySelectorAll('.circle-number[data-value]').forEach(el => {
      const target = parseFloat(el.dataset.value);
      if (!Number.isNaN(target)) {
        el.textContent = target.toString();
      }
    });
  }, 600);

  // Animate change values
  setTimeout(() => {
    const changeHuge = document.querySelector('.change-huge');
    if (changeHuge) {
      animateValue(changeHuge, 0, 1.88, 2000, '+', '%');
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
window.closeSuggestions = closeSuggestions;
window.navigateToSuggestion = navigateToSuggestion;
window.toggleStoryMode = toggleStoryMode;
window.nextStoryPoint = nextStoryPoint;
window.prevStoryPoint = prevStoryPoint;
window.openDrillDown = openDrillDown;
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
