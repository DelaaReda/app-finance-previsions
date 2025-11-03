// Types pour le brief et dashboard

// Updated to match actual backend response
export interface BriefData {
  top_signals: any[]
  top_risks: any[]
  picks: any[]
  sources: any[]
  generated_at: string
  period: string
  universe: string[]
}

// More detailed interface based on actual backend structure
export interface DetailedBriefData {
  top_signals: Array<{
    ticker: string
    composite_score: number
    macro_score: number
    technical_score: number
    news_score: number
    reason: string
    confidence: number
  }>
  top_risks: Array<{
    ticker: string
    composite_score: number
    macro_score: number
    technical_score: number
    news_score: number
    reason: string
  }>
  picks: Array<{
    ticker: string
    composite_score: number
    action: 'BUY' | 'HOLD' | 'SELL'
    price: number | null
    targets: {
      support: number | null
      resistance: number | null
    }
  }>
  sources: Array<{
    type: string
    [key: string]: any
  }>
  generated_at: string
  period: string
  universe: string[]
}
