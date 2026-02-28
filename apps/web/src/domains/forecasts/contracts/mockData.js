// ============================================================================
// FINANCE COPILOT MOCK DATA
// This file contains all the mock data used by the application.
// In the future, this data will be replaced by API calls to the Python backend.
// ============================================================================

// Diamond Facettes Configuration
let facettes = {
    'deep-dive': {
        icon: '📈',
        name: 'Deep Dive Action',
        color: '#3B82F6',
        needsSearch: true,
        tabs: ['Synthèse', 'Prévisions', 'Risques', 'Signaux Techniques', 'Actualités', 'Copilot']
    },
    'economie': {
        icon: '🌍',
        name: 'Économie Globale',
        color: '#10B981',
        needsSearch: false,
        tabs: ['Marché', 'Macro Économie', 'Prévisions', 'News Économiques', 'Copilot Macro']
    },
    'news': {
        icon: '📰',
        name: 'News Impactantes',
        color: '#F59E0B',
        needsSearch: false,
        tabs: ['Toutes les News', 'High Impact', 'Mes Holdings', 'Par Secteur']
    },
    'previsions': {
        icon: '🔮',
        name: 'Prévisions AI',
        color: '#8B5CF6',
        needsSearch: false,
        tabs: ['Portfolio', 'Marché Général', 'Secteurs', 'Actions Suivies']
    },
    'risques': {
        icon: '🚦',
        name: 'Risques & Signaux',
        color: '#EF4444',
        needsSearch: false,
        tabs: ['Alertes Actives', 'Risk Dashboard', 'Anomalies Détectées', 'Monitoring']
    },
    'copilot': {
        icon: '🤖',
        name: 'Copilot Q&A',
        color: '#14B8A6',
        needsSearch: false,
        tabs: ['Chat Global', 'Questions Fréquentes', 'Historique', 'Suggestions']
    },
    'trading': {
        icon: '💹',
        name: 'Opportunités Trading',
        color: '#FCD34D',
        needsSearch: false,
        tabs: ['Trade Ideas', 'Backtests', 'Scenarios', 'Exécution']
    },
    'portfolio': {
        icon: '🗂️',
        name: 'Portfolio Analytics',
        color: '#6366F1',
        needsSearch: false,
        tabs: ['Vue d’Ensemble', 'Performance', 'Holdings', 'Attribution', 'Dividendes']
    },
    'explorer': {
        icon: '🗺️',
        name: 'Explorer Avancé',
        color: '#EC4899',
        needsSearch: false,
        tabs: ['Corrélations', 'Clustering', 'Patterns', 'Heatmaps', 'Network Graph']
    }
};

// V11 Enhanced Data
let v11Data = {
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
        { type: 'check', title: 'Check Risk Concentration Alert', priority: 'high', widget: 'Risk Alerts', tab: 'Opportunities', timestamp: '2 min ago' },
        { type: 'view', title: "You haven't viewed Sector Performance today", priority: 'medium', widget: 'Sector Performance', tab: 'Market Intel', timestamp: 'Today' },
        { type: 'action', title: 'NVDA signal 92% confidence - Act Now', priority: 'high', widget: 'Trade Ideas', tab: 'Opportunities', timestamp: '2h ago' }
    ],
    storyPoints: {
        overview: [
            { step: 1, title: 'Portfolio Performance', description: 'Your portfolio is up 1.88% today, driven by tech sector rally. NVDA (+8.5%) and META (+5.2%) are your top performers.', widget: 'Hero KPIs', highlight: 'portfolioValue' },
            { step: 2, title: 'AI Forecast', description: 'AI predicts +5.3% growth next 30 days with 82% confidence, based on Fed dovish signals and earnings momentum.', widget: 'Hero KPIs', highlight: 'forecast' },
            { step: 3, title: 'Market Drivers', description: 'Technical signals (40%) and market sentiment (35%) are main drivers today. Fed policy impact moderate.', widget: 'Market Drivers' },
            { step: 4, title: 'Recommended Action', description: 'Hold current positions. Set alerts on NVDA resistance at $880 and META at $530.', widget: 'Priority Actions' }
        ]
    },
    aiInsights: {
        overview: [
            { type: 'positive', icon: '📈', title: 'Tech exposure increased', description: 'Your tech holdings grew 5% this week, now 45% of portfolio', severity: 'info', action: 'View Holdings' },
            { type: 'positive', icon: '🎯', title: 'Win rate improving', description: '+2.3% vs last month, now 72% (above target 70%)', severity: 'success', action: 'View Performance' },
            { type: 'neutral', icon: '⚖️', title: 'Risk level moderate', description: '6/10 risk score, portfolio volatility stable', severity: 'info', action: 'View Risk' }
        ],
        opportunities: [
            { type: 'opportunity', icon: '💎', title: 'Healthcare undervalued', description: 'Sector 12% below historical average, AI confidence 78%', severity: 'info', action: 'Explore' }
        ]
    },
    anomalies: [
        { widget: 'Volatility Tracker', severity: 'medium', title: 'Volatility Spike Detected', description: 'VIX jumped 15% in last hour, unusual for this time of day', timestamp: '10 min ago', dismissed: false },
        { widget: 'Holdings Table', severity: 'low', title: 'TSLA Underperforming', description: 'TSLA down 12% while tech sector up 8.5%, correlation breakdown', timestamp: '2h ago', dismissed: false }
    ],
    splitView: { enabled: false, leftPane: 'current', rightPane: 'october', syncScroll: true },
    filters: {
        timePeriod: { start: '2025-10-18', end: '2025-11-18' },
        assetClasses: ['stocks'],
        riskLevel: { min: 0, max: 10 },
        confidenceThreshold: 70,
        tags: ['tech', 'growth'],
        performanceRange: { min: -100, max: 100 }
    }
};

// V13 Trade Ideas Data
let tradeIdeas = [
    { symbol: 'NVDA', signalType: 'Breakout', entry: 875, target: 980, confidence: 92 },
    { symbol: 'META', signalType: 'Reversal', entry: 520, target: 565, confidence: 85 },
    { symbol: 'AAPL', signalType: 'Value', entry: 178, target: 185, confidence: 78 },
    { symbol: 'MSFT', signalType: 'Momentum', entry: 413, target: 435, confidence: 75 },
    { symbol: 'GOOGL', signalType: 'Breakout', entry: 143, target: 155, confidence: 72 }
];

// V13 Market Calendar Data
let marketCalendar = {
    earnings: [
        { stock: 'NVDA', date: 'Nov 20', impact: 'High', holding: true },
        { stock: 'META', date: 'Nov 22', impact: 'High', holding: true },
        { stock: 'AAPL', date: 'Nov 24', impact: 'Medium', holding: true }
    ],
    economicData: [
        { event: 'Fed Minutes', date: 'Nov 21', impact: 'High' },
        { event: 'CPI Report', date: 'Nov 23', impact: 'High' }
    ],
    exDividend: [
        { stock: 'MSFT', date: 'Nov 19', amount: 0.68 }
    ]
};

// V13 News Items Data (EXPANDED)
let newsItems = [
    { headline: 'Fed Signals Rate Cuts Q2', impact: 8.5, effect: '+3.2%', time: '2h ago', source: 'Reuters', category: 'Macro' },
    { headline: 'NVDA Earnings Beat Expectations', impact: 9.2, effect: '+5.1%', time: '4h ago', source: 'Bloomberg', category: 'Earnings' },
    { headline: 'Tech Sector Volatility Spike', impact: 6.2, effect: '-2.3%', time: '6h ago', source: 'WSJ', category: 'Sector' },
    { headline: 'CPI Data Shows Inflation Cooling', impact: 7.8, effect: '+2.8%', time: '8h ago', source: 'CNBC', category: 'Macro' },
    { headline: 'China Economic Growth Slows', impact: 5.5, effect: '-1.5%', time: '10h ago', source: 'FT', category: 'Global' }
];

// V13 LLM Judge Data
let llmJudgeData = {
    question: 'What should I do with my portfolio today?',
    consensus: 'HOLD POSITIONS',
    confidence: 87,
    models: [
        { name: 'GPT-5', verdict: 'Hold', confidence: 85, icon: '🤖' },
        { name: 'Claude', verdict: 'Hold', confidence: 90, icon: '🧠' },
        { name: 'Gemini', verdict: 'Hold', confidence: 86, icon: '💎' }
    ],
    reasoning: 'Tech rally remains strong with Fed dovish signals supporting momentum. Your portfolio is well-positioned with 45% tech exposure capturing gains. Monitor NVDA resistance at $880 and META at $530 for potential profit-taking.',
    dataSources: ['Portfolio Analysis', 'Latest 15 News', 'Market Signals', 'Technical Indicators'],
    suggestedActions: [
        { icon: '🔔', title: 'Set Alert', detail: 'NVDA $880', action: 'setAlert' },
        { icon: '⚖️', title: 'Review Risk', detail: 'Concentration Check', action: 'reviewRisk' },
        { icon: '📅', title: 'Check Calendar', detail: '3 Events This Week', action: 'viewCalendar' }
    ]
};

// V13 Market Drivers Visual
let marketDrivers = [
    { factor: 'Technical', contribution: 40, color: '#1F40AF' },
    { factor: 'Sentiment', contribution: 35, color: '#8B5CF6' },
    { factor: 'News', contribution: 20, color: '#F59E0B' },
    { factor: 'Macro', contribution: 5, color: '#10B981' }
];

let appData = {
    // Enhanced with 60 data points for smoother graphs
    portfolioSparkline: [125000, 125150, 125300, 125400, 125550, 125700, 125800, 125950, 126100, 126200, 126100, 126250, 126400, 126500, 126650, 126800, 126900, 127050, 127200, 127150, 127100, 127250, 127400, 127550, 127600, 127750, 127800, 127650, 127500, 127650, 127700, 127850, 127900, 128050, 128100, 127950, 127800, 127650, 127600, 127450, 127400, 127250, 127200, 127050, 127000, 126850, 126800, 126950, 127100, 127250, 127500, 127650, 127800, 127950, 128000, 128150, 128200, 128050, 127900, 127456],
    forecastProjection: [127456, 127650, 127850, 128100, 128350, 128600, 128800, 129000, 129250, 129500, 129700, 129900, 130100, 130300, 130500, 130700, 130900, 131100, 131300, 131500, 131700, 131900, 132100, 132300, 132500, 132700, 132900, 133100, 133300, 134200],
    // Enhanced with 60 data points for ultra-smooth sparklines
    stockSparklines: {
        NVDA: [820, 822, 825, 828, 830, 832, 835, 837, 840, 842, 845, 847, 850, 852, 855, 857, 860, 862, 865, 867, 870, 870.5, 871, 871.5, 872, 872.5, 873, 873.5, 874, 874.5, 875, 875.5, 876, 876.5, 877, 877.5, 878, 878.5, 879, 879.5, 880, 879.5, 879, 878.5, 878, 877.5, 877, 876.5, 876, 875.5, 875, 874.5, 874, 873.5, 873, 873.5, 874, 874.5, 875, 875.60],
        META: [500, 501, 502, 503, 505, 506, 508, 509, 510, 511, 512, 513, 515, 516, 518, 519, 520, 521, 522, 522.5, 523, 523.5, 524, 524.5, 525, 525.5, 524.5, 524, 523.5, 523, 522.5, 522, 521.5, 521, 520.5, 520, 519.5, 519, 520, 520.5, 521, 521.5, 522, 522.5, 523, 523.5, 524, 524.5, 525, 525.5, 524.5, 524, 523.5, 523, 522.5, 522, 522.5, 523, 523.5, 523.45],
        AAPL: [175, 175.5, 176, 176.5, 177, 177.5, 178, 178.5, 179, 179.5, 178.5, 178, 177.5, 177, 176.5, 176, 177, 177.5, 178, 178.5, 179, 179.5, 180, 180.5, 179.5, 179, 178.5, 178, 177.5, 177, 176.5, 176, 177, 177.5, 178, 178.5, 179, 179.5, 178.5, 178, 177.5, 177, 176.5, 176, 177, 177.5, 178, 178.5, 179, 179.5, 178.5, 178, 177.5, 177, 178, 178.5, 179, 179.5, 178.5, 178.23],
        MSFT: [400, 401, 402, 403, 405, 406, 408, 409, 410, 411, 412, 413, 414, 415, 416, 415, 414, 413, 412, 411, 410, 411, 412, 413, 414, 415, 414, 413, 412, 411, 410, 411, 412, 413, 414, 415, 414, 413, 412, 411, 410, 411, 412, 413, 414, 415, 414, 413, 412, 411, 410, 411, 412, 413, 414, 415, 414, 413, 412, 412.89],
        GOOGL: [138, 138.5, 139, 139.5, 140, 140.5, 141, 141.5, 142, 141.5, 141, 140.5, 140, 139.5, 139, 140, 140.5, 141, 141.5, 142, 142.5, 143, 142.5, 142, 141.5, 141, 140.5, 140, 141, 141.5, 142, 142.5, 143, 143.5, 144, 143.5, 143, 142.5, 142, 141.5, 141, 142, 142.5, 143, 143.5, 144, 143.5, 143, 142.5, 142, 141.5, 141, 142, 142.5, 143, 142.5, 142, 141.5, 142, 142.78]
    },
    user: {
        name: 'Alex',
        avatar: '👤'
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
        content: 'Les signaux IA détectent un retour de confiance tech. Fed dovish + earnings beats = backdrop bullish modéré.',
        sentiment: 'bullish',
        timestamp: 'Updated 5 minutes ago'
    },
    alerts: [
        { type: 'opportunity', title: 'NVDA Signal Haussier Fort', confidence: 92, time: '2h ago', priority: 'high' },
        { type: 'news', title: 'Fed Minutes Publiés', confidence: 85, time: '4h ago', priority: 'medium' },
        { type: 'signal', title: 'Pattern Convergence Détecté', confidence: 78, time: '6h ago', priority: 'medium' }
    ],
    marketDrivers: [
        { factor: 'Technique', contribution: 40 },
        { factor: 'Sentiment', contribution: 35 },
        { factor: 'Nouvelles', contribution: 20 },
        { factor: 'Macro', contribution: 5 }
    ],
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
    clusterMap: [
        { name: 'NVDA', return: 12.5, risk: 25, group: 'High Growth' },
        { name: 'META', return: 8.2, risk: 18, group: 'High Growth' },
        { name: 'AAPL', return: 5.5, risk: 12, group: 'Stable' },
        { name: 'MSFT', return: 6.8, risk: 15, group: 'Stable' },
        { name: 'GOOGL', return: 4.2, risk: 14, group: 'Stable' },
        { name: 'AMZN', return: 3.8, risk: 16, group: 'Stable' },
        { name: 'TSLA', return: -2.3, risk: 28, group: 'High Growth' },
        { name: 'JNJ', return: 2.1, risk: 8, group: 'Defensive' },
        { name: 'PG', return: 1.8, risk: 7, group: 'Defensive' },
        { name: 'KO', return: 1.5, risk: 6, group: 'Defensive' },
        { name: 'WMT', return: 2.5, risk: 9, group: 'Defensive' },
        { name: 'XOM', return: 1.2, risk: 13, group: 'Energy' },
        { name: 'CVX', return: 0.8, risk: 12, group: 'Energy' },
        { name: 'BAC', return: 3.5, risk: 17, group: 'Finance' },
        { name: 'JPM', return: 4.1, risk: 16, group: 'Finance' }
    ],
    newsImpact: [
        { headline: 'Fed Signals Rate Cuts Q2', impact: 8.5, effect: '+3.2%', time: '2h ago', source: 'Reuters' },
        { headline: 'NVDA Earnings Beat Expectations', impact: 9.2, effect: '+5.1%', time: '4h ago', source: 'Bloomberg' },
        { headline: 'Tech Sector Volatility Spike', impact: 6.2, effect: '-2.3%', time: '6h ago', source: 'WSJ' },
        { headline: 'CPI Data Shows Inflation Cooling', impact: 7.8, effect: '+2.8%', time: '8h ago', source: 'CNBC' },
        { headline: 'China Economic Growth Slows', impact: 5.5, effect: '-1.5%', time: '10h ago', source: 'FT' },
        { headline: 'Oil Prices Decline on Supply', impact: 4.2, effect: '-0.8%', time: '12h ago', source: 'Reuters' },
        { headline: 'Apple Announces New Products', impact: 6.8, effect: '+1.2%', time: '14h ago', source: 'TechCrunch' },
        { headline: 'European Markets Rally', impact: 5.1, effect: '+0.9%', time: '16h ago', source: 'Bloomberg' },
        { headline: 'Jobless Claims Better Expected', impact: 6.5, effect: '+1.5%', time: '18h ago', source: 'CNBC' },
        { headline: 'Tesla Production Concerns', impact: 7.2, effect: '-3.1%', time: '20h ago', source: 'Reuters' }
    ],
    sectorPerformance: [
        { sector: 'Technology', change: 8.5, holdings: true, weight: 45 },
        { sector: 'Finance', change: 3.1, holdings: true, weight: 15 },
        { sector: 'Consumer', change: 2.8, holdings: true, weight: 20 },
        { sector: 'Industrials', change: 2.1, holdings: true, weight: 10 },
        { sector: 'Real Estate', change: 1.2, holdings: true, weight: 5 },
        { sector: 'Communications', change: 4.5, holdings: true, weight: 5 },
        { sector: 'Healthcare', change: 5.2, holdings: false, weight: 0 },
        { sector: 'Energy', change: 1.8, holdings: false, weight: 0 },
        { sector: 'Materials', change: -0.5, holdings: false, weight: 0 },
        { sector: 'Utilities', change: 0.8, holdings: false, weight: 0 },
        { sector: 'Discretionary', change: -1.2, holdings: false, weight: 0 }
    ],
    portfolioHealth: {
        overall: 83,
        suggestion: 'Diversifier Tech → Santé'
    },
    backtestResults: {
        sharpeRatio: 1.28,
        winRate: 72,
        maxDrawdown: -12.3,
        totalReturn: 28.5
    },
    opportunities: [
        { conviction: 'High', return: 12.3, confidence: 92 },
        { conviction: 'Medium', return: 5.8, confidence: 78 },
        { conviction: 'Exploratory', return: 2.1, confidence: 54 }
    ],
    topStocks: [
        { symbol: 'NVDA', price: 875.60, change: 8.5, forecast: '+12.3%', confidence: 92 },
        { symbol: 'META', price: 523.45, change: 5.2, forecast: '+8.1%', confidence: 85 },
        { symbol: 'AAPL', price: 178.23, change: 2.1, forecast: '+4.5%', confidence: 78 },
        { symbol: 'MSFT', price: 412.89, change: 1.8, forecast: '+3.2%', confidence: 75 },
        { symbol: 'GOOGL', price: 142.78, change: 1.5, forecast: '+2.8%', confidence: 70 },
        { symbol: 'AMZN', price: 187.45, change: 0.8, forecast: '+1.9%', confidence: 65 }
    ]
};
