// webapp/src/types/stocks.types.ts
import { TimeSeriesPoint } from './common.types'

export interface StockPriceData {
  ticker: string
  interval: string
  points: TimeSeriesPoint[]
  count: number
  source: string
  timestamp: string
}

export interface TechnicalIndicators {
  rsi: number | null
  sma20: number | null
  macd: number | null
}

export interface TickerDetail {
  ticker: string
  last_price: number | null
  date: string | null
  indicators: TechnicalIndicators
  news_count: number
}

export interface Universe {
  tickers: string[]
  count: number
}
