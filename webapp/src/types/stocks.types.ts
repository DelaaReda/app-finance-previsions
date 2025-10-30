/**
 * Types pour le Pilier 2: ACTIONS
 * yfinance, SMA/RSI/MACD, comparaisons secteurs
 */

import { Source, ScoreBreakdown } from './common.types'

export type StockPrice = {
  ticker: string
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  adj_close?: number
}

export type TechnicalIndicators = {
  ticker: string
  timestamp: string
  sma_20?: number
  sma_50?: number
  sma_200?: number
  rsi?: number
  macd?: number
  macd_signal?: number
  macd_histogram?: number
  bollinger_upper?: number
  bollinger_lower?: number
  bollinger_middle?: number
}

export type StockAnalysis = {
  ticker: string
  name: string
  sector: string
  current_price: number
  change_pct: number
  volume: number
  technical: TechnicalIndicators
  score: ScoreBreakdown
  signals: string[]
  alerts: StockAlert[]
  sources: Source[]
  last_updated: string
}

export type StockAlert = {
  type: 'sma_crossover' | 'rsi_overbought' | 'rsi_oversold' | 'volume_spike' | 'breakout' | 'breakdown'
  severity: 'info' | 'warning' | 'critical'
  message: string
  timestamp: string
  value?: number
}

export type SectorComparison = {
  sector: string
  tickers: string[]
  avg_return: number
  avg_score: number
  momentum: 'strong_up' | 'up' | 'neutral' | 'down' | 'strong_down'
  timestamp: string
}

export type TickerSheet = {
  ticker: string
  name: string
  sector: string
  price_history: StockPrice[]
  technical: TechnicalIndicators
  score: ScoreBreakdown
  related_news: any[] // NewsItem from news.types
  peers: string[]
  analysis_summary: string
  sources: Source[]
  last_updated: string
}
