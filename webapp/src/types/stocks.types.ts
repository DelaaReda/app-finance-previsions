// Types pour le pilier Actions (yfinance, indicateurs techniques)

import { Source, ScoreBreakdown } from './common.types'

export type Stock = {
  ticker: string
  name: string
  sector: string
  industry?: string
  price: number
  previousClose: number
  change: number
  changePercent: number
  volume: number
  marketCap?: number
  lastUpdate: string
}

export type TechnicalIndicators = {
  ticker: string
  sma20: number
  sma50: number
  sma200: number
  rsi: number
  macd: {
    value: number
    signal: number
    histogram: number
  }
  bollingerBands: {
    upper: number
    middle: number
    lower: number
  }
}
export type StockAnalysis = {
  stock: Stock
  technicals: TechnicalIndicators
  score: ScoreBreakdown
  signals: StockSignal[]
  priceHistory: PricePoint[]
  levels: PriceLevels
  lastUpdate: string
}

export type StockSignal = {
  type: 'buy' | 'sell' | 'hold'
  indicator: string // Ex: "RSI", "SMA_Cross", "MACD"
  strength: number // 0-100
  description: string
  timestamp: string
}

export type PricePoint = {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type PriceLevels = {
  support: number[]
  resistance: number[]
}

export type Watchlist = {
  id: string
  name: string
  tickers: string[]
  createdAt: string
  updatedAt: string
}
