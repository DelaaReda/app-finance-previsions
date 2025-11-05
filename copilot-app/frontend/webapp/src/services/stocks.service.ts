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
    // Use the actual API endpoint for ticker sheet data, then transform to match expected format
    const response = await apiGet<any>(`/stocks/${ticker}`)
    
    if (!response.ok) {
      return response
    }
    
    // Transform the API response to match the expected StockAnalysis format
    const apiData = response.data
    
    const transformedAnalysis: StockAnalysis = {
      stock: {
        ticker: apiData.ticker || ticker,
        name: apiData.company_name || ticker + ' Corp',
        price: apiData.current_price || 0,
        change: apiData.price_change || 0,
        changePercent: apiData.price_change_pct || 0,
        sector: apiData.fundamentals?.sector || 'N/A',
        volume: apiData.fundamentals?.volume || 0
      },
      score: {
        macro: apiData.score_breakdown?.macro || 0,
        technical: apiData.score_breakdown?.technical || 0,
        news: apiData.score_breakdown?.news || 0,
        composite: apiData.composite_score || 0
      },
      technicals: {
        sma20: apiData.technical_indicators?.sma20 ?? null,
        sma50: apiData.technical_indicators?.sma50 ?? null,
        sma200: apiData.technical_indicators?.sma200 ?? null,
        rsi: apiData.technical_indicators?.rsi ?? null
      },
      signals: apiData.alerts || [] // Assuming alerts can be used as signals, or use a different field
    }
    
    // Ensure signals is an array to prevent .map errors
    if (!transformedAnalysis.signals || !Array.isArray(transformedAnalysis.signals)) {
      transformedAnalysis.signals = []
    }
    
    return { ok: true, data: transformedAnalysis }
  }
}
