// Service pour les stocks (Pilier 2)
import { apiGet } from '../api/client'
import type { ApiResponse } from '../types/common'
import type { StocksResponse } from '../types/stocks'

export async function fetchStockPrices(
  tickers: string[],
  range: string = '1y',
  interval: string = '1d'
): Promise<ApiResponse<StocksResponse>> {
  const query = tickers.map(t => `tickers=${encodeURIComponent(t)}`).join('&')
  const fullPath = `/stocks/prices?${query}&range=${range}&interval=${interval}`
  
  return apiGet<StocksResponse>(fullPath.replace('/stocks', ''))
}

export async function fetchStockFundamentals(ticker: string): Promise<ApiResponse<any>> {
  return apiGet<any>(`/stocks/fundamentals/${ticker}`)
}
