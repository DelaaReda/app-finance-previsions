/**
 * Types communs utilisés à travers l'application
 * Basé sur la VISION: Traçabilité (sources, dates, versions)
 */

export type Source = {
  name: string
  url?: string
  timestamp: string
  version?: string
}

export type Signal = {
  id: string
  type: 'opportunity' | 'risk'
  title: string
  description: string
  score: number
  horizon: 'CT' | 'MT' | 'LT' // Court, Moyen, Long terme
  sources: Source[]
  tickers?: string[]
  category: string
  timestamp: string
}

export type Horizon = 'CT' | 'MT' | 'LT' | 'ALL'

export type ScoreBreakdown = {
  macro: number      // 40%
  technical: number  // 40%
  news: number       // 20%
  composite: number  // Score final
}

export type ApiResponse<T> = {
  ok: true
  data: T
} | {
  ok: false
  error: string
}
