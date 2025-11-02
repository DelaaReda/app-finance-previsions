// webapp/src/services/stocks.service.ts
import { apiGet } from '../api/client'
import type { StockPriceData, TickerDetail, Universe } from '../types/stocks.types'

// Define additional types for search and analysis
type StockSearchResult = {
  ticker: string
  name: string
  changePercent: number
  change: number
}

type StockAnalysis = {
  stock: {
    ticker: string
    name: string
    price: number
    change: number
    changePercent: number
    sector: string
    volume: number
  }
  score: {
    macro: number
    technical: number
    news: number
    composite: number
  }
  technicals: {
    sma20: number
    sma50: number
    sma200: number
    rsi: number
  }
  signals: {
    type: 'buy' | 'sell' | 'hold'
    strength: number
    indicator: string
    description: string
  }[]
}

export const stocksService = {
  /**
   * Get stock prices with technical indicators (downsampled)
   */
  getPrices: async (ticker: string, interval = '1d', downsample = 1000) => {
    return apiGet<StockPriceData>('/stocks/prices', {
      ticker,
      interval,
      downsample: String(downsample)
    })
  },

  /**
   * Get list of tracked tickers
   */
  getUniverse: async () => {
    return apiGet<Universe>('/stocks/universe')
  },

  /**
   * Get detailed ticker sheet (prix + indicators + news)
   */
  getTickerDetail: async (ticker: string) => {
    return apiGet<TickerDetail>(`/stocks/${ticker}`)
  },

  /**
   * Search for stocks by ticker or name
   */
  search: async (query: string) => {
    // Since there's no search endpoint in the backend yet, return mock data for now
    const mockResults: StockSearchResult[] = [
      { ticker: 'AAPL', name: 'Apple Inc.', changePercent: 1.2, change: 0.85 },
      { ticker: 'MSFT', name: 'Microsoft Corp.', changePercent: -0.5, change: -0.32 },
      { ticker: 'GOOGL', name: 'Alphabet Inc.', changePercent: 0.8, change: 0.45 },
      { ticker: 'TSLA', name: 'Tesla Inc.', changePercent: 2.3, change: 1.25 },
      { ticker: 'AMZN', name: 'Amazon.com Inc.', changePercent: -0.2, change: -0.15 }
    ].filter(item => 
      item.ticker.toLowerCase().includes(query.toLowerCase()) || 
      item.name.toLowerCase().includes(query.toLowerCase())
    )
    return { ok: true, data: mockResults } as any
  },

  /**
   * Get analysis for a specific ticker
   */
  getAnalysis: async (ticker: string) => {
    // Since there's no analysis endpoint in the backend yet, return mock data for now
    const mockAnalysis: StockAnalysis = {
      stock: {
        ticker: ticker,
        name: ticker + ' Corp',
        price: 150.25,
        change: 1.25,
        changePercent: 0.84,
        sector: 'Technology',
        volume: 15000000
      },
      score: {
        macro: 32,
        technical: 35,
        news: 18,
        composite: 85
      },
      technicals: {
        sma20: 148.50,
        sma50: 145.20,
        sma200: 140.80,
        rsi: 62.5
      },
      signals: [
        { type: 'buy', strength: 85, indicator: 'RSI', description: 'RSI indicates bullish momentum' },
        { type: 'hold', strength: 70, indicator: 'SMA', description: 'Price above SMA20 but below SMA50' }
      ]
    }
    return { ok: true, data: mockAnalysis } as any
  }
}
