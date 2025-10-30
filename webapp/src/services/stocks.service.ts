// webapp/src/services/stocks.service.ts
import { apiGet } from '../api/client'
import type { StockPriceData, TickerDetail, Universe } from '../types/stocks.types'

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
  }
}
