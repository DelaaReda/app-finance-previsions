// Types communs pour toute l'application

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string }

export type TimeHorizon = 'CT' | 'MT' | 'LT' // Court, Moyen, Long terme

export type Signal = {
  id: string
  type: 'bullish' | 'bearish' | 'neutral'
  title: string
  description: string
  score: number // 0-100
  horizon: TimeHorizon
  sources: Source[]
  timestamp: string
  ticker?: string
  category?: string
}

export type Source = {
  type: 'news' | 'macro' | 'technical' | 'fundamental'
  name: string
  url?: string
  date: string
  reliability?: number // 0-1
}

export type ScoreBreakdown = {
  macro: number    // 40%
  technical: number // 40%
  news: number     // 20%
  composite: number // Score final
}
