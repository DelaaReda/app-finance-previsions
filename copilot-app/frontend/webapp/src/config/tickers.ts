/**
 * Configuration centrale des tickers - Univers d'investissement complet
 * Catégories: Métaux précieux, Crypto, Tech, Indices, Commodités, International
 * 
 * Auteur: CLAUDE-CODE
 * Task: Diversification complète de l'univers des tickers
 */

export const TICKER_CATEGORIES = {
  // Métaux précieux & Mining
  PRECIOUS_METALS: [
    { ticker: 'GC=F', name: 'Gold Futures', category: 'Commodity' },
    { ticker: 'XAU', name: 'Gold Spot', category: 'Commodity' },
    { ticker: 'NGD', name: 'New Gold Inc', category: 'Mining' },
    { ticker: 'LG', name: 'Lahontan Gold', category: 'Mining' },
  ],

  // Crypto & Blockchain
  CRYPTO: [
    { ticker: 'BTC-USD', name: 'Bitcoin', category: 'Crypto' },
    { ticker: 'ETH-USD', name: 'Ethereum', category: 'Crypto' },
    { ticker: 'SOL-USD', name: 'Solana', category: 'Crypto' },
    { ticker: 'COIN', name: 'Coinbase', category: 'Crypto Exchange' },
    { ticker: 'HUT', name: 'Hut 8 Mining', category: 'Crypto Mining' },
  ],

  // Tech Giants (US)
  US_TECH: [
    { ticker: 'PLTR', name: 'Palantir', category: 'AI/Data' },
    { ticker: 'MSFT', name: 'Microsoft', category: 'Tech' },
    { ticker: 'AAPL', name: 'Apple', category: 'Tech' },
    { ticker: 'GOOGL', name: 'Alphabet', category: 'Tech' },
    { ticker: 'AMZN', name: 'Amazon', category: 'E-commerce/Cloud' },
    { ticker: 'NVDA', name: 'NVIDIA', category: 'Semiconductors' },
    { ticker: 'TSLA', name: 'Tesla', category: 'EV' },
    { ticker: 'META', name: 'Meta', category: 'Social Media' },
  ],

  // International
  INTERNATIONAL: [
    { ticker: 'BABA', name: 'Alibaba', category: 'China Tech' },
    { ticker: 'TSM', name: 'Taiwan Semiconductor', category: 'Taiwan Semis' },
    { ticker: 'SAP', name: 'SAP SE', category: 'Europe Tech' },
    { ticker: 'ASML', name: 'ASML Holding', category: 'Europe Semis' },
  ],

  // Indices
  INDICES: [
    { ticker: 'SPY', name: 'S&P 500 ETF', category: 'Index' },
    { ticker: '^GSPC', name: 'S&P 500', category: 'Index' },
    { ticker: 'QQQ', name: 'Nasdaq 100 ETF', category: 'Index' },
    { ticker: '^VIX', name: 'VIX Volatility', category: 'Volatility' },
  ],

  // Autres secteurs stratégiques
  OTHER_SECTORS: [
    { ticker: 'JPM', name: 'JPMorgan Chase', category: 'Banking' },
    { ticker: 'V', name: 'Visa', category: 'Payments' },
    { ticker: 'JNJ', name: 'Johnson & Johnson', category: 'Healthcare' },
    { ticker: 'XOM', name: 'Exxon Mobil', category: 'Energy' },
    { ticker: 'DIS', name: 'Disney', category: 'Entertainment' },
  ],
} as const;

// Liste complète (flat array)
export const ALL_TICKERS = [
  ...TICKER_CATEGORIES.PRECIOUS_METALS,
  ...TICKER_CATEGORIES.CRYPTO,
  ...TICKER_CATEGORIES.US_TECH,
  ...TICKER_CATEGORIES.INTERNATIONAL,
  ...TICKER_CATEGORIES.INDICES,
  ...TICKER_CATEGORIES.OTHER_SECTORS,
];

// Liste de tickers par défaut pour le Dashboard (prioritaires)
export const DEFAULT_DASHBOARD_TICKERS = [
  'BTC-USD', 'ETH-USD', 'SOL-USD',  // Crypto
  'GC=F', 'XAU', 'NGD', 'LG',       // Gold
  'PLTR', 'MSFT', 'AAPL', 'NVDA',   // Tech
  'BABA', 'COIN',                    // International + Crypto
  'SPY', 'QQQ', '^VIX',              // Indices
  'AMZN', 'GOOGL', 'TSLA',           // Mega caps
  'HUT',                              // Mining crypto
];

// Watchlist par catégorie
export const WATCHLISTS = {
  'Crypto & Blockchain': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'COIN', 'HUT'],
  'Gold & Precious Metals': ['GC=F', 'XAU', 'NGD', 'LG'],
  'AI & Data': ['PLTR', 'NVDA', 'GOOGL', 'MSFT'],
  'International': ['BABA', 'TSM', 'SAP', 'ASML'],
  'Market Indices': ['SPY', 'QQQ', '^VIX', '^GSPC'],
} as const;

// Helper pour obtenir le nom d'un ticker
export function getTickerName(ticker: string): string {
  const found = ALL_TICKERS.find(t => t.ticker === ticker);
  return found?.name || ticker;
}

// Helper pour obtenir la catégorie
export function getTickerCategory(ticker: string): string {
  const found = ALL_TICKERS.find(t => t.ticker === ticker);
  return found?.category || 'Other';
}

// Type helpers
export type TickerSymbol = typeof ALL_TICKERS[number]['ticker'];
export type WatchlistName = keyof typeof WATCHLISTS;
