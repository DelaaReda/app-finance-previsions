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

export interface CompositeComponentScores {
  macro?: {
    macro_score?: number
    inflation_score?: number
    yield_score?: number
    unemployment_score?: number
    recession_score?: number
    [key: string]: unknown
  }
  technical?: {
    technical_score?: number
    trend_score?: number
    rsi_score?: number
    current_price?: number
    sma20?: number
    sma50?: number
    rsi?: number
    [key: string]: unknown
  }
  news?: {
    news_score?: number
    avg_sentiment?: number
    news_count?: number
    recent_count?: number
    [key: string]: unknown
  }
}

export interface CompositeSignal {
  ticker: string
  composite_score?: number
  final_score?: number
  macro_score?: number
  technical_score?: number
  news_score?: number
  weights?: {
    macro: number
    technical: number
    news: number
  }
  timestamp?: string
  components?: CompositeComponentScores
  // Optional descriptive fields that may be supplied by other APIs
  reason?: string
  description?: string
  confidence?: number
  score?: number
  type?: 'opportunity' | 'risk'
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
