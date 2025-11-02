// webapp/src/types/common.types.ts
export interface ApiResponse<T> {
  ok: boolean
  data?: T
  error?: string
}

export interface TimeSeriesPoint {
  timestamp: number
  value: number
}

export interface DataSource {
  name: string
  url?: string
  timestamp: string
}

export interface Signal {
  ticker: string
  type: 'opportunity' | 'risk'
  score: number
  reason: string
  sources: DataSource[]
  // Optional fields used by some UI components
  composite_score?: number
  confidence?: number
  description?: string
  title?: string
}

export interface CompositeScore {
  ticker: string
  macro_score: number
  technical_score: number
  news_score: number
  final_score: number
  weights: {
    macro: number
    technical: number
    news: number
  }
}
