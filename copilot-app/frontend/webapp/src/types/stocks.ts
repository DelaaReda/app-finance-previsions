// Types pour les stocks (Pilier 2)
import { OHLCVPoint } from './common'

export interface StockIndicators {
  rsi: number | null
  sma_20: number | null
  sma_50: number | null
  macd: number | null
  macd_signal: number | null
}

export interface StockData {
  prices: OHLCVPoint[]
  indicators: StockIndicators
  last_price: number | null
  source: string
  generated_at: string
}

export interface StocksResponse {
  [ticker: string]: StockData | null
}
